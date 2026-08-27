from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps.auth import require_role
from app.core.exceptions import AppException
from app.core.constants import UserRole
from app.services.expert_service import ExpertService

router = APIRouter()


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision: str
    reason: Optional[str] = None


class LinkPassportRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    ksm_code: str


@router.get("/reviews")
def list_reviews(
    current_user: dict = Depends(require_role(UserRole.EXPERT, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = ExpertService(db)
        return svc.get_pending_reviews()
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to list reviews: {e}")


@router.post("/review/{review_id}")
def submit_review(
    review_id: int,
    body: ReviewDecisionRequest,
    current_user: dict = Depends(require_role(UserRole.EXPERT, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = ExpertService(db)
        return svc.submit_review(
            review_id=review_id,
            decision=body.decision,
            reason=body.reason,
            reviewed_by=current_user["username"],
        )
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to submit review: {e}")


@router.get("/passports/pending")
def pending_passports(
    current_user: dict = Depends(require_role(UserRole.EXPERT, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = ExpertService(db)
        return svc.get_pending_passports()
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to list pending passports: {e}")


@router.post("/passports/link")
def link_passport(
    body: LinkPassportRequest,
    current_user: dict = Depends(require_role(UserRole.EXPERT, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    try:
        svc = ExpertService(db)
        return svc.link_passport(body.document_id, body.ksm_code)
    except AppException:
        raise
    except Exception as e:
        from app.core.exceptions import InternalError

        raise InternalError(f"Failed to link passport: {e}")
