from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.exceptions import AppException
from app.services.norms_service import NormsService

router = APIRouter()


class NormSearchRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query: str
    limit: int = 20
    document_type: Optional[str] = None


class NormItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ksm_code: str
    mtr_code: str | None = None
    name: str
    designation: str | None = None
    item_type: str
    gost_tu: str | None = None
    standard: str | None = None


@router.post("/search", response_model=list[NormItem])
def search_norms(body: NormSearchRequest, db: Session = Depends(get_db)):
    try:
        svc = NormsService(db)
        return svc.search_norms(
            query=body.query,
            limit=body.limit,
            document_type=body.document_type,
        )
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Norms search failed: {e}")
