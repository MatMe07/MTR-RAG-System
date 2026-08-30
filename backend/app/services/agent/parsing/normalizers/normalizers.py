# query_parser/normalizers.py

import re
from typing import Optional



def normalize_decimal(value: str) -> float:
    value = value.replace(",", ".")
    return float(value)



def normalize_steel(value: str) -> str:
    return value.upper()


def normalize_strength_class(value: str) -> str:
    return value.upper().replace(" ", "")


def normalize_medium(value: str) -> str:
    value = value.lower().strip()

    mapping = {
        "сероводород": "H2S",
        "сероводородная среда": "H2S",
        "h2s": "H2S",
        "углекислый газ": "CO2",
        "co2": "CO2",
        "природный газ": "природный газ",
        "газ": "газ",
        "нефть": "нефть",
        "вода": "вода",
    }

    return mapping.get(value, value)


def normalize_pn_from_text(value: str) -> float:
    """
    Канон PN = «PN-класс» (число): PN16 → 16, PN40 → 40, Ру16 → 16,
    РУ40 → 40. Рабочее давление в МПа хранится отдельно (working_pressure_mpa = PN / 10).
    16 (без префикса) → 16.
    """
    value = value.upper().replace(" ", "")
    
    # PN40 → 40
    if value.startswith("PN"):
        return float(value[2:])
    
    # РУ40 → 40
    if value.startswith("РУ"):
        return float(value[2:])
    
    # Если просто число — считаем PN-классом
    try:
        return float(value)
    except ValueError:
        return None
