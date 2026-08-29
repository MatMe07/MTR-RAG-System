# repository/providers/passport_provider.py
"""Провайдер параметров паспортов из PostgreSQL (documents +
extracted_characteristics). Если документ не загружен в БД — возвращает None,
и вызывающий слой использует legacy fallback (регэкспы по raw-файлам).
"""

import logging
import re
from typing import Any, Dict, Optional

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


class PassportProvider:
    def __init__(self, access_logger: Optional[Any] = None):
        self._access_logger = access_logger

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

    def get_passport_params(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Параметры паспорта из PG; None — документ не загружен в БД."""
        if not document_id:
            return None
        try:
            from app.db.session import SessionLocal
            from app.models.sqlalchemy.all_models import Document, ExtractedCharacteristic

            db = SessionLocal()
            try:
                doc = (
                    db.query(Document)
                    .filter(Document.document_id == document_id)
                    .first()
                )
                if doc is None:
                    self._log("postgresql", fallback=True, reason="документ не загружен в БД")
                    return None

                rows = (
                    db.query(ExtractedCharacteristic)
                    .filter(ExtractedCharacteristic.document_id == document_id)
                    .all()
                )
            finally:
                db.close()

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
        except Exception as e:
            log.warning("PassportProvider: запрос не удался: %s", e)
            self._log("postgresql", fallback=True, reason=f"ошибка БД: {e}")
            return None