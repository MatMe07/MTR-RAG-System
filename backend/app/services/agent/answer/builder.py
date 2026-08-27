# agent/answer/builder.py

from typing import Any, Dict, List

from app.schemas import AgentAnswer, AgentComponent, AgentSource, ParsedQuery
from .warnings import build_scenario_warnings


class AnswerBuilder:
    """Сборщик структурированного ответа"""
    
    def build(
        self,
        parsed: ParsedQuery,
        intent: str,
        result: Dict[str, Any]
    ) -> AgentAnswer:
        answers = result.get("answers", [])
        if not answers:
            answers.append("Не удалось собрать ответ: недостаточно данных.")
        
        scenario_warnings = build_scenario_warnings(parsed, intent)
        
        components = self._to_components(result.get("components", []))
        sources = self._to_sources(result.get("sources", []))
        
        warnings = list(dict.fromkeys(
            list(result.get("warnings", [])) + scenario_warnings
        ))
        missing = list(dict.fromkeys(result.get("missing", [])))
        
        return AgentAnswer(
            query=parsed.original_query,
            intent=intent,
            intent_label=self._intent_label(intent),
            route="agent",
            mode=result.get("mode", "offline_rules"),
            tools_used=list(dict.fromkeys(result.get("tools_used", []))),
            answer="\n".join(answers),
            components=components,
            warnings=warnings,
            sources=sources,
            missing_parameters=missing,
            human_review_required=bool(result.get("review")),
            parsed_confidence=parsed.confidence,
            parsed_query=parsed,
        )
    
    def _to_components(self, rows: List[Dict]) -> List[AgentComponent]:
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
            )
            for r in rows
            if isinstance(r, dict)
        ]
    
    def _to_sources(self, rows: List[Dict]) -> List[AgentSource]:
        return [
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
