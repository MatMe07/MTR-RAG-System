"""Deterministic routing between ordinary, clarification and agent search."""

import re
from typing import Any, Mapping, Sequence

from app.schemas import RouterDecision
from ..query_normalizer import normalize_query
from ..agent.intent_resolver import INTENT_LABELS, intent_from_operation

# Re-export для обратной совместимости (importer'ы: llm_router, main).
# noqa: F401


EXACT_CODE_PATTERN = re.compile(
    r"\b(?:MTR|KSM|COMP|UNIT)-[A-ZА-Я0-9-]+\b",
    re.IGNORECASE,
)

ITEM_COLLECTIONS = {
    "труба": "pipes",
    "отвод": "elbows",
    "переход": "reducers",
    "задвижка": "valves",
    "заглушка": "plugs",
    "тройник": "tees",
}


def _has_values(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Sequence):
        return bool(value)
    return value is not None


def route_search(context: Mapping[str, Any]) -> dict[str, Any]:
    """Return a transparent route decision for an extracted request context."""
    exact_codes = context.get("exact_codes") or []
    collections = list(context.get("collections") or [])
    source_types = set(context.get("required_source_types") or [])

    if _has_values(exact_codes):
        return {
            "route": "ordinary",
            "mode": "exact",
            "reasons": ["В запросе указан точный код МТР, КСМ или обозначение."],
        }

    missing_parameters = list(context.get("missing_critical_parameters") or [])
    if missing_parameters:
        return {
            "route": "clarification",
            "mode": "missing_parameters",
            "reasons": [
                "Не хватает ключевых параметров: "
                + ", ".join(missing_parameters)
                + "."
            ],
        }

    agent_reasons = []
    if len(collections) > 1:
        agent_reasons.append("Запрос затрагивает несколько DCD-коллекций.")
    if len(source_types) > 1:
        agent_reasons.append("Нужно собрать доказательства из нескольких источников.")
    if context.get("has_conflicting_facts"):
        agent_reasons.append("В источниках обнаружены противоречащие факты.")
    if context.get("composite_replacement"):
        agent_reasons.append("Проверяется составная замена.")
    if context.get("needs_rule_reasoning"):
        agent_reasons.append("Требуется многошаговое применение правил.")

    if agent_reasons:
        return {
            "route": "agent",
            "mode": str(context.get("agent_mode") or "multi_step"),
            "reasons": agent_reasons,
        }

    return {
        "route": "ordinary",
        "mode": str(context.get("ordinary_mode") or "hybrid"),
        "reasons": ["Достаточно одного поискового прохода в одной коллекции."],
    }


def _detected_values(
    detected_aliases: Sequence[Mapping[str, Any]],
    category: str,
) -> set[str]:
    return {
        str(alias["canonical"])
        for alias in detected_aliases
        if alias.get("category") == category
    }


def _missing_search_parameters(
    normalized_text: str,
    item_types: set[str],
    exact_codes: Sequence[str],
    intent: str,
) -> list[str]:
    if exact_codes or intent not in {"replacement", "catalog_search"}:
        return []

    has_dn = bool(re.search(r"\bdn\s*\d+", normalized_text))
    has_dimensions = bool(
        re.search(r"\b\d+(?:\.\d+)?x\d+(?:\.\d+)?\b", normalized_text)
    )
    missing = []

    if "отвод" in item_types:
        if not re.search(r"\b(?:30|45|60|90)\b", normalized_text):
            missing.append("angle")
        if not has_dn and not has_dimensions:
            missing.append("dn_or_diameter")
        if not has_dimensions and "стен" not in normalized_text:
            missing.append("wall_thickness")
    elif "задвижка" in item_types:
        if not has_dn:
            missing.append("dn")
        if not re.search(r"\bpn\s*\d+", normalized_text):
            missing.append("pn")
    elif item_types & {"труба", "заглушка"}:
        if not has_dn and not has_dimensions:
            missing.append("dn_or_diameter")
        if not has_dimensions and "стен" not in normalized_text:
            missing.append("wall_thickness")
    elif "переход" in item_types and not has_dimensions:
        missing.append("d1_d2")

    return missing


def route_query_text(
    query: str,
    extracted_card: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Analyze a user phrase and choose a transparent processing route."""
    normalized = normalize_query(query)
    text = normalized["normalized_text"]
    aliases = normalized["detected_aliases"]
    actions = _detected_values(aliases, "action")
    item_types = _detected_values(aliases, "item_type")
    relations = _detected_values(aliases, "object_relation")
    mediums = _detected_values(aliases, "medium")

    if (
        not item_types
        and extracted_card
        and extracted_card.get("item_type")
    ):
        item_types.add(str(extracted_card["item_type"]).casefold())

    exact_codes = EXACT_CODE_PATTERN.findall(query)
    # Приоритет действий такой же, как в детерминированном baseline:
    # проверяется от более специфичного к общему. Каждое действие нормализуется
    # через INTENT_MAP (например, explanation -> equipment_guidance).
    intent = None
    for action in ("maintenance", "impact_analysis", "object_configuration",
                   "document_search", "explanation", "replacement", "inventory"):
        if action in actions:
            intent = intent_from_operation(action)
            break
    if intent is None and "graph" in relations:
        intent = "object_configuration"
    if intent is None:
        intent = "catalog_search"

    tools = ["catalog_search"]
    if intent == "replacement":
        tools.append("rules_engine")
    if "inventory" in actions:
        tools.append("stock_query")
    if "maintenance" in actions:
        tools.extend(["graph_search", "stock_query", "maintenance_planner"])
    if "object_configuration" in actions:
        tools.extend(["graph_search", "object_builder"])
    if "impact_analysis" in actions:
        tools.extend(["graph_search", "rules_engine", "impact_analyzer"])
    if "graph" in relations or any(
        code.upper().startswith(("COMP-", "UNIT-"))
        for code in exact_codes
    ):
        tools.append("graph_search")
    if "document_search" in actions:
        tools.append("document_search")
    if "explanation" in actions:
        tools.append("explanation_generator")
    if mediums or re.search(r"\b(?:gost|гост|tu|ту)\b", text):
        tools.append("regulation_lookup")

    tools = list(dict.fromkeys(tools))
    missing_parameters = _missing_search_parameters(
        text,
        item_types,
        exact_codes,
        intent,
    )

    reasons = []
    if missing_parameters:
        route = "clarification"
        mode = "missing_parameters"
        reasons.append(
            "До поиска нужно уточнить: "
            + ", ".join(missing_parameters)
            + "."
        )
    else:
        multi_step_tools = {
            "stock_query",
            "graph_search",
            "maintenance_planner",
            "document_search",
        }
        if multi_step_tools.intersection(tools) or len(item_types) > 1:
            route = "agent"
            if "maintenance_planner" in tools:
                mode = "maintenance_plan"
                reasons.append(
                    "Нужно связать состав объекта, склад и план ремонта."
                )
            elif "stock_query" in tools and "rules_engine" in tools:
                mode = "inventory_and_match"
                reasons.append(
                    "Нужно одновременно подобрать аналоги и проверить остатки."
                )
            elif "stock_query" in tools:
                mode = "inventory"
                reasons.append(
                    "Ответ требует отдельного обращения к складским остаткам."
                )
            elif "document_search" in tools:
                mode = "evidence_collection"
                reasons.append(
                    "Нужно собрать подтверждения из документов и каталога."
                )
            elif "impact_analyzer" in tools:
                mode = "impact_analysis"
                reasons.append(
                    "Нужно проверить влияние изменения на связанные детали."
                )
            else:
                mode = "object_configuration"
                reasons.append(
                    "Нужно пройти по связям компонентов объекта."
                )
        else:
            route = "ordinary"
            mode = "exact" if exact_codes else "hybrid"
            reasons.append(
                "Достаточно одного поиска по каталогу"
                + (" по точному коду." if exact_codes else " и проверки правил.")
            )

    if len(item_types) > 1:
        reasons.append(
            "Запрос затрагивает несколько классов изделий: "
            + ", ".join(sorted(item_types))
            + "."
        )
    if mediums:
        reasons.append(
            "Условия среды требуют отдельного нормативного предупреждения."
        )

    return validate_route_decision({
        "intent": intent,
        "intent_label": INTENT_LABELS[intent],
        "route": route,
        "mode": mode,
        "reasons": reasons,
        "required_tools": tools,
        "missing_parameters": missing_parameters,
        "exact_codes": exact_codes,
        "collections": [
            ITEM_COLLECTIONS[item_type]
            for item_type in sorted(item_types)
            if item_type in ITEM_COLLECTIONS
        ],
        "normalized_query": text,
        "detected_aliases": aliases,
    })


def validate_route_decision(decision: dict[str, Any]) -> dict[str, Any]:
    """Валидирует решение роутера через схему RouterDecision.

    Дополнительные ключи (например, parsed_query) сохраняются за счёт
    extra="ignore"; возвращается обычный dict, совместимый с потребителями.
    """
    return RouterDecision.model_validate(decision).model_dump()
