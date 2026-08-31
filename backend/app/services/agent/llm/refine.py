# agent/llm/refine.py
"""LLM-дооформление ответа (вариант С1).

Одним LLM-вызовом улучшает текстовую часть ответа и explanation,
сохраняя структуру components/sources/warnings (детерминированные данные).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger("mtr.agent.llm.refine")

_REFINE_PROMPT_TEMPLATE = """\
Ты — инженерный агент MTR. Детерминированный пайплайн уже собрал структурированный \
ответ, но он не полностью отвечает на запрос пользователя. \
Твоя задача — дооформить текст ответа и explanation, НЕ ИЗМЕНЯЯ components/sources/warnings.

Исходный запрос пользователя:
{query}

Структурированный ответ (components, warnings, sources):
{structured_answer}

Недостатки, которые нужно исправить:
{gaps}

Верни строго JSON:
{{
  "answer_text": "исправленный пользовательский текст ответа",
  "explanation": "краткое обоснование",
  "extra_recommendations": ["рекомендация 1", "рекомендация 2"],
  "confidence_gate": "pass" | "still_unclear"
}}

Правила:
- answer_text должен явно отвечать на запрос ( verdict-строки для «хватает ли», списки для «покажи все»).
- Не повторяй сухие данные components — переформулируй.
- Если данных критически не хватает — confidence_gate = "still_unclear".
"""


def _format_gaps(gaps: List[Dict[str, Any]]) -> str:
    lines = []
    for g in gaps:
        lines.append(f"- [{g.get('severity', '?')}] {g.get('type', '?')}: {g.get('detail', '')}")
    return "\n".join(lines) if lines else "- неизвестные недостатки"


def _format_structured_answer(answer: Any) -> str:
    parts = []
    for c in (answer.components or [])[:10]:
        name = getattr(c, "name", None) or c.get("name", "?") if isinstance(c, dict) else "?"
        status = getattr(c, "status", "") or (c.get("status", "") if isinstance(c, dict) else "")
        qty = getattr(c, "quantity", None) or (c.get("quantity") if isinstance(c, dict) else None)
        parts.append(f"  - {name}: {status} (кол-во: {qty})")
    warnings = getattr(answer, "warnings", []) or []
    if warnings:
        parts.append(f"  Предупреждения: {'; '.join(warnings[:5])}")
    return "\n".join(parts) if parts else "  (пусто)"


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

    prompt = _REFINE_PROMPT_TEMPLATE.format(
        query=query,
        structured_answer=_format_structured_answer(answer),
        gaps=_format_gaps(gaps),
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
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None
