# tests/test_phase8_passport_pipeline.py
"""План B.8: Celery-конвейер паспортов в eager-режиме (работник не нужен).

B.8.1: сквозной флоу «загрузка → обработка → статус → извлечённые параметры».
B.8.2: изоляция тестов — отдельная тестовая БД (TEST_DATABASE_URL, по умолчанию
    sqlite) + celery_always_eager=True; брокер/Redis/Qdrant/Neo4j не нужны.

Нюанс: eager-задачи выполняются синхронно в вызывающем процессе, поэтому
OCR-раннер и семантический репозиторий подменяются фейками (без Docling/Qdrant).
Тестовая БД — отдельный per-test sqlite-файл (check_same_thread=False), поэтому
общий app.db.session.SessionLocal подменяется фикстурой на всём прогоне теста.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.main import app
from app.models.sqlalchemy.all_models import (
    Document,
    DocumentLink,
    ExtractedCharacteristic,
    Base,
)
# Порядок важен: сначала celery_app, затем shared_task-модуль — тогда
# passport.process/passport.reprocess регистрируются на нашем приложении.
import app.workers.passport_worker as pw  # noqa: E402,F401
from app.workers.celery_app import celery_app  # noqa: F401,E402
import app.db.session as db_session  # noqa: E402
from app.services.agent.repository import db_repository  # noqa: E402

_PASSPORT_TEXT = (
    "ПАСПОРТ ТРУБОПРОВОДНОЙ АРМАТУРЫ\n"
    "DN 250 PN 1.6\n"
    "Толщина стенки 12\n"
    "Материал Сталь 20\n"
    "Рабочая среда: газ."
)


@pytest.fixture
def engine_url(tmp_path):
    """Отдельная тестовая БД на каждый тест (beз общего mtr.db)."""
    return f"sqlite:///{tmp_path}/passport_test.db"


@pytest.fixture
def passport_db(engine_url, monkeypatch):
    engine = create_engine(
        engine_url,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Session = sessionmaker(bind=engine)
    # Подмена общего SessionLocal/engine для АПИ, Celery-задач и провайдеров.
    monkeypatch.setattr(db_session, "engine", engine)
    monkeypatch.setattr(db_session, "SessionLocal", Session)
    Base.metadata.create_all(engine)
    yield Session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(passport_db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DOCUMENT_UPLOAD_DIR", str(tmp_path / "uploads"))
    return TestClient(app)


def _fake_pages(*args, **kwargs):
    """OCR-раннер-заглушка: игнорирует file_path, отдаёт фиксированный текст."""
    return [{"page_number": 1, "text": _PASSPORT_TEXT}]


class _FakeRepo:
    """Заглушка DbRepository.suggest_ksm_links (без Qdrant/Neo4j)."""

    _suggestions = []

    def __init__(self, *args, **kwargs):
        pass

    def suggest_ksm_links(self, document_id, limit=5):
        return [dict(s) for s in self._suggestions]

    def close(self):
        pass


def _register_fake_repo(monkeypatch, suggestions):
    _FakeRepo._suggestions = suggestions
    monkeypatch.setattr(db_repository, "DbRepository", _FakeRepo)


def _seed_document(Session, doc_id, text_=_PASSPORT_TEXT, status="completed"):
    db = Session()
    try:
        db.add(
            Document(
                document_id=doc_id,
                file_name="pass.pdf",
                file_path="/nonexistent/pass.pdf",
                document_type="passport",
                ocr_status=status,
                page_texts=[{"page_number": 1, "text": text_}],
            )
        )
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------- B.8.2 (инфра)
def test_eager_and_test_db_configured():
    assert celery_app.conf.get("task_always_eager") is True, "celery_always_eager"
    assert settings.DATABASE_URL.startswith("sqlite"), (
        "тесты должны идти на отдельной тестовой БД (не dev-PG)"
    )
    for name in ("passport.process", "passport.reprocess"):
        assert celery_app.tasks.get(name) is not None, f"задача {name} не зарегистрирована"


# ------------------------------------------------------------------- B.8.1 флоу
def test_upload_status_extract(client, passport_db, monkeypatch):
    monkeypatch.setattr(pw, "_default_ocr_runner", _fake_pages)

    r = client.post(
        "/api/v1/passport/upload",
        files={"file": ("pass001.pdf", b"%PDF-1.4 test bytes", "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "pending"
    doc_id = body["document_id"]
    assert body["task_id"], "eager-задача должна вернуть task_id"

    r = client.get(f"/api/v1/passport/status/{doc_id}")
    assert r.status_code == 200, r.text
    st = r.json()
    assert st["ocr_status"] == "completed"
    assert st["progress"] == 1.0
    assert st["page_count"] == 1
    assert st["needs_review"] is False

    r = client.get(f"/api/v1/passport/extracted/{doc_id}")
    assert r.status_code == 200, r.text
    fields = {p["field_name"]: p for p in r.json()["params"]}
    assert set(fields) >= {"dn", "pn", "material", "medium"}
    assert fields["dn"]["normalized_value"] == "250"
    assert fields["pn"]["normalized_value"] == "1.6"
    assert fields["material"]["normalized_value"] == "20"

    db = passport_db()
    try:
        doc = db.query(Document).filter(Document.document_id == doc_id).first()
        assert doc.ocr_status == "completed"
        assert doc.page_count == 1
        assert doc.processed_date is not None
    finally:
        db.close()


def test_status_not_found(client):
    r = client.get("/api/v1/passport/status/does-not-exist")
    assert r.status_code == 404


# --------------------------------------------------- B.8.1 автосвязь (> 0.8)
def test_pipeline_auto_link_above_threshold(client, passport_db, monkeypatch):
    monkeypatch.setattr(pw, "_default_ocr_runner", _fake_pages)
    _register_fake_repo(
        monkeypatch,
        [{"ksm_code": "KSM-00001", "mtr_code": "MTR-1", "name": "Задвижка", "confidence": 0.9}],
    )

    r = client.post(
        "/api/v1/passport/upload",
        files={"file": ("pass002.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    doc_id = r.json()["document_id"]

    st = client.get(f"/api/v1/passport/status/{doc_id}").json()
    assert st["ocr_status"] == "completed"
    assert st["needs_review"] is False

    db = passport_db()
    try:
        links = db.query(DocumentLink).filter(DocumentLink.document_id == doc_id).all()
        assert len(links) == 1
        link = links[0]
        assert link.ksm_code == "KSM-00001"
        assert link.confidence == 0.9
        assert link.linked is True
        assert link.needs_review is False
    finally:
        db.close()


# ----------------------------------------------- B.8.2 review-зона (0.6–0.8)
def test_reprocess_review_band_sets_needs_review(client, passport_db, monkeypatch):
    monkeypatch.setattr(pw, "_default_ocr_runner", _fake_pages)
    _register_fake_repo(
        monkeypatch,
        [{"ksm_code": "KSM-00002", "mtr_code": "MTR-2", "name": "Кран", "confidence": 0.75}],
    )

    doc_id = "doc-review-01"
    _seed_document(passport_db, doc_id)

    r = client.post(f"/api/v1/passport/reprocess/{doc_id}")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending"

    st = client.get(f"/api/v1/passport/status/{doc_id}").json()
    assert st["ocr_status"] == "completed", st.get("error_message")
    assert st["needs_review"] is True

    db = passport_db()
    try:
        links = db.query(DocumentLink).filter(DocumentLink.document_id == doc_id).all()
        assert len(links) == 1
        assert links[0].ksm_code == "KSM-00002"
        assert links[0].linked is False
        assert links[0].needs_review is True
        fields = db.query(ExtractedCharacteristic).filter(
            ExtractedCharacteristic.document_id == doc_id
        )
        assert {f.field_name for f in fields} >= {"dn", "pn"}
    finally:
        db.close()


def test_reprocess_below_review_leaves_no_link(client, passport_db, monkeypatch):
    monkeypatch.setattr(pw, "_default_ocr_runner", _fake_pages)
    _register_fake_repo(
        monkeypatch,
        [{"ksm_code": "KSM-00003", "mtr_code": "MTR-3", "name": "Отвод", "confidence": 0.5}],
    )

    doc_id = "doc-low-01"
    _seed_document(passport_db, doc_id)

    client.post(f"/api/v1/passport/reprocess/{doc_id}")

    st = client.get(f"/api/v1/passport/status/{doc_id}").json()
    assert st["ocr_status"] == "completed"
    assert st["needs_review"] is False

    db = passport_db()
    try:
        assert (
            db.query(DocumentLink).filter(DocumentLink.document_id == doc_id).count() == 0
        )
    finally:
        db.close()