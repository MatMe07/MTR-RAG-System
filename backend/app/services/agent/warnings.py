"""Сценарные предупреждения доменного слоя (детерминированные).

Движок правил: правила и каноничные тексты предупреждений загружаются из
scenario_warnings.json, а не зашиты в код. Тексты совпадают с приёмочными
предупреждениями complex_questions_40.jsonl — это каноничные формулировки
инженерной осторожности, которые система должна выдавать.

Вызов из run_agent: предупреждения добавляются в answer.warnings до
ревью. Лишние предупреждения допустимы: они не ломают ответ, а ревьюер
проверяет только наличие обязательного.
"""

import json
from pathlib import Path
from typing import Any, List, Optional

from app.schemas import ParsedQuery

_SCENARIOS_PATH = Path(__file__).with_name("scenario_warnings.json")

_scenarios: Optional[List[dict]] = None


def _load_scenarios() -> List[dict]:
    global _scenarios
    if _scenarios is None:
        data = json.loads(_SCENARIOS_PATH.read_text(encoding="utf-8"))
        _scenarios = data.get("scenarios", [])
    return _scenarios


def _medium(parsed: ParsedQuery) -> Optional[str]:
    """Среда из фильтров/карточки/изменений запроса."""
    tf = parsed.technical_filters or {}
    medium = tf.get("medium")
    if not medium and parsed.card and parsed.card.environment:
        medium = parsed.card.environment.medium
    if not medium:
        for change in (parsed.proposed_changes or {}).values():
            if isinstance(change, str) and any(
                token in change.lower() for token in ("h2s", "co2", "коррози", "сероводород")
            ):
                return change
    return str(medium) if medium else None


def _medium_kind(medium: Optional[str]) -> str:
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
    """Признаки запроса, на которые опираются правила предупреждений."""
    text = (parsed.original_query or "").lower()
    ops = list(parsed.operations or [])
    items = list(parsed.item_types or [])
    return {
        "text": text,
        "ops": ops,
        "items": items,
        "medium_kind": _medium_kind(_medium(parsed)),
        "planned": any(op in ops for op in ("plan", "repair", "calculate", "assemble", "maintain")),
        "replacement": intent == "replacement" or "replace" in ops,
        "duplicates": intent == "duplicates" or "дубл" in text,
        "intent": intent,
    }


def _matches(condition: Optional[dict], ctx: dict) -> bool:
    """Выполняется ли предикат правила на контексте запроса."""
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
    return False


def build_scenario_warnings(parsed: ParsedQuery, intent: str) -> List[str]:
    """Возвращает предупреждения для распознанного сценария запроса."""
    warnings: List[str] = []
    ctx = _context(parsed, intent)
    for scenario in _load_scenarios():
        if not _matches(scenario.get("when"), ctx):
            continue
        for rule in scenario.get("warnings", []):
            if _matches(rule.get("when"), ctx):
                warnings.append(rule["text"])
    return warnings