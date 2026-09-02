# agent/graph/nodes.py

from typing import Any, Callable, Dict, Optional, List
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
    sufficiency_check,
    maintenance_planner,
    duplicate_detector,
)
from ..tools.error_handler import ErrorDecision, ErrorHandler
from ..tools.errors import ToolErrorCode
from ..answer.builder import build_answer

log = logging.getLogger("mtr.agent.graph.nodes")


def _set_repository(state: AgentState) -> None:
    # Репозиторий не кладём в state: он не msgpack-сериализуем и ломает
    # контрольные точки LangGraph. Инструменты получают ctx из обёрток узлов.
    pass


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
    patch = _merge_result(state, result)
    return {**patch, "candidates": state.get("candidates", [])}


def stock_node(state: AgentState) -> Dict[str, Any]:
    ctx = get_repository()
    result = _guarded_tool("check_stock", stock_query, state, ctx, required=True)
    result["_tool_name"] = "stock_query"
    patch = _merge_result(state, result)
    return {**patch, "stock_rows": state.get("stock_rows", [])}


def rules_node(state: AgentState) -> Dict[str, Any]:
    result = _guarded_tool("rules_engine", lambda s, c: rules_engine(s), state)
    result["_tool_name"] = "rules_engine"
    patch = _merge_result(state, result)
    return {**patch, "candidates": state.get("candidates", [])}


def graph_node(state: AgentState) -> Dict[str, Any]:
    ctx = get_repository()
    _set_repository(state)
    result = _guarded_tool("graph_search", graph_search, state, ctx)
    result["_tool_name"] = "graph_search"
    patch = _merge_result(state, result)
    return {**patch, "ksm_targets": state.get("ksm_targets", [])}


def impact_node(state: AgentState) -> Dict[str, Any]:
    _set_repository(state)
    result = _guarded_tool("impact_analyzer", lambda s, c: impact_analyzer(s), state)
    result["_tool_name"] = "impact_analyzer"
    return _merge_result(state, result)


def regulation_node(state: AgentState) -> Dict[str, Any]:
    ctx = get_repository()
    result = _guarded_tool("regulation_lookup", regulation_lookup, state, ctx)
    result["_tool_name"] = "regulation_lookup"
    return _merge_result(state, result)


def inventory_node(state: AgentState) -> Dict[str, Any]:
    _set_repository(state)
    result = _guarded_tool("inventory_calculator", lambda s, c: inventory_calculator(s), state)
    result["_tool_name"] = "inventory_calculator"
    return _merge_result(state, result)


def sufficiency_node(state: AgentState) -> Dict[str, Any]:
    _set_repository(state)
    result = _guarded_tool("sufficiency_check", lambda s, c: sufficiency_check(s), state)
    result["_tool_name"] = "sufficiency_check"
    return _merge_result(state, result)


def maintenance_node(state: AgentState) -> Dict[str, Any]:
    _set_repository(state)
    result = _guarded_tool("maintenance_planner", lambda s, c: maintenance_planner(s), state)
    result["_tool_name"] = "maintenance_planner"
    return _merge_result(state, result)


def duplicates_node(state: AgentState) -> Dict[str, Any]:
    _set_repository(state)
    result = _guarded_tool("duplicate_detector", lambda s, c: duplicate_detector(s), state)
    result["_tool_name"] = "duplicate_detector"
    return _merge_result(state, result)


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

    return {"answer": answer, "completed": True}


def _is_stock_row(row: Dict[str, Any]) -> bool:
    """Признак строки склада (stock_query): несёт реальный остаток."""
    status = str(row.get("status") or "").lower()
    return "складе" in status


def _component_key(row: Dict[str, Any]) -> Optional[Any]:
    """Ключ агрегации: mtr_code/ksm_code либо (name, item_type, status) для бескодовых."""
    for code_key in ("mtr_code", "ksm_code"):
        code = row.get(code_key)
        if code:
            return ("code", code)
    return ("row", row.get("name"), row.get("item_type"), row.get("status"))


def _merge_rows(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Слияние двух строк-компонентов одной детали (каталог + правила + склад)."""
    for k in ("mtr_code", "ksm_code", "name", "item_type"):
        if not a.get(k) and b.get(k):
            a[k] = b[k]
    if b.get("match_score") is not None and a.get("match_score") is None:
        for k in ("match_score", "match_percent", "matched_params",
                  "mismatched_params", "missing_params", "tz_status"):
            if b.get(k) is not None:
                a[k] = b[k]
        if b.get("status"):
            a["status"] = b["status"]
    qty_b = b.get("quantity")
    stock_b = _is_stock_row(b)
    if (qty_b is not None
            and a.get("quantity") in (None, 0)
            and (qty_b != 0 or stock_b)):
        a["quantity"] = qty_b
    if stock_b and a.get("detail") is None and b.get("detail"):
        a["detail"] = b["detail"]
    if a.get("status") != b.get("status") and b.get("status"):
        extra = str(b["status"])
        detail = str(a.get("detail") or "")
        if extra not in detail:
            join = "; " if detail else ""
            a["detail"] = f"{detail}{join}{extra}"
    if not a.get("source_id") and b.get("source_id"):
        a["source_id"] = b["source_id"]
    return a


def _dedup_components(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Схлопывает дубли одной позиции (каталог+правила+склад = одна запись)."""
    seen: Dict[Any, Dict[str, Any]] = {}
    for row in rows:
        key = _component_key(row)
        if key in seen:
            _merge_rows(seen[key], row)
        else:
            seen[key] = row
    return list(seen.values())


def _merge_result(state: AgentState, result: Dict[str, Any]) -> Dict[str, Any]:
    """Сливает результат инструмента в state (в т.ч. review → review_required).

    Возвращает патч накопленных каналов. LangGraph применяет к state только
    то, что узел возвращает из функции, поэтому узлы обязаны отдавать все
    затронутые каналы (иначе in-place-мутации теряются между супершагами).

    Канал context сознательно НЕ возвращаем: он мутируется in-place, а
    несериализуемый объект утекал бы в pull-райты чекпоинтера
    (см. _set_repository — репозиторий в state не кладём).
    """
    if result.get("components"):
        state.setdefault("components", [])
        state["components"].extend(result["components"])
        state["components"] = _dedup_components(state["components"])
    if result.get("sources"):
        state.setdefault("sources", []).extend(result["sources"])
    if result.get("warnings"):
        state.setdefault("warnings", []).extend(result["warnings"])
    if result.get("missing"):
        state.setdefault("missing", []).extend(result["missing"])
    if result.get("review"):
        state["review_required"] = True
    if result.get("text"):
        state.setdefault("context", {})["last_text"] = result["text"]
    if result.get("_tool_name"):
        state.setdefault("context", {}).setdefault("tools_used", []).append(result["_tool_name"])

    return {
        "components": state.get("components", []),
        "sources": state.get("sources", []),
        "warnings": state.get("warnings", []),
        "missing": state.get("missing", []),
        "review_required": state.get("review_required", False),
    }


def _resolve_intent(parsed) -> str:
    from ..intent.resolver import resolve_top_level_intent

    return resolve_top_level_intent(parsed)
