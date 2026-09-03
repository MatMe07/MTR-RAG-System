# agent/answer/tz_result.py

"""Сборка структуры ТЗ 11.2 из AgentAnswer (ЭТАП 5, 5B).

Преобразует ответ агента в элементы списка `results` ТЗ-ответа:
mtr_code, ksm_code, match_percent, status, matched_params,
mismatched_params, missing_params, explanation, stock, sources.
"""

from typing import Any, Dict, List

from app.schemas import AgentAnswer, AgentComponent

from .explanation import build_explanation
from .status import (
    candidate_tz_status,
    format_sources,
)


def component_to_tz_result(component: AgentComponent) -> Dict[str, Any]:
    """Формирует один элемент results ТЗ 11.2."""
    percent = component.match_percent
    if percent is None:
        percent = round((component.match_score or 0.0) * 100)
    tz_status = component.tz_status or candidate_tz_status(percent)

    item: Dict[str, Any] = {
        "mtr_code": component.mtr_code,
        "ksm_code": component.ksm_code,
        "match_percent": percent,
        "status": tz_status,
        "matched_params": list(component.matched_params or []),
        "mismatched_params": list(component.mismatched_params or []),
        "missing_params": list(component.missing_params or []),
        "explanation": build_explanation(
            tz_status,
            component.matched_params,
            component.mismatched_params,
            component.missing_params,
        ),
        "stock": None,
        "sources": [],
    }
    if component.quantity is not None:
        item["stock"] = {
            "quantity": component.quantity,
            "unit": "pcs",
            "business_unit": "",
        }
    return item


def build_tz_result_items(answer: AgentAnswer) -> List[Dict[str, Any]]:
    items = [component_to_tz_result(c) for c in answer.components or []]
    sources = format_sources(answer.sources or [])
    if items and sources:
        # На уровне agent sources привязываем к каждому результату (демо).
        for item in items:
            item["sources"] = sources
    return items