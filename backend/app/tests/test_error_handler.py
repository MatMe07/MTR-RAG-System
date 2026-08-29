# tests/test_error_handler.py
"""Юнит-тесты ErrorHandler (ЭТАП 4, секция 4B.1)."""

from app.services.agent.tools.error_handler import (
    ErrorHandler,
    ErrorDecision,
    REQUIRED_TOOLS,
)
from app.services.agent.tools.errors import ToolErrorCode


def _make_execute(responses):
    """Возвращает execute(input), который последовательно отдаёт responses."""
    state = {"i": 0}

    def execute(input_data):
        idx = min(state["i"], len(responses) - 1)
        state["i"] += 1
        return responses[idx]

    return execute


def test_proceed_without_error():
    handler = ErrorHandler(retry_backoff_base=0.0)
    result = handler.run(_make_execute([{"result": {"value": 1}, "error": None}]), tool_name="t")
    assert result["decision"] == ErrorDecision.PROCEED


def test_not_found_non_required_skips():
    handler = ErrorHandler(retry_backoff_base=0.0)
    calls = [{"result": None, "error": {"code": ToolErrorCode.NOT_FOUND, "message": "нет"}}]
    result = handler.run(_make_execute(calls), tool_name="search_norms", required=False)
    assert result["decision"] == ErrorDecision.SKIP


def test_not_found_required_stops():
    handler = ErrorHandler(retry_backoff_base=0.0)
    calls = [{"result": None, "error": {"code": ToolErrorCode.NOT_FOUND, "message": "нет"}}]
    result = handler.run(_make_execute(calls), tool_name="search_catalog", required=True)
    assert result["decision"] == ErrorDecision.STOP


def test_invalid_params_stops_immediately():
    handler = ErrorHandler(retry_backoff_base=0.0)
    error = {"code": ToolErrorCode.INVALID_PARAMS, "message": "плохо"}
    result = handler.run(_make_execute([{"result": None, "error": error}]), tool_name="t")
    assert result["decision"] == ErrorDecision.STOP


def test_dal_error_retries_then_stops():
    handler = ErrorHandler(max_retries=3, retry_backoff_base=0.0)
    error = {"code": ToolErrorCode.DAL_ERROR, "message": "БД недоступна"}
    # Первый вызов + 3 ретрая — все ошибки.
    calls = [{"result": None, "error": error}] * 4
    result = handler.run(_make_execute(calls), tool_name="check_stock", required=True)
    assert result["decision"] == ErrorDecision.STOP


def test_dal_error_retries_then_succeeds():
    handler = ErrorHandler(max_retries=3, retry_backoff_base=0.0)
    error = {"code": ToolErrorCode.DAL_ERROR, "message": "БД недоступна"}
    calls = [
        {"result": None, "error": error},
        {"result": None, "error": error},
        {"result": {"value": "ok"}, "error": None},
    ]
    result = handler.run(_make_execute(calls), tool_name="check_stock")
    assert result["decision"] == ErrorDecision.PROCEED


def test_batch_too_large_reduces_batch():
    handler = ErrorHandler(max_retries=2, retry_backoff_base=0.0)
    seen = []

    def execute(input_data):
        seen.append(list(input_data.get("ksm_codes", [])))
        if len(input_data.get("ksm_codes", [])) > 1:
            return {"result": None, "error": {"code": ToolErrorCode.BATCH_TOO_LARGE, "message": "x"}}
        return {"result": {"value": "ok"}, "error": None}

    result = handler.run(execute, tool_name="check_compatibility_batch",
                         input_data={"ksm_codes": ["a", "b", "c", "d"], "context": {}})
    # Первая попытка 4 шт → ретрай 2 шт → ещё >1? 2>1 → next retry 1 шт → успех.
    assert seen[0] == ["a", "b", "c", "d"]
    assert seen[1] == ["a", "b"]
    assert seen[2] == ["a"]
    assert result["decision"] == ErrorDecision.PROCEED


def test_required_tools_set():
    assert {"search_catalog", "get_component", "check_stock"} <= REQUIRED_TOOLS


# ---------------------------------------------------------------------------
# Интеграция ErrorHandler в детерминированный граф (_guarded_tool, 4B.1)
# ---------------------------------------------------------------------------

from app.services.agent.graph.nodes import _guarded_tool  # noqa: E402
from app.services.agent.core.state import create_initial_state  # noqa: E402
from app.schemas import ParsedQuery  # noqa: E402


def _test_state(query="отвод"):
    return create_initial_state(query=query, parsed=ParsedQuery(original_query=query))


def _tool_result(**overrides):
    base = {
        "text": "",
        "components": [],
        "warnings": [],
        "sources": [],
        "missing": [],
        "review": False,
        "error": None,
    }
    base.update(overrides)
    return base


def test_guarded_tool_success_no_error():
    state = _test_state()

    def tool(state, ctx):
        return _tool_result(text="ok")

    result = _guarded_tool("catalog_search", tool, state, ctx=None, required=True)
    assert result["error"] is None
    assert result["text"] == "ok"
    assert result["warnings"] == []


def test_guarded_tool_invalid_params_stops_required():
    state = _test_state()

    def tool(state, ctx):
        return _tool_result(
            error={"code": ToolErrorCode.INVALID_PARAMS, "message": "плохие параметры"}
        )

    result = _guarded_tool("search_catalog", tool, state, ctx=None, required=True)
    assert result["decision"] == ErrorDecision.STOP
    assert result["review"] is True
    assert any("остановлен" in w for w in result["warnings"])


def test_guarded_tool_not_found_skips_non_required():
    state = _test_state("норматив")

    def tool(state, ctx):
        return _tool_result(
            error={"code": ToolErrorCode.NOT_FOUND, "message": "нет документа"}
        )

    result = _guarded_tool("search_norms", tool, state, ctx=None, required=False)
    assert result["decision"] == ErrorDecision.SKIP
    assert any("пропущен" in w for w in result["warnings"])
    assert result["review"] is False


def test_guarded_tool_exception_becomes_dal_error():
    state = _test_state()

    def tool(state, ctx):
        raise RuntimeError("БД упала")

    result = _guarded_tool("graph_search", tool, state, ctx=None)
    assert result["error"]["code"] == ToolErrorCode.DAL_ERROR
    assert result["decision"] == ErrorDecision.STOP
    assert any("остановлен" in w for w in result["warnings"])


def test_guarded_tool_string_error_normalized():
    state = _test_state()

    def tool(state, ctx):
        return _tool_result(error="repository_not_available")

    # Строковая ошибка нормализуется в {"code": ...}; для необязательного
    # инструмента с кодом DAL_ERROR — ретраи, затем STOP.
    result = _guarded_tool("rules_engine", tool, state, ctx=None)
    assert isinstance(result["error"], dict)
    assert result["error"]["code"] == ToolErrorCode.DAL_ERROR