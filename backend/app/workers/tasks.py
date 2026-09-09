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
    """OCR-синк загруженного документа (Фаза 3: полный конвейер паспорта)."""
    from .passport_worker import _run_pipeline

    return _run_pipeline(None, document_id, path, reprocess=False)


@shared_task(name="norms.reindex")
def reindex_norms() -> dict:
    """Переиндексация нормативных фрагментов в Qdrant (norm_documents)."""
    try:
        from app.services.agent.repository.providers.norms_provider import NormsProvider
        from app.services.agent.repository.providers.redis_cache import get_redis_cache

        provider = NormsProvider()
        ok = provider.ensure_index()
        provider.close()
        # Протухшие кешированные поиски норм (TTL 24ч) инвалидируем сразу.
        get_redis_cache().delete_prefix("norms:")
        log.info("reindex_norms: indexed=%s", ok)
        return {"indexed": bool(ok), "finished_at": datetime.now(timezone.utc).isoformat()}
    except Exception as e:  # noqa: BLE001
        log.warning("reindex_norms failed: %s", e)
        return {"indexed": False, "error": str(e)}