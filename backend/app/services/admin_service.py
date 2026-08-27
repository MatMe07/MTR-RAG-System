from typing import Any

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

    # ── Group Keywords ──────────────────────────────────────────────

    def list_group_keywords(self, group_name: str | None = None) -> list[dict[str, Any]]:
        q = self.db.query(GroupKeyword)
        if group_name:
            q = q.filter(GroupKeyword.group_name == group_name)
        rows = q.order_by(GroupKeyword.group_name, GroupKeyword.priority.desc()).all()
        return [self._gk_to_dict(r) for r in rows]

    def create_group_keyword(self, data: dict[str, Any]) -> dict[str, Any]:
        gk = GroupKeyword(
            group_name=data["group_name"],
            keyword=data["keyword"],
            priority=data.get("priority", 0),
            is_active=data.get("is_active", True),
        )
        self.db.add(gk)
        self.db.commit()
        self.db.refresh(gk)
        return self._gk_to_dict(gk)

    def update_group_keyword(self, item_id: int, data: dict[str, Any]) -> dict[str, Any]:
        gk = self.db.query(GroupKeyword).filter(GroupKeyword.id == item_id).first()
        if not gk:
            raise NotFoundError(f"GroupKeyword id={item_id} not found")
        for key in ("group_name", "keyword", "priority", "is_active"):
            if key in data:
                setattr(gk, key, data[key])
        self.db.commit()
        self.db.refresh(gk)
        return self._gk_to_dict(gk)

    def delete_group_keyword(self, item_id: int) -> None:
        gk = self.db.query(GroupKeyword).filter(GroupKeyword.id == item_id).first()
        if not gk:
            raise NotFoundError(f"GroupKeyword id={item_id} not found")
        self.db.delete(gk)
        self.db.commit()

    # ── Contextual Overrides ────────────────────────────────────────

    def list_contextual_overrides(self) -> list[dict[str, Any]]:
        rows = self.db.query(ContextualOverride).order_by(ContextualOverride.priority.desc()).all()
        return [self._co_to_dict(r) for r in rows]

    def create_contextual_override(self, data: dict[str, Any]) -> dict[str, Any]:
        co = ContextualOverride(
            trigger_phrase=data["trigger_phrase"],
            target_group=data["target_group"],
            priority=data.get("priority", 0),
            is_active=data.get("is_active", True),
        )
        self.db.add(co)
        self.db.commit()
        self.db.refresh(co)
        return self._co_to_dict(co)

    def update_contextual_override(self, item_id: int, data: dict[str, Any]) -> dict[str, Any]:
        co = self.db.query(ContextualOverride).filter(ContextualOverride.id == item_id).first()
        if not co:
            raise NotFoundError(f"ContextualOverride id={item_id} not found")
        for key in ("trigger_phrase", "target_group", "priority", "is_active"):
            if key in data:
                setattr(co, key, data[key])
        self.db.commit()
        self.db.refresh(co)
        return self._co_to_dict(co)

    def delete_contextual_override(self, item_id: int) -> None:
        co = self.db.query(ContextualOverride).filter(ContextualOverride.id == item_id).first()
        if not co:
            raise NotFoundError(f"ContextualOverride id={item_id} not found")
        self.db.delete(co)
        self.db.commit()

    # ── Synonyms ────────────────────────────────────────────────────

    def list_synonyms(self, group_name: str | None = None) -> list[dict[str, Any]]:
        q = self.db.query(SynonymRecord)
        if group_name:
            q = q.filter(SynonymRecord.group_name == group_name)
        rows = q.order_by(SynonymRecord.group_name).all()
        return [self._syn_to_dict(r) for r in rows]

    def create_synonym(self, data: dict[str, Any]) -> dict[str, Any]:
        syn = SynonymRecord(
            group_name=data["group_name"],
            raw_value=data["raw_value"],
            normalized_value=data["normalized_value"],
            is_active=data.get("is_active", True),
        )
        self.db.add(syn)
        self.db.commit()
        self.db.refresh(syn)
        return self._syn_to_dict(syn)

    def update_synonym(self, item_id: int, data: dict[str, Any]) -> dict[str, Any]:
        syn = self.db.query(SynonymRecord).filter(SynonymRecord.id == item_id).first()
        if not syn:
            raise NotFoundError(f"SynonymRecord id={item_id} not found")
        for key in ("group_name", "raw_value", "normalized_value", "is_active"):
            if key in data:
                setattr(syn, key, data[key])
        self.db.commit()
        self.db.refresh(syn)
        return self._syn_to_dict(syn)

    def delete_synonym(self, item_id: int) -> None:
        syn = self.db.query(SynonymRecord).filter(SynonymRecord.id == item_id).first()
        if not syn:
            raise NotFoundError(f"SynonymRecord id={item_id} not found")
        self.db.delete(syn)
        self.db.commit()

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

    def create_validation_constant(self, data: dict[str, Any]) -> dict[str, Any]:
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
        return {"id": vc.id, "constant_name": vc.constant_name, "value": vc.value}

    def update_validation_constant(self, item_id: int, data: dict[str, Any]) -> dict[str, Any]:
        vc = self.db.query(ValidationConstant).filter(ValidationConstant.id == item_id).first()
        if not vc:
            raise NotFoundError(f"ValidationConstant id={item_id} not found")
        if "value" in data:
            vc.value = data["value"]
        if "description" in data:
            vc.description = data["description"]
        self.db.commit()
        self.db.refresh(vc)
        return {"id": vc.id, "constant_name": vc.constant_name, "value": vc.value}

    def delete_validation_constant(self, item_id: int) -> None:
        vc = self.db.query(ValidationConstant).filter(ValidationConstant.id == item_id).first()
        if not vc:
            raise NotFoundError(f"ValidationConstant id={item_id} not found")
        self.db.delete(vc)
        self.db.commit()

    # ── Validation Rules ────────────────────────────────────────────

    def list_validation_rules(self) -> list[dict[str, Any]]:
        rows = self.db.query(ValidationRule).order_by(ValidationRule.item_type).all()
        return [self._vr_to_dict(r) for r in rows]

    def create_validation_rule(self, data: dict[str, Any]) -> dict[str, Any]:
        existing = (
            self.db.query(ValidationRule)
            .filter(ValidationRule.item_type == data["item_type"])
            .first()
        )
        if existing:
            raise ValidationError(f"Rule for item_type '{data['item_type']}' already exists")
        vr = ValidationRule(
            item_type=data["item_type"],
            required_params=data.get("required_params", []),
            forbidden_params=data.get("forbidden_params", []),
            optional_params=data.get("optional_params", []),
            logical_conditions=data.get("logical_conditions"),
            is_active=data.get("is_active", True),
        )
        self.db.add(vr)
        self.db.commit()
        self.db.refresh(vr)
        return self._vr_to_dict(vr)

    def update_validation_rule(self, item_id: int, data: dict[str, Any]) -> dict[str, Any]:
        vr = self.db.query(ValidationRule).filter(ValidationRule.id == item_id).first()
        if not vr:
            raise NotFoundError(f"ValidationRule id={item_id} not found")
        for key in ("required_params", "forbidden_params", "optional_params", "logical_conditions", "is_active"):
            if key in data:
                setattr(vr, key, data[key])
        self.db.commit()
        self.db.refresh(vr)
        return self._vr_to_dict(vr)

    def delete_validation_rule(self, item_id: int) -> None:
        vr = self.db.query(ValidationRule).filter(ValidationRule.id == item_id).first()
        if not vr:
            raise NotFoundError(f"ValidationRule id={item_id} not found")
        self.db.delete(vr)
        self.db.commit()

    # ── Cache ───────────────────────────────────────────────────────

    def reload_cache(self) -> dict[str, Any]:
        try:
            from services.agent.parsing.dictionaries import reload_dictionaries

            reload_dictionaries()
        except ImportError:
            pass

        return {"status": "ok", "message": "Cache reloaded"}

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
        return {
            "id": r.id,
            "item_type": r.item_type,
            "required_params": r.required_params,
            "forbidden_params": r.forbidden_params,
            "optional_params": r.optional_params,
            "logical_conditions": r.logical_conditions,
            "is_active": r.is_active,
        }
