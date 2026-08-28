# agent/intent/__init__.py

"""Интентный слой (Этап 1, §1B–1H): матрица, детекция, статусы, уточнение."""

from .matrix import (
    INTENT_ORDER,
    INTENT_REQUIREMENTS,
    INCOMPATIBLE_INTENTS,
    PARAMETER_VALIDATION_RULES,
    BLOCKER_FIELDS,
    get_intent_requirements,
)
from .detect import (
    detect_intents,
    filter_params_for_intent,
    missing_required_for_intent,
    params_from_parsed,
    enrich_parsed,
    determine_parsed_status,
)
from .clarify import ClarificationManager, RequireClarification, build_question

PARSED_STATUS_COMPLETE = "COMPLETE"
PARSED_STATUS_PARTIAL = "PARTIAL"
PARSED_STATUS_REQUIRES_EXPERT = "REQUIRES_EXPERT"
PARSED_STATUS_UNCLEAR = "UNCLEAR"

__all__ = [
    "INTENT_ORDER",
    "INTENT_REQUIREMENTS",
    "INCOMPATIBLE_INTENTS",
    "PARAMETER_VALIDATION_RULES",
    "BLOCKER_FIELDS",
    "get_intent_requirements",
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