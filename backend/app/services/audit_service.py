from typing import Any
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.sqlalchemy.all_models import Log


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        request_id: str | None,
        user_id: str | None,
        action: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        entry = Log(
            request_id=request_id,
            user_id=user_id,
            action=action,
            data=data or {},
        )
        self.db.add(entry)
        self.db.commit()

    def get_logs(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = self.db.query(Log)

        if filters:
            if "request_id" in filters:
                query = query.filter(Log.request_id == filters["request_id"])
            if "user_id" in filters:
                query = query.filter(Log.user_id == filters["user_id"])
            if "action" in filters:
                query = query.filter(Log.action == filters["action"])
            if "from_date" in filters:
                query = query.filter(Log.created_at >= filters["from_date"])
            if "to_date" in filters:
                query = query.filter(Log.created_at <= filters["to_date"])

        logs = (
            query.order_by(Log.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [
            {
                "id": log.id,
                "request_id": str(log.request_id) if log.request_id else None,
                "user_id": log.user_id,
                "action": log.action,
                "data": log.data,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
