"""Фасад LLM-слоя: транспорт + извлечение карточки + парсинг запроса.

Публичный API сохранён для совместимости:
- `LLMService` наследует `LLMClient` (транспорт: llm/fallback_llm/invoke/
  structured_invoke, `_make_client` можно патчить в тестах);
- методы `parse_query`, `extract_card_from_text`, `generate_explanation`,
  `parse_engineering_query`, `validate_and_correct_query` делегируют
  в `CardExtractor` и `QueryParserLLM`.
"""

from typing import Any, Dict, Type

from app.schemas import ItemCard, ParsedQuery
from app.services.card_extractor import CardExtractor
from app.services.llm_client import LLMClient
from app.services.query_parser_llm import QueryParserLLM


class LLMService(LLMClient):
    """Сервис инженерного LLM: транспорт, извлечение карточек, парсинг запросов."""

    def __init__(self):
        super().__init__()
        self._card_extractor = CardExtractor(self)
        self._query_parser = QueryParserLLM(self)

    # ===== Извлечение карточек =====
    def extract_card_from_text(self, text: str, source: Dict[str, Any]) -> ItemCard:
        return self._card_extractor.extract_card_from_text(text, source)

    def generate_explanation(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return self._card_extractor.generate_explanation(result)

    # ===== Парсинг запроса =====
    def parse_query(self, query: str) -> ItemCard:
        return self._query_parser.parse_query(query)

    def parse_engineering_query(self, query: str) -> ParsedQuery:
        return self._query_parser.parse_engineering_query(query)

    def validate_and_correct_query(self, parsed: ParsedQuery) -> ParsedQuery:
        return self._query_parser.validate_and_correct_query(parsed)