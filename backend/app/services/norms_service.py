from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.sqlalchemy.all_models import MtrItem


class NormsService:
    def __init__(self, db: Session):
        self.db = db

    def search_norms(
        self,
        query: str,
        limit: int = 20,
        document_type: str | None = None,
    ) -> list[dict[str, Any]]:
        q = self.db.query(MtrItem).filter(
            or_(
                MtrItem.gost_tu.ilike(f"%{query}%"),
                MtrItem.standard.ilike(f"%{query}%"),
                MtrItem.name.ilike(f"%{query}%"),
            )
        )

        if document_type:
            q = q.filter(MtrItem.item_type == document_type)

        items = q.limit(limit).all()

        return [
            {
                "ksm_code": item.ksm_code,
                "mtr_code": item.mtr_code,
                "name": item.name,
                "designation": item.designation,
                "item_type": item.item_type,
                "gost_tu": item.gost_tu,
                "standard": item.standard,
            }
            for item in items
        ]
