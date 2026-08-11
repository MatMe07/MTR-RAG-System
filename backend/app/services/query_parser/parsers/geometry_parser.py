# query_parser/geometry_parser.py

import re
from typing import Dict, Any

from .normalizers.normalizers import normalize_decimal


class GeometryParser:

    def parse(self, text: str) -> Dict[str, Any]:
        result = {
            "dn": None,
            "d1": None,
            "d2": None,
            "wall_thickness": None,
            "wall_thickness_2": None,
            "angle": None,
            "radius": None,
        }

        normalized = text.lower()

        # ---------------------------------------------------------
        # 0. Определяем тип детали
        # ---------------------------------------------------------
        is_transition = bool(re.search(r"\bпереход(?:а|ом|е)?\b", normalized))
        is_tee = bool(re.search(r"\bтройник(?:а|у|ом|е|ов)?\b", normalized))
        is_elbow = bool(re.search(r"\bотвод(?:а|у|ом|е|ов)?|ог|окш\b", normalized))
        is_pipe = bool(re.search(r"\bтруб(?:а|ы|у|ой|е|ам)?\b", normalized))

        # ---------------------------------------------------------
        # 1. DN / Ду
        # ---------------------------------------------------------
        dn_patterns = [
            r"\bdn\s*[-:]?\s*(\d+(?:[.,]\d+)?)",
            r"\bду\s*[-:]?\s*(\d+(?:[.,]\d+)?)",
        ]
        for pattern in dn_patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                result["dn"] = normalize_decimal(match.group(1))
                break

        # ---------------------------------------------------------
        # 1.1 ДИАМЕТР
        # ---------------------------------------------------------
        if result["dn"] is None:
            diam_match = re.search(r'\bдиаметр(?:ом|е|а)?\s*(\d+(?:[.,]\d+)?)', normalized)
            if diam_match:
                result["dn"] = normalize_decimal(diam_match.group(1))

        # ---------------------------------------------------------
        # 1.2 "на X" как DN (если одно число и не переход/тройник)
        # ---------------------------------------------------------
        if not is_transition and not is_tee:
            single_on = re.search(r'\bна\s+(\d+(?:[.,]\d+)?)\b', normalized)
            if single_on and not re.search(r'\d+\s*на\s*\d+', normalized):
                if result["dn"] is None:
                    result["dn"] = normalize_decimal(single_on.group(1))

        # ---------------------------------------------------------
        # 2. Переход или тройник: "219 на 159" или "219х159"
        #    Для них d1 и d2, НЕ wall_thickness
        # ---------------------------------------------------------
        if is_transition or is_tee:
            size_match = re.search(
                r"(\d+(?:[.,]\d+)?)\s*(?:x|х|×|на)\s*(\d+(?:[.,]\d+)?)",
                normalized,
            )
            if size_match:
                result["d1"] = normalize_decimal(size_match.group(1))
                result["d2"] = normalize_decimal(size_match.group(2))
                if result["dn"] is None:
                    result["dn"] = result["d1"]
                # НЕ присваиваем wall_thickness для переходов и тройников

        # ---------------------------------------------------------
        # 3. Диаметр x толщина (только для труб и отводов)
        # ---------------------------------------------------------
        if is_pipe or is_elbow:
            diameter_wall = re.search(
                r"\b(\d+(?:[.,]\d+)?)\s*"
                r"(?:x|х|×|на)\s*"
                r"(\d+(?:[.,]\d+)?)\b",
                normalized,
            )
            if diameter_wall:
                first = normalize_decimal(diameter_wall.group(1))
                second = normalize_decimal(diameter_wall.group(2))
                if result["dn"] is None:
                    result["dn"] = first
                if result["wall_thickness"] is None:
                    result["wall_thickness"] = second

        # ---------------------------------------------------------
        # 3.1 Стенка (отдельное слово)
        # ---------------------------------------------------------
        wall_match = re.search(r'\bстенк(?:а|и|ой)\s*(\d+(?:[.,]\d+)?)', normalized)
        if wall_match:
            result["wall_thickness"] = normalize_decimal(wall_match.group(1))

        # ---------------------------------------------------------
        # 4. Угол
        # ---------------------------------------------------------
        angle_patterns = [
            r"\bугол(?:ом)?\s*(?:поворота\s*)?(\d+(?:[.,]\d+)?)",
            r"\b(\d+(?:[.,]\d+)?)\s*°",
        ]
        for pattern in angle_patterns:
            match = re.search(pattern, normalized)
            if match:
                result["angle"] = normalize_decimal(match.group(1))
                break

        # 4.1 "прямой угол" -> 90
        if result["angle"] is None and re.search(r'\bпрямой\s+угол\b', normalized):
            result["angle"] = 90.0

        # 4.2 слитные ОКШ90, ОГ90
        if result["angle"] is None:
            abbr_match = re.search(r'\b(?:окш|ог)\s*(\d{1,3})\b', normalized, re.IGNORECASE)
            if abbr_match:
                result["angle"] = float(abbr_match.group(1))

        # 4.3 Для "отвод 90 426 на 10" (все падежи)
        if is_elbow and result["angle"] is None:
            angle_match = re.search(
                r"\b(?:отвод(?:а|у|ом|е|ов)?|окш|ог)\s+(30|45|60|90)\s+",
                normalized,
            )
            if angle_match:
                result["angle"] = float(angle_match.group(1))

        # ---------------------------------------------------------
        # 5. Радиус
        # ---------------------------------------------------------
        radius = re.search(
            r"\b(?:радиус|r)\s*[:=]?\s*([0-9.,]+\s*d|[0-9.,]+)",
            normalized,
        )
        if radius:
            result["radius"] = radius.group(1)

        return result
