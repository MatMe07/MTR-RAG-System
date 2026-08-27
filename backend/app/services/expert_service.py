from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.sqlalchemy.all_models import ExpertMatch


class ExpertService:
    def __init__(self, db: Session):
        self.db = db

    def get_pending_reviews(self) -> list[dict[str, Any]]:
        rows = (
            self.db.query(ExpertMatch)
            .filter(ExpertMatch.expert_status == "pending")
            .order_by(ExpertMatch.created_at.desc())
            .all()
        )
        return [self._to_dict(r) for r in rows]

    def submit_review(
        self, review_id: int, decision: str, reason: str | None = None, reviewed_by: str | None = None
    ) -> dict[str, Any]:
        match = self.db.query(ExpertMatch).filter(ExpertMatch.id == review_id).first()
        if not match:
            raise NotFoundError(f"Review with id {review_id} not found")

        valid_decisions = {"confirmed", "rejected", "needs_info"}
        if decision not in valid_decisions:
            raise ValidationError(f"Decision must be one of {valid_decisions}")

        match.expert_status = decision
        match.expert_reason = reason
        match.confirmed_by = reviewed_by
        match.confirmed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(match)

        return self._to_dict(match)

    def get_pending_passports(self) -> list[dict[str, Any]]:
        rows = (
            self.db.query(ExpertMatch)
            .filter(ExpertMatch.expert_status == "pending")
            .order_by(ExpertMatch.created_at.desc())
            .all()
        )
        return [self._to_dict(r) for r in rows]

    def link_passport(
        self, document_id: str, ksm_code: str
    ) -> dict[str, Any]:
        existing = (
            self.db.query(ExpertMatch)
            .filter(
                ExpertMatch.candidate_ksm_code == ksm_code,
                ExpertMatch.requested_mtr_code == document_id,
            )
            .first()
        )
        if existing:
            raise ValidationError(
                f"Link between document '{document_id}' and KSM '{ksm_code}' already exists"
            )

        match = ExpertMatch(
            requested_mtr_code=document_id,
            candidate_ksm_code=ksm_code,
            expert_status="pending",
        )
        self.db.add(match)
        self.db.commit()
        self.db.refresh(match)

        return self._to_dict(match)

    def _to_dict(self, m: ExpertMatch) -> dict[str, Any]:
        return {
            "id": m.id,
            "match_id": m.match_id,
            "lot": m.lot,
            "requested_mtr_code": m.requested_mtr_code,
            "candidate_ksm_code": m.candidate_ksm_code,
            "expert_status": m.expert_status,
            "expert_reason": m.expert_reason,
            "confirmed_by": m.confirmed_by,
            "confirmed_at": m.confirmed_at.isoformat() if m.confirmed_at else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
