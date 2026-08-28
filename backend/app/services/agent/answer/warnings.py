# agent/answer/warnings.py

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.schemas import ParsedQuery


_SCENARIOS_PATH = Path(__file__).parent / "scenario_warnings.json"
_scenarios: Optional[List[dict]] = None


def _load_scenarios() -> List[dict]:
    """Ленивая загрузка сценариев предупреждений"""
    global _scenarios
    if _scenarios is None:
        try:
            data = json.loads(_SCENARIOS_PATH.read_text(encoding="utf-8"))
            _scenarios = data.get("scenarios", [])
        except Exception:
            _scenarios = []
    return _scenarios


def _medium(parsed: ParsedQuery) -> Optional[str]:
    """Определение среды из запроса"""
    tf = parsed.technical_filters or {}
    medium = tf.get("medium")
    if not medium and parsed.card and parsed.card.environment:
        medium = parsed.card.environment.medium
    return str(medium) if medium else None


def _medium_kind(medium: Optional[str]) -> str:
    """Тип среды"""
    if not medium:
        return ""
    text = medium.lower()
    if "h2s" in text or "сероводород" in text:
        return "h2s"
    if "co2" in text:
        return "co2"
    if "коррози" in text:
        return "corrosive"
    return ""


def _context(parsed: ParsedQuery, intent: str) -> dict:
    """Контекст запроса для проверки условий"""
    text = (parsed.original_query or "").lower()
    ops = list(parsed.operations or [])
    items = list(parsed.item_types or [])
    return {
        "text": text,
        "ops": ops,
        "items": items,
        "medium_kind": _medium_kind(_medium(parsed)),
        "planned": any(op in ops for op in ("plan", "repair", "calculate", "assemble")),
        "replacement": intent == "replacement" or "replace" in ops,
        "duplicates": intent == "duplicates" or "дубл" in text,
        "intent": intent,
        "has_changes": bool(getattr(parsed, "proposed_changes", {})),
    }


def _matches(condition: Optional[dict], ctx: dict) -> bool:
    """Проверка условия"""
    if not condition:
        return True
    if isinstance(condition, list):
        return any(_matches(c, ctx) for c in condition)
    if "any" in condition:
        return any(_matches(c, ctx) for c in condition["any"])
    if "all" in condition:
        return all(_matches(c, ctx) for c in condition["all"])
    if "text" in condition:
        return any(token in ctx["text"] for token in condition["text"])
    if "ops" in condition:
        return any(op in ctx["ops"] for op in condition["ops"])
    if "items" in condition:
        return any(item in ctx["items"] for item in condition["items"])
    if "medium_kind" in condition:
        return ctx["medium_kind"] in condition["medium_kind"]
    if "intent" in condition:
        value = condition["intent"]
        wanted = {value} if isinstance(value, str) else set(value)
        return ctx["intent"] in wanted
    if "planned" in condition:
        return bool(ctx["planned"]) == bool(condition["planned"])
    if "replacement" in condition:
        return bool(ctx["replacement"]) == bool(condition["replacement"])
    if "duplicates" in condition:
        return bool(ctx["duplicates"]) == bool(condition["duplicates"])
    if "has_changes" in condition:
        return bool(ctx["has_changes"]) == bool(condition["has_changes"])
    return False


def build_scenario_warnings(parsed: ParsedQuery, intent: str) -> List[str]:
    """Сбор предупреждений на основе сценариев"""
    warnings = []
    ctx = _context(parsed, intent)
    
    for scenario in _load_scenarios():
        if not _matches(scenario.get("when"), ctx):
            continue
        for rule in scenario.get("warnings", []):
            if _matches(rule.get("when"), ctx):
                warnings.append(rule["text"])
    
    return warnings


def build_required_params_warnings(parsed: ParsedQuery, provider: Any = None) -> List[str]:
    """Предупреждения по обязательным параметрам типа детали (ValidationRule).

    Для каждого типа из запроса: какие обязательные (required) параметры не
    указаны в technical_filters. БД-правила (validation_rules) поверх дефолтов.
    """
    item_types = list(getattr(parsed, "item_types", []) or [])
    if not item_types:
        return []
    context = _rule_context(parsed, provider)
    if context is None:
        return []
    provider, labels = context

    tf = getattr(parsed, "technical_filters", {}) or {}

    warnings: List[str] = []
    for item_type in item_types:
        rule = provider.validation_rule(item_type)
        if not rule or rule.get("is_active") is False:
            continue
        missing = [
            p for p in rule.get("required", []) if not tf.get(p)
        ]
        if not missing:
            continue
        names = ", ".join(labels.get(p, p) for p in missing)
        if len(item_types) == 1:
            warnings.append(
                f"Для типа «{item_type}» не указаны обязательные параметры: {names}. "
                "Уточните их для точного подбора."
            )
        else:
            warnings.append(
                f"Для типа «{item_type}» не указаны обязательные параметры: {names}."
            )
    return warnings


def build_forbidden_params_warnings(parsed: ParsedQuery, provider: Any = None) -> List[str]:
    """Параметры, запрещённые для типа детали (ValidationRule.forbidden).

    Если пользователь указал параметр из forbidden — это несовместимость
    с типом, выдаём предупреждение.
    """
    item_types = list(getattr(parsed, "item_types", []) or [])
    if not item_types:
        return []
    context = _rule_context(parsed, provider)
    if context is None:
        return []
    provider, labels = context

    tf = getattr(parsed, "technical_filters", {}) or {}

    warnings: List[str] = []
    for item_type in item_types:
        rule = provider.validation_rule(item_type)
        if not rule or rule.get("is_active") is False:
            continue
        present = [
            p for p in rule.get("forbidden", []) if tf.get(p) is not None
        ]
        if not present:
            continue
        names = ", ".join(labels.get(p, p) for p in present)
        warnings.append(
            f"Для типа «{item_type}» параметр {names} недопустим — уточните запрос."
        )
    return warnings


def build_optional_params_recommendations(parsed: ParsedQuery, provider: Any = None) -> List[str]:
    """Рекомендации указать опциональные параметры (ValidationRule.optional).

    Выдаются только когда required-параметры типа полностью указаны (иначе
    сначала обязательные), и если опциональных параметров не больше трёх —
    чтобы не спамить.
    """
    item_types = list(getattr(parsed, "item_types", []) or [])
    if not item_types:
        return []
    context = _rule_context(parsed, provider)
    if context is None:
        return []
    provider, labels = context

    tf = getattr(parsed, "technical_filters", {}) or {}

    recommendations: List[str] = []
    for item_type in item_types:
        rule = provider.validation_rule(item_type)
        if not rule or rule.get("is_active") is False:
            continue
        optional = list(rule.get("optional", []) or [])
        if not optional or len(optional) > 3:
            continue
        if any(not tf.get(p) for p in rule.get("required", [])):
            continue
        missing = [p for p in optional if not tf.get(p)]
        if not missing:
            continue
        names = ", ".join(labels.get(p, p) for p in missing)
        recommendations.append(
            f"Для типа «{item_type}» можно дополнительно уточнить: {names}."
        )
    return recommendations


def evaluate_parameter_rules(
    parsed: ParsedQuery,
    provider: Any = None,
) -> Tuple[List[str], List[str]]:
    """Полная оценка правил по типам (required / forbidden / optional / условия).

    Возвращает (warnings, recommendations). Учтёт is_active и logical_conditions.
    """
    warnings = build_required_params_warnings(parsed, provider)
    warnings += build_forbidden_params_warnings(parsed, provider)
    warnings += _logical_conditions_warnings(parsed, provider)
    recommendations = build_optional_params_recommendations(parsed, provider)
    return warnings, recommendations


def _logical_conditions_warnings(parsed: ParsedQuery, provider: Any = None) -> List[str]:
    """Оценка logical_conditions правил (не одна, а все, независимо от is_active)."""
    item_types = list(getattr(parsed, "item_types", []) or [])
    if not item_types:
        return []
    context = _rule_context(parsed, provider)
    if context is None:
        return []
    provider, labels = context

    tf = getattr(parsed, "technical_filters", {}) or {}

    warnings: List[str] = []
    for item_type in item_types:
        rule = provider.validation_rule(item_type)
        if not rule or rule.get("is_active") is False:
            continue
        conditions = rule.get("logical_conditions")
        if not conditions:
            continue
        try:
            from ..rules.conditions import evaluate_logical_conditions

            warnings += evaluate_logical_conditions(item_type, conditions, tf, labels)
        except Exception:  # noqa: BLE001
            continue
    return warnings


def _rule_context(parsed: ParsedQuery, provider: Any) -> Optional[Tuple[Any, Dict[str, str]]]:
    """Возвращает (provider, labels) или None при невозможности оценки."""
    try:
        if provider is None:
            from ..rules.dynamic_rules import get_dynamic_rules as _gdr

            provider = _gdr()
        from .status import _param_labels

        labels = _param_labels()
    except Exception:  # noqa: BLE001
        return None
    return provider, labels
