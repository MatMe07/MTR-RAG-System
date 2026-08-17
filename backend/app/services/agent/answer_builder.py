"""Сборка структурированного ответа агента (AgentAnswer).

Выделено из executor.run_agent (фаза 3 рефакторинга): конвертация строк
результатов тулов в AgentComponent/AgentSource, дедупликация и сборка
AgentAnswer. Сценарные предупреждения добавляются здесь.
"""

from typing import Any, Dict, List

from app.schemas import AgentAnswer, AgentComponent, AgentSource, ParsedQuery

from .intent_resolver import INTENT_LABELS
from .warnings import build_scenario_warnings


def to_components(rows: List[Dict[str, Any]]) -> List[AgentComponent]:
    components = []
    for row in rows:
        if not row:
            continue
        components.append(AgentComponent(
            mtr_code=row.get("mtr_code"),
            ksm_code=row.get("ksm_code"),
            name=row.get("name"),
            item_type=row.get("item_type"),
            quantity=row.get("quantity"),
            status=row.get("status"),
            detail=row.get("detail"),
            source_id=row.get("source_id"),
        ))
    return components


def to_sources(rows: List[Dict[str, Any]]) -> List[AgentSource]:
    sources = []
    for row in rows:
        if not row:
            continue
        sources.append(AgentSource(
            kind=row.get("kind"),
            id=row.get("id"),
            fragment=row.get("fragment"),
        ))
    return sources


def dedupe(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def build_answer(parsed: ParsedQuery, intent: str, result: Dict[str, Any]) -> AgentAnswer:
    """Собирает черновик AgentAnswer из результата execute_plan.

    review (human_review_required) приходит из результатов тулов; сценарные
    предупреждения добавляются до ревью.
    """
    answers = list(result.get("answers") or [])
    if not answers:
        answers.append("Не удалось собрать ответ: недостаточно данных по запросу.")

    scenario_warnings = build_scenario_warnings(parsed, intent)
    components = to_components(result.get("components") or [])
    sources = to_sources(result.get("sources") or [])
    warnings = dedupe(list(result.get("warnings") or []) + scenario_warnings)
    missing = dedupe(result.get("missing") or [])

    return AgentAnswer(
        query=parsed.original_query,
        intent=intent,
        intent_label=INTENT_LABELS.get(intent),
        route="agent",
        mode="offline_rules",
        tools_used=list(result.get("tools_used") or []),
        answer="\n".join(answers),
        components=components,
        warnings=warnings,
        sources=sources,
        missing_parameters=missing,
        human_review_required=bool(result.get("review")),
        parsed_confidence=parsed.confidence,
        parsed_query=parsed,
    )


# Обратная совместимость с именами из executor.py.
_to_components = to_components
_to_sources = to_sources
_dedupe = dedupe
