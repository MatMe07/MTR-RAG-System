# backend/app/utils/jsonb_utils.py

from copy import deepcopy
from typing import Any, Dict, Optional, List
from app.schemas import ItemCard, Geometry, Pressure, Material, Environment, Coating, Normative


CANONICAL_PROPERTY_ALIASES = {
    "pressure": "pn",
    "gost_or_tu": "gost_tu",
}

PROPERTY_READ_FALLBACKS = {
    "pn": ("pressure",),
    "pressure": ("pn",),
    "gost_tu": ("gost_or_tu", "standard"),
    "gost_or_tu": ("gost_tu", "standard"),
}


def canonical_property_name(key: str) -> str:
    return CANONICAL_PROPERTY_ALIASES.get(key, key)


def normalize_properties(properties: Dict) -> Dict:
    """Return JSONB properties using canonical keys without losing metadata."""
    if not properties:
        return {}

    result = {}
    explicit_keys = {
        canonical_property_name(key)
        for key in properties
        if key not in CANONICAL_PROPERTY_ALIASES
    }

    for key, characteristic in properties.items():
        canonical_key = canonical_property_name(key)
        if key in CANONICAL_PROPERTY_ALIASES and canonical_key in explicit_keys:
            continue
        result[canonical_key] = deepcopy(characteristic)

    # ItemCardV2 used "standard" before the backend contract introduced
    # the explicit manufacturing-standard key.
    if "gost_tu" not in result and "standard" in result:
        result["gost_tu"] = deepcopy(result["standard"])

    return result


def get_property_value(properties: Dict, key: str) -> Optional[Any]:
    if not properties:
        return None

    prop = properties.get(key)
    if prop is None:
        for fallback_key in PROPERTY_READ_FALLBACKS.get(key, ()):
            if fallback_key in properties:
                prop = properties[fallback_key]
                break
    if isinstance(prop, dict):
        return prop.get('value')
    return prop


def get_property_unit(properties: Dict, key: str) -> Optional[str]:
    if not properties:
        return None

    prop = properties.get(key)
    if prop is None:
        for fallback_key in PROPERTY_READ_FALLBACKS.get(key, ()):
            if fallback_key in properties:
                prop = properties[fallback_key]
                break
    if isinstance(prop, dict):
        return prop.get('unit')
    return None


def set_property_value(properties: Dict, key: str, value: Any, unit: Optional[str] = None) -> Dict:
    key = canonical_property_name(key)
    if value is None:
        if key in properties:
            del properties[key]
        return properties
    
    if unit is not None:
        properties[key] = {"value": value, "unit": unit}
    else:
        properties[key] = {"value": value}
    
    return properties


def card_to_properties(card: ItemCard) -> Dict:
    props = {}
    
    if card.geometry:
        if card.geometry.dn is not None:
            props = set_property_value(props, 'dn', card.geometry.dn, 'мм')
        if card.geometry.wall_thickness is not None:
            props = set_property_value(props, 'wall_thickness', card.geometry.wall_thickness, 'мм')
        if card.geometry.angle is not None:
            props = set_property_value(props, 'angle', card.geometry.angle, '°')
        if card.geometry.d1 is not None:
            props = set_property_value(props, 'd1', card.geometry.d1, 'мм')
        if card.geometry.d2 is not None:
            props = set_property_value(props, 'd2', card.geometry.d2, 'мм')
        if card.geometry.radius:
            props = set_property_value(props, 'radius', card.geometry.radius)
    
    if card.pressure and card.pressure.pn is not None:
        props = set_property_value(props, 'pn', card.pressure.pn, 'PN')
    
    if card.material:
        if card.material.steel_grade:
            props = set_property_value(props, 'steel_grade', card.material.steel_grade)
        if card.material.strength_class:
            props = set_property_value(props, 'strength_class', card.material.strength_class)
        if card.material.standard:
            props = set_property_value(props, 'standard', card.material.standard)
    
    if card.environment:
        if card.environment.medium:
            props = set_property_value(props, 'medium', card.environment.medium)
        if card.environment.h2s_confirmed is not None:
            props = set_property_value(props, 'h2s_confirmed', card.environment.h2s_confirmed)
        if card.environment.co2_confirmed is not None:
            props = set_property_value(props, 'co2_confirmed', card.environment.co2_confirmed)
        if card.environment.climate_version:
            props = set_property_value(props, 'climate_version', card.environment.climate_version)
        if card.environment.temperature_min_c is not None:
            props = set_property_value(props, 'temperature_min', card.environment.temperature_min_c, '°C')
    
    if card.coating:
        if card.coating.inner_coating is not None:
            props = set_property_value(props, 'inner_coating', card.coating.inner_coating)
        if card.coating.outer_coating is not None:
            props = set_property_value(props, 'outer_coating', card.coating.outer_coating)
        if card.coating.coating_type:
            props = set_property_value(props, 'coating_type', card.coating.coating_type)
        if card.coating.coating_standard:
            props = set_property_value(props, 'coating_standard', card.coating.coating_standard)
    
    if card.normative:
        if card.normative.gost_tu:
            props = set_property_value(props, 'gost_tu', card.normative.gost_tu)
        if card.normative.lnd_sections:
            props = set_property_value(props, 'lnd_sections', card.normative.lnd_sections)
    
    return props


def properties_to_card_dict(properties: Dict, mtr_code: str = None, ksm_code: str = None) -> Dict:
    return {
        "mtr_code": mtr_code,
        "ksm_code": ksm_code,
        "geometry": {
            "dn": get_property_value(properties, 'dn'),
            "wall_thickness": get_property_value(properties, 'wall_thickness'),
            "angle": get_property_value(properties, 'angle'),
            "d1": get_property_value(properties, 'd1'),
            "d2": get_property_value(properties, 'd2'),
            "radius": get_property_value(properties, 'radius')
        },
        "pressure": {
            "pn": get_property_value(properties, 'pn')
        },
        "material": {
            "steel_grade": get_property_value(properties, 'steel_grade'),
            "strength_class": get_property_value(properties, 'strength_class'),
            "standard": get_property_value(properties, 'standard')
        },
        "environment": {
            "medium": get_property_value(properties, 'medium'),
            "h2s_confirmed": get_property_value(properties, 'h2s_confirmed'),
            "co2_confirmed": get_property_value(properties, 'co2_confirmed'),
            "climate_version": get_property_value(properties, 'climate_version'),
            "temperature_min_c": get_property_value(properties, 'temperature_min')
        },
        "coating": {
            "inner_coating": get_property_value(properties, 'inner_coating'),
            "outer_coating": get_property_value(properties, 'outer_coating'),
            "coating_type": get_property_value(properties, 'coating_type'),
            "coating_standard": get_property_value(properties, 'coating_standard')
        },
        "normative": {
            "gost_tu": get_property_value(properties, 'gost_tu'),
            "lnd_sections": get_property_value(properties, 'lnd_sections') or []
        }
    }
