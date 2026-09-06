# agent/parsing/normalizers/normalizers.py

"""Нормализация параметров (Этап 1, §1E).

- normalize_dn      — приведение к ряду R10 (§1E.1);
- normalize_pressure— всё давление → МПа (§1E.2: бар/10, кгс/см2/10);
- normalize_material— «Ст20 / сталь 20 / 20» → «Сталь 20» (§1E.3);
- normalize_medium  — «сероводород» → H2S и пр. через MEDIUM_ALIASES + synonyms БД;
- normalize_climate — «северный» → ХЛ и пр. (§1E.5);
- normalize_item_type — «колено» → отвод и пр. (§1E.6).

Через get_synonym из DynamicRules поддерживаются кастомные алиасы из БД.
"""

import re
from typing import Any, Dict, Optional

from ..dictionaries import CLIMATE_ALIASES, ITEM_TYPE_ALIASES, MEDIUM_ALIASES

# Ряд R10 условных проходов (§1E.1). Значения вне ряда не искажаем
# (фактический наружный диаметр 159/219 не «округляем» в 150/200).
DN_SERIES = (15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250,
             300, 350, 400, 450, 500, 600, 700, 800, 900, 1000)

_PRESSURE_UNITS = {
    "бар": 10.0, "bar": 10.0, "bars": 10.0,
    "кгс/см2": 10.0, "кгс/см²": 10.0, "кг/см2": 10.0, "кг/см²": 10.0, "атм": 10.0,
    "кпа": 1000.0, "kpa": 1000.0,
    "мпа": 1.0, "mpa": 1.0, "мегапаскаль": 1.0, "мегапаскаля": 1.0,
}

_STEEL_RE = re.compile(r"^ст(?:аль)?[\s-]?(\d{1,3})$", re.IGNORECASE)


def normalize_decimal(value: str) -> float:
    value = value.replace(",", ".")
    return float(value)


def normalize_steel(value: str) -> str:
    return value.upper()


def normalize_strength_class(value: str) -> str:
    return value.upper().replace(" ", "")


def normalize_dn(value: Any, series: tuple = DN_SERIES) -> Any:
    """§1E.1: приведение к ряду R10 (в пределах точности 1% или 0.5).

    DN150 / Ду150 / 150 мм → 150; фактический OD 159 остаётся 159.
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    for s in series:
        if abs(v - s) <= 0.5 or (s and abs(v - s) / s <= 0.01):
            return s
    return value


def normalize_pressure(value: Any, unit: Optional[str] = None) -> Optional[float]:
    """§1E.2: давление в МПа (бар/10, кгс/см2/10, кПа/1000).

    При unit=None значение считается уже в МПа (пассивная проверка).
    """
    try:
        v = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if not unit:
        return v
    key = str(unit).strip().lower()
    divisor = _PRESSURE_UNITS.get(key)
    if divisor is None:
        for raw, d in _PRESSURE_UNITS.items():
            if key in raw or raw in key:
                divisor = d
                break
    if divisor is None:
        return None
    return round(v / divisor, 3)


def normalize_material(value: Any) -> Optional[str]:
    """§1E.3: «Ст20 / сталь 20 / 20» → «Сталь 20»; «09Г2С-12» → «09Г2С»."""
    if value is None:
        return None
    raw = str(value).strip()
    m = _STEEL_RE.match(raw)
    if m:
        return f"Сталь {m.group(1)}"
    if re.fullmatch(r"\d{1,3}", raw):
        return f"Сталь {raw}"
    base = re.split(r"[\-\s]+", normalize_steel(raw))[0]
    return base or None


def _synonym(value: str, group: str) -> Optional[str]:
    try:
        from ...rules.dynamic_rules import get_dynamic_rules

        norm = get_dynamic_rules().get_synonym(value, group)
        if norm:
            return norm
    except Exception:  # noqa: BLE001
        pass
    return None


def normalize_medium(value: Any) -> Optional[str]:
    """§1E.4: «сероводород» → H2S (MEDIUM_ALIASES + synonyms БД)."""
    if value is None:
        return None
    raw = str(value).strip()
    alias = MEDIUM_ALIASES.get(raw.lower())
    if alias:
        return alias
    return _synonym(raw, "medium") or raw


def normalize_climate(value: Any) -> Optional[str]:
    """§1E.5: «северный» → ХЛ; У/УХЛ/ХЛ/Т — как есть."""
    if value is None:
        return None
    raw = str(value).strip()
    alias = CLIMATE_ALIASES.get(raw.lower())
    if alias:
        return alias
    return _synonym(raw, "climate") or raw.upper()


def normalize_item_type(value: Any) -> Optional[str]:
    """§1E.6: «колено / отвод гнутый» → «отвод» (ITEM_TYPE_ALIASES)."""
    if value is None:
        return None
    raw = str(value).strip().lower()
    alias = ITEM_TYPE_ALIASES.get(raw)
    if alias:
        return alias
    return _synonym(raw, "item_type") or raw


NORMALIZERS: Dict[str, Any] = {
    "dn": normalize_dn,
    "pn": normalize_pressure,
    "material": normalize_material,
    "medium": normalize_medium,
    "climate": normalize_climate,
    "item_type": normalize_item_type,
}