"""Тесты динамических правил валидации (БД-first, fallback, кэш).

Проверяют: seed → БД; БД переопределяет дефолты; недоступная БД → дефолты;
синонимы из БД попадают в публичные словари без перезапуска.
"""

import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def db_env():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp.name}"
    from app.models.sqlalchemy.all_models import Base  # регистрирует все таблицы

    engine = create_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    yield Session
    os.remove(tmp.name)


@pytest.fixture()
def empty_db_env():
    """БД с таблицами, удалёнными после импорта (имитация недоступной схемы)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    from app.models.sqlalchemy.all_models import Base  # регистрирует все таблицы

    engine = create_engine(f"sqlite:///{tmp.name}")
    Base.metadata.create_all(engine)
    Base.metadata.drop_all(engine)
    Session = sessionmaker(bind=engine)
    yield Session
    os.remove(tmp.name)


def _new_provider(Session, ttl_seconds=600, **kwargs):
    from app.services.agent.rules.dynamic_rules import DynamicRules

    return DynamicRules(db=Session(), ttl_seconds=ttl_seconds, **kwargs)


def test_seed_and_provider_read(db_env):
    Session = db_env
    from app.services.agent.rules.seed import seed_rules

    db = Session()
    counts = seed_rules(db)
    db.close()

    assert counts["constants"] >= 5
    assert counts["synonyms"] > 0
    assert counts["rules"] == 7

    prov = _new_provider(Session)
    prov.refresh(force=True)

    assert prov.matching_tolerances()["dn"] == 0.1
    assert prov.numeric_tolerance() == 0.1
    rule = prov.validation_rule("труба")
    assert rule["required"] == ["dn", "wall_thickness", "steel_grade"]
    assert rule["forbidden"] == []
    assert rule["optional"] == ["angle", "pn"]
    assert rule["is_active"] is True
    assert rule["logical_conditions"] is None
    assert "задвижка" in prov.validation_rule_item_types()
    # синонимы засеяны из словарей кода
    mediums = [s for s in prov.synonyms("medium") if s["raw"] == "сероводород"]
    assert mediums and mediums[0]["norm"] == "H2S"


def test_db_values_override_defaults(db_env):
    Session = db_env
    from app.models.sqlalchemy.all_models import SynonymRecord, ValidationRule
    from app.services.agent.rules.seed import seed_rules

    db = Session()
    seed_rules(db)

    # изменить дефолт через "админку" (прямой upsert в БД)
    vc = db.query(ValidationRule).filter(ValidationRule.item_type == "труба").first()
    vc.required_params = '["dn", "material"]'
    db.add(SynonymRecord(
        group_name="item_type", raw_value="вентиль", normalized_value="кран"
    ))
    db.commit()
    db.close()

    prov = _new_provider(Session)
    prov.refresh(force=True)

    rule = prov.validation_rule("труба")
    assert rule["required"] == ["dn", "material"]

    from app.models.sqlalchemy.all_models import ValidationConstant
    db = Session()
    c = db.query(ValidationConstant).filter(
        ValidationConstant.constant_name == "numeric_tolerance"
    ).first()
    c.value = 0.5
    db.commit()
    db.close()

    prov.refresh(force=True)
    assert prov.numeric_tolerance() == 0.5


def test_unavailable_db_falls_back_to_defaults(empty_db_env):
    Session = empty_db_env
    prov = _new_provider(Session, db_retry_seconds=0)
    prov.refresh(force=True)

    # таблиц нет — должны вернуться дефолты кода без исключений
    assert prov.matching_tolerances() == {
        "dn": 0.1, "angle": 0.0, "wall_thickness": 0.15, "default": 0.1,
    }
    assert prov.numeric_tolerance() == 0.1
    assert prov.validation_rule("труба")["required"] == ["dn", "wall_thickness", "steel_grade"]
    assert prov.synonyms("item_type") == []


def test_ttl_cache(db_env):
    Session = db_env
    from app.services.agent.rules.seed import seed_rules

    db = Session()
    seed_rules(db)
    db.close()

    provider = _new_provider(Session, ttl_seconds=600)
    first = provider.constants()
    assert first["numeric_tolerance"] == 0.1
    # повторный запрос в пределах TTL не должен ничего ломать
    second = provider.constants()
    assert second == first


def test_dictionaries_get_synonyms_from_db(db_env, monkeypatch):
    Session = db_env
    from app.models.sqlalchemy.all_models import SynonymRecord
    from app.services.agent.rules.seed import seed_rules

    db = Session()
    seed_rules(db)
    db.close()

    from app.services.agent.rules.dynamic_rules import DynamicRules

    provider = DynamicRules(db=Session(), ttl_seconds=600)
    provider.refresh(force=True)

    ptrov_marker = provider
    monkeypatch.setattr(
        "app.services.agent.parsing.dictionaries.get_dynamic_rules",
        lambda: ptrov_marker,
    )

    import app.services.agent.parsing.dictionaries as dic

    # алиас, которого нет в коде, добавлен в БД
    db = Session()
    db.add(SynonymRecord(
        group_name="item_type", raw_value="вентиль", normalized_value="кран"
    ))
    db.commit()
    db.close()

    provider.refresh(force=True)
    dic.refresh_dictionaries(force=True)

    assert dic.ITEM_TYPE_ALIASES.get("вентиль") == "кран"


def test_admin_service_writes_respect_upsert_and_invalidation(db_env):
    Session = db_env
    from app.services.agent.rules.seed import seed_rules

    db = Session()
    seed_rules(db)
    db.close()

    svc_db = Session()
    from app.services.admin_service import AdminService
    from app.models.sqlalchemy.all_models import SynonymRecord

    svc = AdminService(svc_db)
    svc.create_synonym({"group_name": "item_type", "raw_value": "вентиль", "normalized_value": "кран"})

    row = (
        svc_db.query(SynonymRecord)
        .filter(SynonymRecord.raw_value == "вентиль")
        .first()
    )
    assert row is not None and row.normalized_value == "кран"

    # инвалидация кэшей не должна бросать исключений (БД этой связи нет)
    svc._invalidate_dynamic_rules()
    svc_db.close()


class _FakeParsed:
    def __init__(self, item_types=None, technical_filters=None):
        self.item_types = item_types or []
        self.technical_filters = technical_filters or {}


def test_required_params_warnings_default_rule(db_env):
    Session = db_env
    from app.services.agent.rules.seed import seed_rules

    db = Session()
    seed_rules(db)
    db.close()

    provider = _new_provider(Session)

    from app.services.agent.answer.warnings import build_required_params_warnings

    # «труба» требует dn, стенку, марку — ничего не указано
    parsed = _FakeParsed(item_types=["труба"])
    warnings = build_required_params_warnings(parsed, provider=provider)
    assert len(warnings) == 1
    assert "DN" in warnings[0] and "марка стали" in warnings[0]

    # тип не указан → предупреждений нет
    assert build_required_params_warnings(_FakeParsed(), provider=provider) == []

    # dn указан → предупреждение о DN исчезает, остаётся стенка/сталь
    parsed = _FakeParsed(item_types=["труба"], technical_filters={"dn": 219})
    warnings = build_required_params_warnings(parsed, provider=provider)
    assert "DN" not in " ".join(warnings)


def test_required_params_warnings_custom_rule(db_env):
    Session = db_env
    from app.models.sqlalchemy.all_models import ValidationRule

    db = Session()
    db.add(ValidationRule(
        item_type="штуцер",
        required_params='["dn", "pn"]',
        forbidden_params="[]",
        optional_params="[]",
    ))
    db.commit()
    db.close()

    provider = _new_provider(Session)
    from app.services.agent.answer.warnings import build_required_params_warnings

    parsed = _FakeParsed(item_types=["штуцер"], technical_filters={"dn": 100})
    warnings = build_required_params_warnings(parsed, provider=provider)
    assert len(warnings) == 1
    assert "PN" in warnings[0]

    parsed = _FakeParsed(item_types=["штуцер"], technical_filters={"dn": 100, "pn": 16})
    assert build_required_params_warnings(parsed, provider=provider) == []


def test_forbidden_params_warning(db_env):
    Session = db_env
    from app.models.sqlalchemy.all_models import ValidationRule

    db = Session()
    db.add(ValidationRule(
        item_type="клапан",
        required_params='["dn"]',
        forbidden_params='["angle"]',
        optional_params="[]",
    ))
    db.commit()
    db.close()

    provider = _new_provider(Session)
    from app.services.agent.answer.warnings import build_forbidden_params_warnings

    parsed = _FakeParsed(item_types=["клапан"], technical_filters={"dn": 100, "angle": 45})
    warnings = build_forbidden_params_warnings(parsed, provider=provider)
    assert len(warnings) == 1
    assert "угол" in warnings[0]

    parsed = _FakeParsed(item_types=["клапан"], technical_filters={"dn": 100})
    assert build_forbidden_params_warnings(parsed, provider=provider) == []


def test_optional_params_recommendation(db_env):
    Session = db_env
    from app.models.sqlalchemy.all_models import ValidationRule

    db = Session()
    db.add(ValidationRule(
        item_type="клапан",
        required_params='["dn"]',
        forbidden_params="[]",
        optional_params='["pn", "medium"]',
    ))
    db.commit()
    db.close()

    provider = _new_provider(Session)
    from app.services.agent.answer.warnings import build_optional_params_recommendations

    # required указаны → мягкая рекомендация про optional
    parsed = _FakeParsed(item_types=["клапан"], technical_filters={"dn": 100})
    recs = build_optional_params_recommendations(parsed, provider=provider)
    assert len(recs) == 1
    assert "PN" in recs[0] and "среда" in recs[0]

    # required не указаны → рекомендацию не выдаём (сначала обязательные)
    parsed = _FakeParsed(item_types=["клапан"])
    assert build_optional_params_recommendations(parsed, provider=provider) == []


def test_logical_conditions_warnings(db_env):
    Session = db_env
    from app.models.sqlalchemy.all_models import ValidationRule

    db = Session()
    db.add(ValidationRule(
        item_type="тройник",
        required_params='["dn"]',
        forbidden_params="[]",
        optional_params="[]",
        logical_conditions=[
            {
                "when": {"param": "dn", "op": "gte", "value": 500},
                "then_require": ["wall_thickness", "steel_grade"],
                "then_forbid": ["angle"],
            }
        ],
    ))
    db.commit()
    db.close()

    provider = _new_provider(Session)
    from app.services.agent.answer.warnings import evaluate_parameter_rules

    # условие сработало: стенка не указана + угол запрещён и указан
    parsed = _FakeParsed(item_types=["тройник"], technical_filters={"dn": 500, "angle": 90})
    warnings, recs = evaluate_parameter_rules(parsed, provider=provider)
    joined = " ".join(warnings)
    assert "стенка" in joined
    assert "угол" in joined
    assert "недопустим" in joined
    assert recs == []

    # условие не сработало (dn=300 < 500)
    parsed = _FakeParsed(item_types=["тройник"], technical_filters={"dn": 300, "angle": 90, "wall_thickness": 8})
    warnings, recs = evaluate_parameter_rules(parsed, provider=provider)
    assert all("стенка" not in w and "недопустим" not in w for w in warnings)
    assert recs == []

    # условие сработало, но required/forbidden-параметры в порядке
    parsed = _FakeParsed(item_types=["тройник"], technical_filters={"dn": 500, "wall_thickness": 8, "steel_grade": "09Г2С"})
    warnings, recs = evaluate_parameter_rules(parsed, provider=provider)
    assert warnings == []


def test_is_active_false_skips_rule(db_env):
    Session = db_env
    from app.models.sqlalchemy.all_models import ValidationRule
    from app.services.agent.rules.seed import seed_rules

    db = Session()
    seed_rules(db)
    # правило «заглушка» деактивировано через админку
    row = db.query(ValidationRule).filter(ValidationRule.item_type == "заглушка").first()
    row.is_active = False
    db.commit()
    db.close()

    provider = _new_provider(Session)
    from app.services.agent.answer.warnings import build_required_params_warnings

    # заглушка требует dn/pn, но правило выключено → предупреждений нет
    parsed = _FakeParsed(item_types=["заглушка"])
    assert build_required_params_warnings(parsed, provider=provider) == []

    # активное правило «труба» продолжает работать
    rule = provider.validation_rule("заглушка")
    assert rule["is_active"] is False
    assert provider.validation_rule("труба")["is_active"] is True