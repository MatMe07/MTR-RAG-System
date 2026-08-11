# query_parser/pressure_parser.py

import re
from typing import Dict, Any, Optional

from .normalizers.normalizers import normalize_decimal


class PressureParser:

    def parse(self, text: str) -> Dict[str, Any]:
        result = {
            "pn": None,
            "working_pressure_mpa": None,
            "test_pressure_mpa": None,
            "raw_value": None,
        }

        normalized = text.lower()

        # ---------------------------------------------------------
        # 1. PN / Ру
        #    PN40 -> 4.0, PN63 -> 6.3, PN100 -> 10.0
        # ---------------------------------------------------------
        pn_match = re.search(
            r"\b(?:pn|ру)\s*[:]?\s*(\d+)",
            normalized,
            re.IGNORECASE,
        )
        if pn_match:
            raw_value = pn_match.group(1)
            result["raw_value"] = f"PN{raw_value}"
            result["pn"] = self._normalize_pn(raw_value)
        
        if result["pn"] is None:
            pressure_match = re.search(
                r'\bдавлени[ея]\s*(\d+(?:[.,]\d+)?)',
                normalized,
                re.IGNORECASE
            )
            if pressure_match:
                val = float(pressure_match.group(1).replace(',', '.'))
                result["raw_value"] = f"PN{int(val)}" if val.is_integer() else f"PN{val}"
                result["pn"] = val / 10.0 if val >= 10 else val
        
        # ---------------------------------------------------------
        # 2. Давление в МПа
        # ---------------------------------------------------------
        mpa_match = re.search(
            r"(\d+(?:[.,]\d+)?)\s*(?:мпа|mpa)",
            normalized,
            re.IGNORECASE,
        )
        if mpa_match:
            result["working_pressure_mpa"] = normalize_decimal(mpa_match.group(1))

        # ---------------------------------------------------------
        # 3. Испытательное давление
        # ---------------------------------------------------------
        test_match = re.search(
            r"(?:испытательн(?:ое|ый)|опрессовк[аи])\s*(\d+(?:[.,]\d+)?)\s*(?:мпа|mpa)",
            normalized,
            re.IGNORECASE,
        )
        if test_match:
            result["test_pressure_mpa"] = normalize_decimal(test_match.group(1))

        return result

    def _normalize_pn(self, value: str) -> float:
        """PN40 -> 4.0, PN63 -> 6.3, PN100 -> 10.0"""
        num = float(value)
        if num >= 10:
            return num / 10.0
        return num
