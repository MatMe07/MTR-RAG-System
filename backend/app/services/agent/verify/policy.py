# agent/verify/policy.py
"""Политика эскалации: C1 (refine) vs skip.

В v1 реализован только C1 (один LLM-вызов для дооформления).
C2 (полный перезапуск LLMAgent) отложен на будущее.
"""

from __future__ import annotations

import logging
from typing import List

from .verifier import Gap

log = logging.getLogger("mtr.agent.verify.policy")

FULL_LLM_TYPES = {"intent_mismatch", "quantity_unmet", "scope_mismatch"}


def should_full_llm(gaps: List[Gap]) -> bool:
    """Определяет, нужен ли полный LLM-перезапуск (C2).

    В v1 всегда возвращает False — только C1 (refine).
    """
    for gap in gaps:
        if gap.type in FULL_LLM_TYPES and gap.severity == "high":
            log.info("[Policy] Would escalate to C2 for gap=%s (deferred in v1)", gap.type)
            return False

    return False


def should_refine(gaps: List[Gap]) -> bool:
    """Нужно ли LLM-дооформление (C1)."""
    return len(gaps) > 0


def escalate_type(gaps: List[Gap]) -> str:
    """Тип эскалации: 'none' | 'refine' | 'full_llm' (full_llm отложен)."""
    if not gaps:
        return "none"
    if should_full_llm(gaps):
        return "full_llm"
    return "refine"
