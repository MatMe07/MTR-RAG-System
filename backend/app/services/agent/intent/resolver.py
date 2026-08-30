# agent/intent/resolver.py

"""Выбор top-level интента из гранулярных (§1B) с приоритетом по семантике.

Приоритет top-level (важное действие выше «поиска/склада»):
maintenance > object_configuration > document_search > impact_analysis
> replacement > inventory > equipment_guidance > duplicates > search.
"""

from typing import Any, Dict, List

TOP_LEVEL_PRIORITY = [
    "maintenance",
    "object_configuration",
    "document_search",
    "impact_analysis",
    "replacement",
    "inventory",
    "equipment_guidance",
    "duplicates",
    "search",
]

# Гранулярный интент -> top-level
_INTENT_TOP: Dict[str, str] = {
    # ПОИСК
    "FIND_BY_CODE": "search",
    "FIND_BY_COMPONENT": "search",
    "FIND_BY_PARAMS": "search",
    "COMPARE_DUPLICATES": "duplicates",
    # ЗАМЕНА
    "FIND_ALTERNATIVE": "replacement",
    "REPLACE_WITH_DIFFERENT_SIZE": "replacement",
    "REPLACE_WITH_COMPOSITE": "replacement",
    "COMPARE_ALTERNATIVES": "replacement",
    # СКЛАД
    "CHECK_STOCK": "inventory",
    "CHECK_MINIMUM_STOCK": "inventory",
    "LIST_OUT_OF_STOCK": "inventory",
    "FIND_UNUSED_STOCK": "inventory",
    # РЕМОНТ / ТОиР
    "PLAN_REPAIR": "maintenance",
    "BUILD_REPAIR_KIT": "maintenance",
    # АНАЛИЗ
    "IMPACT_MEDIUM_CHANGE": "impact_analysis",
    "IMPACT_DIAMETER_CHANGE": "impact_analysis",
    "IMPACT_MATERIAL_CHANGE": "impact_analysis",
    "IMPACT_PRESSURE_CHANGE": "impact_analysis",
    "ANALYZE_RISK": "impact_analysis",
    # ОБЪЯСНЕНИЕ
    "EXPLAIN_TERM": "equipment_guidance",
    "EXPLAIN_DIFFERENCE": "equipment_guidance",
    # ДОКУМЕНТЫ
    "FIND_DOCUMENTS": "document_search",
    "FIND_STANDARDS": "document_search",
    # КОНФИГУРАЦИЯ ОБЪЕКТА
    "GET_UNIT_STRUCTURE": "object_configuration",
    "ADD_COMPONENT": "object_configuration",
}

# Операция -> top-level (fallback, если интенты не определены).
_OP_TOP: Dict[str, str] = {
    "replace": "replacement",
    "repair": "maintenance",
    "plan": "maintenance",
    "inventory": "inventory",
    "calculate": "inventory",
    "impact": "impact_analysis",
    "explain": "equipment_guidance",
    "document": "document_search",
    "assemble": "object_configuration",
    "check": "search",
    "search": "search",
}

# Явные маркеры плана ТОиР (сильнее складской семантики при совпадении).
_MAINTENANCE_STRONG = (
    "план обслужив", "план работ", "план ремонт", "план замен",
    "обслужив", "тоир", "регламент обслужив", "запланируй", "составь план",
)


def _pick_maintenance_vs_inventory(q: str) -> str:
    """Если одновременно maintenance и inventory — решает лексика."""
    if any(w in q for w in _MAINTENANCE_STRONG):
        return "maintenance"
    return "inventory"


def detect_or_empty(parsed: Any) -> List[str]:
    """Интенты в порядке §1B (без исключений)."""
    try:
        from .detect import detect_intents

        return detect_intents(parsed) or []
    except Exception:  # noqa: BLE001
        return []


def resolve_top_level_intent(
    parsed: Any,
    intents: List[str] | None = None,
) -> str:
    """Top-level интент: сначала по гранулярным интентам, затем по операциям."""
    if intents is None:
        intents = detect_or_empty(parsed)

    mapped = {_INTENT_TOP[i] for i in intents if i in _INTENT_TOP}
    if "maintenance" in mapped and "inventory" in mapped:
        q = (getattr(parsed, "original_query", "") or "").lower()
        return _pick_maintenance_vs_inventory(q)
    for top in TOP_LEVEL_PRIORITY:
        if top in mapped:
            return top

    operations = getattr(parsed, "operations", []) or []
    query = (getattr(parsed, "original_query", "") or "")
    if "дубл" in query.lower():
        return "duplicates"
    if getattr(parsed, "proposed_changes", {}):
        return "impact_analysis"
    for op in operations:
        if op in _OP_TOP:
            return _OP_TOP[op]

    return "search"