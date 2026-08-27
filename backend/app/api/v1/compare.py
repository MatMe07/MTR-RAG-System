from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.exceptions import AppException
from app.services.compare_service import CompareService

router = APIRouter()


class CompareRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ksm_code_1: str
    ksm_code_2: str


class CompareResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ksm1: str
    ksm2: str
    matches: list[dict]
    mismatches: list[dict]
    only_in_first: list[str]
    only_in_second: list[str]
    match_count: int
    mismatch_count: int
    similarity: float


@router.post("/", response_model=CompareResponse)
def compare(body: CompareRequest, db: Session = Depends(get_db)):
    try:
        svc = CompareService(db)
        return svc.compare(body.ksm_code_1, body.ksm_code_2)
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Comparison failed: {e}")
