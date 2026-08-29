# agent/graph/nodes.py

from typing import Any, Callable, Dict, Optional
import time
import logging

from ..core.state import AgentState
from ..repository.repository_factory import get_repository
from ..llm.client import get_llm_client
from ..tools.core_tools import (
    catalog_search,
    stock_query,
    rules_engine,
    graph_search,
    regulation_lookup,
)
from ..tools.analytic_tools import (
    impact_analyzer,
    inventory_calculator,
    maintenance_planner,
    duplicate_detector,
)
from ..tools.error_handler import ErrorDecision, ErrorHandler
from ..tools.errors import ToolErrorCode
from ..answer.builder import build_answer

log = logging.getLogger("mtr.agent.graph.nodes")


def _set_repository(state: AgentState) -> None:
    state.setdefault("context", {}).setdefault("repository", get_repository())


def _normalize_error(error: Any) -> Optional[Dict[str, Any]]:
    """Приводит error-контракт к виду {'code', 'message', 'details'} (3D)."""
    if error is None:
        return None
    if isinstance(error, dict):
        return {
            "code": str(error.get("code") or "UNKNOWN"),
            "message": str(error.get("message") or ""),
            "details": error.get("details"),
        }
    return {"code": ToolErrorCode.DAL_ERROR, "message": str(error), "details": None}


def _empty_error_result(message: str) -> Dict[str, Any]:
    return {
        "text": "",
        "components": [],
        "warnings": [],
        "sources": [],
        "missing": [],
        "review": False,
        "error": {"code": ToolErrorCode.DAL_ERROR, "message": message, "details": None},
    }


def _guarded_tool(
    tool_name: str,
    tool_fn: Callable,
    state: AgentState,
    ctx: Any = None,
    required: bool = False,
) -> Dict[str, Any]:
    """Исполняет инструмент графа через ErrorHandler (4B.1).

    Инструменты графа возвращают dict с полем "error". Обёртка нормализует
    контракт, применяет ретраи/классификацию и отмечает STOP/SKIP warning'ами.
    Вызывается единообразно: tool_fn(state, ctx).
    """
    handler = ErrorHandler()

    def execute(_input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = tool_fn(state, ctx)
        except Exception as e:  # noqa: BLE001
            log.error("[%s] unexpected exception: %s", tool_name, e)
            result = _empty_error_result(str(e))
        result["error"] = _normalize_error(result.get("error"))
        return result

    result = handler.run(execute, tool_name=tool_name, input_data={}, required=required)
    decision = result.get("decision")
    err = result.get("error")
    if err:
        if decision == ErrorDecision.STOP:
            result.setdefault("warnings", []).append(
                f"Инструмент «{tool_name}» остановлен: {err.get('message')}"
            )
            result["review"] = True
        elif decision == ErrorDecision.SKIP:
            result.setdefault("warnings", []).append(
                f"Инструмент «{tool_name}» пропущен: {err.get('message')}"
            )
    return result


def parse_node(state: AgentState) -> Dict[str, Any]:
    parsed = state.get("parsed")
    if parsed is None:
        from ..parsing.hybrid_parser import HybridParser

        parser = HybridParser()
        parsed = parser.parse(state["query"])
        state["parsed"] = parsed

    if not getattr(parsed, "intents", None):
        from ..intent.detect import enrich_parsed

        try:
            enrich_parsed(parsed)
        except Exception as e:  # прагматично: не ломаем основной путь
            log.warning("[parse_node] intent enrichment failed: %s", e)

    state["context"]["intent"] = _resolve_intent(parsed)
    return {"parsed": parsed}


def catalog_node(state: AgentState) -> Dict[str, Any]:
    ctx = get_repository()
    result = _guarded_tool("search_catalog", catalog_search, state, ctx, required=True)
    result["_tool_name"] = "catalog_search"
    _merge_result(state, result)
    return {"candidates": state.get("candidates", [])}


def stock_node(state: AgentState) -> Dict[str, Any]:
    ctx = get_repository()
    result = _guarded_tool("check_stock", stock_query, state, ctx, required=True)
    result["_tool_name"] = "stock_query"
    _merge_result(state, result)
    return {"stock_rows": state.get("stock_rows", [])}


def rules_node(state: AgentState) -> Dict[str, Any]:
    result = _guarded_tool("rules_engine", lambda s, c: rules_engine(s), state)
    result["_tool_name"] = "rules_engine"
    _merge_result(state, result)
    return {"candidates": state.get("candidates", [])}


def graph_node(state: AgentState) -> Dict[str, Any]:
    ctx = get_repository()
    result = _guarded_tool("graph_search", graph_search, state, ctx)
    result["_tool_name"] = "graph_search"
    _merge_result(state, result)
    return {"ksm_targets": state.get("ksm_targets", [])}


def impact_node(state: AgentState) -> Dict[str, Any]:
    result = _guarded_tool("impact_analyzer", lambda s, c: impact_analyzer(s), state)
    result["_tool_name"] = "impact_analyzer"
    _merge_result(state, result)
    return {"warnings": state.get("warnings", [])}


def regulation_node(state: AgentState) -> Dict[str, Any]:
    ctx = get_repository()
    result = _guarded_tool("regulation_lookup", regulation_lookup, state, ctx)
    result["_tool_name"] = "regulation_lookup"
    _merge_result(state, result)
    return {"warnings": state.get("warnings", [])}


def inventory_node(state: AgentState) -> Dict[str, Any]:
    _set_repository(state)
    result = _guarded_tool("inventory_calculator", lambda s, c: inventory_calculator(s), state)
    result["_tool_name"] = "inventory_calculator"
    _merge_result(state, result)
    return {"components": state.get("components", [])}


def maintenance_node(state: AgentState) -> Dict[str, Any]:
    _set_repository(state)
    result = _guarded_tool("maintenance_planner", lambda s, c: maintenance_planner(s), state)
    result["_tool_name"] = "maintenance_planner"
    _merge_result(state, result)
    return {"components": state.get("components", [])}


def duplicates_node(state: AgentState) -> Dict[str, Any]:
    _set_repository(state)
    result = _guarded_tool("duplicate_detector", lambda s, c: duplicate_detector(s), state)
    result["_tool_name"] = "duplicate_detector"
    _merge_result(state, result)
    return {"components": state.get("components", [])}


def llm_enhance_node(state: AgentState) -> Dict[str, Any]:
    """Узел для LLM-усиления ответа (если нужно)"""
    # ✅ LLM получаем через глобальную фабрику
    from ..llm.client import get_llm_client
    llm = get_llm_client()
    
    if not llm:
        return {"llm_enhanced": False}
    
    # Здесь можно добавить LLM-обработку
    # Например, улучшить текст ответа
    
    return {"llm_enhanced": True}


def answer_node(state: AgentState) -> Dict[str, Any]:
    intent = state.get("context", {}).get("intent", "search")
    result = {
        "components": state.get("components", []),
        "sources": state.get("sources", []),
        "warnings": state.get("warnings", []),
        "missing": state.get("missing", []),
        "review": state.get("review_required", False),
        "answers": [state.get("context", {}).get("last_text", "")],
        "mode": state.get("context", {}).get("mode", "offline_rules"),
        "tools_used": state.get("context", {}).get("tools_used", []),
    }
    
    answer = build_answer(state["parsed"], intent, result)
    state["answer"] = answer
    state["completed"] = True
    
    return {"answer": answer}


def _merge_result(state: AgentState, result: Dict[str, Any]) -> None:
    if result.get("components"):
        state.setdefault("components", []).extend(result["components"])
    if result.get("sources"):
        state.setdefault("sources", []).extend(result["sources"])
    if result.get("warnings"):
        state.setdefault("warnings", []).extend(result["warnings"])
    if result.get("missing"):
        state.setdefault("missing", []).extend(result["missing"])
    if result.get("review"):
        state["review_required"] = True
    if result.get("text"):
        state["context"]["last_text"] = result["text"]
    if result.get("_tool_name"):
        state.setdefault("context", {}).setdefault("tools_used", []).append(result["_tool_name"])


def _resolve_intent(parsed) -> str:
    operations = getattr(parsed, "operations", [])
    query = getattr(parsed, "original_query", "").lower()
    
    if "дубл" in query:
        return "duplicates"
    if getattr(parsed, "proposed_changes", {}):
        return "impact_analysis"
    
    intent_map = {
        "replace": "replacement",
        "repair": "maintenance",
        "inventory": "inventory",
        "calculate": "inventory",
        "plan": "maintenance",
        "impact": "impact_analysis",
        "explain": "equipment_guidance",
        "document": "document_search",
        "assemble": "object_configuration",
    }
    
    for op in operations:
        if op in intent_map:
            return intent_map[op]
    
    return "search"
