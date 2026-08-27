from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.sqlalchemy.all_models import MtrItem


class CompareService:
    def __init__(self, db: Session):
        self.db = db

    def compare(self, ksm1: str, ksm2: str) -> dict[str, Any]:
        item1 = self._get_item(ksm1)
        item2 = self._get_item(ksm2)

        attrs1 = item1.attributes or {}
        attrs2 = item2.attributes or {}

        all_keys = sorted(set(list(attrs1.keys()) + list(attrs2.keys())))

        matches: list[dict[str, Any]] = []
        mismatches: list[dict[str, Any]] = []
        only_in_first: list[str] = []
        only_in_second: list[str] = []

        for key in all_keys:
            val1 = attrs1.get(key)
            val2 = attrs2.get(key)

            if val1 is None:
                only_in_second.append(key)
            elif val2 is None:
                only_in_first.append(key)
            else:
                entry = {
                    "field": key,
                    f"value_{ksm1}": val1,
                    f"value_{ksm2}": val2,
                }
                if val1 == val2:
                    matches.append(entry)
                else:
                    mismatches.append(entry)

        return {
            "ksm1": ksm1,
            "ksm2": ksm2,
            "matches": matches,
            "mismatches": mismatches,
            "only_in_first": only_in_first,
            "only_in_second": only_in_second,
            "match_count": len(matches),
            "mismatch_count": len(mismatches),
            "similarity": (
                len(matches) / len(all_keys) if all_keys else 0.0
            ),
        }

    def _get_item(self, ksm_code: str) -> MtrItem:
        item = (
            self.db.query(MtrItem)
            .filter(MtrItem.ksm_code == ksm_code)
            .first()
        )
        if not item:
            raise NotFoundError(f"Component with KSM code '{ksm_code}' not found")
        return item
