# backend/app/services/expert_service.py

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models import ExpertMatch, ExpertReviewLog, MTRItem, KSMItem
from app.schemas import ExpertReviewRequest


class ExpertService:
    def __init__(self, db: Session):
        self.db = db

    def save_review(self, request: ExpertReviewRequest) -> Dict[str, Any]:
        ksm = self.db.query(KSMItem).filter(
            KSMItem.ksm_code == request.candidate_ksm_code
        ).first()
        if not ksm:
            return {
                "success": False,
                "message": f"Кандидат с кодом {request.candidate_ksm_code} не найден"
            }

        log = ExpertReviewLog(
            search_id=request.search_id,
            candidate_ksm_code=request.candidate_ksm_code,
            user_comment=request.comment,
            expert_decision=request.decision,
            reviewed_by=request.reviewer
        )
        self.db.add(log)

        mtr = self.db.query(MTRItem).filter(
            MTRItem.ksm_code == request.candidate_ksm_code
        ).first()

        if mtr and request.decision in ["approve", "reject"]:
            status = "соответствует" if request.decision == "approve" else "не соответствует"
            
            match = ExpertMatch(
                lot=mtr.lot,
                requested_mtr_code=mtr.mtr_code,
                candidate_ksm_code=request.candidate_ksm_code,
                expert_status=status,
                expert_reason=request.comment,
                confirmed_by=request.reviewer
            )
            self.db.add(match)

        self.db.commit()

        return {
            "success": True,
            "message": "Решение сохранено",
            "review_id": log.id
        }

    def get_review_history(
        self,
        ksm_code: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        query = self.db.query(ExpertReviewLog)
        
        if ksm_code:
            query = query.filter(ExpertReviewLog.candidate_ksm_code == ksm_code)
        
        logs = query.order_by(
            ExpertReviewLog.reviewed_at.desc()
        ).limit(limit).all()

        return [
            {
                "id": log.id,
                "search_id": log.search_id,
                "candidate_ksm_code": log.candidate_ksm_code,
                "decision": log.expert_decision,
                "comment": log.user_comment,
                "reviewed_by": log.reviewed_by,
                "reviewed_at": log.reviewed_at.isoformat() if log.reviewed_at else None
            }
            for log in logs
        ]

    def get_stats(self) -> Dict[str, Any]:
        total = self.db.query(ExpertReviewLog).count()
        approved = self.db.query(ExpertReviewLog).filter(
            ExpertReviewLog.expert_decision == "approve"
        ).count()
        rejected = self.db.query(ExpertReviewLog).filter(
            ExpertReviewLog.expert_decision == "reject"
        ).count()
        need_more = self.db.query(ExpertReviewLog).filter(
            ExpertReviewLog.expert_decision == "need_more_info"
        ).count()

        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "need_more_info": need_more
        }
