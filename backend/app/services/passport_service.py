import logging
import uuid
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.sqlalchemy.all_models import Document, DocumentLink, ExtractedCharacteristic

log = logging.getLogger("mtr.passport_service")


def _uploads_dir() -> Path:
    configured = (settings.DOCUMENT_UPLOAD_DIR or "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "data" / "uploads"


def _eager_mode() -> bool:
    try:
        from app.workers.celery_app import celery_app

        return bool(celery_app.conf.get("task_always_eager"))
    except Exception:  # noqa: BLE001
        return False


class PassportService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ upload
    def upload_document(self, file: Any) -> dict[str, Any]:
        document_id = str(uuid.uuid4())
        file_path = self._save_upload(file)
        doc = Document(
            document_id=document_id,
            file_name=getattr(file, "filename", "unknown"),
            file_path=file_path,
            document_type="passport",
            ocr_status="pending",
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        task_id = self._enqueue_process(doc.document_id, file_path)
        doc.task_id = task_id
        self.db.commit()

        return {"document_id": document_id, "status": "pending", "task_id": task_id}

    def reprocess(self, document_id: str) -> dict[str, Any]:
        doc = self._get_document(document_id)
        if doc.ocr_status == "processing":
            raise ValidationError(f"Document '{document_id}' is already being processed")

        self.db.query(ExtractedCharacteristic).filter(
            ExtractedCharacteristic.document_id == document_id
        ).delete()
        self.db.query(DocumentLink).filter(DocumentLink.document_id == document_id).delete()

        doc.ocr_status = "pending"
        doc.processing_progress = 0.0
        doc.error_message = None
        doc.needs_review = False
        doc.processed_date = None
        # Очистка коммитится до постановки задачи, иначе в eager-режиме
        # (задача в отдельном потоке) незакоммиченные DELETE держат write-lock.
        self.db.commit()

        task_id = self._enqueue_process(document_id, doc.file_path, task_name="passport.reprocess")
        doc.task_id = task_id
        self.db.commit()
        return {"document_id": document_id, "status": "pending", "task_id": task_id}

    def get_status(self, document_id: str) -> dict[str, Any]:
        doc = self._get_document(document_id)
        progress = float(doc.processing_progress or 0.0)
        task_state: Optional[str] = None
        stage: Optional[str] = None

        if doc.task_id and not _eager_mode():
            state, meta = self._task_state(doc.task_id)
            if state is not None:
                task_state = state
                if isinstance(meta, dict):
                    stage = meta.get("stage")
                    meta_progress = meta.get("progress")
                    if isinstance(meta_progress, (int, float)):
                        progress = float(meta_progress)

        return {
            "document_id": doc.document_id,
            "file_name": doc.file_name,
            "document_type": doc.document_type,
            "ocr_status": doc.ocr_status,
            "task_state": task_state,
            "progress": progress,
            "stage": stage,
            "ocr_confidence": doc.ocr_confidence,
            "page_count": doc.page_count,
            "needs_review": bool(doc.needs_review),
            "error_message": doc.error_message,
            "task_id": doc.task_id,
            "upload_date": doc.upload_date.isoformat() if doc.upload_date else None,
            "processed_date": doc.processed_date.isoformat() if doc.processed_date else None,
        }

    def get_extracted_params(self, document_id: str) -> dict[str, Any]:
        self._get_document(document_id)

        rows = (
            self.db.query(ExtractedCharacteristic)
            .filter(ExtractedCharacteristic.document_id == document_id)
            .all()
        )
        params = [
            {
                "field_name": r.field_name,
                "raw_value": r.raw_value,
                "normalized_value": r.normalized_value,
                "unit": r.unit,
                "confidence": r.confidence,
                "source_fragment": r.source_fragment,
                "source_type": r.source_type,
                "is_verified": r.is_verified,
            }
            for r in rows
        ]
        return {"document_id": document_id, "params": params}

    # ------------------------------------------------------------------ helpers
    def _get_document(self, document_id: str) -> Document:
        doc = (
            self.db.query(Document)
            .filter(Document.document_id == document_id)
            .first()
        )
        if not doc:
            raise NotFoundError(f"Document '{document_id}' not found")
        return doc

    @staticmethod
    def _save_upload(file: Any) -> str:
        uploads = _uploads_dir()
        uploads.mkdir(parents=True, exist_ok=True)

        name = getattr(file, "filename", None) or "document.pdf"
        sink = name.replace(" ", "_").replace("/", "_")[:80] or "document"
        suffix = Path(sink).suffix or ".pdf"
        target = uploads / f"{Path(sink).stem}-{uuid.uuid4().hex[:8]}{suffix}"

        data = getattr(file, "file", None)
        if data is None:
            data = file.read() if hasattr(file, "read") else b""
        elif hasattr(data, "read"):
            data = data.read()
        target.write_bytes(data if isinstance(data, bytes) else b"")
        return str(target)

    def _enqueue_process(
        self, document_id: str, file_path: Optional[str], task_name: str = "passport.process"
    ) -> Optional[str]:
        """Постановка задачи в очередь Celery. None — брокер недоступен."""
        from app.workers import passport_worker
        from app.workers.celery_app import celery_app

        if _eager_mode():
            try:
                task = celery_app.tasks.get(task_name)
                if task is None:
                    task = passport_worker.process_passport
                result = task.apply(args=[document_id, file_path])
                return getattr(result, "id", None)
            except Exception as e:  # noqa: BLE001
                log.warning("enqueue (eager) failed: %s", e)
                return None

        try:
            result = celery_app.send_task(task_name, args=[document_id, file_path])
            return getattr(result, "id", None)
        except Exception as e:  # noqa: BLE001
            log.warning("enqueue failed: %s", e)
            return None

    @staticmethod
    def _task_state(task_id: str):
        """Состояние Celery-задачи (state + meta dict)."""
        try:
            from celery.result import AsyncResult

            from app.workers.celery_app import celery_app

            result = AsyncResult(task_id, app=celery_app)
            try:
                meta = result.info if result.ready() else result.result
            except Exception:  # noqa: BLE001
                meta = None
            return result.state, (meta if isinstance(meta, dict) else None)
        except Exception:  # noqa: BLE001
            return None, None
