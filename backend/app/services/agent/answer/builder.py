# agent/answer/builder.py

from typing import Any, Callable, Dict, List, Optional

from app.schemas import AgentAnswer, AgentComponent, AgentSource, ParsedQuery
from .explanation import ExplanationGenerator, build_explanation
from .warnings import (
    build_scenario_warnings,
    evaluate_parameter_rules,
    filter_by_intent,
    group_warnings,
)
from .reviewer import auto_review
from ..tools.stock_filters import passes_stock_filter
from .status import (
    determine_status,
    build_recommendations,
    expert_review_id,
    _request_present,
    STATUS_EXPERT,
    STATUS_UNCLEAR,
)


class AnswerBuilder:
    """Сборщик структурированного ответа"""

    # Жёсткий кап на «несмысловые» (не защищённые фильтром/вердиктом) строки
    MAX_COMPONENTS = 10

    # Марки стали для подбора ADD_COMPONENT (по приоритету узнавания в имени).
    STEEL_GRADES = ("13ХФА", "09Г2С", "09ГСФ", "09ГС", "12Х1МФ", "10", "20")

    def __init__(self, generator: Optional[Callable[[Dict[str, Any]], Optional[str]]] = None):
        """generator — LLM-генератор объяснения (5A.3); None → default_generator."""
        self._explanations = ExplanationGenerator(generator)

    def build(
        self,
        parsed: ParsedQuery,
        intent: str,
        result: Dict[str, Any]
    ) -> AgentAnswer:
        scenario_warnings = build_scenario_warnings(parsed, intent)
        rule_warnings, rule_recommendations = evaluate_parameter_rules(parsed)

        raw_components = result.get("components", [])
        components = self._to_components(raw_components, parsed=parsed, intent=intent)
        sources = self._to_sources(result.get("sources", []))
        tools_used = list(dict.fromkeys(result.get("tools_used", [])))
        purchase_recommendation = (
            result.get("purchase_recommendation")
            or self._purchase_recommendation(raw_components)
        )

        warnings = list(dict.fromkeys(filter_by_intent(
            list(result.get("warnings", [])) + scenario_warnings + rule_warnings,
            intent,
        )))
        warning_categories = group_warnings(warnings)
        missing = list(dict.fromkeys(result.get("missing", [])))

        status = determine_status(
            components,
            warnings,
            errors=result.get("errors"),
            has_request=_request_present(parsed),
            parsed=parsed,
            intent=intent,
        )
        review = bool(result.get("review")) or status == STATUS_EXPERT
        mode = result.get("mode", "offline_rules")
        recommendations = build_recommendations(status, warnings, missing) + rule_recommendations

        explanation = self._explanations.generate(
            status=status,
            query=parsed.original_query,
            mode=mode,
            parsed=parsed,
            components=components,
            warnings=warnings,
            errors=result.get("errors"),
            recommendations=recommendations,
        )
        # LLM/refine final text (head_answer) — осмысленный пользовательский
        # текст; подставляем его в explanation, если генератор его не дал.
        head_answer = (result.get("answer") or "").strip()
        if not explanation and head_answer:
            explanation = head_answer
        llm_text = explanation or head_answer
        if not explanation and intent in ("inventory", "calculate"):
            explanation = self._inventory_explanation(
                components, purchase_recommendation, parsed
            ) or ""
        if not explanation:
            explanation = result.get("normative_detail") or ""
        if not explanation:
            explanation = self._template_explanation(status, components) or ""

        # «Попробовать LLM-режим?» — только когда LLM/refine не дали текста
        # (иначе в auto с успешным LLM-прогоном подсказка вводит в заблуждение).
        # Шаблонная/детерминированная сводка сама по себе подсказку не снимает.
        if (
            mode != "llm"
            and not llm_text
            and status in (STATUS_UNCLEAR, STATUS_EXPERT)
        ):
            recommendations.append(
                "Не удалось однозначно обработать запрос. Попробовать LLM-режим?"
            )

        verdict, review_issues = auto_review(result, tools_used, sources, explanation or "")

        return AgentAnswer(
            query=parsed.original_query,
            intent=intent,
            intent_label=self._intent_label(intent),
            route="agent",
            mode=result.get("mode", "offline_rules"),
            tools_used=tools_used,
            explanation=explanation,
            components=components,
            warnings=warnings,
            warning_categories=warning_categories,
            purchase_recommendation=purchase_recommendation,
            sources=sources,
            missing_parameters=missing,
            human_review_required=review,
            human_review_reasons=["expert_data"] if review else [],
            status=status,
            recommendations=recommendations,
            expert_review_id=expert_review_id() if status == STATUS_EXPERT else None,
            parsed_confidence=parsed.confidence,
            parsed_query=parsed,
            review_verdict=verdict,
            review_issues=review_issues,
        )

    def _to_components(self, rows: List[Dict], parsed=None, intent: str = None) -> List[AgentComponent]:
        out_of_stock = False
        if parsed:
            intents = getattr(parsed, "intents", []) or []
            out_of_stock = (
                "LIST_OUT_OF_STOCK" in intents
                or getattr(parsed, "on_stock", None) is False
            )
        has_stock_filter = _has_stock_filters(parsed)

        # Скоуп заявки (F1): инвентарный запрос по участку считает установленные
        # компоненты (unit_id), а не все кандидаты каталога. Когда в результате
        # есть установленные позиции, каталоговые строки без unit_id (остатки
        # склада вне участка) в заявку не попадают.
        unit_scope_inventory = (
            intent in ("inventory", "calculate")
            and any(isinstance(r, dict) and r.get("unit_id") for r in rows)
        )
        if unit_scope_inventory:
            rows = [
                r for r in rows
                if (isinstance(r, dict)
                    and (r.get("unit_id") or r.get("_context_only")
                         or self._is_analysis_row(r)))
            ]

        scored = [
            r for r in rows
            if isinstance(r, dict) and r.get("match_score") is not None
            and not r.get("unit_id")
        ]
        aux = [
            r for r in rows
            if isinstance(r, dict)
            and (r.get("match_score") is None or r.get("unit_id"))
        ]

        # Аналитические/verdict-строки (sufficiency/inventory/план) всегда
        # сохраняем в ответе — они отвечают на запрос «хватает ли».
        verdict_aux = [r for r in aux if self._is_analysis_row(r)]
        # «Общие» aux-строки — без привязки к участку. Установленные
        # компоненты (unit_id) обрабатываются только unit_aux, иначе строки,
        # не прошедшие _matches_geometry, просачивались бы в ответ повторно
        # (напр. переход с чужими диаметрами при выборе перехода 219→159).
        generic_aux = [
            r for r in aux
            if not self._is_analysis_row(r) and not r.get("unit_id")
        ]
        # ADD_COMPONENT: вместо «дампа» всех кандидатов каталога сужаем их
        # параметрами уже установленной детали того же типа на участке
        # (DN/PN/марка стали) — пользователь просил «подбери параметры».
        if intent == "object_configuration":
            generic_aux = self._narrow_add_component(generic_aux, aux)

        unit_aux = [r for r in aux if r.get("unit_id")]
        unit_aux = [r for r in unit_aux if self._matches_geometry(r, parsed)]

        if out_of_stock:
            scored = [
                r for r in scored
                if not r.get("quantity") or r.get("quantity", 0) == 0
            ]
            # Установленные компоненты/прочие aux-строки с реальным остатком
            # тоже не должны утекать в ответ «нет на складе» (F1: unit_rows
            # теперь несут фактический остаток).
            unit_aux = [
                r for r in unit_aux
                if not r.get("quantity") or r.get("quantity", 0) == 0
            ]
            generic_aux = [
                r for r in generic_aux
                if not r.get("quantity") or r.get("quantity", 0) == 0
            ]
            # Аналитические/verdict-строки с фактическим остатком (напр. unit-строки,
            # чей detail содержит «остаток: N») тоже не должны утекать в ответ
            # «нет на складе» — контекст с положительным остатком здесь неуместен.
            verdict_aux = [
                r for r in verdict_aux
                if r.get("quantity") is None or r.get("quantity", 0) == 0
            ]
            rows = scored + verdict_aux + unit_aux + generic_aux
        elif has_stock_filter:
            # Порог остатка (quantity_min/max) применяем к ФАКТИЧЕСКОМУ остатку,
            # который в строках-кандидатах уже проставлен мержем склада.
            # Строки без известного остатка (quantity=None) — это каталог/вердикты,
            # их оставляем как вспомогательные; строки с остатком фильтруем по
            # порогу, а прошедшие сортируем по остатку (убыв.).
            verdict_aux = [
                r for r in self._iter_rows(rows)
                if self._is_analysis_row(r) and (
                    r.get("quantity") is None
                    or passes_stock_filter(r.get("quantity"), parsed)
                )
            ]
            candidates = [
                r for r in self._iter_rows(rows)
                if not self._is_analysis_row(r)
                and r.get("quantity") is not None
                and passes_stock_filter(r.get("quantity"), parsed)
            ]
            candidates.sort(key=lambda r: r.get("quantity") or 0, reverse=True)
            rows = candidates + verdict_aux + unit_aux
        else:
            scored.sort(key=lambda r: r.get("match_percent") or 0.0, reverse=True)
            rows = (
                scored
                + verdict_aux
                + unit_aux
                + generic_aux
            )

        rows = self._apply_stock_filter(rows, parsed)
        rows = self._cap_components(rows, parsed)

        return [
            AgentComponent(
                mtr_code=r.get("mtr_code"),
                ksm_code=r.get("ksm_code"),
                name=r.get("name"),
                item_type=r.get("item_type"),
                quantity=r.get("quantity"),
                status=r.get("status"),
                detail=r.get("detail"),
                source_id=r.get("source_id"),
                unit_id=r.get("unit_id"),
                match_score=r.get("match_score"),
                match_percent=r.get("match_percent"),
                tz_status=r.get("tz_status"),
                matched_params=list(r.get("matched_params") or []),
                mismatched_params=list(r.get("mismatched_params") or []),
                missing_params=list(r.get("missing_params") or []),
            )
            for r in rows
        ]

    @staticmethod
    def _iter_rows(rows: List[Dict]) -> List[Dict]:
        return [r for r in rows if isinstance(r, dict)]

    @staticmethod
    def _matches_geometry(row: Dict, parsed: Any) -> bool:
        """Проверяет, совпадает ли строка графа с d1/d2 фильтрами запроса.

        Для переходов в name содержатся диаметры (76x4-57x3, 219x8-159x6).
        Если parsed содержит d1 или d2, строка должна их содержать.
        """
        if parsed is None:
            return True
        tf = getattr(parsed, "technical_filters", {}) or {}
        want_d1 = tf.get("d1")
        want_d2 = tf.get("d2")
        if not want_d1 and not want_d2:
            return True
        import re
        name = (row.get("name") or "").lower()
        nums = re.findall(r'\b(\d+)x(\d+)\b', name)
        if not nums:
            return True
        found_any = False
        for d1_str, d2_str in nums:
            d1, d2 = float(d1_str), float(d2_str)
            if want_d1 and abs(d1 - want_d1) <= want_d1 * 0.02:
                found_any = True
            if want_d2 and abs(d2 - want_d2) <= want_d2 * 0.02:
                found_any = True
        return found_any

    @staticmethod
    def _parse_component_params(row: Dict) -> tuple:
        """Извлекает (DN, PN, марка стали) из имени/обозначения детали."""
        import re

        name = str(row.get("name") or row.get("designation") or "")
        text = name.lower()
        dn = pn = None
        m_dn = re.search(r"\bdn\s*(\d{2,4})\b", text)
        if m_dn:
            dn = float(m_dn.group(1))
        m_pn = re.search(r"\bpn\s*(\d{2,4})\b", text)
        if m_pn:
            pn = float(m_pn.group(1))
        material = None
        for grade in AnswerBuilder.STEEL_GRADES:
            if grade.lower() in text:
                material = grade
                break
        return dn, pn, material

    @staticmethod
    def _narrow_add_component(candidates: List[Dict], rows: List[Dict]) -> List[Dict]:
        """Сужает кандидатов ADD_COMPONENT параметрами установленной детали того же типа.

        DN/PN/марка стали берутся из установленной детали участка (напр.
        «Задвижка клиновая DN150 PN40»). Для каждого типа оставляем только
        кандидатов с совпадающим DN/PN (допуск 2%), предпочтение — той же марке
        стали; итог не более 3 позиций на тип. Нет установленной детали типа или
        параметров — текущее поведение (группа как была).
        """
        if not candidates:
            return candidates
        installed = [r for r in rows if isinstance(r, dict) and r.get("unit_id")]
        by_type: Dict[str, List[Dict]] = {}
        for c in candidates:
            by_type.setdefault(((c.get("item_type") or "").lower()), []).append(c)

        narrowed: List[Dict] = []
        for item_type, group in by_type.items():
            inst = next(
                (r for r in installed if (r.get("item_type") or "").lower() == item_type),
                None,
            )
            if inst is None:
                narrowed.extend(group)
                continue
            want_dn, want_pn, want_material = AnswerBuilder._parse_component_params(inst)
            if want_dn is None and want_pn is None:
                narrowed.extend(group[:3])
                continue

            def _matches(c: Dict) -> bool:
                dn, pn, _ = AnswerBuilder._parse_component_params(c)
                if want_dn is not None and dn is not None and abs(dn - want_dn) > want_dn * 0.02:
                    return False
                if want_pn is not None and pn is not None and abs(pn - want_pn) > want_pn * 0.02:
                    return False
                return True

            def _dist(c: Dict) -> float:
                dn, pn, material = AnswerBuilder._parse_component_params(c)
                d = 0.0
                if want_dn is not None and dn is not None:
                    d += abs(dn - want_dn)
                if want_pn is not None and pn is not None:
                    d += abs(pn - want_pn) * 10.0
                if want_material and material == want_material:
                    d -= 50.0
                return d

            matched = [c for c in group if _matches(c)]
            if not matched:
                matched = list(group)
            matched.sort(key=_dist)
            narrowed.extend(matched[:3])
        return narrowed

    def _apply_stock_filter(self, rows: List[Dict], parsed: Any) -> List[Dict]:
        """Финальный фильтр кандидатов по порогам stock_filters (quantity_min/max).

        Аналитические/verdict-строки (sufficiency, inventory, планы) не фильтруются.
        Кандидаты с quantity=None (поиск по каталогу без склада) — без изменений.
        """
        if parsed is None:
            return rows
        result = []
        for r in rows:
            if self._is_analysis_row(r):
                result.append(r)
            else:
                qty = r.get("quantity")
                if qty is None or passes_stock_filter(qty, parsed):
                    result.append(r)
        return result

    def _cap_components(self, rows: List[Dict], parsed: Any) -> List[Dict]:
        """Умный лимит числа компонентов ответа.

        Срезаются только «несмысловые» строки (обычные кандидаты и прочая
        вспомогательная информация). Защищены от среза:
          - аналитические вердикты (sufficiency/дефицит/рекомендации),
          - позиции, отобранные явным фильтром запроса (порог остатка / on_stock):
            они уже прошли _apply_stock_filter, и их нельзя терять.
        Голый on_stock (True/False) снимает кап, только если флаг исходит из
        реального складского контекста: «есть» в «в схеме есть …» теперь не даёт
        on_stock (parser._extract_on_stock), поэтому позиции с остатком защищены
        только по-настоящему осмысленными запросами «что на складе / чего нет».
        Порядок: кандидаты (по match_percent убыв.) -> вспомогательные.
        """
        if parsed is None:
            return rows[: self.MAX_COMPONENTS]

        explicit_filter = _has_stock_filters(parsed) or (
            getattr(parsed, "on_stock", None) is not None
        ) or (
            "LIST_OUT_OF_STOCK" in (getattr(parsed, "intents", None) or [])
        )

        protected: List[Dict] = []
        plain: List[Dict] = []

        for r in self._iter_rows(rows):
            if self._is_analysis_row(r):
                protected.append(r)
            elif r.get("unit_id") and self._matches_geometry(r, parsed):
                protected.append(r)
            elif explicit_filter and r.get("quantity") is not None:
                # строка с фактическим остатком, прошедшая явный фильтр запроса
                protected.append(r)
            else:
                plain.append(r)

        # кандидаты (со скорингом) — раньше прочих, по релевантности убыв.
        plain.sort(key=lambda r: (0 if r.get("match_score") is not None else 1,
                                  -(r.get("match_score") or 0.0)))
        plain = plain[: self.MAX_COMPONENTS]

        return plain + protected

    @staticmethod
    def _is_analysis_row(row: Dict) -> bool:
        """Признак аналитической (verdict/план) строки, а не просто кандидата."""
        status = str(row.get("status") or "").lower()
        detail = str(row.get("detail") or "").lower()
        hay = f"{status} {detail}"
        return any(k in hay for k in (
            "хватает", "не хватает", "дефицит", "потребность",
            "критично", "рассчитан", "рекомендуется закуп",
            "дата", "план работ", "остаток", "нет позиций",
        ))
    
    def _purchase_recommendation(self, rows: List[Dict]) -> Optional[str]:
        """Итоговая сводка по закупке из компонентов inventory_calculator.

        Использует _urgency_score (1–5), выставленный inventory_calculator.
        """
        buckets: Dict[int, List[str]] = {5: [], 4: [], 3: [], 2: [], 1: []}
        for r in rows:
            if not isinstance(r, dict):
                continue
            score = r.get("_urgency_score")
            if not isinstance(score, int):
                continue
            item_type = r.get("item_type") or "?"
            if item_type not in buckets[score]:
                buckets[score].append(item_type)

        parts = []
        if buckets[5]:
            parts.append(f"{', '.join(sorted(set(buckets[5])))} — критически срочно")
        if buckets[4]:
            parts.append(f"{', '.join(sorted(set(buckets[4])))} — срочно")
        if buckets[3]:
            parts.append(f"{', '.join(sorted(set(buckets[3])))} — рекомендуется")
        if buckets[2] or buckets[1]:
            low = sorted(set(buckets[2] + buckets[1]))
            parts.append(f"{', '.join(low)} — можно позже")
        if not parts:
            return None
        return "Рекомендация по закупке: " + "; ".join(parts)

    def _to_sources(self, rows: List[Dict]) -> List[AgentSource]:        return [
            AgentSource(
                kind=r.get("kind"),
                id=r.get("id"),
                fragment=r.get("fragment"),
            )
            for r in rows
            if isinstance(r, dict)
        ]
    
    def _template_explanation(self, status: str, components: List) -> Optional[str]:
        """Шаблонное объяснение для штатных ответов (ЭТАП 5, 5A.3 template).

        Страховка, когда LLM-генератор не активирован. Если есть кандидаты —
        по лучшему из них (build_explanation по статусу и параметрам), иначе
        чистая строка по статусу.
        """
        scored = sorted(
            (c for c in components if c.match_percent is not None),
            key=lambda c: c.match_percent or 0,
            reverse=True,
        )
        top = scored[0] if scored else (components[0] if components else None)
        if top is not None:
            text = build_explanation(
                status,
                matched=top.matched_params or [],
                mismatched=top.mismatched_params or [],
                missing=top.missing_params or [],
            )
        else:
            text = build_explanation(status)
        if scored:
            count = len(scored)
            return f"Найдено {count} подходящих позиций. {text}"
        return text or None

    def _inventory_explanation(
        self,
        components: List,
        purchase_recommendation: Optional[str],
        parsed: Optional[Any],
    ) -> Optional[str]:
        """Детерминированная сводка для инвентарного / заявочного запроса (F4).

        Показывает заключение по остаткам (позиции ниже порога или отсутствие
        таких) вместо сухой строки нормативов/«базы данных».
        """
        rows = [c for c in components if getattr(c, "quantity", None) is not None]
        if not rows:
            return None

        threshold = None
        if parsed is not None:
            stock_filters = getattr(parsed, "stock_filters", None) or {}
            threshold = stock_filters.get("quantity_max")

        # Строка-вердикт «нет позиций ниже порога» (quantity=0) — не позиция.
        real = [
            c for c in rows
            if "нет позиций" not in (getattr(c, "status", "") or "").lower()
        ]

        parts = []
        if threshold is not None:
            if real:
                below = [
                    c for c in real if (c.quantity or 0) < threshold
                ]
                if below:
                    names = ", ".join(
                        dict.fromkeys(str(c.name or c.ksm_code or c.item_type or "?") for c in below)
                    )
                    parts.append(
                        f"Ниже порога остатка (≤{threshold}) — {len(below)} позиций: {names}."
                    )
                else:
                    parts.append(
                        f"Позиций с остатком ниже порога (≤{threshold}) нет — заявка не требуется."
                    )
            else:
                parts.append(
                    f"Позиций с остатком ниже порога (≤{threshold}) нет — заявка не требуется."
                )
        parts.append(
            f"Проверены остатки по {len(real) if real else len(rows)} позициям складского учёта."
        )
        if purchase_recommendation:
            parts.append(purchase_recommendation)
        return " ".join(p for p in parts if p)

    def _intent_label(self, intent: str) -> str:
        labels = {
            "search": "Поиск по каталогу",
            "catalog_search": "поиск по каталогу",
            "replacement": "Подбор замены",
            "inventory": "Склад и запас",
            "maintenance": "План ТОиР",
            "object_configuration": "Сборка участка",
            "document_search": "Поиск документов",
            "impact_analysis": "Анализ влияния",
            "equipment_guidance": "Справочная информация",
            "duplicates": "Проверка дублей",
        }
        return labels.get(intent, intent)


# Функция-обёртка для обратной совместимости
def _has_stock_filters(parsed: Any) -> bool:
    if parsed is None:
        return False
    filters = getattr(parsed, "stock_filters", None) or {}
    return filters.get("quantity_min") is not None or filters.get("quantity_max") is not None


def build_answer(parsed: ParsedQuery, intent: str, result: Dict[str, Any]) -> AgentAnswer:
    """Обёртка для сборки ответа"""
    builder = AnswerBuilder()
    return builder.build(parsed, intent, result)
