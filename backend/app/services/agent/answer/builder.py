# agent/answer/builder.py

from typing import Any, Callable, Dict, List, Optional

from app.schemas import AgentAnswer, AgentComponent, AgentSource, ParsedQuery
from .explanation import ExplanationGenerator
from .warnings import build_scenario_warnings, evaluate_parameter_rules, group_warnings
from .reviewer import auto_review, _FALLBACK_ANSWER
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

    # Сколько топ-кандидатов со скорингом показывать в компонентах ответа
    CANDIDATE_TOP_N = 10
    # Лимит бескодовых (граф/склад/план) строк
    AUX_MAX = 25

    def __init__(self, generator: Optional[Callable[[Dict[str, Any]], Optional[str]]] = None):
        """generator — LLM-генератор объяснения (5A.3); None → default_generator."""
        self._explanations = ExplanationGenerator(generator)

    def build(
        self,
        parsed: ParsedQuery,
        intent: str,
        result: Dict[str, Any]
    ) -> AgentAnswer:
        answers = [a for a in (result.get("answers") or []) if a]
        head_answer = result.get("answer")
        if head_answer and head_answer not in answers:
            answers.insert(0, head_answer)
        if not answers:
            answers.append(_FALLBACK_ANSWER)
        answer_text = "\n".join(answers)

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

        warnings = list(dict.fromkeys(
            list(result.get("warnings", [])) + scenario_warnings + rule_warnings
        ))
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
        verdict, review_issues = auto_review(result, tools_used, sources, answer_text)
        recommendations = build_recommendations(status, warnings, missing) + rule_recommendations
        mode = result.get("mode", "offline_rules")
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

        return AgentAnswer(
            query=parsed.original_query,
            intent=intent,
            intent_label=self._intent_label(intent),
            route="agent",
            mode=result.get("mode", "offline_rules"),
            tools_used=tools_used,
            answer=answer_text,
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

        if out_of_stock:
            scored = [
                r for r in scored
                if not r.get("quantity") or r.get("quantity", 0) == 0
            ]
            rows = verdict_aux + generic_aux[: self.AUX_MAX] + scored[: self.CANDIDATE_TOP_N]
        else:
            scored.sort(key=lambda r: r.get("match_percent") or 0.0, reverse=True)
            rows = (
                scored[: self.CANDIDATE_TOP_N]
                + verdict_aux
                + generic_aux[: self.AUX_MAX]
            )

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
def build_answer(parsed: ParsedQuery, intent: str, result: Dict[str, Any]) -> AgentAnswer:
    """Обёртка для сборки ответа"""
    builder = AnswerBuilder()
    return builder.build(parsed, intent, result)
