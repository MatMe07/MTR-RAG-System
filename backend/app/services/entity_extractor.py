# backend/app/services/entity_extractor.py

from typing import Optional

from app.core.config import settings
from app.schemas import ParsedQuery
from app.services.query_parser.hybrid_parser import HybridParser
from app.services.llm_service import LLMService


class EntityExtractor:
    def __init__(self, llm: Optional[LLMService] = None):
        self.hybrid_parser = HybridParser()
        self.llm = llm or LLMService()

    def extract(self, query: str) -> ParsedQuery:
        # 1. Гибридный парсинг (rule-based + Natasha)
        parsed = self.hybrid_parser.parse(query)

        # 2. Если результат не уверенный или есть неоднозначности
        #    — вызываем LLM для проверки и исправления.
        #    AGENT_LLM_MODE=off полностью отключает LLM в агентном конвейере.
        if getattr(settings, "AGENT_LLM_MODE", "auto") == "off":
            return parsed
        if parsed.confidence >= 0.85 and not parsed.ambiguities:
            return parsed

        # Снапшот фактов rule-based парсера до LLM-коррекции.
        rule_ops = list(parsed.operations or [])
        rule_unit_ids = list(parsed.unit_ids or [])
        rule_component_ids = list(parsed.component_ids or [])
        rule_confidence = parsed.confidence

        try:
            result = self.llm.validate_and_correct_query(parsed)
        except Exception:
            return parsed
        if result is None:
            return parsed

        # 3. Защита от деградации: LLM не должен удалять факты, извлечённые
        #    детерминированным парсером (коды участков/компонентов, операции).
        if not result.unit_ids and rule_unit_ids:
            result.unit_ids = rule_unit_ids
        if not result.component_ids and rule_component_ids:
            result.component_ids = rule_component_ids
        result.operations = list(dict.fromkeys(rule_ops + list(result.operations or [])))
        result.confidence = max(result.confidence or 0.0, rule_confidence)
        return result


def get_entity_extractor() -> EntityExtractor:
    return EntityExtractor()
