# tests/test_api_http.py

"""HTTP-контракт API (P4.2): auth/login, search, clarify, history, me,
compare, norms/search, expert/*. Офлайн: sqlite-файл + JSON-каталог агента,
LLM выключен (conftest). Зависимости get_db/get_current_user подменяются на
реальную сессию с посеянными пользователями и каталогом.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.sqlalchemy.all_models import ExpertMatch, MtrItem, User


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("api") / "api.db"
    engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    session.add(User(username="user", hashed_password=hash_password("user123"),
                     role="user", is_active=True))
    session.add(User(username="expert", hashed_password=hash_password("expert123"),
                     role="expert", is_active=True))
    session.add(User(username="admin", hashed_password=hash_password("admin123"),
                     role="admin", is_active=True))
    session.add(MtrItem(
        mtr_code="MTR-0001", ksm_code="KSM-0001", item_type="отвод",
        name="Отвод 90", designation="90",
        attributes={"dn": 50, "pn": 16, "material": "Сталь 20"},
        gost_tu="ГОСТ 17375-2001", standard="ГОСТ",
    ))
    session.add(MtrItem(
        mtr_code="MTR-0002", ksm_code="KSM-0002", item_type="отвод",
        name="Отвод 90 сварной", designation="90",
        attributes={"dn": 80, "pn": 25, "material": "09Г2С"},
        gost_tu="ГОСТ 17375-2001", standard="ГОСТ",
    ))
    session.add(ExpertMatch(
        requested_mtr_code="MTR-000X", candidate_ksm_code="KSM-0001",
        expert_status="pending",
    ))
    session.commit()

    def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


@pytest.fixture(scope="module")
def user_token(client):
    r = client.post("/api/v1/auth/login", json={"username": "user", "password": "user123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def expert_token(client):
    r = client.post("/api/v1/auth/login", json={"username": "expert", "password": "expert123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ----------------------------------------------------------------- auth
class TestAuth:
    def test_login_success(self, client):
        r = client.post("/api/v1/auth/login", json={"username": "user", "password": "user123"})
        assert r.status_code == 200
        body = r.json()
        assert body["token_type"] == "bearer"
        assert body["user"]["username"] == "user"

    def test_login_wrong_password_401(self, client):
        r = client.post("/api/v1/auth/login", json={"username": "user", "password": "wrong"})
        assert r.status_code == 401

    def test_me(self, client, user_token):
        r = client.get("/api/v1/auth/me", headers=_auth(user_token))
        assert r.status_code == 200
        assert r.json()["username"] == "user"

    def test_me_requires_auth(self, client):
        assert client.get("/api/v1/auth/me").status_code == 401


# ----------------------------------------------------------------- search
class TestSearch:
    def test_search_requires_auth(self, client):
        body = {"query": "нужна труба", "mode": "deterministic"}
        assert client.post("/api/v1/search/", json=body).status_code == 401
        hdr = {"Authorization": "Bearer garbage"}
        assert client.post("/api/v1/search/", json=body, headers=hdr).status_code == 401

    def test_search_ok(self, client, user_token):
        r = client.post(
            "/api/v1/search/",
            json={"query": "нужен отвод DN50", "mode": "deterministic"},
            headers=_auth(user_token),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        for key in ("request_id", "query", "status", "results", "warnings"):
            assert key in body
        assert body["query"] == "нужен отвод DN50"

    def test_history_requires_auth(self, client):
        assert client.get("/api/v1/search/history").status_code == 401

    def test_history_reflects_search(self, client, user_token):
        client.post(
            "/api/v1/search/",
            json={"query": "задвижка", "mode": "deterministic"},
            headers=_auth(user_token),
        )
        r = client.get("/api/v1/search/history", headers=_auth(user_token))
        assert r.status_code == 200
        queries = [item["query"] for item in r.json()]
        assert "задвижка" in queries


# ----------------------------------------------------------------- clarify
class TestClarify:
    def test_clarify_requires_auth(self, client):
        r = client.post("/api/v1/search/clarify", json={"query": "хз", "session_id": "c1"})
        assert r.status_code == 401

    def test_clarify_vague_query_asks(self, client, user_token):
        r = client.post(
            "/api/v1/search/clarify",
            json={"query": "нужна деталь", "session_id": "c-vague-1"},
            headers=_auth(user_token),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["route"] in ("clarification", "expert", "answer")
        assert body["session_id"] == "c-vague-1"


# ----------------------------------------------------------------- compare
class TestCompare:
    def test_compare_ok(self, client):
        r = client.post("/api/v1/compare/",
                        json={"ksm_code_1": "KSM-0001", "ksm_code_2": "KSM-0002"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ksm1"] == "KSM-0001"
        assert body["ksm2"] == "KSM-0002"
        assert body["match_count"] + body["mismatch_count"] >= 1

    def test_compare_missing_404(self, client):
        r = client.post("/api/v1/compare/",
                        json={"ksm_code_1": "KSM-0001", "ksm_code_2": "KSM-NOPE"})
        assert r.status_code == 404


# ----------------------------------------------------------------- norms
class TestNorms:
    def test_search_finds_by_name_case_insensitive(self, client):
        r = client.post("/api/v1/norms/search", json={"query": "отвод"})
        assert r.status_code == 200, r.text
        names = [item["name"] for item in r.json()]
        assert any("Отвод" in n for n in names)

    def test_search_filters_by_document_type(self, client):
        r = client.post("/api/v1/norms/search", json={"query": "отвод", "document_type": "задвижка"})
        assert r.status_code == 200
        assert r.json() == []


# ----------------------------------------------------------------- expert
class TestExpert:
    def test_reviews_requires_expert_role(self, client, user_token):
        assert client.get("/api/v1/expert/reviews", headers=_auth(user_token)).status_code == 403

    def test_reviews_requires_auth(self, client):
        assert client.get("/api/v1/expert/reviews").status_code == 401

    def test_list_and_submit_review(self, client, expert_token):
        r = client.get("/api/v1/expert/reviews", headers=_auth(expert_token))
        assert r.status_code == 200, r.text
        as_list = r.json()
        assert isinstance(as_list, list)
        if not as_list:
            return
        review_id = as_list[0]["id"]
        r = client.post(
            f"/api/v1/expert/review/{review_id}",
            json={"decision": "confirmed", "reason": "ok"},
            headers=_auth(expert_token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["expert_status"] == "confirmed"

    def test_bad_decision_422(self, client, expert_token):
        r = client.post(
            "/api/v1/expert/review/1",
            json={"decision": "BRUH"},
            headers=_auth(expert_token),
        )
        assert r.status_code == 422
