# tests/test_dictionary_manager.py
# 1K/1L: снимок справочников в Redis + чтение DynamicRules из БД.
# 1K.6/1L.6: аудит изменений справочников и правил.

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def db():
    from app.models.sqlalchemy.all_models import Base

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()
    engine.dispose()


def _rules(session):
    from app.services.agent.rules.dynamic_rules import DynamicRules

    return DynamicRules(db=session, ttl_seconds=0)


# ---------------------------------------------------------------------------
# Чтение справочников из БД (1K.2 / 1L)
# ---------------------------------------------------------------------------

def test_get_keywords_from_db(db):
    from app.models.sqlalchemy.all_models import GroupKeyword

    db.add(GroupKeyword(group_name="item_type", keyword="фланец", priority=10))
    db.add(GroupKeyword(group_name="item_type", keyword="заглушка", priority=5))
    db.commit()

    rules = _rules(db)
    keywords = rules.get_keywords("item_type")
    assert "фланец" in keywords
    assert "заглушка" in keywords


def test_get_keywords_unknown_group(db):
    rules = _rules(db)
    assert rules.get_keywords("no_such_group") == []


def test_get_synonym_from_db(db):
    from app.models.sqlalchemy.all_models import SynonymRecord

    db.add(SynonymRecord(group_name="item_type", raw_value="фл", normalized_value="фланец"))
    db.commit()

    rules = _rules(db)
    assert rules.get_synonym("фл", "item_type") == "фланец"
    assert rules.get_synonym("фл", "operation") is None


def test_get_constant_from_db(db):
    from app.models.sqlalchemy.all_models import ValidationConstant

    db.add(ValidationConstant(constant_name="x0", value=1.25))
    db.commit()

    rules = _rules(db)
    assert rules.get_constant("x0") == 1.25
    assert rules.get_constant("missing") is None


def test_get_validation_rule_from_db(db):
    import json
    from app.models.sqlalchemy.all_models import ValidationRule

    db.add(ValidationRule(
        item_type="фланец",
        required_params=json.dumps(["dn"]),
        forbidden_params=json.dumps([]),
        optional_params=json.dumps(["p"]),
    ))
    db.commit()

    rules = _rules(db)
    rule = rules.get_validation_rule("фланец")
    assert rule is not None
    assert "dn" in rule["required"]


# ---------------------------------------------------------------------------
# Аудит изменений (1K.6 / 1L.6)
# ---------------------------------------------------------------------------

def test_admin_mutation_writes_audit_log(db):
    from app.services.admin_service import AdminService
    from app.models.sqlalchemy.all_models import Log

    svc = AdminService(db)
    created = svc.create_group_keyword(
        {"group_name": "item_type", "keyword": "фланец", "priority": 10},
        actor={"id": "admin-1"},
    )
    svc.update_group_keyword(created["id"], {"keyword": "фланец стальной"}, actor={"id": "admin-1"})
    svc.delete_group_keyword(created["id"], actor={"id": "admin-1"})

    logs = db.query(Log).order_by(Log.id).all()
    actions = [l.action for l in logs]
    assert "admin.dictionaries.group_keywords.create" in actions
    assert "admin.dictionaries.group_keywords.update" in actions
    assert "admin.dictionaries.group_keywords.delete" in actions
    assert all(str(l.user_id) == "admin-1" for l in logs)


def test_admin_validation_rule_audit(db):
    from app.services.admin_service import AdminService
    from app.models.sqlalchemy.all_models import Log, ValidationRule

    import json
    db.add(ValidationRule(
        item_type="фланец",
        required_params=json.dumps(["dn"]),
        forbidden_params=json.dumps([]),
        optional_params=json.dumps([]),
    ))
    db.commit()
    existing = db.query(ValidationRule).first()

    svc = AdminService(db)
    svc.update_validation_rule(existing.id, {"optional_params": ["pn"]}, actor={"id": "admin-2"})
    svc.delete_validation_rule(existing.id, actor={"id": "admin-2"})

    actions = [l.action for l in db.query(Log).order_by(Log.id).all()]
    assert actions == ["admin.rules.rule.update", "admin.rules.rule.delete"]


def test_constants_audit(db):
    from app.services.admin_service import AdminService
    from app.models.sqlalchemy.all_models import Log

    svc = AdminService(db)
    vc = svc.create_validation_constant({"constant_name": "beta", "value": 0.75}, actor={"id": "admin-1"})
    svc.delete_validation_constant(vc["id"], actor={"id": "admin-1"})

    actions = [l.action for l in db.query(Log).order_by(Log.id).all()]
    assert actions == ["admin.rules.constants.create", "admin.rules.constants.delete"]