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
        components = self._to_components(raw_components, parsed=parsed)
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
        if mode != "llm" and status in (STATUS_UNCLEAR, STATUS_EXPERT):
            recommendations.append(
                "Не удалось однозначно обработать запрос. Попробовать LLM-режим?"
            )

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
        if not explanation:
            explanation = result.get("normative_detail") or ""
        if not explanation:
            explanation = self._template_explanation(status, components) or ""

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
            status=status,
            recommendations=recommendations,
            expert_review_id=expert_review_id() if status == STATUS_EXPERT else None,
            parsed_confidence=parsed.confidence,
            parsed_query=parsed,
            review_verdict=verdict,
            review_issues=review_issues,
        )

    def _to_components(self, rows: List[Dict], parsed=None) -> List[AgentComponent]:
        out_of_stock = False
        if parsed:
            intents = getattr(parsed, "intents", []) or []
            out_of_stock = (
                "LIST_OUT_OF_STOCK" in intents
                or getattr(parsed, "on_stock", None) is False
            )
        has_stock_filter = _has_stock_filters(parsed)

        scored = [
            r for r in rows
            if isinstance(r, dict) and r.get("match_score") is not None
        ]
        aux = [
            r for r in rows
            if isinstance(r, dict) and r.get("match_score") is None
        ]

        # Аналитические/verdict-строки (sufficiency/inventory/план) всегда
        # сохраняем в ответе — они отвечают на запрос «хватает ли».
        verdict_aux = [r for r in aux if self._is_analysis_row(r)]
        generic_aux = [r for r in aux if not self._is_analysis_row(r)]

        unit_aux = [r for r in aux if r.get("unit_id")]
        unit_aux = [r for r in unit_aux if self._matches_geometry(r, parsed)]

        if out_of_stock:
            scored = [
                r for r in scored
                if not r.get("quantity") or r.get("quantity", 0) == 0
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
        Порядок: кандидаты (по match_percent убыв.) -> вспомогательные.
        """
        if parsed is None:
            return rows[: self.MAX_COMPONENTS]

        explicit_filter = _has_stock_filters(parsed) or (
            getattr(parsed, "on_stock", None) is not None
        ) or ("LIST_OUT_OF_STOCK" in (getattr(parsed, "intents", None) or []))

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
            "дата", "план работ",
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
