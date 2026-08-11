# backend/app/services/entity_extractor.py

from app.schemas import ParsedQuery
from backend.app.services.query_parser.hybrid_parser import HybridParser
from app.services.llm_service import LLMService


class EntityExtractor:
    def __init__(self):
        self.hybrid_parser = HybridParser()
        self.llm = LLMService()

    def extract(self, query: str) -> ParsedQuery:
        # 1. Гибридный парсинг (rule-based + Natasha)
        parsed = self.hybrid_parser.parse(query)
        
        # 2. Если результат не уверенный или есть неоднозначности
        #    — вызываем LLM для проверки и исправления
        if parsed.confidence < 0.8 or parsed.ambiguities:
            parsed = self.llm.validate_and_correct_query(parsed)
        
        return parsed


def get_entity_extractor() -> EntityExtractor:
    return EntityExtractor()
