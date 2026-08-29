# workers/tasks.py
"""Задачи Celery.

Каркас async-обработки (вне итераций A–E): ingestion документов (OCR) и
переиндексация нормативов в Qdrant. Запускаются через celery_app.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from celery import shared_task

log = logging.getLogger("mtr.workers")


@shared_task(name="documents.ingest")
def ingest_document(document_id: str, path: Optional[str] = None) -> dict:
    """OCR-синк загруженного документа.

    Каркас: принятие и постановка в очередь. Реализация OCR/извлечения —
    отдельная итерация.
    """
    log.info("ingest_document: %s (path=%s)", document_id, path)
    return {
        "document_id": document_id,
        "status": "accepted",
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "note": "OCR-синк реализуется отдельной итерацией",
    }


@shared_task(name="norms.reindex")
def reindex_norms() -> dict:
    """Переиндексация нормативных фрагментов в Qdrant (mtr_descriptions)."""
    try:
        from app.services.agent.repository.providers.norms_provider import NormsProvider

        provider = NormsProvider()
        ok = provider.ensure_index()
        provider.close()
        log.info("reindex_norms: indexed=%s", ok)
        return {"indexed": bool(ok), "finished_at": datetime.now(timezone.utc).isoformat()}
    except Exception as e:  # noqa: BLE001
        log.warning("reindex_norms failed: %s", e)
        return {"indexed": False, "error": str(e)}