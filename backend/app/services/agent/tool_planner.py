"""Планирование тулов по интентам: планы исполнения и plan_for_operations.

Выделено из registry.py (фаза 2 рефакторинга). Интенты и их карта живут
в intent_resolver.py — здесь только соответствие интент -> план тулов
и детерминированные дополнения плана под контент запроса.
"""

from typing import Any, Dict, List

from .intent_resolver import INTENT_MAP, resolve_intent

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


def plan_for_operations(operations: List[str], required_agents: List[str],
                        ambiguities: List[str], parsed: Any = None) -> List[str]:
    """Детерминированный план тулов: один основной интент + дополнения агентов."""
    ops = list(operations or ["search"])

    # Единое разрешение интента (intent_resolver учитывает сборку участка
    # по геометрии, proposed_changes и «дубли»).
    primary_intent = resolve_intent(ops, parsed=parsed)

    plan = list(INTENT_PLANS.get(primary_intent, INTENT_PLANS["search"]))

    # Комбинированные запросы (например, «состав участка и складские остатки» =
    # inventory+plan): добавляем тулы остальных интентов.
    for op in ops:
        other_intent = INTENT_MAP.get((op or "").strip().lower())
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


def build_agent_plan(parsed: Any) -> List[str]:
    """Полный план агентского запроса: базовый план + контекстные подключения.

    Объединяет plan_for_operations и правки, которые раньше делались прямо
    в run_agent: граф вперёд при unit/component_ids, keyword «дубли»,
    proposed_changes -> обязательные аналитические тулы.
    """
    plan = plan_for_operations(parsed.operations, parsed.required_agents,
                               parsed.ambiguities, parsed=parsed)

    # Если запрос явно про участки/компоненты — сначала загружаем состав объекта,
    # чтобы stock_query/document_search работали по установленным позициям.
    if parsed.unit_ids or parsed.component_ids:
        plan = [t for t in plan if t != "graph_search"]
        plan.insert(0, "graph_search")

    # Ключевое слово «дубли» не выделяется парсером как операция — подключаем тул.
    if "дубл" in (parsed.original_query or "").lower():
        for t in ("duplicate_detector", "catalog_search"):
            if t not in plan:
                plan.append(t)

    # Если парсер вычленил изменение (DN150->DN200, среда H2S) — обязательно
    # нужен анализ влияния даже без явной операции impact.
    if parsed.proposed_changes:
        for t in ("impact_analyzer", "graph_search", "regulation_lookup"):
            if t not in plan:
                plan.append(t)
    return plan
