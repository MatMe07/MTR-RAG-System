from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.exceptions import AppException
from app.services.component_service import ComponentService

router = APIRouter()


@router.get("/{ksm_code}")
def get_component(
    ksm_code: str,
    detail_level: str = Query("full", pattern="^(basic|with_stock|full)$"),
    db: Session = Depends(get_db),
):
    try:
        svc = ComponentService(db)
        return svc.get_component(ksm_code, detail_level=detail_level)
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to get component: {e}")
