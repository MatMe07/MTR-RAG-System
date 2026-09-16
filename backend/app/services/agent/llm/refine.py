# agent/llm/refine.py
"""LLM-дооформление ответа (вариант С1).

Одним LLM-вызовом улучшает текстовую часть ответа и explanation,
сохраняя структуру components/sources/warnings (детерминированные данные).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .json_utils import extract_json_object
from .prompts import REFINE_PROMPT_TEMPLATE, format_gaps, format_structured_answer

log = logging.getLogger("mtr.agent.llm.refine")


class RefineResult:
    __slots__ = ("answer_text", "explanation", "extra_recommendations", "confidence_gate")

    def __init__(
        self,
        answer_text: str,
        explanation: str,
        extra_recommendations: List[str],
        confidence_gate: str,
    ):
        self.answer_text = answer_text
        self.explanation = explanation
        self.extra_recommendations = extra_recommendations
        self.confidence_gate = confidence_gate


def refine_answer(
    llm_client: Any,
    query: str,
    answer: Any,
    gaps: List[Dict[str, Any]],
) -> Optional[RefineResult]:
    """Одним LLM-вызовом улучшает текстовую часть ответа.

    Возвращает RefineResult или None при ошибке LLM.
    """
    if llm_client is None:
        log.warning("[Refine] LLM client unavailable, skipping refine")
        return None

    prompt = REFINE_PROMPT_TEMPLATE.format(
        query=query,
        structured_answer=format_structured_answer(answer),
        gaps=format_gaps(gaps),
    )

    try:
        raw = llm_client.invoke(prompt)
        data = _parse_json(raw)
        if data is None:
            log.warning("[Refine] Failed to parse LLM response")
            return None

        return RefineResult(
            answer_text=data.get("answer_text", ""),
            explanation=data.get("explanation", ""),
            extra_recommendations=data.get("extra_recommendations", []),
            confidence_gate=data.get("confidence_gate", "pass"),
        )
    except Exception as e:
        log.error("[Refine] LLM call failed: %s", e)
        return None


def _parse_json(raw: str) -> Optional[Dict[str, Any]]:
    return extract_json_object(raw)
