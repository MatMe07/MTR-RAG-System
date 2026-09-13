# agent/intent/__init__.py

"""Интентный слой (Этап 1, §1B–1H): матрица, детекция, статусы, уточнение."""

from .clarify import ClarificationManager, RequireClarification, build_question
from .detect import (
    PARSED_STATUS_COMPLETE,
    PARSED_STATUS_PARTIAL,
    PARSED_STATUS_REQUIRES_EXPERT,
    PARSED_STATUS_UNCLEAR,
    detect_intents,
    determine_parsed_status,
    enrich_parsed,
    filter_params_for_intent,
    missing_required_for_intent,
    params_from_parsed,
)
from .matrix import (
    BLOCKER_FIELDS,
    INCOMPATIBLE_INTENTS,
    INTENT_ORDER,
    INTENT_REQUIREMENTS,
    PARAMETER_VALIDATION_RULES,
)

__all__ = [
    "INTENT_ORDER",
    "INTENT_REQUIREMENTS",
    "INCOMPATIBLE_INTENTS",
    "PARAMETER_VALIDATION_RULES",
    "BLOCKER_FIELDS",
    "detect_intents",
    "filter_params_for_intent",
    "missing_required_for_intent",
    "params_from_parsed",
    "enrich_parsed",
    "determine_parsed_status",
    "ClarificationManager",
    "RequireClarification",
    "build_question",
    "PARSED_STATUS_COMPLETE",
    "PARSED_STATUS_PARTIAL",
    "PARSED_STATUS_REQUIRES_EXPERT",
    "PARSED_STATUS_UNCLEAR",
]
