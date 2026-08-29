from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps.auth import require_role
from app.core.exceptions import AppException
from app.core.constants import UserRole
from app.services.admin_service import AdminService

router = APIRouter()


def _get_admin_service(db: Session, current_user: dict) -> AdminService:
    return AdminService(db)


# ── Generic dictionary endpoints ─────────────────────────────────────

@router.get("/dictionaries/{dict_name}")
def list_dict_entries(
    dict_name: str,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = _get_admin_service(db, current_user)
        method = {
            "group_keywords": svc.list_group_keywords,
            "contextual_overrides": svc.list_contextual_overrides,
            "synonyms": svc.list_synonyms,
            "validation_constants": svc.list_validation_constants,
        }.get(dict_name)
        if not method:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(f"Dictionary '{dict_name}' not found")
        return method()
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to list '{dict_name}': {e}")


@router.post("/dictionaries/{dict_name}")
def create_dict_entry(
    dict_name: str,
    body: dict[str, Any],
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = _get_admin_service(db, current_user)
        method = {
            "group_keywords": svc.create_group_keyword,
            "contextual_overrides": svc.create_contextual_override,
            "synonyms": svc.create_synonym,
            "validation_constants": svc.create_validation_constant,
        }.get(dict_name)
        if not method:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(f"Dictionary '{dict_name}' not found")
        return method(body, current_user)
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to create entry in '{dict_name}': {e}")


@router.put("/dictionaries/{dict_name}/{item_id}")
def update_dict_entry(
    dict_name: str,
    item_id: int,
    body: dict[str, Any],
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = _get_admin_service(db, current_user)
        method = {
            "group_keywords": svc.update_group_keyword,
            "contextual_overrides": svc.update_contextual_override,
            "synonyms": svc.update_synonym,
            "validation_constants": svc.update_validation_constant,
        }.get(dict_name)
        if not method:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(f"Dictionary '{dict_name}' not found")
        return method(item_id, body, current_user)
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to update entry in '{dict_name}': {e}")


@router.delete("/dictionaries/{dict_name}/{item_id}")
def delete_dict_entry(
    dict_name: str,
    item_id: int,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = _get_admin_service(db, current_user)
        method = {
            "group_keywords": svc.delete_group_keyword,
            "contextual_overrides": svc.delete_contextual_override,
            "synonyms": svc.delete_synonym,
            "validation_constants": svc.delete_validation_constant,
        }.get(dict_name)
        if not method:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(f"Dictionary '{dict_name}' not found")
        method(item_id, current_user)
        return {"status": "deleted"}
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to delete entry in '{dict_name}': {e}")


@router.post("/dictionaries/reload")
def reload_cache(
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = _get_admin_service(db, current_user)
        return svc.reload_cache()
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to reload cache: {e}")


# ── Validation Rules ─────────────────────────────────────────────────

class ValidationRuleCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_type: str
    required_params: list[str] = []
    forbidden_params: list[str] = []
    optional_params: list[str] = []
    logical_conditions: dict | None = None
    is_active: bool = True


@router.get("/validation-rules")
def list_validation_rules(
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = _get_admin_service(db, current_user)
        return svc.list_validation_rules()
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to list validation rules: {e}")


@router.post("/validation-rules")
def create_validation_rule(
    body: ValidationRuleCreate,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = _get_admin_service(db, current_user)
        return svc.create_validation_rule(body.model_dump(), current_user)
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to create validation rule: {e}")


@router.put("/validation-rules/{item_type}")
def update_validation_rule(
    item_type: str,
    body: dict[str, Any],
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = _get_admin_service(db, current_user)
        rules = svc.list_validation_rules()
        existing = next((r for r in rules if r["item_type"] == item_type), None)
        if not existing:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(f"Validation rule for '{item_type}' not found")
        return svc.update_validation_rule(existing["id"], body, current_user)
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to update validation rule for '{item_type}': {e}")


@router.delete("/validation-rules/{item_type}")
def delete_validation_rule(
    item_type: str,
    current_user: dict = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = _get_admin_service(db, current_user)
        rules = svc.list_validation_rules()
        existing = next((r for r in rules if r["item_type"] == item_type), None)
        if not existing:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(f"Validation rule for '{item_type}' not found")
        svc.delete_validation_rule(existing["id"], current_user)
        return {"status": "deleted"}
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to delete validation rule for '{item_type}': {e}")
