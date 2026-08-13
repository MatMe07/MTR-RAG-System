"""Реестр агентских тулов и планов исполнения для интентов."""

from typing import Any, Callable, Dict, List

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

# intent (operations) -> план тулов. catalog_search идёт до stock_query,
# чтобы складские фильтры применялись к кандидатам каталога.
INTENT_PLANS: Dict[str, List[str]] = {
    "search": ["catalog_search", "stock_query", "rules_engine", "regulation_lookup"],
    "replacement": ["graph_search", "catalog_search", "stock_query",
                    "rules_engine", "impact_analyzer", "regulation_lookup"],
    "inventory": ["catalog_search", "stock_query", "inventory_calculator",
                  "priority_ranker", "regulation_lookup"],
    "maintenance": ["graph_search", "maintenance_planner", "document_search",
                    "regulation_lookup"],
    "object_configuration": ["object_builder", "catalog_search", "stock_query",
                             "rules_engine"],
    "document_search": ["graph_search", "document_search", "regulation_lookup"],
    "impact_analysis": ["graph_search", "impact_analyzer", "rules_engine",
                        "regulation_lookup"],
    "equipment_guidance": ["catalog_search", "rules_engine", "explanation_generator",
                           "regulation_lookup"],
    "duplicates": ["catalog_search", "duplicate_detector", "regulation_lookup"],
}

# Синонимы из required_agents (query_parser) -> тулы
AGENT_TO_TOOLS: Dict[str, List[str]] = {
    "search": ["catalog_search", "rules_engine"],
    "inventory": ["stock_query", "inventory_calculator"],
    "rules": ["rules_engine", "regulation_lookup"],
    "knowledge": ["catalog_search", "document_search", "explanation_generator"],
    "topology": ["graph_search", "impact_analyzer"],
    "impact": ["impact_analyzer", "rules_engine"],
    "plan": ["maintenance_planner", "document_search"],
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


def plan_for_operations(operations: List[str], required_agents: List[str],
                        ambiguities: List[str], parsed: Any = None) -> List[str]:
    """Детерминированный план тулов: один основной интент + дополнения агентов."""
    op_to_intent = {
        "search": "search", "replace": "replacement",
        "inventory": "inventory", "calculate": "inventory",
        "plan": "maintenance", "repair": "maintenance",
        "assemble": "object_configuration",
        "document": "document_search", "impact": "impact_analysis",
        "explain": "equipment_guidance", "check": "search",
    }
    # Приоритет интентов: более специфичный побеждает, если операций несколько
    # (например, check+impact -> impact_analysis, а не search).
    intent_priority = [
        "impact_analysis", "replacement", "object_configuration",
        "document_search", "inventory", "maintenance",
        "equipment_guidance", "search",
    ]
    ops = operations or ["search"]

    primary_intent = None
    for intent in intent_priority:
        for op in ops:
            if op in op_to_intent and op_to_intent[op] == intent:
                primary_intent = intent
                break
        if primary_intent is not None:
            break
    if primary_intent is None:
        primary_intent = "search"

    # «Составь перечень деталей нового участка» парсится как plan, но без unit_id
    # с DN/PN/средой это скорее сборка объекта.
    if primary_intent == "maintenance" and parsed is not None:
        has_geometry = parsed.card and (parsed.card.geometry or parsed.card.pressure)
        if not parsed.unit_ids and has_geometry:
            primary_intent = "object_configuration"

    plan = list(INTENT_PLANS.get(primary_intent, INTENT_PLANS["search"]))

    # Комбинированные запросы (например, «состав участка и складские остатки» =
    # inventory+plan): добавляем тулы остальных интентов.
    for op in ops:
        other_intent = op_to_intent.get(op)
        if not other_intent or other_intent == primary_intent:
            continue
        for tool in INTENT_PLANS.get(other_intent, []):
            if tool not in plan:
                plan.append(tool)

    if parsed is not None:
        tf = parsed.technical_filters or {}
        medium = str(tf.get("medium") or "").lower() if tf.get("medium") else ""
        if parsed.card and parsed.card.environment and not medium:
            medium = str(parsed.card.environment.medium or "").lower()

        # Запрос про участок/объект со средой: нужен граф объекта и проверка правил.
        if medium and any(
            token in medium for token in ("h2s", "co2", "коррози", "сероводород")
        ):
            if "graph_search" not in plan:
                plan.append("graph_search")
            if "rules_engine" not in plan:
                plan.append("rules_engine")

        # «Не установлены ни на одном участке» — нужен граф для сверки установленных КСМ.
        if parsed.not_installed and "graph_search" not in plan:
            plan.append("graph_search")

        # Объяснительные запросы: что означает / расскажи / покажи чем / откуда взяты.
        text = (parsed.original_query or "").lower()
        if "explanation_generator" not in plan and any(
            token in text for token in (
                "что означает", "расскажи", "объясн", "что нужно поставить",
                "что стоит", "откуда взяты", "покажи чем", "почему они",
                "проверить рядом", "по одному примеру",
            )
        ):
            plan.append("explanation_generator")

    if ambiguities and "document_search" not in plan:
        plan.append("document_search")
    return plan


def build_workspace() -> Dict[str, Any]:
    return {
        "ksm_targets": [],
        "candidates": [],
        "stock_rows": [],
        "unit_ids": [],
        "component_ids": [],
        "duplicate_groups": [],
        "graph_components": [],
    }
