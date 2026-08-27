from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps.auth import require_role
from app.core.exceptions import AppException
from app.core.constants import UserRole
from app.services.audit_service import AuditService

router = APIRouter()


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: str | None = None
    user_id: str | None = None
    action: str
    data: dict[str, Any] = {}
    created_at: str | None = None


@router.get("/logs", response_model=list[AuditLogEntry])
def get_logs(
    request_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_role(UserRole.AUDITOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        filters: dict[str, Any] = {}
        if request_id:
            filters["request_id"] = request_id
        if user_id:
            filters["user_id"] = user_id
        if action:
            filters["action"] = action
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date

        svc = AuditService(db)
        return svc.get_logs(filters=filters or None, limit=limit, offset=offset)
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to fetch audit logs: {e}")
