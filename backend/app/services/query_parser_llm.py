"""LLM-парсинг и валидация инженерного запроса.

Методы перенесены из llm_service.py без изменения поведения.
"""

import json
import re
from typing import Any, Dict, Type

from app.schemas import ItemCard, ParsedQuery, Source
from app.services.card_extractor import CardExtractor
from app.services.llm_prompts import (
    ENTITY_EXTRACTION_PROMPT,
    QUERY_TO_CARD_PROMPT,
    QUERY_VALIDATION_PROMPT,
)
from app.services.query_normalizer import normalize_query


class QueryParserLLM:
    """LLM-парсинг запроса в ItemCard/ParsedQuery и LLM-коррекция парсинга."""

    def __init__(self, client) -> None:
        self.client = client

    def parse_query(self, query: str) -> ItemCard:
        if re.match(r'^[A-Z]{3}-[A-Z]{3}-[A-Z]{3}-\d{6}$', query.strip()):
            return ItemCard(
                item_type="",
                mtr_code=query.strip(),
                sources=[Source(type="user_query", fragment=query)]
            )
        normalized = normalize_query(query)
        prompt = QUERY_TO_CARD_PROMPT.format(query=normalized["normalized_text"])
        response = self.client.invoke(prompt).content
        return CardExtractor(self.client)._extract_card_from_response(
            response,
            {"type": "user_query", "text": query}
        )

    def parse_engineering_query(self, query: str) -> ParsedQuery:
        # 1. Быстрая проверка регуляркой (остается без изменений)
        if re.match(r"^[A-Z]{3}-[A-Z]{3}-[A-Z]{3}-\d{6}$", query.strip()):
            return ParsedQuery(
                original_query=query,
                operations=["find"],
                technical_filters={"mtr_code": query.strip()},
                confidence=1.0,
            )

        # 2. Привязываем схему ParsedQuery к модели: LangChain вернёт объект
        #    строго по схеме (вложенные Geometry, Pressure, Material внутри).
        try:
            prompt = ENTITY_EXTRACTION_PROMPT.format(query=query)
            parsed_result = self.client.structured_invoke(prompt, ParsedQuery)
            parsed_result.original_query = query
            return parsed_result
        except Exception as e:
            return ParsedQuery(
                original_query=query,
                ambiguities=[f"Ошибка структурирования: {str(e)}"],
                confidence=0.0,
            )

    def validate_and_correct_query(self, parsed: ParsedQuery) -> ParsedQuery:
        """Проверяет и исправляет результат гибридного парсинга с помощью LLM."""
        # Если confidence высокий и нет ambiguities — возвращаем как есть
        if parsed.confidence >= 0.8 and not parsed.ambiguities:
            return parsed

        prompt = QUERY_VALIDATION_PROMPT.format(
            original_query=parsed.original_query,
            parsed_json=parsed.model_dump_json(indent=2)
        )
        try:
            response = self.client.invoke(prompt).content
            data = json.loads(response)
            corrected = self._apply_llm_corrections(parsed, data)
            corrected.confidence = data.get("confidence", parsed.confidence)
            return corrected
        except Exception as e:
            # Если LLM упала — возвращаем исходный
            parsed.ambiguities.append(f"LLM проверка не удалась: {str(e)}")
            return parsed

    def _apply_llm_corrections(self, parsed: ParsedQuery, corrections: Dict) -> ParsedQuery:
        """Применяет исправления от LLM к ParsedQuery."""
        if corrections.get("operations"):
            parsed.operations = corrections["operations"]

        if corrections.get("card"):
            card_data = corrections["card"]
            if parsed.card:
                if card_data.get("item_type"):
                    parsed.card.item_type = card_data["item_type"]
                if card_data.get("subtype"):
                    parsed.card.subtype = card_data["subtype"]
                if card_data.get("designation"):
                    parsed.card.designation = card_data["designation"]
                if card_data.get("geometry"):
                    geo = card_data["geometry"]
                    if geo.get("dn"):
                        parsed.card.geometry.dn = geo["dn"]
                    if geo.get("wall_thickness"):
                        parsed.card.geometry.wall_thickness = geo["wall_thickness"]
                    if geo.get("angle"):
                        parsed.card.geometry.angle = geo["angle"]
                if card_data.get("pressure") and card_data["pressure"].get("pn"):
                    parsed.card.pressure.pn = card_data["pressure"]["pn"]
                if card_data.get("material"):
                    if card_data["material"].get("steel_grade"):
                        parsed.card.material.steel_grade = card_data["material"]["steel_grade"]
                    if card_data["material"].get("strength_class"):
                        parsed.card.material.strength_class = card_data["material"]["strength_class"]
                if card_data.get("environment"):
                    if card_data["environment"].get("medium"):
                        parsed.card.environment.medium = card_data["environment"]["medium"]
                    if card_data["environment"].get("h2s_confirmed") is not None:
                        parsed.card.environment.h2s_confirmed = card_data["environment"]["h2s_confirmed"]
                    if card_data["environment"].get("climate_version"):
                        parsed.card.environment.climate_version = card_data["environment"]["climate_version"]

        # Исправляем фильтры
        if corrections.get("filters"):
            parsed.technical_filters.update(corrections["filters"])

        # Исправляем контекст
        if corrections.get("context"):
            if corrections["context"].get("unit_id"):
                parsed.unit_context["unit_id"] = corrections["context"]["unit_id"]
                parsed.unit_ids.append(corrections["context"]["unit_id"])
            if corrections["context"].get("component_id"):
                parsed.component_context["component_id"] = corrections["context"]["component_id"]
                parsed.component_ids.append(corrections["context"]["component_id"])

        # Исправляем неоднозначности
        if corrections.get("ambiguities") is not None:
            parsed.ambiguities = corrections["ambiguities"]

        # Обновляем confidence_details
        parsed.confidence_details["llm_correction"] = corrections.get("confidence", 0.9)

        return parsed