# tests/test_admin_reload.py
"""Регрессия A3: POST /dictionaries/reload не должен затеняться generic-маршрутом.

Баг: generic create (POST /dictionaries/{dict_name}) регистрировался раньше
reload-эндпоинта, и POST /dictionaries/reload матчился на него → 422
(требовалось тело запроса). Теперь reload регистрируется первым.
"""

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps.auth import get_current_user
from app.api.v1 import admin as admin_module
from app.db.session import get_db
from app.main import app


def test_reload_route_registered_before_generic_create():
    """Статичный маршрут reload стоит раньше параметрического create."""
    reload_idx = None
    create_idx = None
    for i, route in enumerate(admin_module.router.routes):
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        if path == "/dictionaries/reload":
            reload_idx = i
        if path == "/dictionaries/{dict_name}" and "POST" in methods:
            create_idx = i
    assert reload_idx is not None, "reload маршрут не зарегистрирован"
    assert create_idx is not None, "generic create маршрут не зарегистрирован"
    assert reload_idx < create_idx, (
        "reload затенён generic create: POST /dictionaries/reload получает 422"
    )


@pytest.fixture()
def admin_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/admin.db")
    Session = sessionmaker(bind=engine)
    session = Session()

    def _get_db():
        yield session

    app.dependency_overrides[get_current_user] = lambda: {
        "id": 1,
        "username": "admin",
        "role": "admin",
    }
    app.dependency_overrides[get_db] = _get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


def test_reload_returns_ok(admin_client):
    """POST /dictionaries/reload → 200 {status: ok, reloaded: [...]} без body."""
    r = admin_client.post("/api/v1/admin/dictionaries/reload")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert "catalog_repository" in body["reloaded"]
    assert "dictionaries" in body["reloaded"]