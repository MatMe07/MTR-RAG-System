# workers/passport_worker.py
"""Celery-задачи обработки паспортов (Фаза 3).

process_passport: OCR (Docling/EasyOCR, движок из OCR_ENGINE) → постраничный
    текст → параметры (regex + опциональное LLM-доизвлечение) →
    extracted_characteristics → suggest_ksm_links → document_links
    (автосвязь confidence > 0.8, needs_review 0.6–0.8, < 0.6 — без связки).
reprocess_passport: повторная обработка (изменились правила/LLM). Переиспользует
    сохранённый OCR-текст, если файл не передан заново.

Docling поставляется как optional-dependency ([project.optional-dependencies]
ocr); при его отсутствии задача завершается со статусом error и сообщением.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from celery import shared_task

log = logging.getLogger("mtr.workers.passport")

_AUTO_THRESHOLD = 0.8
_REVIEW_THRESHOLD = 0.6

_PASSPORT_FIELDS = ("dn", "pn", "angle", "wall_thickness", "material", "medium")


def _link_thresholds() -> Dict[str, float]:
    """Пороги автосвязи/review из validation_constants (БД > дефолты кода)."""
    try:
        from app.services.agent.rules.dynamic_rules import get_dynamic_rules

        auto = float(
            get_dynamic_rules().constant("passport_link_auto_threshold", _AUTO_THRESHOLD)
        )
        review = float(
            get_dynamic_rules().constant("passport_link_review_threshold", _REVIEW_THRESHOLD)
        )
        return {"auto": auto, "review": review}
    except Exception:  # noqa: BLE001
        return {"auto": _AUTO_THRESHOLD, "review": _REVIEW_THRESHOLD}


def _default_ocr_runner(file_path: str) -> List[Dict[str, Any]]:
    """OCR через Docling; движок — из настройки OCR_ENGINE."""
    from app.config import settings
    from app.services.ocr_service import get_ocr_service

    pages = get_ocr_service(engine=settings.OCR_ENGINE).extract_text_from_pdf(file_path)
    return [p for p in pages if (p.get("text") or "").strip()]


def _llm_merge_params(text: str, params: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Опциональное LLM-доизвлечение недостающих параметров (§1F). Best-effort."""
    try:
        from app.services.agent.parsing.llm_extractor import get_llm_extractor

        extractor = get_llm_extractor()
        if not extractor.enabled:
            return params
        missing = [f for f in _PASSPORT_FIELDS if f not in params]
        if not missing:
            return params
        extra = extractor.extract_missing(
            intent="search_by_passport", query=text[:3000], missing=missing, known=dict(params)
        )
        for key, value in (extra or {}).items():
            if key not in params and value is not None:
                params[key] = {"value": value, "confidence": 0.95}
        return params
    except Exception:  # noqa: BLE001
        return params


def _normalize_pages(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Разметка страниц с гарантированным page_number и текстом."""
    out: List[Dict[str, Any]] = []
    for idx, page in enumerate(pages or []):
        text = str(page.get("text", "") or "")
        if not text.strip():
            continue
        number = page.get("page_number")
        number = int(number) if isinstance(number, (int, float)) and number else idx + 1
        out.append({"page_number": number, "text": text})
    return out


def _run_pipeline(
    task: Any,
    document_id: str,
    file_path: Optional[str],
    reprocess: bool,
    ocr_runner: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Ядро конвейера обработки паспорта. Никогда не бросает."""
    from app.db.session import SessionLocal
    from app.models.sqlalchemy.all_models import Document, DocumentLink
    from app.services.agent.repository.db_repository import DbRepository
    from app.services.agent.repository.providers.passport_provider import extract_passport_params
    from app.services.agent.repository.providers.redis_cache import get_redis_cache

    runner = ocr_runner or _default_ocr_runner
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if doc is None:
            return {"document_id": document_id, "status": "error", "error": "not_found"}

        def set_progress(progress: float, stage: str) -> None:
            doc.processing_progress = float(progress)
            doc.ocr_status = "processing"
            doc.error_message = None
            db.commit()
            if task is not None:
                try:
                    task.update_state(
                        state="PROCESSING",
                        meta={"progress": float(progress), "stage": stage, "document_id": document_id},
                    )
                except Exception:  # noqa: BLE001
                    pass

        def fail(stage: str, message: str) -> Dict[str, Any]:
            doc.ocr_status = "error"
            doc.processing_progress = 0.0
            doc.error_message = message
            db.commit()
            log.warning("passport %s: %s", document_id, message)
            return {"document_id": document_id, "status": "error", "error": message, "stage": stage}

        # ------------------------------------------------------------------ OCR
        set_progress(0.05, "ocr")
        pages = doc.page_texts if (reprocess and doc.page_texts) else None
        if pages is None:
            source = file_path or doc.file_path
            if not source:
                return fail("ocr", "файл документа не сохранён")
            try:
                pages = _normalize_pages(runner(source))
            except Exception as e:  # noqa: BLE001
                return fail("ocr", f"OCR не удался: {e}")
        if not pages:
            return fail("ocr", "OCR не вернул текст ни на одной странице")

        doc.page_texts = pages
        doc.page_count = len(pages)
        db.commit()

        # ------------------------------------------------ векторный индекс (P2-16)
        # Инкрементальный upsert текстов паспорта в Qdrant documents.
        # Не роняет конвейер: Qdrant недоступен/пуст — просто пропускаем.
        try:
            from app.services.agent.repository.providers.documents_provider import DocumentsProvider

            if not DocumentsProvider().upsert_document(document_id, pages):
                log.warning(
                    "passport %s: documents-индекс не обновлён (Qdrant недоступен/пуст)",
                    document_id,
                )
        except Exception as e:  # noqa: BLE001
            log.warning("passport %s: documents-индекс не обновлён: %s", document_id, e)

        # ------------------------------------------------------------ параметры
        set_progress(0.4, "extract")
        text = "\n".join(str(p.get("text", "")) for p in pages)
        params = _llm_merge_params(text, extract_passport_params(text))

        from app.services.agent.repository.providers.passport_provider import PassportProvider

        provider = PassportProvider()
        persisted = provider.extract_params(document_id, params=params)
        if persisted is None:
            return fail("extract", "не удалось сохранить параметры паспорта")
        params = persisted

        # --------------------------------------------------------------- связи
        set_progress(0.65, "links")
        thresholds = _link_thresholds()

        db.query(DocumentLink).filter(DocumentLink.document_id == document_id).delete()
        db.commit()

        suggestions: List[Dict[str, Any]] = []
        needs_review = False
        try:
            repo = DbRepository()
            suggestions = repo.suggest_ksm_links(document_id, limit=5)
        except Exception as e:  # noqa: BLE001
            log.warning("passport %s: suggest_ksm_links не удался: %s", document_id, e)
        finally:
            try:
                repo.close()  # noqa: F821
            except Exception:
                pass

        linked: List[str] = []
        if suggestions:
            best = suggestions[0]
            if best["confidence"] > thresholds["auto"]:
                provider.link_passport_to_ksm(
                    document_id, best["ksm_code"], best["confidence"], method="semantic"
                )
                linked.append(best["ksm_code"])
            for s in suggestions:
                if s is best and best["confidence"] > thresholds["auto"]:
                    continue
                if s["confidence"] >= thresholds["review"]:
                    provider.link_passport_to_ksm(
                        document_id, s["ksm_code"], s["confidence"],
                        method="semantic", needs_review=True,
                    )
                    needs_review = True

        # -------------------------------------------------------------- финал
        doc.ocr_status = "completed"
        doc.processing_progress = 1.0
        doc.processed_date = datetime.now(timezone.utc)
        doc.needs_review = needs_review
        db.commit()

        try:
            get_redis_cache().delete(f"passport:{document_id}")
        except Exception:  # noqa: BLE001
            pass

        if task is not None:
            try:
                task.update_state(
                    state="SUCCESS",
                    meta={"progress": 1.0, "stage": "done", "document_id": document_id},
                )
            except Exception:  # noqa: BLE001
                pass

        return {
            "document_id": document_id,
            "status": "completed",
            "progress": 1.0,
            "params": sorted(params.keys()),
            "links": linked,
            "needs_review": needs_review,
        }
    finally:
        db.close()


@shared_task(name="passport.process", bind=True, track_started=True)
def process_passport(self, document_id: str, file_path: Optional[str] = None) -> dict:
    """Обработка загруженного паспорта (OCR → параметры → связи)."""
    return _run_pipeline(self, document_id, file_path, reprocess=False)


@shared_task(name="passport.reprocess", bind=True, track_started=True)
def reprocess_passport(self, document_id: str, file_path: Optional[str] = None) -> dict:
    """Переобработка паспорта (повторно извлекает параметры и связи)."""
    return _run_pipeline(self, document_id, file_path, reprocess=True)
