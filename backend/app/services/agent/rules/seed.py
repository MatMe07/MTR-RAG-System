# agent/rules/seed.py
"""Идемпотентный перенос правил из кода в БД (validation_constants,
validation_rules, synonyms). Действует как бутстрап: дефолты кода
копируются в БД один раз, после чего БД становится источником истины.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("mtr.agent.rules.seed")

SYNONYM_GROUPS = ("item_type", "medium", "operation", "climate")


def _alias_pairs(aliases: Dict[str, str]) -> List[Tuple[str, str]]:
    return list(aliases.items())


def _upsert_synonyms(db, group: str, pairs: List[Tuple[str, str]]) -> int:
    from app.models.sqlalchemy.all_models import SynonymRecord

    count = 0
    for raw, norm in pairs:
        row = (
            db.query(SynonymRecord)
            .filter(SynonymRecord.group_name == group, SynonymRecord.raw_value == raw)
            .first()
        )
        if row is None:
            db.add(SynonymRecord(group_name=group, raw_value=raw, normalized_value=norm))
            count += 1
        elif row.normalized_value != norm:
            row.normalized_value = norm
            count += 1
    return count


def _upsert_constant(db, name: str, value) -> int:
    from app.models.sqlalchemy.all_models import ValidationConstant

    row = db.query(ValidationConstant).filter(ValidationConstant.constant_name == name).first()
    if row is None:
        db.add(ValidationConstant(constant_name=name, value=value))
        return 1
    if row.value != value:
        row.value = value
        return 1
    return 0


def _upsert_rule(db, item_type: str, required, forbidden, optional) -> int:
    from app.models.sqlalchemy.all_models import ValidationRule

    row = db.query(ValidationRule).filter(ValidationRule.item_type == item_type).first()
    if row is None:
        db.add(ValidationRule(
            item_type=item_type,
            required_params=json.dumps(required, ensure_ascii=False),
            forbidden_params=json.dumps(forbidden, ensure_ascii=False),
            optional_params=json.dumps(optional, ensure_ascii=False),
        ))
        return 1
    changed = 0
    for col, value in (
        ("required_params", required),
        ("forbidden_params", forbidden),
        ("optional_params", optional),
    ):
        text = json.dumps(value, ensure_ascii=False)
        if getattr(row, col) != text:
            setattr(row, col, text)
            changed = 1
    return changed


def seed_rules(db) -> Dict[str, int]:
    """Заполняет БД правилами из дефолтов кода. Возвращает счётчики изменений."""
    from ..parsing.dictionaries import CLIMATE_ALIASES, ITEM_TYPE_ALIASES, MEDIUM_ALIASES, OPERATION_ALIASES
    from .dynamic_rules import (
        DEFAULT_MATCHING_TOLERANCES,
        DEFAULT_NUMERIC_TOLERANCE,
        DEFAULT_PASSPORT_WEIGHTS,
        DEFAULT_VALIDATION_RULES,
    )
    from ..answer.status import PARAM_LABELS

    counts: Dict[str, int] = {"synonyms": 0, "constants": 0, "rules": 0}

    for group, aliases in (
        ("item_type", ITEM_TYPE_ALIASES),
        ("medium", MEDIUM_ALIASES),
        ("operation", OPERATION_ALIASES),
        ("climate", CLIMATE_ALIASES),
    ):
        counts["synonyms"] += _upsert_synonyms(db, group, _alias_pairs(aliases))

    constants = [
        ("matching_tolerances", dict(DEFAULT_MATCHING_TOLERANCES)),
        ("numeric_tolerance", DEFAULT_NUMERIC_TOLERANCE),
        ("passport_weights", dict(DEFAULT_PASSPORT_WEIGHTS)),
        ("passport_confidence_threshold", 0.6),
        ("param_labels", dict(PARAM_LABELS)),
    ]
    for name, value in constants:
        counts["constants"] += _upsert_constant(db, name, value)

    for item_type, rule in DEFAULT_VALIDATION_RULES.items():
        counts["rules"] += _upsert_rule(
            db,
            item_type,
            rule["required"],
            rule["forbidden"],
            rule["optional"],
        )

    db.commit()
    log.info("seed_rules: %s", counts)
    return counts


class _SeedContext:
    def __init__(self, db_session_factory=None):
        from app.db.session import SessionLocal

        self._factory = db_session_factory or SessionLocal
        self._owns = db_session_factory is None

    def __enter__(self):
        self._db = self._factory()
        return self._db

    def __exit__(self, exc_type, exc, tb):
        try:
            self._db.close()
        finally:
            if exc_type is not None:
                self._db.rollback()
        return False


def seed_rules_standalone(db_session_factory=None) -> Dict[str, int]:
    """Запуск seed с собственным соединением (для скриптов и тестов)."""
    with _SeedContext(db_session_factory) as db:
        return seed_rules(db)