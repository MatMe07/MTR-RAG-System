# query_parser/material_parser.py – полностью заменить файл

import re
from typing import Dict, Any

from .dictionaries import STEEL_GRADES, STRENGTH_CLASSES
from .normalizersPars import (
    normalize_steel,
    normalize_strength_class,
)


class MaterialParser:

    def parse(self, text: str) -> Dict[str, Any]:
        result = {
            "steel_grade": None,
            "strength_class": None,
            "standard": None,
        }

        normalized = text.upper()

        # ---------------------------------------------------------
        # 1. Проверяем замену: "стали 20 на 09Г2С" -> исходная сталь 20
        # ---------------------------------------------------------
        replacement_match = re.search(
            r'(?:из\s+)?стали?\s+([0-9а-яёa-z]+)\s+(?:на|в|вместо)\s+([0-9а-яёa-z]+)',
            normalized,
            re.IGNORECASE
        )
        if replacement_match:
            steel_from = replacement_match.group(1).upper()
            steel_to = replacement_match.group(2).upper()
            garbage_words = ["УЧАСТКЕ", "СКЛАДЕ", "НЕТ", "ЕСТЬ"]
            if steel_from not in garbage_words and steel_to not in garbage_words:
                result["steel_grade"] = steel_from  # исходная сталь
                return result

        # ---------------------------------------------------------
        # 2. Составные марки (09Г2С, 09ГСФ, 13ХФА)
        # ---------------------------------------------------------
        if result["steel_grade"] is None:
            composite_grades = [g for g in STEEL_GRADES if len(g) > 2]
            for steel in composite_grades:
                pattern = rf"(?<!\w){re.escape(steel)}(?!\w)"
                if re.search(pattern, normalized):
                    result["steel_grade"] = steel
                    break

        # ---------------------------------------------------------
        # 3. Простая сталь (сталь 20, сталь 45)
        # ---------------------------------------------------------
        if result["steel_grade"] is None:
            simple_match = re.search(
                r'(?:стал[иь])\s+(\d+)',
                normalized,
            )
            if simple_match:
                result["steel_grade"] = simple_match.group(1)

        # ---------------------------------------------------------
        # 4. Класс прочности
        # ---------------------------------------------------------
        for strength in STRENGTH_CLASSES:
            pattern = rf"(?<!\w){re.escape(strength)}(?!\w)"
            if re.search(pattern, normalized):
                result["strength_class"] = strength
                break

        # ---------------------------------------------------------
        # 5. ГОСТ/ТУ
        # ---------------------------------------------------------
        standard = re.search(
            r"\b(?:ГОСТ|ТУ)\s+[\d\-]+(?:\.[\d\-]+)?",
            normalized,
        )
        if standard:
            result["standard"] = standard.group(0)

        return result
