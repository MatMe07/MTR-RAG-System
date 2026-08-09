# query_parser/material_parser.py

import re
from typing import Dict, Any

from .dictionaries import STEEL_GRADES, STRENGTH_CLASSES
from .normalizers import (
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
        # 0. Проверяем замену материала
        # ---------------------------------------------------------
        replacement_match = re.search(
            r'(?:из\s+)?стали?\s+([0-9а-яёa-z]+)\s+(?:на|в|вместо)\s+([0-9а-яёa-z]+)',
            normalized,
            re.IGNORECASE
        )
        if replacement_match:
            steel_from = replacement_match.group(1).upper()
            if steel_from not in ["УЧАСТКЕ", "СКЛАДЕ", "НЕТ", "ЕСТЬ"]:
                result["steel_grade"] = steel_from
                # Дальше не идём, т.к. это замена, а не поиск

        # ---------------------------------------------------------
        # 1. Простая сталь (сталь 20, сталь 45) – ИСПРАВЛЕНО
        # ---------------------------------------------------------
        if result["steel_grade"] is None:
            simple_match = re.search(
                r'(?:стал[иь])\s+(\d+)',
                normalized,
                re.IGNORECASE  # добавлено для надёжности
            )
            if simple_match:
                result["steel_grade"] = simple_match.group(1)

        # ---------------------------------------------------------
        # 2. Составные марки стали
        # ---------------------------------------------------------
        if result["steel_grade"] is None:
            composite_grades = [g for g in STEEL_GRADES if len(g) > 2]
            for steel in composite_grades:
                pattern = rf"(?<!\w){re.escape(steel)}(?!\w)"
                if re.search(pattern, normalized):
                    result["steel_grade"] = normalize_steel(steel)
                    break

        # ---------------------------------------------------------
        # 3. Класс прочности
        # ---------------------------------------------------------
        for strength in STRENGTH_CLASSES:
            pattern = rf"(?<!\w){re.escape(strength)}(?!\w)"
            if re.search(pattern, normalized):
                result["strength_class"] = normalize_strength_class(strength)
                break

        # ---------------------------------------------------------
        # 4. ГОСТ / ТУ
        # ---------------------------------------------------------
        standard = re.search(
            r"\b(?:ГОСТ|ТУ)\s+[\d\-]+(?:\.[\d\-]+)?",
            normalized,
        )
        if standard:
            result["standard"] = standard.group(0)

        return result
