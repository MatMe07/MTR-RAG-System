# agent/intent/matrix.py

"""Декларативная матрица интентов (Этап 1, §1B–1H).

- INTENT_REQUIREMENTS: обязательные/опциональные параметры 24 интентов
  (таблица §1C; в тексте плана фигурирует «28», в таблице перечислены 24).
- INCOMPATIBLE_INTENTS: несовместимые комбинации (§1H.2).
- PARAMETER_VALIDATION_RULES: валидация параметров по типу изделия (§1H.3).
- BLOCKER_FIELDS: критические параметры — единый источник для status/status.py.

Соглашение по required: каждый элемент — кортеж AND-группы параметров,
список в целом — OR между группами. Пример CHECK_STOCK:
    [("ksm_code",), ("item_type", "dn"), ("unit_id",)]
означает «ksm_code ИЛИ (item_type И dn) ИЛИ unit_id».
"""

from typing import Dict, List, Tuple

# Порядок = приоритет внутри группы (§1B.9); первыми в списке — «поисковые».
INTENT_ORDER: Tuple[str, ...] = (
    # ПОИСК
    "FIND_BY_CODE",
    "FIND_BY_COMPONENT",
    "FIND_BY_PARAMS",
    "COMPARE_DUPLICATES",
    # ЗАМЕНА
    "FIND_ALTERNATIVE",
    "REPLACE_WITH_DIFFERENT_SIZE",
    "REPLACE_WITH_COMPOSITE",
    "COMPARE_ALTERNATIVES",
    # СКЛАД
    "CHECK_STOCK",
    "CHECK_MINIMUM_STOCK",
    "LIST_OUT_OF_STOCK",
    "FIND_UNUSED_STOCK",
    # РЕМОНТ
    "PLAN_REPAIR",
    "BUILD_REPAIR_KIT",
    # АНАЛИЗ
    "IMPACT_MEDIUM_CHANGE",
    "IMPACT_DIAMETER_CHANGE",
    "IMPACT_MATERIAL_CHANGE",
    "IMPACT_PRESSURE_CHANGE",
    "ANALYZE_RISK",
    # ОБЪЯСНЕНИЕ
    "EXPLAIN_TERM",
    "EXPLAIN_DIFFERENCE",
    # ДОКУМЕНТЫ
    "FIND_DOCUMENTS",
    "FIND_STANDARDS",
    # КОНФИГУРАЦИЯ ОБЪЕКТА
    "GET_UNIT_STRUCTURE",
    "ADD_COMPONENT",
)

# ---------------------------------------------------------------- 1C
# Каждый элемент required — кортеж AND-группы; список — OR между ними.
INTENT_REQUIREMENTS: Dict[str, Dict[str, List[Tuple[str, ...]]]] = {
    "FIND_BY_CODE": {"required": [("mtr_code",), ("ksm_code",)], "optional": []},
    "FIND_BY_COMPONENT": {"required": [("component_id",)], "optional": ["unit_id"]},
    "FIND_BY_PARAMS": {
        "required": [("item_type", "dn"), ("item_type", "material")],
        "optional": ["pn", "medium", "climate", "angle"],
    },
    "COMPARE_DUPLICATES": {
        "required": [("item_type",)],
        "optional": ["dn", "material", "unit_id"],
    },
    "CHECK_STOCK": {
        "required": [("ksm_code",), ("item_type", "dn"), ("unit_id",)],
        "optional": [],
    },
    "CHECK_MINIMUM_STOCK": {
        "required": [("unit_id",), ("item_type",)],
        "optional": ["quantity"],
    },
    "LIST_OUT_OF_STOCK": {"required": [("medium",), ("unit_id",)], "optional": []},
    "FIND_UNUSED_STOCK": {"required": [("min_stock",)], "optional": ["unit_id"]},
    "PLAN_REPAIR": {"required": [("component_id",), ("unit_id",)], "optional": ["depth"]},
    "BUILD_REPAIR_KIT": {"required": [("component_id",)], "optional": ["depth"]},
    "FIND_ALTERNATIVE": {
        "required": [("item_type", "dn", "pn")],
        "optional": ["medium", "material"],
    },
    "REPLACE_WITH_COMPOSITE": {
        "required": [("item_type", "dn", "from_angle", "to_angle")],
        "optional": [],
    },
    "REPLACE_WITH_DIFFERENT_SIZE": {
        "required": [("item_type", "old_dn", "new_dn", "unit_id")],
        "optional": ["pn", "medium"],
    },
    "COMPARE_ALTERNATIVES": {
        "required": [("item_type", "dn", "pn", "from_value", "to_value")],
        "optional": ["medium", "material"],
    },
    "IMPACT_MEDIUM_CHANGE": {
        "required": [("old_medium", "new_medium", "unit_id")],
        "optional": [],
    },
    "IMPACT_DIAMETER_CHANGE": {
        "required": [("old_dn", "new_dn")],
        "optional": ["unit_id"],
    },
    "IMPACT_MATERIAL_CHANGE": {
        "required": [("old_material", "new_material")],
        "optional": ["unit_id", "item_type"],
    },
    "IMPACT_PRESSURE_CHANGE": {
        "required": [("old_pn", "new_pn")],
        "optional": ["unit_id"],
    },
    "ANALYZE_RISK": {
        "required": [("unit_id",), ("medium",)],
        "optional": ["top_n", "item_type"],
    },
    "EXPLAIN_TERM": {"required": [("term",)], "optional": []},
    "EXPLAIN_DIFFERENCE": {"required": [("term1", "term2")], "optional": []},
    "FIND_DOCUMENTS": {"required": [("component_id",), ("unit_id",)], "optional": []},
    "FIND_STANDARDS": {
        "required": [("gost_tu",), ("item_type",)],
        "optional": [],
    },
    "GET_UNIT_STRUCTURE": {"required": [("unit_id",)], "optional": ["depth"]},
    "ADD_COMPONENT": {"required": [("item_type",)], "optional": ["dn", "pn", "medium", "unit_id"]},
}

# ---------------------------------------------------------------- 1H.2
INCOMPATIBLE_INTENTS: Dict[str, List[str]] = {
    "FIND_ALTERNATIVE": ["REPLACE_WITH_COMPOSITE", "REPLACE_WITH_DIFFERENT_SIZE"],
    "CHECK_STOCK": ["LIST_OUT_OF_STOCK"],
    "PLAN_REPAIR": ["FIND_BY_PARAMS"],
}

# ---------------------------------------------------------------- 1H.3
PARAMETER_VALIDATION_RULES: Dict[str, Dict[str, List[str]]] = {
    "задвижка": {"forbidden": ["angle"], "required": ["dn", "pn"]},
    "отвод": {"forbidden": [], "required": ["dn", "angle"]},
    "труба": {"forbidden": [], "required": ["dn", "wall_thickness"]},
    "переход": {"forbidden": [], "required": ["dn_from", "dn_to"]},
    "unknown": {"forbidden": [], "required": ["item_type"]},
}

# ---------------------------------------------------------------- 1H / 5A
# Критические параметры: их расхождение или недостаток данных → эскалация.
BLOCKER_FIELDS = {
    "dn", "pn", "angle", "wall_thickness",
    "medium", "material", "steel_grade", "item_type",
}


def get_intent_requirements(intent: str) -> Dict[str, List[Tuple[str, ...]]]:
    """Требования интента (required как OR of AND-групп) + optional."""
    return INTENT_REQUIREMENTS.get(intent, {"required": [], "optional": []})


def all_optional_params() -> List[str]:
    return sorted({p for r in INTENT_REQUIREMENTS.values() for p in r["optional"]})