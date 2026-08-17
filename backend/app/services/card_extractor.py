"""Извлечение ItemCard из текста (паспорт/запрос) и генерация объяснений.

Методы перенесены из llm_service.py без изменения поведения.
"""

import json
import re
from typing import Any, Dict

from app.schemas import (
    Coating,
    Environment,
    Extraction,
    Geometry,
    ItemCard,
    Material,
    Normative,
    Pressure,
    Source,
)
from app.services.llm_prompts import EXPLAIN_MATCH_PROMPT, PASSPORT_TO_CARD_PROMPT


class CardExtractor:
    """LLM-извлечение карточки из паспорта и генерация объяснения матчинга."""

    def __init__(self, client) -> None:
        self.client = client

    # ===== Извлечение карточки =====
    def extract_card_from_text(self, text: str, source: Dict[str, Any]) -> ItemCard:
        prompt = PASSPORT_TO_CARD_PROMPT.format(text=text[:4000])
        response = self.client.invoke(prompt).content
        return self._extract_card_from_response(response, source)

    def generate_explanation(self, result: Dict[str, Any]) -> Dict[str, Any]:
        prompt = EXPLAIN_MATCH_PROMPT.format(result=json.dumps(result, ensure_ascii=False))
        response = self.client.invoke(prompt).content
        return self._parse_explanation_response(response)

    def _extract_card_from_response(self, response: str, source: Dict[str, Any]) -> ItemCard:
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return self._empty_card(source)
            data = json.loads(json_match.group())
            source_copy = {k: v for k, v in source.items() if k != "type"}
            return ItemCard(
                card_id=None,
                mtr_code=None,
                ksm_code=None,
                item_type=data.get('item_type', ''),
                subtype=data.get('subtype'),
                designation=data.get('designation'),
                name=data.get('name'),
                geometry=Geometry(
                    dn=data.get('geometry', {}).get('dn'),
                    wall_thickness=data.get('geometry', {}).get('wall_thickness'),
                    angle=data.get('geometry', {}).get('angle')
                ),
                pressure=Pressure(
                    pn=data.get('pressure', {}).get('pn')
                ),
                material=Material(
                    steel_grade=data.get('material', {}).get('steel_grade'),
                    strength_class=data.get('material', {}).get('strength_class'),
                    standard=data.get('material', {}).get('standard')
                ),
                environment=Environment(
                    medium=data.get('environment', {}).get('medium'),
                    h2s_confirmed=data.get('environment', {}).get('h2s_confirmed'),
                    co2_confirmed=data.get('environment', {}).get('co2_confirmed'),
                    climate_version=data.get('environment', {}).get('climate_version')
                ),
                coating=Coating(
                    inner_coating=data.get('coating', {}).get('inner_coating'),
                    outer_coating=data.get('coating', {}).get('outer_coating')
                ),
                normative=Normative(
                    gost_tu=data.get('normative', {}).get('gost_tu')
                ),
                extraction=Extraction(
                    confidence=data.get('extraction', {}).get('confidence'),
                    method=data.get('extraction', {}).get('method') or "user_query",
                    missing_fields=data.get('extraction', {}).get('missing_fields', []),
                ),
                sources=[Source(type="LLM", **source_copy)]
            )
        except Exception:
            return self._empty_card(source)

    def _parse_explanation_response(self, response: str) -> Dict[str, Any]:
        fallback = {
            "summary": "Объяснение не сгенерировано.",
            "why_in_results": "",
            "matched": [],
            "warnings": [],
            "expert_next_steps": [],
            "source_note": ""
        }
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return fallback
            return json.loads(json_match.group())
        except Exception:
            fallback["summary"] = "Ошибка генерации объяснения."
            return fallback

    def _empty_card(self, source: Dict[str, Any]) -> ItemCard:
        source_copy = {k: v for k, v in source.items() if k != "type"}
        return ItemCard(
            card_id=None,
            mtr_code=None,
            ksm_code=None,
            item_type="",
            subtype=None,
            designation=None,
            name=None,
            geometry=Geometry(),
            pressure=Pressure(),
            material=Material(),
            environment=Environment(),
            coating=Coating(),
            normative=Normative(),
            sources=[Source(type="llm", **source_copy)]
        )