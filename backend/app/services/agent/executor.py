# agent/executor.py

import logging
import time
from typing import Optional, Any, Dict

from langgraph.errors import GraphRecursionError

from app.schemas import AgentAnswer, ParsedQuery

from .core.config import DEFAULT_CONFIG, AgentConfig
from .core.state import create_initial_state
from .graph.agent_graph import get_graph 
from .parsing.hybrid_parser import HybridParser
from .repository.repository_factory import get_repository
from .answer.builder import build_answer
from .llm.client import LLMClient

log = logging.getLogger("mtr.agent.executor")


class AgentExecutor:
    """Исполнитель агента — точка входа"""

    def __init__(self, config: Optional[AgentConfig] = None, llm_agent: Optional[Any] = None):
        self.config = config or DEFAULT_CONFIG
        self._graph = None
        self._repository = None
        self._llm = None
        self._llm_agent = llm_agent

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
        thread_id: Optional[str] = None,
        mode: str = "deterministic",
        request_id: Optional[str] = None,
    ) -> AgentAnswer:
        start = time.time()
        log.info("[Executor] Execute query=%r mode=%s request_id=%s", query, mode, request_id)

        if mode == "llm":
            return self._execute_llm(query, parsed, start, request_id=request_id)

        if parsed is None:
            log.info("[Executor] No parsed query, running HybridParser...")
            parser_start = time.time()
            parser = HybridParser()
            parsed = parser.parse(query)
            log.info(
                "[Executor] Parsed: confidence=%.2f operations=%s item_types=%s "
                "technical_filters=%s ambiguities=%s (%.0fms)",
                parsed.confidence,
                parsed.operations,
                parsed.item_types,
                getattr(parsed, "technical_filters", {}),
                parsed.ambiguities,
                (time.time() - parser_start) * 1000,
            )
            self._enrich_parsed(parsed)

        state = create_initial_state(query=query, parsed=parsed)
        state["context"]["intent"] = self._resolve_intent(parsed)
        log.info("[Executor] Intent resolved: %s", state["context"]["intent"])

        config = {
            "configurable": {"thread_id": thread_id or self.config.checkpoint_thread_id},
            "recursion_limit": self.config.recursion_limit,
        }
        graph_start = time.time()
        log.info("[Executor] Invoking graph...")
        try:
            result = self.graph.invoke(state, config=config)
        except GraphRecursionError:
            log.warning("[Executor] Recursion limit exceeded (limit=%d) for query=%r",
                        self.config.recursion_limit, query)
            answer = self._build_answer_from_result(parsed, {
                "components": [],
                "sources": [],
                "warnings": ["Не удалось завершить анализ: превышен лимит шагов анализа."],
                "missing": [],
                "review": True,
                "answers": ["Анализ не завершён из-за сложности запроса. Обратитесь к эксперту."],
                "mode": "offline_rules",
                "tools_used": [],
            })
            log.info("[Executor] Total execution (recursion fallback): %.0fms",
                     (time.time() - start) * 1000)
            return answer
        graph_elapsed = (time.time() - graph_start) * 1000

        log.info(
            "[Executor] Graph finished in %.0fms: components=%d sources=%d warnings=%d "
            "tools_used=%s completed=%s",
            graph_elapsed,
            len(result.get("components", [])),
            len(result.get("sources", [])),
            len(result.get("warnings", [])),
            result.get("context", {}).get("tools_used", []),
            result.get("completed", False),
        )

        if result.get("answer"):
            log.info("[Executor] Answer found in state, returning directly")
            return result["answer"]

        log.info("[Executor] No answer in state, building from result")
        answer = self._build_answer_from_result(parsed, result)
        log.info("[Executor] Total execution: %.0fms", (time.time() - start) * 1000)
        return answer

    def _execute_llm(
        self,
        query: str,
        parsed: Optional[ParsedQuery],
        start: float,
        request_id: Optional[str] = None,
    ) -> AgentAnswer:
        """Режим 2 (4C): LLM-управляемый цикл call_tool/ask_user/finish."""
        if parsed is None:
            parser = HybridParser()
            parsed = parser.parse(query)
            self._enrich_parsed(parsed)

        from .llm.agent import LLMAgent
        from .tools.tool_dal import ToolDAL

        agent = self._llm_agent or LLMAgent(
            config=self.config,
            llm=self.llm,
            dal=ToolDAL(self.repository),
            request_id=request_id,
        )
        intent = self._resolve_intent(parsed)
        log.info("[Executor] LLM-agent started: request_id=%s", getattr(agent, "_request_id", "-"))
        result = agent.run(query, parsed)
        log.info(
            "[Executor] LLM-agent finished in %.0fms: iterations=%d tools=%s components=%d",
            (time.time() - start) * 1000,
            getattr(agent, "iterations", 0),
            result.get("tools_used", []),
            len(result.get("components", [])),
        )
        return build_answer(parsed, intent, result)

    def _enrich_parsed(self, parsed: ParsedQuery) -> None:
        """Интентный слой: intents/status/missing_params Парсеру (Этап 1, §1H)."""
        try:
            from .intent.detect import enrich_parsed as _enrich

            enriched = _enrich(parsed)
            log.info(
                "[Executor] Parsed enriched: status=%s intents=%s missing=%s",
                getattr(enriched, "status", ""),
                getattr(enriched, "intents", []),
                getattr(enriched, "missing_params", {}),
            )
        except Exception as e:  # прагматично: не ломаем основной путь
            log.warning("[Executor] Intent enrichment failed: %s", e)

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
            "mode": result.get("context", {}).get("mode", "offline_rules"),
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
# Functions for backward compatibility
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
    return run_agent(query, parsed)
