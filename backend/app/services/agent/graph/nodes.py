# agent/graph/nodes.py

from typing import Any, Dict
import time

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
from ..answer.builder import build_answer


def parse_node(state: AgentState) -> Dict[str, Any]:
    from ..parsing.hybrid_parser import HybridParser
    
    parser = HybridParser()
    parsed = parser.parse(state["query"])
    state["parsed"] = parsed
    state["context"]["intent"] = _resolve_intent(parsed)
    
    return {"parsed": parsed}


def catalog_node(state: AgentState) -> Dict[str, Any]:
    ctx = get_repository()
    result = catalog_search(state, ctx)
    _merge_result(state, result)
    return {"candidates": state.get("candidates", [])}


def stock_node(state: AgentState) -> Dict[str, Any]:
    ctx = get_repository()
    result = stock_query(state, ctx)
    _merge_result(state, result)
    return {"stock_rows": state.get("stock_rows", [])}


def rules_node(state: AgentState) -> Dict[str, Any]:
    result = rules_engine(state)
    _merge_result(state, result)
    return {"candidates": state.get("candidates", [])}


def graph_node(state: AgentState) -> Dict[str, Any]:
    ctx = get_repository()
    result = graph_search(state, ctx)
    _merge_result(state, result)
    return {"ksm_targets": state.get("ksm_targets", [])}


def impact_node(state: AgentState) -> Dict[str, Any]:
    result = impact_analyzer(state)
    _merge_result(state, result)
    return {"warnings": state.get("warnings", [])}


def regulation_node(state: AgentState) -> Dict[str, Any]:
    ctx = get_repository()
    result = regulation_lookup(state, ctx)
    _merge_result(state, result)
    return {"warnings": state.get("warnings", [])}


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
