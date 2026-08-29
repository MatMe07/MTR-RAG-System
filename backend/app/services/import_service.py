# services/import_service.py
"""Формализованные процедуры импорта данных (2E).

2E.1 каталог (upsert в mtr_items с историей изменений + candidate_items);
2E.2 складские остатки (candidate_items);
2E.3 граф (pipeline_edges).

После успешного импорта — сброс кешей репозитория (Redis + in-memory)
и запись в журнал (Log).
"""

from typing import Any, List, Optional

from sqlalchemy.orm import Session

from app.models.sqlalchemy.all_models import (
    CandidateItem,
    MtrItem,
    MtrItemHistory,
    PipelineEdge,
)


def _flatten_props(props: Any) -> dict:
    if not isinstance(props, dict):
        return {}
    flat: dict = {}
    for k, v in props.items():
        if isinstance(v, dict) and "value" in v:
            flat[k] = v["value"]
        elif v is not None:
            flat[k] = v
    return flat


class ImportService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # 2E.1 Каталог
    # ------------------------------------------------------------------
    def import_catalog(self, items: List[dict], changed_by: Optional[str] = None) -> dict:
        created = 0
        updated = 0
        errors: List[str] = []

        for row in items:
            if not isinstance(row, dict):
                errors.append(f"invalid row: {row!r}")
                continue

            codes = row.get("codes") or {}
            mtr_code = codes.get("mtr_code")
            ksm_code = codes.get("ksm_code")

            if not mtr_code:
                errors.append(f"row без mtr_code: {row.get('name') or row.get('designation') or '?'}")
                continue
            item_type = row.get("item_type")
            if not item_type:
                errors.append(f"row {mtr_code}: нет item_type")
                continue

            props = _flatten_props(row.get("properties"))
            name = row.get("name") or row.get("designation") or mtr_code

            existing = None
            q = self.db.query(MtrItem)
            if mtr_code:
                existing = q.filter(MtrItem.mtr_code == mtr_code).first()
            if existing is None and ksm_code:
                existing = q.filter(MtrItem.ksm_code == ksm_code).first()

            if existing is not None:
                self.db.add(
                    MtrItemHistory(
                        mtr_code=existing.mtr_code,
                        changed_by=changed_by,
                        old_attributes=existing.attributes or {},
                        new_attributes=props,
                    )
                )
                existing.mtr_code = mtr_code
                if ksm_code:
                    existing.ksm_code = ksm_code
                existing.card_id = row.get("card_id") or existing.card_id
                existing.item_type = item_type
                existing.subtype = row.get("subtype") or existing.subtype
                existing.name = name
                existing.designation = row.get("designation") or existing.designation
                existing.attributes = props
                existing.gost_tu = props.get("gost_tu") or props.get("gost_or_tu")
                existing.standard = props.get("standard")
                existing.stock_qty = float(props.get("stock_qty", 0) or 0)
                existing.unit = props.get("unit", "pcs") or "pcs"
                existing.is_synthetic = bool(props.get("synthetic", False))
                updated += 1
            else:
                self.db.add(
                    MtrItem(
                        mtr_code=mtr_code,
                        ksm_code=ksm_code,
                        card_id=row.get("card_id"),
                        item_type=item_type,
                        subtype=row.get("subtype"),
                        name=name,
                        designation=row.get("designation"),
                        attributes=props,
                        gost_tu=props.get("gost_tu") or props.get("gost_or_tu"),
                        standard=props.get("standard"),
                        stock_qty=float(props.get("stock_qty", 0) or 0),
                        unit=props.get("unit", "pcs") or "pcs",
                        is_synthetic=bool(props.get("synthetic", False)),
                    )
                )
                created += 1

            if ksm_code:
                self._upsert_stock(ksm_code, short_text=name, quantity=float(props.get("stock_qty", 0) or 0))

        self._finish("admin.imports.catalog", {"created": created, "updated": updated, "errors": len(errors)}, changed_by)
        return {"created": created, "updated": updated, "errors": errors}

    # ------------------------------------------------------------------
    # 2E.2 Складские остатки
    # ------------------------------------------------------------------
    def import_stock(self, rows: List[dict], changed_by: Optional[str] = None) -> dict:
        errors: List[str] = []
        total = 0
        for row in rows or []:
            ksm = (row or {}).get("ksm_code")
            if not ksm:
                errors.append(f"строка без ksm_code: {row!r}")
                continue
            quantity = row.get("quantity", 0)
            cost = row.get("cost")
            item = self.db.query(CandidateItem).filter(CandidateItem.ksm_code == ksm).first()
            if item is None:
                errors.append(f"ksm_code не найден в каталоге: {ksm}")
                continue
            item.quantity = float(quantity or 0)
            if cost is not None:
                item.cost = float(cost)
            total += 1

        self._finish("admin.imports.stock", {"total": total, "errors": len(errors)}, changed_by)
        return {"total": total, "errors": errors}

    # ------------------------------------------------------------------
    # 2E.3 Граф
    # ------------------------------------------------------------------
    def import_graph(self, graph: dict, changed_by: Optional[str] = None) -> dict:
        edges = (graph or {}).get("edges", []) or []
        total = 0
        for edge in edges:
            from_ksm = edge.get("from") or edge.get("from_ksm")
            to_ksm = edge.get("to") or edge.get("to_ksm")
            if not from_ksm or not to_ksm:
                continue
            self.db.add(
                PipelineEdge(
                    from_ksm=from_ksm,
                    to_ksm=to_ksm,
                    connection_type=edge.get("connection_type"),
                    distance_m=edge.get("distance_m"),
                )
            )
            total += 1

        self._finish("admin.imports.graph", {"edges": total}, changed_by)
        return {"edges": total}

    # ------------------------------------------------------------------
    # Вспомогательные
    # ------------------------------------------------------------------
    def _upsert_stock(self, ksm: str, short_text: Optional[str] = None, quantity: float = 0) -> None:
        item = self.db.query(CandidateItem).filter(CandidateItem.ksm_code == ksm).first()
        if item is None:
            self.db.add(
                CandidateItem(
                    ksm_code=ksm,
                    short_text=short_text,
                    quantity=quantity,
                    stock_balance=quantity,
                )
            )

    def _finish(self, action: str, payload: dict, changed_by: Optional[str]) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        try:
            from app.services.audit_service import AuditService

            AuditService(self.db).log(None, changed_by, action, payload)
        except Exception:  # noqa: BLE001 — аудит не блокирует импорт
            self.db.rollback()

        try:
            from app.services.agent.repository.repository_factory import reset_repository

            reset_repository()
        except Exception:  # noqa: BLE001
            pass