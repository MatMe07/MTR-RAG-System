# tests/test_import_service.py
# 2E: процедуры импорта каталога / склада / графа.

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


def test_import_catalog_creates_items(db):
    from app.services.import_service import ImportService
    from app.models.sqlalchemy.all_models import CandidateItem, MtrItem

    result = ImportService(db).import_catalog(
        [
            {
                "codes": {"mtr_code": "MTR-1", "ksm_code": "KSM-1"},
                "card_id": "c1",
                "item_type": "фланец",
                "name": "Фланец стальной",
                "properties": {"dn": {"value": 100}, "pn": {"value": 16}},
            }
        ],
        changed_by="importer",
    )
    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["errors"] == []

    item = db.query(MtrItem).filter(MtrItem.mtr_code == "MTR-1").first()
    assert item is not None
    assert item.item_type == "фланец"
    assert item.attributes == {"dn": 100, "pn": 16}

    stock = db.query(CandidateItem).filter(CandidateItem.ksm_code == "KSM-1").first()
    assert stock is not None


def test_import_catalog_update_writes_history(db):
    from app.services.import_service import ImportService
    from app.models.sqlalchemy.all_models import MtrItem, MtrItemHistory

    svc = ImportService(db)
    svc.import_catalog([{"codes": {"mtr_code": "MTR-1"}, "item_type": "отвод", "name": "Отвод 90", "properties": {"dn": 50}}])

    result = svc.import_catalog(
        [{"codes": {"mtr_code": "MTR-1"}, "item_type": "отвод", "name": "Отвод 90 ст", "properties": {"dn": 80}}],
        changed_by="editor",
    )
    assert result["created"] == 0
    assert result["updated"] == 1

    item = db.query(MtrItem).filter(MtrItem.mtr_code == "MTR-1").first()
    assert item.attributes == {"dn": 80}
    assert item.name == "Отвод 90 ст"

    history = db.query(MtrItemHistory).all()
    assert len(history) == 1
    assert history[0].changed_by == "editor"
    assert history[0].old_attributes == {"dn": 50}
    assert history[0].new_attributes == {"dn": 80}


def test_import_catalog_errors_on_invalid_rows(db):
    from app.services.import_service import ImportService

    result = ImportService(db).import_catalog(
        [
            {"codes": {}, "item_type": "фланец"},       # без mtr_code
            {"codes": {"mtr_code": "MTR-2"}},            # без item_type
        ]
    )
    assert result["created"] == 0
    assert len(result["errors"]) == 2


def test_import_stock_updates_quantities(db):
    from app.services.import_service import ImportService
    from app.models.sqlalchemy.all_models import CandidateItem

    svc = ImportService(db)
    svc.import_catalog([{"codes": {"mtr_code": "MTR-1", "ksm_code": "KSM-1"}, "item_type": "фланец", "name": "Фланец"}])

    result = svc.import_stock([{"ksm_code": "KSM-1", "quantity": 12.5, "cost": 90.0}])
    assert result["total"] == 1
    assert result["errors"] == []

    stock = db.query(CandidateItem).filter(CandidateItem.ksm_code == "KSM-1").first()
    assert stock.quantity == 12.5
    assert stock.cost == 90.0


def test_import_stock_unknown_ksm_errors(db):
    from app.services.import_service import ImportService

    result = ImportService(db).import_stock([{"ksm_code": "KSM-UNKNOWN", "quantity": 1}])
    assert result["total"] == 0
    assert len(result["errors"]) == 1


def test_import_graph_edges(db):
    from app.services.import_service import ImportService
    from app.models.sqlalchemy.all_models import PipelineEdge

    result = ImportService(db).import_graph(
        {
            "edges": [
                {"from": "KSM-1", "to": "KSM-2", "connection_type": "pipeline", "distance_m": 12.0},
                {"from": "KSM-2", "to": "KSM-3"},
            ]
        }
    )
    assert result["edges"] == 2
    assert db.query(PipelineEdge).count() == 2