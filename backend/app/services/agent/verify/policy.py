# agent/verify/policy.py
"""Политика эскалации: C1 (refine) vs C2 (полный LLM-перезапуск).

C1 — один LLM-вызов для дооформления текстовой части.
C2 — полный перезапуск LLMAgent (см. §4 Авто-режим/C2).
"""

from __future__ import annotations

import logging
from typing import List

from .verifier import Gap

log = logging.getLogger("mtr.agent.verify.policy")

FULL_LLM_TYPES = {"intent_mismatch", "quantity_unmet", "scope_mismatch", "safety_unconfirmed"}


def should_full_llm(gaps: List[Gap]) -> bool:
    """Нужен ли полный LLM-перезапуск (C2).

    C2, если среди gaps есть тип из FULL_LLM_TYPES с severity == high
    (интерпретация количественных требований / отсутствие охвата скоупа).
    Иначе — только C1 (дооформление).
    """
    for gap in gaps:
        if gap.type in FULL_LLM_TYPES and gap.severity == "high":
            log.info("[Policy] Escalating to C2 for gap=%s", gap.type)
            return True

    return False


def should_refine(gaps: List[Gap]) -> bool:
    """Нужно ли LLM-дооформление (C1)."""
    return len(gaps) > 0


def escalate_type(gaps: List[Gap]) -> str:
    """Тип эскалации: 'none' | 'refine' | 'full_llm'."""
    if not gaps:
        return "none"
    if should_full_llm(gaps):
        return "full_llm"
    return "refine"
