# agent/executor.py

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from langgraph.errors import GraphRecursionError

from app.schemas import AgentAnswer, ParsedQuery

from .answer.builder import build_answer
from .core.config import DEFAULT_CONFIG, AgentConfig
from .core.state import create_initial_state
from .graph.agent_graph import get_graph
from .llm.client import LLMClient
from .parsing.hybrid_parser import HybridParser
from .repository.repository_factory import get_repository

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
            if not self.config.use_llm and self._llm_agent is None:
                log.warning(
                    "[Executor] mode='llm' запрошен, но AGENT_LLM_MODE != 'on' "
                    "и LLM-агент не инжектирован. Откат к deterministic."
                )
            else:
                return self._execute_llm(query, parsed, start, request_id=request_id)

        if mode == "auto":
            return self._execute_auto(query, parsed, start, request_id=request_id)

        if parsed is None:
            parsed = self._parse_query(query)

        return self._execute_deterministic(query, parsed, start, thread_id=thread_id,
                                           request_id=request_id)

    def _parse_query(self, query: str) -> ParsedQuery:
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
        return parsed

    def _execute_deterministic(
        self,
        query: str,
        parsed: ParsedQuery,
        start: float,
        thread_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AgentAnswer:
        state = create_initial_state(query=query, parsed=parsed)
        state["context"]["intent"] = self._resolve_intent(parsed)
        log.info("[Executor] Intent resolved: %s", state["context"]["intent"])

        config = {
            "configurable": {"thread_id": thread_id or str(uuid.uuid4())},
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

    def _execute_auto(
        self,
        query: str,
        parsed: Optional[ParsedQuery],
        start: float,
        request_id: Optional[str] = None,
    ) -> AgentAnswer:
        """Режим 3 (auto): deterministic → quality gate → C1 (refine) | C2 (полный LLM)."""
        if parsed is None:
            parsed = self._parse_query(query)

        answer = self._execute_deterministic(query, parsed, start, request_id=request_id)
        answer.mode = "auto"
        answer.mode_refined = "auto"

        if not self.config.auto_verify:
            log.info("[Executor][auto] auto_verify=False, returning deterministic answer")
            return answer

        from .verify.verifier import verify_answer

        verification = verify_answer(parsed, answer)
        answer.verification_verdict = verification.verdict
        answer.verification_reasons = verification.reasons

        if verification.verdict == "pass" or not verification.gaps:
            log.info("[Executor][auto] verdict=pass, no LLM escalation needed")
            return answer

        from .verify.policy import escalate_type

        escalation = escalate_type(verification.gaps)
        log.info(
            "[Executor][auto] verdict=%s reasons=%s escalation=%s",
            verification.verdict,
            verification.reasons,
            escalation,
        )

        if escalation == "none":
            log.info("[Executor][auto] escalation 'none', returning review answer")
            self._mark_review(answer, "quality_gate")
            return answer

        tokens_before = self._llm_tokens_used()

        if escalation == "full_llm":
            return self._auto_full_llm(query, parsed, start, request_id,
                                       answer, verification, tokens_before)

        if self.llm is None:
            log.warning(
                "[Executor][auto] LLM недоступен, эскалация невозможна. "
                "Помечаем ответ как требующий проверки (fallback deterministic)."
            )
            self._mark_review(answer, "quality_gate")
            self._log_escalation(query, request_id, mode_used="refine_skipped_no_llm",
                                 gaps=verification.gaps, verdict=verification.verdict,
                                 start=start)
            return answer

        refined = self._apply_refine(query, answer, verification.gaps)
        answer.llm_tokens_used = self._llm_tokens_used() - tokens_before
        self._log_escalation(query, request_id, mode_used="refine" if refined else "refine_failed",
                             gaps=verification.gaps, verdict=verification.verdict,
                             llm_tokens_used=answer.llm_tokens_used, start=start)
        self._reverify_after_escalation(parsed, answer, verification)
        return answer

    def _auto_full_llm(self, query, parsed, start, request_id, answer, verification,
                       tokens_before: int) -> AgentAnswer:
        """C2: полный перезапуск LLMAgent; результат полностью заменяет answer."""
        if self.llm is None:
            log.warning(
                "[Executor][auto] C2 запрошен, но LLM недоступен. "
                "Помечаем ответ как требующий проверки (fallback deterministic)."
            )
            self._mark_review(answer, "quality_gate")
            self._log_escalation(query, request_id, mode_used="full_llm_skipped_no_llm",
                                 gaps=verification.gaps, verdict=verification.verdict,
                                 start=start)
            return answer

        try:
            llm_answer = self._execute_llm(query, parsed, start, request_id=request_id)
        except Exception as e:  # noqa: BLE001
            log.warning("[Executor][auto] C2 full-LLM failed: %s", e)
            self._mark_review(answer, "quality_gate")
            self._log_escalation(query, request_id, mode_used="full_llm_failed",
                                 gaps=verification.gaps, verdict=verification.verdict,
                                 llm_tokens_used=self._llm_tokens_used() - tokens_before,
                                 start=start)
            return answer

        llm_answer.mode = "auto"
        llm_answer.mode_refined = "auto_llm_full"
        for r in list(getattr(answer, "human_review_reasons", None) or []):
            if r not in (llm_answer.human_review_reasons or []):
                llm_answer.human_review_reasons.append(r)
        llm_answer.human_review_required = bool(llm_answer.human_review_reasons)
        llm_answer.llm_tokens_used = self._llm_tokens_used() - tokens_before

        self._reverify_after_escalation(parsed, llm_answer, verification)

        self._log_escalation(query, request_id, mode_used="full_llm",
                             gaps=verification.gaps, verdict=verification.verdict,
                             llm_tokens_used=llm_answer.llm_tokens_used, start=start)
        log.info(
            "[Executor][auto] C2 applied: components=%d tokens=%s",
            len(llm_answer.components or []), llm_answer.llm_tokens_used,
        )
        return llm_answer

    def _reverify_after_escalation(self, parsed: ParsedQuery, answer: AgentAnswer,
                                   original_verification) -> None:
        """Повторная верификация после C1/C2: дооформление может закрыть gaps текстом.

        Обновляет verification_verdict/reasons по фактическому результату и пересчитывает
        human_review_required (True оставляется только если гейт всё ещё не пройден).
        """
        from .verify.verifier import verify_answer

        re_verification = verify_answer(parsed, answer)
        answer.verification_verdict = re_verification.verdict
        answer.verification_reasons = re_verification.reasons

        if re_verification.verdict == "pass":
            log.info(
                "[Executor][auto] re-verify: PASS (было review по %s)",
                [g.type for g in original_verification.gaps],
            )
            reasons = list(getattr(answer, "human_review_reasons", None) or [])
            if not answer.llm_refine_failed and "quality_gate" in reasons:
                # Гейт пройден — снимаем только причину качества;
                # требование экспертизы по данным (expert_data) сохраняется.
                reasons.remove("quality_gate")
            answer.human_review_reasons = reasons
            answer.human_review_required = bool(reasons)
        else:
            log.info(
                "[Executor][auto] re-verify: по-прежнему REVIEW (%s)",
                re_verification.reasons,
            )
            self._mark_review(answer, "quality_gate")

    @staticmethod
    def _mark_review(answer: AgentAnswer, reason: str) -> None:
        """Отмечает ответ как требующий проверки с указанием источника причины."""
        reasons = list(getattr(answer, "human_review_reasons", None) or [])
        if reason not in reasons:
            reasons.append(reason)
        answer.human_review_reasons = reasons
        answer.human_review_required = True

    def _llm_tokens_used(self) -> int:
        """Суммарные токены LLMClient на текущий момент (0 для заглушек/None)."""
        llm = getattr(self, "_llm", None)
        if llm is not None and hasattr(llm, "get_metrics"):
            try:
                return int(llm.get_metrics().get("total_tokens", 0) or 0)
            except Exception:  # noqa: BLE001
                return 0
        return 0

    def _apply_refine(self, query: str, answer: AgentAnswer, gaps: List) -> bool:
        """Выполняет LLM-дооформление (С1). Возвращает True если успешно."""
        from .llm.refine import refine_answer

        gaps_dict = [{"type": g.type, "detail": g.detail, "severity": g.severity} for g in gaps]
        refined = refine_answer(self.llm, query, answer, gaps_dict)
        if refined is None:
            log.warning("[Executor][auto] refine failed (LLM error/invalid), keeping deterministic")
            answer.llm_refine_failed = True
            self._mark_review(answer, "quality_gate")
            return False

        if refined.answer_text or refined.explanation:
            answer.explanation = "\n\n".join(
                p for p in (refined.answer_text, refined.explanation) if p
            )
        for rec in refined.extra_recommendations:
            if rec and rec not in answer.recommendations:
                answer.recommendations.append(rec)

        answer.mode_refined = "auto_llm_refine"
        answer.llm_refine_failed = refined.confidence_gate == "still_unclear"
        if answer.llm_refine_failed:
            self._mark_review(answer, "quality_gate")

        log.info(
            "[Executor][auto] refine applied: answer_text_len=%d confidence_gate=%s",
            len(refined.answer_text), refined.confidence_gate,
        )
        return True

    def _log_escalation(self, query, request_id, mode_used, gaps, verdict,
                        llm_tokens_used=None, start: Optional[float] = None) -> None:
        """Фиксирует эскалацию в БД (auto_mode_escalations) и лог."""
        gap_types = [g.type for g in gaps]
        log.info(
            "[Executor][auto] escalation recorded: request_id=%s mode_used=%s verdict=%s "
            "gaps=%s tokens=%s",
            request_id, mode_used, verdict, gap_types, llm_tokens_used,
        )
        try:
            from app.db.session import SessionLocal
            from app.models.sqlalchemy.all_models import AutoModeEscalation

            db = SessionLocal()
            try:
                entry = AutoModeEscalation(
                    request_id=str(request_id) if request_id else None,
                    query=query,
                    mode_used=mode_used,
                    gaps=gap_types,
                    verdict=verdict,
                    duration_ms=int((time.time() - start) * 1000)
                    if start else None,
                    llm_tokens_used=llm_tokens_used,
                )
                db.add(entry)
                db.commit()
            finally:
                db.close()
        except Exception as e:  # БД недоступна — не ломаем основной путь
            log.warning("[Executor][auto] failed to record escalation to DB: %s", e)

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
        from .intent.resolver import resolve_top_level_intent

        return resolve_top_level_intent(parsed)

    def _build_answer_from_result(self, parsed: ParsedQuery, result: Dict) -> AgentAnswer:
        intent = result.get("context", {}).get("intent", "search")

        response = {
            "components": result.get("components", []),
            "sources": result.get("sources", []),
            "warnings": result.get("warnings", []),
            "missing": result.get("missing", []),
            "review": result.get("review_required", False),
            "answers": [result.get("context", {}).get("last_text", "")],
            "normative_detail": result.get("normative_detail", ""),
            "purchase_recommendation": result.get("purchase_recommendation"),
            "mode": result.get("context", {}).get("mode", "offline_rules"),
            "tools_used": list(result.get("context", {}).get("tools_used", [])),
            "stock_rows": result.get("stock_rows", []),
        }

        return build_answer(parsed, intent, response)

    def get_status(self) -> Dict[str, Any]:
        from .verify.policy import FULL_LLM_TYPES

        return {
            "config": {
                "use_llm": self.config.use_llm,
                "storage": self.config.storage,
                "checkpoint_type": self.config.checkpoint_type,
            },
            "repository": getattr(self.repository, "kind", "unknown"),
            "tools_available": len(self._get_available_tools()),
            "llm_available": self.llm is not None,
            "verify": {
                "auto_verify": self.config.auto_verify,
                "full_llm_types": sorted(FULL_LLM_TYPES),
            },
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


def run_agent(query: str, parsed: Optional[ParsedQuery] = None) -> AgentAnswer:
    executor = get_agent_executor()
    return executor.execute(query, parsed)


def execute_agent_query(query: str, parsed: Optional[ParsedQuery] = None) -> AgentAnswer:
    return run_agent(query, parsed)
