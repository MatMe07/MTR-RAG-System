from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.sqlalchemy.all_models import MtrItem

DETAIL_LEVELS = ("basic", "with_stock", "full")


class ComponentService:
    def __init__(self, db: Session):
        self.db = db

    def get_component(
        self, identifier: str, detail_level: str = "full"
    ) -> dict[str, Any]:
        """Карточка компонента с уровнем детализации (2C).

        basic      — паспортный минимум (без attributes и остатков);
        with_stock — + attributes, stock_qty, unit;
        full       — уже с обогащением (история/паспорт при наличии).
        """
        if detail_level not in DETAIL_LEVELS:
            raise ValidationError(
                f"detail_level must be one of {DETAIL_LEVELS}, got '{detail_level}'"
            )

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
            "detail_level": detail_level,
            "is_synthetic": item.is_synthetic,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }

        if detail_level in ("with_stock", "full"):
            result["attributes"] = item.attributes
            result["stock_qty"] = item.stock_qty
            result["unit"] = item.unit

        return result