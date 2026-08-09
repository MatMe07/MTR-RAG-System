# query_parser/context_parser.py

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class ContextReference:
    reference_type: str
    value: str
    raw_text: str


class ContextParser:

    COMPONENT_PATTERN = re.compile(
        r"\bCOMP-[A-Z0-9-]+\b",
        re.IGNORECASE,
    )

    UNIT_PATTERN = re.compile(
        r"\bUNIT-[A-Z0-9-]+\b",
        re.IGNORECASE,
    )

    def parse(self, text: str) -> Dict[str, Any]:
        """Возвращает словарь с контекстной информацией"""
        result = {
            "references": [],
            "quantity": None,
            "length_meters": None,
            "timeframe": None,
            "urgency": None,
        }
        
        text_lower = text.lower()
        references = []

        # Ссылки на компоненты
        for match in self.COMPONENT_PATTERN.finditer(text):
            references.append(
                ContextReference(
                    reference_type="component",
                    value=match.group(0).upper(),
                    raw_text=match.group(0),
                )
            )

        # Ссылки на участки
        for match in self.UNIT_PATTERN.finditer(text):
            references.append(
                ContextReference(
                    reference_type="unit",
                    value=match.group(0).upper(),
                    raw_text=match.group(0),
                )
            )

        result["references"] = references

        # Количество штук
        qty_match = re.search(r'(\d+)\s*(?:штук|шт|ед|штуки|штука)', text_lower)
        if qty_match:
            result["quantity"] = int(qty_match.group(1))

        # Длина в метрах
        length_match = re.search(r'(\d+)\s*(?:м|метр|метров|метра)', text_lower)
        if length_match:
            result["length_meters"] = float(length_match.group(1))

        # Временные рамки
        if re.search(r'следующ(?:ая|ей|ую)?\s*недел[ея]', text_lower):
            result["timeframe"] = "next_week"
        elif re.search(r'сегодня|сейчас', text_lower):
            result["timeframe"] = "immediate"

        # Срочность
        if re.search(r'срочн|важн|критич', text_lower):
            result["urgency"] = "high"

        # Имплицитные ссылки
        implicit_patterns = [
            "такой же", "такую же", "такая же",
            "аналог", "как у", "как на", "как в",
            "соседний", "соседние", "этой детали",
        ]
        for phrase in implicit_patterns:
            if phrase in text_lower:
                references.append(
                    ContextReference(
                        reference_type="implicit_reference",
                        value=phrase,
                        raw_text=phrase,
                    )
                )
                break

        return result

    def parse_references(self, text: str) -> List[ContextReference]:
        """Только ссылки (для обратной совместимости)"""
        return self.parse(text).get("references", [])
