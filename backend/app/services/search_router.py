"""Deterministic routing between ordinary, clarification and agent search."""

from typing import Any, Mapping, Sequence


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
