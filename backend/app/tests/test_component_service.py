# tests/test_component_service.py
# 2C: уровни детализации get_component (basic / with_stock / full).

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


def _seed(db):
    from app.models.sqlalchemy.all_models import MtrItem

    db.add(
        MtrItem(
            ksm_code="KSM-X-001",
            mtr_code="MTR-X-001",
            item_type="фланец",
            name="Фланец стальной",
            attributes={"dn": 100, "pn": 16},
            stock_qty=5.0,
            unit="pcs",
        )
    )
    db.commit()


def test_basic_level_without_stock(db):
    from app.services.component_service import ComponentService

    _seed(db)
    result = ComponentService(db).get_component("KSM-X-001", detail_level="basic")
    assert result["name"] == "Фланец стальной"
    assert "attributes" not in result
    assert "stock_qty" not in result
    assert result["detail_level"] == "basic"


def test_with_stock_level(db):
    from app.services.component_service import ComponentService

    _seed(db)
    result = ComponentService(db).get_component("MTR-X-001", detail_level="with_stock")
    assert result["attributes"] == {"dn": 100, "pn": 16}
    assert result["stock_qty"] == 5.0
    assert result["unit"] == "pcs"


def test_full_level(db):
    from app.services.component_service import ComponentService

    _seed(db)
    result = ComponentService(db).get_component("KSM-X-001", detail_level="full")
    assert result["attributes"] == {"dn": 100, "pn": 16}
    assert result["stock_qty"] == 5.0


def test_invalid_detail_level(db):
    from app.core.exceptions import ValidationError
    from app.services.component_service import ComponentService

    _seed(db)
    with pytest.raises(ValidationError):
        ComponentService(db).get_component("KSM-X-001", detail_level="ultra")


def test_not_found(db):
    from app.core.exceptions import NotFoundError
    from app.services.component_service import ComponentService

    _seed(db)
    with pytest.raises(NotFoundError):
        ComponentService(db).get_component("KSM-NOPE", detail_level="basic")