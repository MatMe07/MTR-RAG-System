from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.sqlalchemy.all_models import MtrItem


class ComponentService:
    def __init__(self, db: Session):
        self.db = db

    def get_component(
        self, identifier: str, detail_level: str = "full"
    ) -> dict[str, Any]:
        item = (
            self.db.query(MtrItem)
            .filter(
                (MtrItem.ksm_code == identifier)
                | (MtrItem.mtr_code == identifier)
            )
            .first()
        )
        if not item:
            raise NotFoundError(f"Component '{identifier}' not found")

        result: dict[str, Any] = {
            "ksm_code": item.ksm_code,
            "mtr_code": item.mtr_code,
            "card_id": item.card_id,
            "item_type": item.item_type,
            "subtype": item.subtype,
            "name": item.name,
            "designation": item.designation,
            "gost_tu": item.gost_tu,
            "standard": item.standard,
            "is_synthetic": item.is_synthetic,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }

        if detail_level == "full":
            result["attributes"] = item.attributes
            result["stock_qty"] = item.stock_qty
            result["unit"] = item.unit

        return result
