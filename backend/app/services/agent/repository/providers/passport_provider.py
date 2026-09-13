# repository/providers/passport_provider.py
"""Провайдер параметров паспортов из PostgreSQL (documents +
extracted_characteristics + document_links).

Если документ не загружен в БД — методы возвращают None, и вызывающий слой
использует legacy fallback (регэкспы по raw-файлам).
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("mtr.repository.passport")

# Параметры, извлекаемые из текста паспорта. Имена полей соответствуют
# контракту ToolDAL.get_passport_params.
_PARAM_CAST = {
    "dn": lambda v: int(float(v)),
    "pn": float,
    "angle": lambda v: int(float(v)),
    "wall_thickness": float,
    "material": str,
    "medium": str,
}

# Паспортное поле -> поле каталога для скоринга связей (2A.14).
_FIELD_TO_SEARCH = {
    "dn": "dn",
    "pn": "pn",
    "material": "steel_grade",
    "angle": "angle",
    "medium": "medium",
    "wall_thickness": "wall_thickness",
}

# Дефолт весов (зеркало instruments.PASSPORT_WEIGHTS). Живые веса — из
# validation_constants (passport_weights), см. _passport_weights().
DEFAULT_PASSPORT_WEIGHTS = {
    "dn": 0.30,
    "pn": 0.25,
    "material": 0.20,
    "angle": 0.15,
    "medium": 0.10,
}


def extract_passport_params(text: str) -> Dict[str, Dict[str, Any]]:
    """Извлечение параметров паспорта из текста (регэкспы по шаблонам)."""
    params: Dict[str, Dict[str, Any]] = {}

    m = re.search(r"\bDN\s*(\d+)\b", text, re.IGNORECASE)
    if m:
        params["dn"] = {"value": int(m.group(1)), "confidence": 1.0}
    m = re.search(r"\bPN\s*([\d]+(?:[.,]\d+)?)\b", text, re.IGNORECASE)
    if m:
        params["pn"] = {"value": float(m.group(1).replace(",", ".")), "confidence": 1.0}
    m = re.search(r"угол(?: наклона)?\s*(\d+)\s*град", text, re.IGNORECASE)
    if not m:
        m = re.search(r"(\d+)\s*градус", text, re.IGNORECASE)
    if m:
        params["angle"] = {"value": int(m.group(1)), "confidence": 1.0}
    m = re.search(r"толщин[ау]\s*стенки\s*(\d+(?:[.,]\d+)?)", text, re.IGNORECASE)
    if m:
        params["wall_thickness"] = {"value": float(m.group(1).replace(",", ".")), "confidence": 1.0}
    m = re.search(r"М(?:атериал|арка)\s*(?:сталь\s*)?[:\s]*([\wА-Яа-я0-9]+)", text, re.IGNORECASE)
    if m:
        params["material"] = {"value": m.group(1), "confidence": 1.0}
    m = re.search(r"Рабочая\s+среда:\s*([^\n\r\.]+)", text, re.IGNORECASE)
    if m:
        params["medium"] = {"value": m.group(1).strip(), "confidence": 0.8}

    return params


def _passport_weights() -> Dict[str, float]:
    """Веса полей паспорта из БД (validation_constants > дефолт кода)."""
    try:
        from ..rules.dynamic_rules import get_dynamic_rules

        return get_dynamic_rules().passport_weights()
    except Exception:  # noqa: BLE001
        return dict(DEFAULT_PASSPORT_WEIGHTS)


def score_suggestions(
    params: Dict[str, Dict[str, Any]],
    catalog_search: Callable[[Dict[str, Any]], List[Dict[str, Any]]],
    weights: Optional[Dict[str, float]] = None,
    param_threshold: float = 0.6,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Весовой скоринг кандидатов KSM по параметрам паспорта (аналог
    инструмента search_by_passport или 2A.14 KsmSuggestion).

    catalog_search(search_params) -> [{card, score}] — поиск по одному полю
    каталога. По каждому достоверному параметру ищем кандидатов и агрегируем
    веса совпавших полей в confidence = hit_weight / total_weight.
    """
    weights = _passport_weights() if weights is None else weights
    extracted = {
        k: v
        for k, v in params.items()
        if isinstance(v, dict) and float(v.get("confidence", 0.0)) > param_threshold
    }
    total_weight = sum(weights[k] for k in extracted if k in weights)
    if not extracted or total_weight <= 0:
        return []

    agg: Dict[str, Dict[str, Any]] = {}
    for field, meta in extracted.items():
        search_field = _FIELD_TO_SEARCH.get(field)
        if not search_field:
            continue
        try:
            hits = catalog_search({search_field: meta.get("value"), "limit": 10})
        except Exception:
            continue
        for hit in hits or []:
            card = hit.get("card") or {}
            ksm_code = (card.get("codes") or {}).get("ksm_code")
            if not ksm_code:
                continue
            entry = agg.setdefault(
                ksm_code,
                {
                    "ksm_code": ksm_code,
                    "mtr_code": (card.get("codes") or {}).get("mtr_code"),
                    "name": card.get("name") or card.get("designation"),
                    "matched": set(),
                },
            )
            entry["matched"].add(field)

    out: List[Dict[str, Any]] = []
    for ksm_code, entry in agg.items():
        hit_weight = sum(weights[f] for f in entry["matched"] if f in weights)
        confidence = round(hit_weight / total_weight, 3) if total_weight else 0.0
        out.append(
            {
                "ksm_code": ksm_code,
                "mtr_code": entry["mtr_code"],
                "name": entry["name"],
                "confidence": confidence,
                "matched_params": sorted(entry["matched"]),
            }
        )

    out.sort(key=lambda x: x["confidence"], reverse=True)
    return out[:limit]


class PassportProvider:
    def __init__(self, access_logger: Optional[Any] = None, catalog_search: Optional[Callable] = None):
        self._access_logger = access_logger
        self._catalog_search = catalog_search

    def _log(self, provider: str, fallback: bool, reason: Optional[str] = None) -> None:
        if self._access_logger is not None:
            try:
                self._access_logger.record(
                    method_name="get_passport_params",
                    provider_used=provider,
                    fallback_used=fallback,
                    fallback_reason=reason,
                )
            except Exception:
                pass

    # ------------------------------------------------------------------ helpers
    def _find_document(self, document_id: str) -> Optional[Any]:
        """Документ из PG; None — не найден/БД недоступна."""
        if not document_id:
            return None
        try:
            from app.db.session import SessionLocal
            from app.models.sqlalchemy.all_models import Document

            db = SessionLocal()
            try:
                return (
                    db.query(Document)
                    .filter(Document.document_id == document_id)
                    .first()
                )
            finally:
                db.close()
        except Exception as e:
            log.warning("PassportProvider: чтение документа не удалось: %s", e)
            return None

    # ------------------------------------------------------------------ API
    def get_passport_params(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Параметры паспорта из PG; None — документ не загружен в БД."""
        doc = self._find_document(document_id)
        if doc is None:
            self._log("postgresql", fallback=True, reason="документ не загружен в БД")
            return None
        try:
            from app.db.session import SessionLocal
            from app.models.sqlalchemy.all_models import ExtractedCharacteristic

            db = SessionLocal()
            try:
                rows = (
                    db.query(ExtractedCharacteristic)
                    .filter(ExtractedCharacteristic.document_id == document_id)
                    .all()
                )
            finally:
                db.close()
        except Exception as e:
            log.warning("PassportProvider: запрос характеристик не удался: %s", e)
            self._log("postgresql", fallback=True, reason=f"ошибка БД: {e}")
            return None

        params: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            raw = r.normalized_value if r.normalized_value is not None else r.raw_value
            if raw is None:
                continue
            cast = _PARAM_CAST.get(r.field_name, str)
            try:
                value = cast(raw)
            except (TypeError, ValueError):
                value = raw
            params[r.field_name] = {"value": value, "confidence": float(r.confidence or 0.0)}

        self._log("postgresql", fallback=False)
        return {"document_id": document_id, "params": params, "path": doc.file_path}

    def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Метаданные документа (2B.4 get_document_metadata)."""
        doc = self._find_document(document_id)
        if doc is None:
            return None
        return {
            "document_id": doc.document_id,
            "file_name": doc.file_name,
            "status": doc.ocr_status or "pending",
            "error_message": doc.error_message,
            "ocr_confidence": doc.ocr_confidence,
            "page_count": doc.page_count,
            "created_at": doc.upload_date.isoformat() if doc.upload_date else None,
            "updated_at": doc.processed_date.isoformat() if doc.processed_date else None,
        }

    def get_passport_text(self, document_id: str, page: Optional[int] = None):
        """Постраничный OCR-текст (2B.4 get_passport_text). page=None — список."""
        doc = self._find_document(document_id)
        if doc is None:
            return None
        pages = doc.page_texts or []
        if page is None:
            return pages
        return next((p.get("text", "") for p in pages if p.get("page_number") == page), "")

    def get_processing_status(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Статус обработки документа (2B.4 get_processing_status)."""
        doc = self._find_document(document_id)
        if doc is None:
            return None
        return {
            "document_id": doc.document_id,
            "ocr_status": doc.ocr_status or "unknown",
            "progress": float(doc.processing_progress or 0.0),
            "page_count": doc.page_count,
            "error_message": doc.error_message,
            "needs_review": bool(doc.needs_review),
            "task_id": doc.task_id,
        }

    def extract_params(
        self, document_id: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Извлечение параметров из постраничного текста (или переданных
        params) и запись в extracted_characteristics (идемпотентно: старые
        строки удаляются).
        """
        doc = self._find_document(document_id)
        if doc is None:
            return None
        pages = doc.page_texts or []
        text = "\n".join(str(p.get("text", "")) for p in pages)
        if params is None:
            params = extract_passport_params(text)
        elif not text.strip():
            params = {}
        if not params:
            return {}

        try:
            from app.db.session import SessionLocal
            from app.models.sqlalchemy.all_models import ExtractedCharacteristic

            db = SessionLocal()
            try:
                db.query(ExtractedCharacteristic).filter(
                    ExtractedCharacteristic.document_id == document_id
                ).delete()
                for field, info in params.items():
                    value = info.get("value")
                    db.add(
                        ExtractedCharacteristic(
                            document_id=document_id,
                            field_name=field,
                            raw_value=str(value),
                            normalized_value=str(value),
                            confidence=float(info.get("confidence", 1.0)),
                            source_fragment="ocr",
                            source_type="regex",
                            is_verified=False,
                            created_at=datetime.now(timezone.utc),
                        )
                    )
                db.commit()
            finally:
                db.close()
        except Exception as e:
            log.warning("PassportProvider: извлечение параметров не удалось: %s", e)
            return None
        return params

    def link_passport_to_ksm(
        self,
        document_id: str,
        ksm_code: str,
        confidence: float,
        method: str = "semantic",
        needs_review: bool = False,
        reviewed_by: Optional[str] = None,
    ) -> bool:
        """Создание/обновление связи паспорт→KSM в document_links (2B.4)."""
        if not document_id or not ksm_code:
            return False
        try:
            from app.db.session import SessionLocal
            from app.models.sqlalchemy.all_models import DocumentLink

            db = SessionLocal()
            try:
                row = (
                    db.query(DocumentLink)
                    .filter(
                        DocumentLink.document_id == document_id,
                        DocumentLink.ksm_code == ksm_code,
                    )
                    .first()
                )
                if row is None:
                    row = DocumentLink(document_id=document_id, ksm_code=ksm_code)
                    db.add(row)
                row.confidence = float(confidence)
                row.method = method or "semantic"
                row.needs_review = bool(needs_review)
                row.linked = not needs_review
                if not needs_review and reviewed_by:
                    row.reviewed_by = reviewed_by
                    row.reviewed_at = datetime.now(timezone.utc)
                db.commit()
            finally:
                db.close()
            return True
        except Exception as e:
            log.warning("PassportProvider: связывание паспорта не удалось: %s", e)
            return False

    def suggest_ksm_links(
        self,
        document_id: str,
        limit: int = 5,
        catalog_search: Optional[Callable] = None,
    ) -> List[Dict[str, Any]]:
        """Кандидаты KSM по параметрам извлечённого паспорта (2B.4
        suggest_ksm_links → 2A.14 KsmSuggestion). Без catalog_search —
        пустой список (скоринг подключает репозиторий).
        """
        search = catalog_search or self._catalog_search
        if search is None:
            return []
        pp = self.get_passport_params(document_id)
        if pp is None:
            return []
        return score_suggestions((pp.get("params") or {}), search, limit=limit)
