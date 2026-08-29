# agent/rules/dynamic_rules.py
"""Динамические правила валидации в БД (а не в коде).

Источники:
- validation_constants  — константы (допуски матчинга, веса паспорта, лейблы);
- validation_rules      — обязательные/запрещённые/опциональные параметры по типу;
- synonyms              — алиасы типов, сред, операций, климатик.

Правило 1: БД — источник истины; код — baseline fallback (если БД недоступна).
Правило 2: записи БД добавляются/переопределяют дефолты кода (merge).
Правило 3: кэш с TTL — новые правила действуют без перезапуска.

Тестируется на in-memory SQLite без PostgreSQL.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

log = logging.getLogger("mtr.agent.dynamic_rules")

# ===========================================================================
# Дефолты кода (baseline). Становятся источником только при недоступной БД.
# ===========================================================================

DEFAULT_MATCHING_TOLERANCES = {
    "dn": 0.10,
    "angle": 0.0,
    "wall_thickness": 0.15,
    "default": 0.10,
}

DEFAULT_NUMERIC_TOLERANCE = 0.10

DEFAULT_PASSPORT_WEIGHTS = {
    "dn": 0.30,
    "pn": 0.25,
    "material": 0.20,
    "angle": 0.15,
    "medium": 0.10,
}

DEFAULT_VALIDATION_RULES: Dict[str, Dict[str, Any]] = {
    "труба": {"required": ["dn", "wall_thickness", "steel_grade"], "forbidden": [], "optional": ["angle", "pn"]},
    "отвод": {"required": ["dn", "angle", "steel_grade"], "forbidden": [], "optional": []},
    "задвижка": {"required": ["dn", "pn", "steel_grade"], "forbidden": [], "optional": []},
    "тройник": {"required": ["dn", "steel_grade"], "forbidden": [], "optional": ["d1", "d2", "angle", "pn"]},
    "переход": {"required": ["d1", "d2", "steel_grade"], "forbidden": [], "optional": []},
    "фланец": {"required": ["dn", "pn", "steel_grade"], "forbidden": [], "optional": []},
    "заглушка": {"required": ["dn", "pn"], "forbidden": [], "optional": []},
}

# Секции карточки (ItemCard) ← параметры из ValidationRule.
RULE_PARAM_TO_SECTION = {
    "dn": "geometry",
    "d1": "geometry",
    "d2": "geometry",
    "wall_thickness": "geometry",
    "angle": "geometry",
    "pn": "pressure",
    "steel_grade": "material",
    "medium": "environment",
    "material": "material",
    "gost_tu": "normative",
}

DEFAULT_CONSTANT_NAMES = {
    "matching_tolerances",
    "numeric_tolerance",
    "param_labels",
    "passport_weights",
    "passport_confidence_threshold",
}


class DynamicRules:
    """Провайдер правил валидации из БД с fallback на дефолты кода.

    db может быть: None (SessionLocal приложения), фабрикой сессий,
    либо самим объектом сессии (удобно для тестов на in-memory SQLite).
    """

    def __init__(self, db=None, ttl_seconds: int = 60, db_retry_seconds: int = 300):
        from app.db.session import SessionLocal

        if db is None:
            self._session_factory = SessionLocal
            self._session = None
        elif callable(db):
            self._session_factory = db
            self._session = None
        else:
            self._session_factory = None
            self._session = db
        self._ttl = ttl_seconds
        self._db_retry = db_retry_seconds
        self._data: Optional[Dict[str, Any]] = None
        self._loaded_at: float = 0.0
        self._db_unavailable_at: Optional[float] = None

    # ------------------------------------------------------------------
    # Доступ к данным
    # ------------------------------------------------------------------
    def _ensure(self) -> None:
        now = time.monotonic()
        if self._data is not None and (now - self._loaded_at) < self._ttl:
            return
        if self._data is None and self._db_unavailable_at is not None:
            if (now - self._db_unavailable_at) < self._db_retry:
                return
        self.refresh()

    def refresh(self, force: bool = False) -> None:
        """Читает правила из БД (fail-safe → сохраняем последний хороший снимок)."""
        data = self._load_from_db()
        if data is None:
            self._db_unavailable_at = time.monotonic()
            return
        self._db_unavailable_at = None
        self._data = data
        self._loaded_at = time.monotonic()

    def _load_from_db(self) -> Optional[Dict[str, Any]]:
        try:
            if self._session is not None:
                db = self._session
                close = False
            else:
                db = self._session_factory()
                close = True
            try:
                from app.models.sqlalchemy.all_models import (
                    SynonymRecord,
                    ValidationConstant,
                    ValidationRule,
                )

                constants = {}
                for vc in db.query(ValidationConstant).all():
                    if vc.value is None:
                        continue
                    value = vc.value
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    constants[vc.constant_name] = value
                synonyms: List[Dict[str, Any]] = [
                    {
                        "group": s.group_name,
                        "raw": s.raw_value,
                        "norm": s.normalized_value,
                    }
                    for s in db.query(SynonymRecord).all()
                ]
                def _json_list(raw) -> List[str]:
                    if isinstance(raw, list):
                        return raw
                    if isinstance(raw, str):
                        try:
                            parsed = json.loads(raw)
                            return parsed if isinstance(parsed, list) else []
                        except (json.JSONDecodeError, TypeError):
                            return []
                    return []

                rules = {}
                for vr in db.query(ValidationRule).all():
                    lc = vr.logical_conditions
                    if isinstance(lc, str):
                        try:
                            lc = json.loads(lc)
                        except (json.JSONDecodeError, TypeError):
                            lc = None
                    rules[vr.item_type] = {
                        "required": _json_list(vr.required_params),
                        "forbidden": _json_list(vr.forbidden_params),
                        "optional": _json_list(vr.optional_params),
                        "logical_conditions": lc,
                        "is_active": bool(vr.is_active),
                    }
                return {"constants": constants, "synonyms": synonyms, "rules": rules}
            finally:
                if close:
                    db.close()
        except Exception as e:  # noqa: BLE001
            log.warning("DynamicRules: БД недоступна, дефолты кода: %s", e)
            return None

    # ------------------------------------------------------------------
    # Константы
    # ------------------------------------------------------------------
    def constants(self) -> Dict[str, Any]:
        self._ensure()
        base: Dict[str, Any] = {}
        for name in DEFAULT_CONSTANT_NAMES:
            value = self._default_constant(name)
            if value is not None:
                base[name] = value
        if self._data:
            base.update(self._data.get("constants") or {})
        return base

    def constant(self, name: str, default: Any = None) -> Any:
        return self.constants().get(name, default)

    @staticmethod
    def _default_constant(name: str) -> Any:
        if name == "matching_tolerances":
            return dict(DEFAULT_MATCHING_TOLERANCES)
        if name == "numeric_tolerance":
            return DEFAULT_NUMERIC_TOLERANCE
        if name == "passport_weights":
            return dict(DEFAULT_PASSPORT_WEIGHTS)
        if name == "passport_confidence_threshold":
            return 0.6
        return None

    def param_labels(self) -> Dict[str, str]:
        labels = self.constant("param_labels")
        return labels if isinstance(labels, dict) else {}

    def matching_tolerances(self) -> Dict[str, float]:
        tol = self.constant("matching_tolerances")
        if not isinstance(tol, dict):
            return dict(DEFAULT_MATCHING_TOLERANCES)
        merged = dict(DEFAULT_MATCHING_TOLERANCES)
        merged.update(tol)
        return merged

    def numeric_tolerance(self) -> float:
        tol = self.constant("numeric_tolerance")
        return float(tol) if isinstance(tol, (int, float)) else DEFAULT_NUMERIC_TOLERANCE

    def passport_weights(self) -> Dict[str, float]:
        w = self.constant("passport_weights")
        return w if isinstance(w, dict) else dict(DEFAULT_PASSPORT_WEIGHTS)

    def validation_rule(self, item_type: str) -> Optional[Dict[str, Any]]:
        self._ensure()
        item_type = (item_type or "").strip().lower()
        if self._data:
            rule = (self._data.get("rules") or {}).get(item_type)
            if rule:
                return rule
        rule = DEFAULT_VALIDATION_RULES.get(item_type)
        if rule is None:
            return None
        return dict(rule, logical_conditions=None, is_active=True)

    def validation_rule_item_types(self) -> List[str]:
        self._ensure()
        types = set(DEFAULT_VALIDATION_RULES.keys())
        if self._data:
            types.update((self._data.get("rules") or {}).keys())
        return sorted(types)

    def synonyms(self, group: str) -> List[Dict[str, str]]:
        self._ensure()
        if not self._data:
            return []
        return [
            s for s in self._data.get("synonyms") or []
            if s.get("group") == group
        ]


_rules: Optional[DynamicRules] = None


def get_dynamic_rules() -> DynamicRules:
    global _rules
    if _rules is None:
        _rules = DynamicRules()
    return _rules


def reset_dynamic_rules() -> None:
    global _rules
    _rules = None
