# agent/core/state.py

from typing import TypedDict, List, Dict, Any, Optional
from app.schemas import ParsedQuery, AgentAnswer


class AgentState(TypedDict, total=False):
    """Состояние агента для LangGraph (только сериализуемые данные)"""
    
    query: str
    parsed: ParsedQuery
    
    candidates: List[Dict[str, Any]]
    stock_rows: List[Dict[str, Any]]
    ksm_targets: List[Dict[str, Any]]
    components: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]
    missing: List[str]
    results: Dict[str, Any]
    
    context: Dict[str, Any]  # Только простые типы
    review_required: bool
    completed: bool
    current_node: str
    
    answer: Optional[AgentAnswer]


def create_initial_state(
    query: str,
    parsed: ParsedQuery,
) -> AgentState:
    return {
        "query": query,
        "parsed": parsed,
        "context": {
            "intent": "search",
            "last_text": "",
        },
        "candidates": [],
        "stock_rows": [],
        "ksm_targets": [],
        "components": [],
        "sources": [],
        "warnings": [],
        "errors": [],
        "missing": [],
        "results": {},
        "review_required": False,
        "completed": False,
        "current_node": "",
    }
