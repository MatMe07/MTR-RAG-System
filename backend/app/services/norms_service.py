from typing import Any

from sqlalchemy.orm import Session

from app.models.sqlalchemy.all_models import MtrItem

_SEARCH_FIELDS = ("gost_tu", "standard", "name")


class NormsService:
    def __init__(self, db: Session):
        self.db = db

    def search_norms(
        self,
        query: str,
        limit: int = 20,
        document_type: str | None = None,
    ) -> list[dict[str, Any]]:
        q = self.db.query(MtrItem)
        if document_type:
            q = q.filter(MtrItem.item_type == document_type)

        # Регистронезависимый поиск делаем в Python: SQLite LOWER() не
        # приводит кириллицу, поэтому ilike('...') не матчит «Отвод» и «отвод».
        items = q.all()
        needle = (query or "").strip().lower()
        if needle:
            items = [
                it for it in items
                if any(needle in (getattr(it, f, None) or "").lower() for f in _SEARCH_FIELDS)
            ]

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
            for item in items[:limit]
        ]
