# tests/test_service_units.py

"""Юнит-тесты сервисов (P4.2c): auth, compare, norms, expert, search.

SQLite-фикстура (in-memory, файл из tmp) в стиле остальных БД-тестов
проекта; PK-типы детектятся как sqlite через conftest (DATABASE_URL=sqlite://).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.core.security import hash_password
from app.db.session import Base
from app.models.sqlalchemy.all_models import ExpertMatch, MtrItem, User
from app.services.auth_service import AuthService
from app.services.compare_service import CompareService
from app.services.expert_service import ExpertService
from app.services.norms_service import NormsService


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path}/svc.db", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_user(db, username="alice", password="secret", role="user", is_active=True):
    user = User(
        username=username,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_items(db):
    a = MtrItem(
        mtr_code="MTR-A", ksm_code="KSM-A", item_type="отвод",
        name="Отвод 90", attributes={"dn": 50, "pn": 16, "material": "Сталь 20"},
        gost_tu="ГОСТ 17375-2001", standard="ГОСТ",
    )
    b = MtrItem(
        mtr_code="MTR-B", ksm_code="KSM-B", item_type="отвод",
        name="Отвод 90 сварной", attributes={"dn": 80, "pn": 25, "material": "09Г2С"},
        gost_tu="ГОСТ 17375-2001", standard="ГОСТ",
    )
    db.add_all([a, b])
    db.commit()
    return a, b


# ----------------------------------------------------------------- auth
class TestAuthService:
    def test_login_returns_token(self, db):
        _seed_user(db)
        result = AuthService(db).login("alice", "secret")
        assert result["token_type"] == "bearer"
        assert result["access_token"]
        assert result["user"]["username"] == "alice"

    def test_login_wrong_password(self, db):
        _seed_user(db)
        with pytest.raises(UnauthorizedError):
            AuthService(db).login("alice", "nope")

    def test_login_inactive_user(self, db):
        _seed_user(db, is_active=False)
        with pytest.raises(UnauthorizedError):
            AuthService(db).login("alice", "secret")

    def test_register_duplicate(self, db):
        _seed_user(db)
        with pytest.raises(ConflictError):
            AuthService(db).register("alice", "x")

    def test_get_current_user_missing(self, db):
        with pytest.raises(NotFoundError):
            AuthService(db).get_current_user(424242)


# ----------------------------------------------------------------- compare
class TestCompareService:
    def test_matches_and_mismatches(self, db):
        _seed_items(db)
        result = CompareService(db).compare("KSM-A", "KSM-B")
        assert result["ksm1"] == "KSM-A"
        assert result["match_count"] + result["mismatch_count"] >= 1
        assert all(k in result for k in (
            "matches", "mismatches", "only_in_first", "only_in_second",
            "match_count", "mismatch_count", "similarity",
        ))

    def test_missing_item(self, db):
        _seed_items(db)
        with pytest.raises(NotFoundError):
            CompareService(db).compare("KSM-A", "KSM-NOPE")


# ----------------------------------------------------------------- norms
class TestNormsService:
    def test_case_insensitive_cyrillic(self, db):
        _seed_items(db)
        rows = NormsService(db).search_norms("ОТВОД")
        assert all(it["item_type"] == "отвод" for it in rows)
        assert len(rows) == 2

    def test_document_type_filter(self, db):
        _seed_items(db)
        rows = NormsService(db).search_norms("отвод", document_type="задвижка")
        assert rows == []

    def test_limit(self, db):
        _seed_items(db)
        rows = NormsService(db).search_norms("отвод", limit=1)
        assert len(rows) == 1


# ----------------------------------------------------------------- expert
class TestExpertService:
    def test_pending_reviews(self, db):
        db.add(ExpertMatch(requested_mtr_code="MTR-X", candidate_ksm_code="KSM-A",
                           expert_status="pending"))
        db.commit()
        rows = ExpertService(db).get_pending_reviews()
        assert len(rows) == 1
        assert rows[0]["expert_status"] == "pending"

    def test_submit_review_valid(self, db):
        em = ExpertMatch(requested_mtr_code="MTR-X", candidate_ksm_code="KSM-A",
                         expert_status="pending")
        db.add(em)
        db.commit()
        db.refresh(em)
        out = ExpertService(db).submit_review(em.id, "confirmed", "ok", "expert1")
        assert out["expert_status"] == "confirmed"
        assert out["confirmed_by"] == "expert1"

    def test_submit_review_invalid_decision(self, db):
        em = ExpertMatch(requested_mtr_code="MTR-X", candidate_ksm_code="KSM-A",
                         expert_status="pending")
        db.add(em)
        db.commit()
        db.refresh(em)
        with pytest.raises(ValidationError):
            ExpertService(db).submit_review(em.id, "BRUH")

    def test_submit_review_not_found(self, db):
        with pytest.raises(NotFoundError):
            ExpertService(db).submit_review(999999, "confirmed")

    def test_link_passport_basic(self, db):
        out = ExpertService(db).link_passport("DOC-1", "KSM-A")
        assert out["expert_status"] == "pending"
        assert out["requested_mtr_code"] == "DOC-1"

    def test_link_passport_duplicate(self, db):
        ExpertService(db).link_passport("DOC-1", "KSM-A")
        with pytest.raises(ValidationError):
            ExpertService(db).link_passport("DOC-1", "KSM-A")
