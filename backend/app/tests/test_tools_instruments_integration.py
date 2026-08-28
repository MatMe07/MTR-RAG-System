# tests/test_tools_instruments_integration.py
"""Интеграционные тесты инструментов ЭТАПА 3 (3G.2) на JSON-репозитории.

Полноценные сценарии 3G.2 против PostgreSQL выполнятся после поднятия
инфраструктуры (Шаг 3); здесь те же сценарии на детерминированном fallback.
"""

import pytest

from app.services.agent.repository.json_repository import JsonRepository
from app.services.agent.tools.instruments import run_instrument
from app.services.agent.tools.tool_dal import ToolDAL


@pytest.fixture()
def dal() -> ToolDAL:
    return ToolDAL(JsonRepository())


def _catalog_ksms(dal, n=None):
    ksms = [
        (c.get("codes") or {}).get("ksm_code")
        for c in dal.repo.get_catalog()
        if (c.get("codes") or {}).get("ksm_code")
    ]
    return ksms if n is None else ksms[:n]


# ---------------------------------------------------------------------------
# search_catalog: отвод 90 DN159, detail_level="full"
# ---------------------------------------------------------------------------
def test_search_catalog_elbow_90_dn159_full(dal):
    result = run_instrument(
        "search_catalog",
        {"params": {"item_type": "отвод", "dn": 159, "angle": 90, "limit": 20}, "detail_level": "full"},
        dal=dal,
    )
    assert result["error"] is None, result["error"]
    assert result["result"]["total_count"] > 0
    first = result["result"]["items"][0]
    assert first["component"]["item_type"] == "отвод"
    assert "stock" in first
    assert "neighbors" in first


# ---------------------------------------------------------------------------
# get_component: KSM-SYN-REG-000001, detail_level="with_stock"
# ---------------------------------------------------------------------------
def test_get_component_with_stock(dal):
    result = run_instrument(
        "get_component", {"identifier": "KSM-SYN-REG-000001", "detail_level": "with_stock"}, dal=dal
    )
    assert result["error"] is None, result["error"]
    comp = result["result"]
    assert comp["component"]["ksm_code"] == "KSM-SYN-REG-000001"
    assert isinstance(comp["stock"]["quantity"], (int, float))


# ---------------------------------------------------------------------------
# search_by_passport: паспорт_001 → правильный KSM в топ-3, confidence > 0.6
# ---------------------------------------------------------------------------
def test_search_by_passport_top3(dal):
    result = run_instrument("search_by_passport", {"document_id": "passport_001", "limit": 5}, dal=dal)
    assert result["error"] is None, result["error"]
    suggestions = result["result"]["value"]
    assert len(suggestions) >= 3
    top3 = suggestions[:3]
    assert top3[0]["confidence"] > 0.6
    assert "dn" in top3[0]["matched_params"]
    # Корректный KSM (отвод DN159) входит в топ-3
    assert any("159" in s["name"] or "отвод" in s["name"] for s in top3)


# ---------------------------------------------------------------------------
# check_stock: 5 KSM
# ---------------------------------------------------------------------------
def test_check_stock_5_ksm(dal):
    ksms = _catalog_ksms(dal, 5)
    result = run_instrument("check_stock", {"ksm_codes": ksms}, dal=dal)
    assert result["error"] is None, result["error"]
    stock = result["result"]
    assert len(stock) == 5
    for ksm, item in stock.items():
        assert item["ksm_code"] == ksm
        assert isinstance(item["quantity"], (int, float))


# ---------------------------------------------------------------------------
# get_unused_stock: остаток > 50, не установлены на участках
# ---------------------------------------------------------------------------
def test_get_unused_stock(dal):
    result = run_instrument("get_unused_stock", {"min_qty": 50}, dal=dal)
    assert result["error"] is None, result["error"]
    items = result["result"]["value"]
    for item in items:
        assert item["quantity"] > 50
        assert not dal.is_installed_anywhere(item["ksm_code"])


# ---------------------------------------------------------------------------
# check_compatibility: задвижка DN150 PN40, среда H2S
# ---------------------------------------------------------------------------
def test_check_compatibility_valve_h2s(dal):
    valve_ksm = next(
        (
            (c.get("codes") or {}).get("ksm_code")
            for c in dal.repo.get_catalog()
            if c.get("item_type") == "задвижка" and (c.get("codes") or {}).get("ksm_code")
        ),
        None,
    )
    assert valve_ksm is not None
    result = run_instrument(
        "check_compatibility",
        {"ksm_code": valve_ksm, "context": {"medium": "gas_h2s", "pn": 40, "temperature": 60}},
        dal=dal,
    )
    assert result["error"] is None, result["error"]
    comp = result["result"]
    assert "compatible" in comp
    assert "warnings" in comp and "required_actions" in comp
    assert "confidence" in comp


# ---------------------------------------------------------------------------
# check_compatibility_batch: 30 деталей, лимит 50 не превышен
# ---------------------------------------------------------------------------
def test_check_compatibility_batch_30(dal):
    ksms = _catalog_ksms(dal, 30)
    result = run_instrument(
        "check_compatibility_batch",
        {"ksm_codes": ksms, "context": {"medium": "gas_h2s", "pn": 40}},
        dal=dal,
    )
    assert result["error"] is None, result["error"]
    assert len(result["result"]) == 30


# ---------------------------------------------------------------------------
# search_norms: "требования к H2S для задвижек", document_type="ЛНД"
# ---------------------------------------------------------------------------
def test_search_norms_filter_lnd(dal):
    result = run_instrument(
        "search_norms", {"query": "требования H2S задвижки", "document_type": "ЛНД", "limit": 5}, dal=dal
    )
    assert result["error"] is None, result["error"]
    items = result["result"]["value"]
    assert items
    assert all(f["document_type"] == "ЛНД" for f in items)


# ---------------------------------------------------------------------------
# get_unit_structure: пагинация (limit=20, offset=0)
# ---------------------------------------------------------------------------
def test_get_unit_structure_pagination(dal):
    unit_code = "UNIT-SYN-H2S-001"
    result = run_instrument(
        "get_unit_structure", {"unit_code": unit_code, "limit": 20, "offset": 0}, dal=dal
    )
    assert result["error"] is None, result["error"]
    page = result["result"]
    assert page["offset"] == 0
    assert page["limit"] == 20
    assert page["total_count"] == len(dal.repo.get_components_by_unit(unit_code))
    assert len(page["items"]) == page["total_count"]
    assert page["has_more"] is False


# ---------------------------------------------------------------------------
# get_component_history
# ---------------------------------------------------------------------------
def test_get_component_history(dal):
    result = run_instrument(
        "get_component_history", {"ksm_code": "KSM-SYN-REG-000001", "limit": 10}, dal=dal
    )
    assert result["error"] is None, result["error"]
    page = result["result"]
    assert {"items", "total_count", "offset", "limit", "has_more"} <= set(page)


# ---------------------------------------------------------------------------
# get_low_stock_items: фильтр по участку
# ---------------------------------------------------------------------------
def test_get_low_stock_items_by_unit(dal):
    result = run_instrument(
        "get_low_stock_items", {"threshold": 2.0, "unit_code": "UNIT-SYN-H2S-001"}, dal=dal
    )
    assert result["error"] is None, result["error"]
    for item in result["result"]["value"]:
        assert item["quantity"] < 2.0


# ---------------------------------------------------------------------------
# get_neighbors / is_installed_anywhere
# ---------------------------------------------------------------------------
def test_neighbors_and_installed(dal):
    installed = {
        c.get("ksm_code")
        for c in dal.repo.get_graph().get("components", [])
        if c.get("ksm_code")
    }
    assert installed
    start = next(iter(installed))
    result = run_instrument(
        "get_neighbors", {"ksm_code": start, "depth": 1, "direction": "both"}, dal=dal
    )
    assert result["error"] is None, result["error"]
    for n in result["result"]["value"]:
        assert n["ksm_code"] in installed

    inst = run_instrument("is_installed_anywhere", {"ksm_code": start}, dal=dal)
    assert inst["result"]["value"] is True


# ---------------------------------------------------------------------------
# Лимит пагинации get_unit_structure автоматически ограничивается 100
# ---------------------------------------------------------------------------
def test_unit_structure_limit_capped(dal):
    result = run_instrument("get_unit_structure", {"unit_code": "UNIT-SYN-GAS-001", "limit": 999}, dal=dal)
    assert result["error"] is None, result["error"]
    assert result["result"]["limit"] == 100