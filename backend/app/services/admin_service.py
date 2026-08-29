from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.sqlalchemy.all_models import (
    GroupKeyword,
    ContextualOverride,
    SynonymRecord,
    ValidationConstant,
    ValidationRule,
)


class AdminService:
    def __init__(self, db: Session):
        self.db = db

    # ── Вспомогательные ─────────────────────────────────────────────

    @staticmethod
    def _json_str(value) -> str:
        import json
        import json as _json
        if isinstance(value, str):
            return value
        return _json.dumps(value, ensure_ascii=False, default=list)

    @staticmethod
    def _json_lst(value) -> list:
        import json
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def _audit(self, action, payload: Optional[dict] = None, actor: Optional[dict] = None) -> None:
        """1K.6/1L.6: журналирование изменений справочников и правил."""
        try:
            from app.services.audit_service import AuditService

            user_id = str(actor["id"]) if actor and actor.get("id") else None
            request_id = str(actor.get("request_id")) if actor and actor.get("request_id") else None
            AuditService(self.db).log(request_id, user_id, action, payload or {})
        except Exception:  # noqa: BLE001 — аудит не должен ломать основную операцию
            pass

    # ── Invalidation ────────────────────────────────────────────────

    def _invalidate_dynamic_rules(self) -> None:
        """После изменений правил/синонимов/констант — сброс кэшей,
        чтобы новые значения применились без перезапуска."""
        try:
            from app.services.agent.rules.dynamic_rules import get_dynamic_rules

            get_dynamic_rules().refresh(force=True)
        except Exception:  # noqa: BLE001
            pass
        try:
            from app.services.agent.parsing.dictionaries import refresh_dictionaries_force

            refresh_dictionaries_force()
        except Exception:  # noqa: BLE001
            pass

    # ── Group Keywords ──────────────────────────────────────────────

    def list_group_keywords(self, group_name: str | None = None) -> list[dict[str, Any]]:
        q = self.db.query(GroupKeyword)
        if group_name:
            q = q.filter(GroupKeyword.group_name == group_name)
        rows = q.order_by(GroupKeyword.group_name, GroupKeyword.priority.desc()).all()
        return [self._gk_to_dict(r) for r in rows]

    def create_group_keyword(self, data: dict[str, Any], actor: Optional[dict] = None) -> dict[str, Any]:
        gk = GroupKeyword(
            group_name=data["group_name"],
            keyword=data["keyword"],
            priority=data.get("priority", 0),
            is_active=data.get("is_active", True),
        )
        self.db.add(gk)
        self.db.commit()
        self.db.refresh(gk)
        self._audit("admin.dictionaries.group_keywords.create", {"id": gk.id, "group": gk.group_name, "keyword": gk.keyword}, actor)
        self._invalidate_dynamic_rules()
        return self._gk_to_dict(gk)

    def update_group_keyword(self, item_id: int, data: dict[str, Any], actor: Optional[dict] = None) -> dict[str, Any]:
        gk = self.db.query(GroupKeyword).filter(GroupKeyword.id == item_id).first()
        if not gk:
            raise NotFoundError(f"GroupKeyword id={item_id} not found")
        for key in ("group_name", "keyword", "priority", "is_active"):
            if key in data:
                setattr(gk, key, data[key])
        self.db.commit()
        self.db.refresh(gk)
        self._audit("admin.dictionaries.group_keywords.update", {"id": gk.id, "group": gk.group_name, "keyword": gk.keyword}, actor)
        self._invalidate_dynamic_rules()
        return self._gk_to_dict(gk)

    def delete_group_keyword(self, item_id: int, actor: Optional[dict] = None) -> None:
        gk = self.db.query(GroupKeyword).filter(GroupKeyword.id == item_id).first()
        if not gk:
            raise NotFoundError(f"GroupKeyword id={item_id} not found")
        self._audit("admin.dictionaries.group_keywords.delete", {"id": gk.id, "group": gk.group_name, "keyword": gk.keyword}, actor)
        self.db.delete(gk)
        self.db.commit()
        self._invalidate_dynamic_rules()

    # ── Contextual Overrides ────────────────────────────────────────

    def list_contextual_overrides(self) -> list[dict[str, Any]]:
        rows = self.db.query(ContextualOverride).order_by(ContextualOverride.priority.desc()).all()
        return [self._co_to_dict(r) for r in rows]

    def create_contextual_override(self, data: dict[str, Any], actor: Optional[dict] = None) -> dict[str, Any]:
        co = ContextualOverride(
            trigger_phrase=data["trigger_phrase"],
            target_group=data["target_group"],
            priority=data.get("priority", 0),
            is_active=data.get("is_active", True),
        )
        self.db.add(co)
        self.db.commit()
        self.db.refresh(co)
        self._audit("admin.dictionaries.contextual_overrides.create", {"id": co.id, "trigger": co.trigger_phrase, "target": co.target_group}, actor)
        self._invalidate_dynamic_rules()
        return self._co_to_dict(co)

    def update_contextual_override(self, item_id: int, data: dict[str, Any], actor: Optional[dict] = None) -> dict[str, Any]:
        co = self.db.query(ContextualOverride).filter(ContextualOverride.id == item_id).first()
        if not co:
            raise NotFoundError(f"ContextualOverride id={item_id} not found")
        for key in ("trigger_phrase", "target_group", "priority", "is_active"):
            if key in data:
                setattr(co, key, data[key])
        self.db.commit()
        self.db.refresh(co)
        self._audit("admin.dictionaries.contextual_overrides.update", {"id": co.id, "trigger": co.trigger_phrase, "target": co.target_group}, actor)
        self._invalidate_dynamic_rules()
        return self._co_to_dict(co)

    def delete_contextual_override(self, item_id: int, actor: Optional[dict] = None) -> None:
        co = self.db.query(ContextualOverride).filter(ContextualOverride.id == item_id).first()
        if not co:
            raise NotFoundError(f"ContextualOverride id={item_id} not found")
        self._audit("admin.dictionaries.contextual_overrides.delete", {"id": co.id, "trigger": co.trigger_phrase, "target": co.target_group}, actor)
        self.db.delete(co)
        self.db.commit()
        self._invalidate_dynamic_rules()

    # ── Synonyms ────────────────────────────────────────────────────

    def list_synonyms(self, group_name: str | None = None) -> list[dict[str, Any]]:
        q = self.db.query(SynonymRecord)
        if group_name:
            q = q.filter(SynonymRecord.group_name == group_name)
        rows = q.order_by(SynonymRecord.group_name).all()
        return [self._syn_to_dict(r) for r in rows]

    def create_synonym(self, data: dict[str, Any], actor: Optional[dict] = None) -> dict[str, Any]:
        syn = SynonymRecord(
            group_name=data["group_name"],
            raw_value=data["raw_value"],
            normalized_value=data["normalized_value"],
            is_active=data.get("is_active", True),
        )
        self.db.add(syn)
        self.db.commit()
        self.db.refresh(syn)
        self._audit("admin.dictionaries.synonyms.create", {"id": syn.id, "raw": syn.raw_value, "norm": syn.normalized_value, "group": syn.group_name}, actor)
        self._invalidate_dynamic_rules()
        return self._syn_to_dict(syn)

    def update_synonym(self, item_id: int, data: dict[str, Any], actor: Optional[dict] = None) -> dict[str, Any]:
        syn = self.db.query(SynonymRecord).filter(SynonymRecord.id == item_id).first()
        if not syn:
            raise NotFoundError(f"SynonymRecord id={item_id} not found")
        for key in ("group_name", "raw_value", "normalized_value", "is_active"):
            if key in data:
                setattr(syn, key, data[key])
        self.db.commit()
        self.db.refresh(syn)
        self._audit("admin.dictionaries.synonyms.update", {"id": syn.id, "raw": syn.raw_value, "norm": syn.normalized_value, "group": syn.group_name}, actor)
        self._invalidate_dynamic_rules()
        return self._syn_to_dict(syn)

    def delete_synonym(self, item_id: int, actor: Optional[dict] = None) -> None:
        syn = self.db.query(SynonymRecord).filter(SynonymRecord.id == item_id).first()
        if not syn:
            raise NotFoundError(f"SynonymRecord id={item_id} not found")
        self._audit("admin.dictionaries.synonyms.delete", {"id": syn.id, "raw": syn.raw_value, "group": syn.group_name}, actor)
        self.db.delete(syn)
        self.db.commit()
        self._invalidate_dynamic_rules()

    # ── Validation Constants ────────────────────────────────────────

    def list_validation_constants(self) -> list[dict[str, Any]]:
        rows = self.db.query(ValidationConstant).order_by(ValidationConstant.constant_name).all()
        return [
            {
                "id": r.id,
                "constant_name": r.constant_name,
                "value": r.value,
                "description": r.description,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]

    def create_validation_constant(self, data: dict[str, Any], actor: Optional[dict] = None) -> dict[str, Any]:
        existing = (
            self.db.query(ValidationConstant)
            .filter(ValidationConstant.constant_name == data["constant_name"])
            .first()
        )
        if existing:
            raise ValidationError(f"Constant '{data['constant_name']}' already exists")
        vc = ValidationConstant(
            constant_name=data["constant_name"],
            value=data["value"],
            description=data.get("description"),
        )
        self.db.add(vc)
        self.db.commit()
        self.db.refresh(vc)
        self._audit("admin.rules.constants.create", {"id": vc.id, "name": vc.constant_name}, actor)
        self._invalidate_dynamic_rules()
        return {"id": vc.id, "constant_name": vc.constant_name, "value": vc.value}

    def update_validation_constant(self, item_id: int, data: dict[str, Any], actor: Optional[dict] = None) -> dict[str, Any]:
        vc = self.db.query(ValidationConstant).filter(ValidationConstant.id == item_id).first()
        if not vc:
            raise NotFoundError(f"ValidationConstant id={item_id} not found")
        if "value" in data:
            vc.value = data["value"]
        if "description" in data:
            vc.description = data["description"]
        self.db.commit()
        self.db.refresh(vc)
        self._audit("admin.rules.constants.update", {"id": vc.id, "name": vc.constant_name}, actor)
        self._invalidate_dynamic_rules()
        return {"id": vc.id, "constant_name": vc.constant_name, "value": vc.value}

    def delete_validation_constant(self, item_id: int, actor: Optional[dict] = None) -> None:
        vc = self.db.query(ValidationConstant).filter(ValidationConstant.id == item_id).first()
        if not vc:
            raise NotFoundError(f"ValidationConstant id={item_id} not found")
        self._audit("admin.rules.constants.delete", {"id": vc.id, "name": vc.constant_name}, actor)
        self.db.delete(vc)
        self.db.commit()
        self._invalidate_dynamic_rules()

    # ── Validation Rules ────────────────────────────────────────────

    def list_validation_rules(self) -> list[dict[str, Any]]:
        rows = self.db.query(ValidationRule).order_by(ValidationRule.item_type).all()
        return [self._vr_to_dict(r) for r in rows]

    def create_validation_rule(self, data: dict[str, Any], actor: Optional[dict] = None) -> dict[str, Any]:
        existing = (
            self.db.query(ValidationRule)
            .filter(ValidationRule.item_type == data["item_type"])
            .first()
        )
        if existing:
            raise ValidationError(f"Rule for item_type '{data['item_type']}' already exists")
        vr = ValidationRule(
            item_type=data["item_type"],
            required_params=self._json_str(data.get("required_params", [])),
            forbidden_params=self._json_str(data.get("forbidden_params", [])),
            optional_params=self._json_str(data.get("optional_params", [])),
            logical_conditions=data.get("logical_conditions"),
            is_active=data.get("is_active", True),
        )
        self.db.add(vr)
        self.db.commit()
        self.db.refresh(vr)
        self._audit("admin.rules.rule.create", {"id": vr.id, "item_type": vr.item_type}, actor)
        self._invalidate_dynamic_rules()
        return self._vr_to_dict(vr)

    def update_validation_rule(self, item_id: int, data: dict[str, Any], actor: Optional[dict] = None) -> dict[str, Any]:
        vr = self.db.query(ValidationRule).filter(ValidationRule.id == item_id).first()
        if not vr:
            raise NotFoundError(f"ValidationRule id={item_id} not found")
        for key in ("required_params", "forbidden_params", "optional_params", "logical_conditions", "is_active"):
            if key in data:
                value = data[key]
                if key in ("required_params", "forbidden_params", "optional_params"):
                    value = self._json_str(value)
                setattr(vr, key, value)
        self.db.commit()
        self.db.refresh(vr)
        self._audit("admin.rules.rule.update", {"id": vr.id, "item_type": vr.item_type}, actor)
        self._invalidate_dynamic_rules()
        return self._vr_to_dict(vr)

    def delete_validation_rule(self, item_id: int, actor: Optional[dict] = None) -> None:
        vr = self.db.query(ValidationRule).filter(ValidationRule.id == item_id).first()
        if not vr:
            raise NotFoundError(f"ValidationRule id={item_id} not found")
        self._audit("admin.rules.rule.delete", {"id": vr.id, "item_type": vr.item_type}, actor)
        self.db.delete(vr)
        self.db.commit()
        self._invalidate_dynamic_rules()

    # ── Cache ───────────────────────────────────────────────────────

    def reload_cache(self) -> dict[str, Any]:
        """Перезагрузка кеша: каталог репозитория агента + справочники."""
        reloaded = []

        from app.services.agent.repository.repository_factory import reset_repository

        reset_repository()
        reloaded.append("catalog_repository")

        import importlib

        from app.services.agent.parsing import dictionaries as dict_module

        importlib.reload(dict_module)

        self._invalidate_dynamic_rules()

        reloaded.append("dictionaries")

        return {"status": "ok", "message": "Cache reloaded", "reloaded": reloaded}

    # ── Serializers ─────────────────────────────────────────────────

    @staticmethod
    def _gk_to_dict(r: GroupKeyword) -> dict[str, Any]:
        return {
            "id": r.id,
            "group_name": r.group_name,
            "keyword": r.keyword,
            "priority": r.priority,
            "is_active": r.is_active,
        }

    @staticmethod
    def _co_to_dict(r: ContextualOverride) -> dict[str, Any]:
        return {
            "id": r.id,
            "trigger_phrase": r.trigger_phrase,
            "target_group": r.target_group,
            "priority": r.priority,
            "is_active": r.is_active,
        }

    @staticmethod
    def _syn_to_dict(r: SynonymRecord) -> dict[str, Any]:
        return {
            "id": r.id,
            "group_name": r.group_name,
            "raw_value": r.raw_value,
            "normalized_value": r.normalized_value,
            "is_active": r.is_active,
        }

    @staticmethod
    def _vr_to_dict(r: ValidationRule) -> dict[str, Any]:
        import json
        lc = r.logical_conditions
        if isinstance(lc, str):
            try:
                lc = json.loads(lc)
            except (json.JSONDecodeError, TypeError):
                lc = None
        return {
            "id": r.id,
            "item_type": r.item_type,
            "required_params": r.required_params if isinstance(r.required_params, list) else __class__._json_lst(r.required_params),
            "forbidden_params": r.forbidden_params if isinstance(r.forbidden_params, list) else __class__._json_lst(r.forbidden_params),
            "optional_params": r.optional_params if isinstance(r.optional_params, list) else __class__._json_lst(r.optional_params),
            "logical_conditions": lc,
            "is_active": r.is_active,
        }
