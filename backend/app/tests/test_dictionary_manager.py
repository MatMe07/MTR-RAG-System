# tests/test_dictionary_manager.py
"""Тесты DictionaryManager-контракта (1L.2) и аудита изменений (1K.6)."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db():
    from app.models.sqlalchemy.all_models import Base

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# DictionaryManager-контракт (1L.2): keywords / synonyms из БД
# ---------------------------------------------------------------------------


def test_get_keywords_includes_dynamic_from_db(db):
    from app.models.sqlalchemy.all_models import GroupKeyword
    from app.services.agent.rules.dynamic_rules import DynamicRules

    db.add(GroupKeyword(group_name="item_type", keyword="фланец клиновой", priority=10))
    db.add(GroupKeyword(group_name="item_type", keyword="заглушка торцевая", priority=5))
    db.commit()

    rules = DynamicRules(db=db, ttl_seconds=0)
    keywords = rules.get_keywords("item_type")
    assert "фланец клиновой" in keywords
    assert "заглушка торцевая" in keywords


def test_get_synonym_from_db(db):
    from app.models.sqlalchemy.all_models import SynonymRecord
    from app.services.agent.rules.dynamic_rules import DynamicRules

    db.add(SynonymRecord(group_name="item_type", raw_value="кш", normalized_value="кран"))
    db.commit()

    rules = DynamicRules(db=db, ttl_seconds=0)
    assert rules.get_synonym("кш", "item_type") == "кран"


# ---------------------------------------------------------------------------
# Аудит изменений (1K.6)
# ---------------------------------------------------------------------------


def test_admin_mutation_creates_audit_log(db):
    from app.models.sqlalchemy.all_models import Log
    from app.services.admin_service import AdminService

    svc = AdminService(db)
    svc.create_group_keyword(
        {"group_name": "item_type", "keyword": "фланец", "priority": 10},
        actor={"id": "admin-1"},
    )
    svc.create_validation_rule(
        {"item_type": "фланец стальной", "required_params": '["dn"]', "forbidden_params": "[]", "optional_params": "[]"},
        actor={"id": "admin-1"},
    )

    logs = db.query(Log).order_by(Log.id).all()
    actions = [l.action for l in logs]
    assert "admin.dictionaries.group_keywords.create" in actions
    assert "admin.rules.rule.create" in actions
    assert all(str(l.user_id) == "admin-1" for l in logs)
    assert any("keyword" in (json.loads(l.data) or {}) for l in logs)