# agent/executor.py

from typing import Optional, Any, Dict
from app.schemas import AgentAnswer, ParsedQuery

from .core.config import DEFAULT_CONFIG, AgentConfig
from .core.state import create_initial_state
from .graph.agent_graph import get_graph
from .parsing.hybrid_parser import HybridParser
from .repository.repository_factory import get_repository
from .answer.builder import build_answer
from .llm.client import LLMClient


class AgentExecutor:
    """Исполнитель агента — точка входа"""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self._graph = None
        self._repository = None
        self._llm = None
    
    @property
    def graph(self):
        if self._graph is None:
            self._graph = get_graph(self.config)
        return self._graph
    
    @property
    def repository(self):
        if self._repository is None:
            self._repository = get_repository(storage=self.config.storage)
        return self._repository
    
    @property
    def llm(self):
        if self._llm is None and self.config.use_llm:
            self._llm = LLMClient(self.config)
        return self._llm
    
    def execute(
        self,
        query: str,
        parsed: Optional[ParsedQuery] = None,
        thread_id: Optional[str] = None
    ) -> AgentAnswer:
        if parsed is None:
            parser = HybridParser()
            parsed = parser.parse(query)
            
        state = create_initial_state(
            query=query,
            parsed=parsed,
        )
        
        state["context"]["intent"] = self._resolve_intent(parsed)
        
        config = {"configurable": {"thread_id": thread_id or self.config.checkpoint_thread_id}}
        result = self.graph.invoke(state, config=config)
        
        if result.get("answer"):
            return result["answer"]
        
        return self._build_answer_from_result(parsed, result)
    
    def _resolve_intent(self, parsed: ParsedQuery) -> str:
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
    
    def _build_answer_from_result(self, parsed: ParsedQuery, result: Dict) -> AgentAnswer:
        intent = result.get("context", {}).get("intent", "search")
        
        response = {
            "components": result.get("components", []),
            "sources": result.get("sources", []),
            "warnings": result.get("warnings", []),
            "missing": result.get("missing", []),
            "review": result.get("review_required", False),
            "answers": [result.get("context", {}).get("last_text", "")],
            "mode": "offline_rules",
            "tools_used": list(result.get("results", {}).keys()),
        }
        
        return build_answer(parsed, intent, response)
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "config": {
                "use_llm": self.config.use_llm,
                "storage": self.config.storage,
                "checkpoint_type": self.config.checkpoint_type,
            },
            "repository": getattr(self.repository, "kind", "unknown"),
            "tools_available": len(self._get_available_tools()),
            "llm_available": self.llm is not None,
        }
    
    def _get_available_tools(self) -> list:
        from .tools.registry import list_tools
        return list_tools()
    
    def clear_cache(self) -> None:
        if self._llm:
            self._llm.clear_cache()
        if self._repository:
            from .repository.repository_factory import reset_repository
            reset_repository()


# ============================================================
# ✅ ФУНКЦИИ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
# ============================================================

_agent_executor: Optional[AgentExecutor] = None


def get_agent_executor(config: Optional[AgentConfig] = None) -> AgentExecutor:
    global _agent_executor
    if _agent_executor is None:
        _agent_executor = AgentExecutor(config or DEFAULT_CONFIG)
    return _agent_executor


def reset_agent_executor() -> None:
    global _agent_executor
    if _agent_executor:
        _agent_executor.clear_cache()
        _agent_executor = None


def run_agent(query: str, parsed: Optional[ParsedQuery] = None) -> AgentAnswer:
    executor = get_agent_executor()
    return executor.execute(query, parsed)


def execute_agent_query(query: str, parsed: Optional[ParsedQuery] = None) -> AgentAnswer:
    """Алиас для main.py"""
    return run_agent(query, parsed)
