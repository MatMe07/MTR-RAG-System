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
    PN16 → 1.6 МПа
    PN40 → 4.0 МПа
    Ру16 → 1.6 МПа
    РУ40 → 4.0 МПа
    16 → 1.6 (если явно не указано PN/Ру)
    """
    value = value.upper().replace(" ", "")
    
    # PN40 → 4.0
    if value.startswith("PN"):
        num = float(value[2:])
        return num / 10.0
    
    # РУ40 → 4.0
    if value.startswith("РУ"):
        num = float(value[2:])
        return num / 10.0
    
    # Если просто число > 10 — считаем PN
    try:
        num = float(value)
        if num >= 10:
            return num / 10.0
        return num
    except ValueError:
        return None
