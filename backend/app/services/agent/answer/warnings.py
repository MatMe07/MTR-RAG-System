# agent/answer/warnings.py

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

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
