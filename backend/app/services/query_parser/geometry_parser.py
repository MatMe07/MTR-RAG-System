# query_parser/geometry_parser.py

import re
from typing import Dict, Any

from .normalizers import normalize_decimal


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
        # 1. Сначала определяем тип детали
        # ---------------------------------------------------------
        is_transition = bool(re.search(r"\bпереход(?:а|ом)?\b", normalized))
        is_elbow = bool(re.search(r"\bотвод(?:а|у|ом|е|ов)?|ог|окш\b", normalized))

        # ---------------------------------------------------------
        # 2. DN / Ду
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
        # 2.1 ДИАМЕТР (НОВЫЙ)
        # ---------------------------------------------------------
        diam_match = re.search(r'\bдиаметр(?:ом|е|а)?\s*(\d+(?:[.,]\d+)?)', normalized)
        if diam_match and result["dn"] is None:
            result["dn"] = normalize_decimal(diam_match.group(1))

        # ---------------------------------------------------------
        # 2.2 "на X" как DN (если одно число и не переход)
        # ---------------------------------------------------------
        if not is_transition:
            single_on = re.search(r'\bна\s+(\d+(?:[.,]\d+)?)\b', normalized)
            if single_on and not re.search(r'\d+\s*на\s*\d+', normalized):
                if result["dn"] is None:
                    result["dn"] = normalize_decimal(single_on.group(1))

        # ---------------------------------------------------------
        # 3. Переход: "219 на 159"
        # ---------------------------------------------------------
        if is_transition:
            transition_match = re.search(
                r"(\d+(?:[.,]\d+)?)\s*(?:x|х|×|на)\s*(\d+(?:[.,]\d+)?)",
                normalized,
            )
            if transition_match:
                result["d1"] = normalize_decimal(transition_match.group(1))
                result["d2"] = normalize_decimal(transition_match.group(2))
                if result["dn"] is None:
                    result["dn"] = result["d1"]

        # ---------------------------------------------------------
        # 4. Диаметр x толщина (только если НЕ переход)
        # ---------------------------------------------------------
        if not is_transition:
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

        wall_match = re.search(r'\bстенк(?:а|и|ой)\s*(\d+(?:[.,]\d+)?)', normalized)
        if wall_match:
            result["wall_thickness"] = normalize_decimal(wall_match.group(1))
            
        # ---------------------------------------------------------
        # 5. Угол (существующий + новые)
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

        # 5.1 "прямой угол" (НОВЫЙ)
        if result["angle"] is None and re.search(r'\bпрямой\s+угол\b', normalized):
            result["angle"] = 90.0

        # 5.2 слитные ОКШ90, ОГ90 (НОВЫЙ)
        if result["angle"] is None:
            abbr_match = re.search(r'\b(?:окш|ог)\s*(\d{1,3})\b', normalized, re.IGNORECASE)
            if abbr_match:
                result["angle"] = float(abbr_match.group(1))

        # Для "отвод 90 426 на 10" (все падежи)
        if is_elbow and result["angle"] is None:
            angle_match = re.search(
                r"\b(?:отвод(?:а|у|ом|е|ов)?|окш|ог)\s+(30|45|60|90)\s+",
                normalized,
            )
            if angle_match:
                result["angle"] = float(angle_match.group(1))

        # ---------------------------------------------------------
        # 6. Радиус
        # ---------------------------------------------------------
        radius = re.search(
            r"\b(?:радиус|r)\s*[:=]?\s*([0-9.,]+\s*d|[0-9.,]+)",
            normalized,
        )
        if radius:
            result["radius"] = radius.group(1)

        return result
