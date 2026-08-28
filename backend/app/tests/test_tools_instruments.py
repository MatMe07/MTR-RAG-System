# tests/test_tools_instruments.py
"""Unit-тесты инструментов ЭТАПА 3 (3G.1): валидация, ошибки, лимиты."""

import pytest

from app.services.agent.repository.json_repository import JsonRepository
from app.services.agent.tools.errors import ToolError, ToolErrorCode
from app.services.agent.tools.instruments import (
    INTENT_TOOLS,
    PASSPORT_WEIGHTS,
    execute_check_compatibility_batch,
    execute_check_stock,
    execute_search_catalog,
    run_instrument,
)
from app.services.agent.tools.registry import (
    get_instrument,
    get_instruments_for_llm,
    get_intent_tools,
    list_instruments,
)
from app.services.agent.tools.tool_dal import ToolDAL
from app.services.agent.tools.tool_log import get_tool_logger
from app.services.agent.tools.validation import validate_input


@pytest.fixture()
def dal() -> ToolDAL:
    return ToolDAL(JsonRepository())


# ===========================================================================
# Реестр инструментов (3B)
# ===========================================================================
def test_thirteen_instruments_registered():
    assert len(list_instruments()) == 13
    assert set(list_instruments()) == {
        "search_catalog",
        "get_component",
        "search_by_passport",
        "check_stock",
        "get_low_stock_items",
        "get_unused_stock",
        "get_unit_structure",
        "get_neighbors",
        "is_installed_anywhere",
        "check_compatibility",
        "check_compatibility_batch",
        "search_norms",
        "get_component_history",
    }


def test_instrument_has_schema_and_validator(dal):
    inst = get_instrument("search_catalog")
    assert inst is not None
    assert inst["input_schema"]["required"] == ["params"]
    assert inst["output_schema"]["properties"]["total_count"]["type"] == "integer"
    inst["validate_input"]({"params": {"dn": 159}})


def test_llm_registry_descriptors():
    registry = get_instruments_for_llm()
    assert len(registry) == 13
    for desc in registry:
        assert {"name", "description", "input_schema", "output_schema", "required_intents"} <= set(desc)


# ===========================================================================
# Карта интентов (3E)
# ===========================================================================
def test_intent_map_covers_spec():
    assert len(INTENT_TOOLS) == 24
    for intent, tools in INTENT_TOOLS.items():
        assert tools, f"intent {intent} без инструментов"
        assert get_intent_tools(intent) == tools


# ===========================================================================
# Валидация входных данных (3C)
# ===========================================================================
def _error(result):
    return result["error"]


def test_unknown_tool():
    with pytest.raises(ToolError) as exc:
        run_instrument("no_such_tool", {})
    assert exc.value.code == ToolErrorCode.TOOL_NOT_FOUND


def test_neighbors_depth_over_5_invalid(dal):
    result = run_instrument(
        "get_neighbors", {"ksm_code": "KSM-SYN-REG-000001", "depth": 6}, dal=dal
    )
    assert result["result"] is None
    assert result["error"]["code"] == ToolErrorCode.INVALID_PARAMS


def test_search_catalog_limit_over_100_invalid(dal):
    result = run_instrument(
        "search_catalog", {"params": {"item_type": "труба", "limit": 101}}, dal=dal
    )
    assert result["error"]["code"] == ToolErrorCode.INVALID_PARAMS


def test_search_catalog_dn_out_of_range_invalid(dal):
    result = run_instrument(
        "search_catalog", {"params": {"dn": 2500}}, dal=dal
    )
    assert result["error"]["code"] == ToolErrorCode.INVALID_PARAMS


def test_detail_level_enum_invalid(dal):
    result = run_instrument(
        "get_component", {"identifier": "KSM-SYN-REG-000001", "detail_level": "ultra"}, dal=dal
    )
    assert result["error"]["code"] == ToolErrorCode.INVALID_PARAMS


def test_compatibility_context_requires_pn(dal):
    result = run_instrument(
        "check_compatibility",
        {"ksm_code": "KSM-SYN-REG-000001", "context": {"medium": "gas_h2s"}},
        dal=dal,
    )
    assert result["error"]["code"] == ToolErrorCode.INVALID_PARAMS


def test_check_stock_empty_returns_empty(dal):
    result = run_instrument("check_stock", {"ksm_codes": []}, dal=dal)
    assert result["error"] is None
    assert result["result"] == {}


def test_check_compatibility_batch_too_large(dal):
    ksms = [f"KSM-{i:06d}" for i in range(51)]
    result = run_instrument(
        "check_compatibility_batch",
        {"ksm_codes": ksms, "context": {"medium": "gas_h2s", "pn": 40}},
        dal=dal,
    )
    assert result["error"]["code"] == ToolErrorCode.BATCH_TOO_LARGE
    assert result["error"]["details"]["max"] == 50
    assert result["error"]["details"]["received"] == 51


def test_validate_input_direct():
    schema = {
        "type": "object",
        "properties": {
            "depth": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["depth"],
    }
    validate_input(schema, {"depth": 3})
    with pytest.raises(ToolError) as exc:
        validate_input(schema, {"depth": 6})
    assert exc.value.code == ToolErrorCode.INVALID_PARAMS


# ===========================================================================
# NOT_FOUND (3D)
# ===========================================================================
def test_get_component_not_found(dal):
    result = run_instrument("get_component", {"identifier": "KSM-NOPE-000"}, dal=dal)
    assert result["error"]["code"] == ToolErrorCode.NOT_FOUND


# ===========================================================================
# Логирование вызовов (3F)
# ===========================================================================
def test_execution_logged(dal):
    get_tool_logger().clear()
    run_instrument("get_component", {"identifier": "KSM-SYN-REG-000001"}, dal=dal)
    run_instrument("get_component", {"identifier": "UNKNOWN-000"}, dal=dal)
    logs = get_tool_logger().get_logs(tool_name="get_component")
    assert len(logs) == 2
    ok = [r for r in logs if r.output_data is not None]
    err = [r for r in logs if r.error is not None]
    assert len(ok) == 1 and len(err) == 1
    assert err[0].error["code"] == ToolErrorCode.NOT_FOUND
    assert all(r.duration_ms >= 0 for r in logs)


# ===========================================================================
# Взвешенный confidence (3A.3)
# ===========================================================================
def test_pasport_weights_summary():
    assert PASSPORT_WEIGHTS["dn"] == 0.30
    assert PASSPORT_WEIGHTS["medium"] == 0.10
    assert abs(sum(PASSPORT_WEIGHTS.values()) - 1.0) < 1e-9