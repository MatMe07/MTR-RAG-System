# agent/medium.py

"""Канонические среды и совместимость среда-сталь (AQ007/AQ002/AQ004).

- MEDIUM_UNIT_CODES — ключевые слова среды → коды участков графа;
- medium_unit_codes — коды, релевантные строке среды;
- medium_match — совпадение сред (в т.ч. канон CORR ↔ «коррозионно-активная среда»).
"""

from typing import Any, Dict, Optional

# Ключевые слова среды -> коды участков графа (для которого узел/компонент валиден).
MEDIUM_UNIT_CODES: Dict[str, set] = {
    "h2s": {"gas_h2s", "gas_h2s_co2"},
    "сероводород": {"gas_h2s", "gas_h2s_co2"},
    "co2": {"gas_co2", "gas_h2s_co2"},
    "углекисл": {"gas_co2", "gas_h2s_co2"},
    "природн": {"natural_gas"},
    "коррозион": {"corrosive_medium"},
    "corr": {"corrosive_medium"},
    "агрессив": {"corrosive_medium"},
    "конденсат": {"oil"},
    "нефт": {"oil"},
    "вод": {"process_water"},
}


def medium_unit_codes(medium: Any) -> set:
    """Коды участков графа, релевантные упомянутой среде."""
    m = str(medium or "").lower()
    codes: set = set()
    for kw, cs in MEDIUM_UNIT_CODES.items():
        if kw in m:
            codes |= cs
    return codes


def medium_match(want: Any, got: Any) -> bool:
    """Совпадение среды: подстрока в обе стороны + общий код участка графа.

    Покрывает канон CORR: канон «CORR» не является подстрокой
    «коррозионно-активная среда», но оба дают код corrosive_medium.
    """
    w = str(want or "").strip().lower()
    g = str(got or "").strip().lower()
    if not w or not g:
        return False
    if w == g or w in g or g in w:
        return True
    w_codes = medium_unit_codes(want)
    g_codes = medium_unit_codes(got)
    return bool(w_codes and g_codes and (w_codes & g_codes))


# ---------------------------------------------------------------
# Совместимость марки стали со средой H2S (AQ002/AQ004)
# ---------------------------------------------------------------

# Статусы пригодности марки для H2S (материал из regulation_matrix.json,
# material_profiles[].h2s_suitability; здесь — дефолт на случай недоступности данных).
H2S_STEEL_STATUS_DEFAULT = {
    "20": "incompatible",
    "09Г2С": "requires_verification",
    "09ГСФ": "requires_verification",
    "13ХФА": "suitable",
}


def normalize_steel_key(value: Any) -> Optional[str]:
    """Ключ марки стали для lookup: «Сталь 20»/«сталь 20»/«20» → «20»."""
    if value is None:
        return None
    raw = str(value).strip()
    upper = raw.upper()
    if upper.startswith("СТАЛЬ "):
        upper = upper[len("СТАЛЬ "):].strip()
    return upper or None


def steel_h2s_status(steel: Any, rules: Optional[Dict[str, str]] = None) -> str:
    """Статус пригодности марки стали для H2S.

    rules — карта «марка → h2s_suitability» (обычно из regulation_matrix.json,
    material_profiles). Если rules пуста/отсутствует — используются дефолты кода.
    """
    key = normalize_steel_key(steel)
    if not key:
        return "unknown"
    rules = rules or {}
    return rules.get(key, H2S_STEEL_STATUS_DEFAULT.get(key, "unknown"))