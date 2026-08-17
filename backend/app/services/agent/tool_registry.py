"""Реестр агентских тулов: реестр функций, алиасы и фабрика workspace.

Выделено из registry.py (фаза 2 рефакторинга). Логика планирования переехала
в tool_planner.py, интенты — в intent_resolver.py. registry.py остаётся
фасадом с re-export для обратной совместимости.
"""

from typing import Any, Callable, Dict

from . import analytic_tools, core_tools

TOOLS: Dict[str, Callable] = {
    "catalog_search": core_tools.catalog_search,
    "stock_query": core_tools.stock_query,
    "graph_search": core_tools.graph_search,
    "regulation_lookup": core_tools.regulation_lookup,
    "rules_engine": core_tools.rules_engine,
    "document_search": core_tools.document_search,
    "duplicate_detector": analytic_tools.duplicate_detector,
    "inventory_calculator": analytic_tools.inventory_calculator,
    "maintenance_planner": analytic_tools.maintenance_planner,
    "priority_ranker": analytic_tools.priority_ranker,
    "object_builder": analytic_tools.object_builder,
    "impact_analyzer": analytic_tools.impact_analyzer,
    "explanation_generator": analytic_tools.explanation_generator,
}

TOOL_ALIASES = {
    "stock": "stock_query",
    "rules": "rules_engine",
    "graph": "graph_search",
    "regulation": "regulation_lookup",
    "documents": "document_search",
    "duplicates": "duplicate_detector",
}


def resolve_tool(name: str) -> Callable | None:
    name = (name or "").strip().lower()
    if name in TOOLS:
        return TOOLS[name]
    resolved = TOOL_ALIASES.get(name)
    return TOOLS.get(resolved) if resolved else None


def build_workspace() -> Dict[str, Any]:
    """Рабочее пространство запроса: результаты тулов + per-request кеш."""
    return {
        "ksm_targets": [],
        "candidates": [],
        "stock_rows": [],
        "unit_ids": [],
        "component_ids": [],
        "duplicate_groups": [],
        "graph_components": [],
        "cache": {},
    }
