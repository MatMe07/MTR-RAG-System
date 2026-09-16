# agent/executor.py

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from langgraph.errors import GraphRecursionError

from app.schemas import AgentAnswer, LLMCallRecord, LLMDiagnostics, ParsedQuery, RefineIterationRecord

from .answer.builder import build_answer
from .core.config import DEFAULT_CONFIG, AgentConfig
from .core.state import create_initial_state
from .graph.agent_graph import get_graph
from .llm.client import (
    LLMClient,
    get_llm_client,
    reset_llm_request_context,
    set_llm_request_context,
)
from .parsing.hybrid_parser import HybridParser
from .repository.repository_factory import get_repository

log = logging.getLogger("mtr.agent.executor")

_CONTINUE_ENDPOINT = "/api/v1/agent/continue"
_OFFER_FULL_LLM_QUESTION = (
    "Полный LLM-анализ может закрыть оставшиеся недостатки ответа. "
    "Продолжить? Это займёт больше времени и требует доступа к OpenRouter."
)

_ALTER_ATTEMPTED = False


def _ensure_details_column(db) -> None:
    """Best-effort ADD COLUMN details в auto_mode_escalations (для существующих БД).

    Для новых БД колонка создаётся через Base.metadata.create_all.
    """
    global _ALTER_ATTEMPTED
    if _ALTER_ATTEMPTED:
        return
    _ALTER_ATTEMPTED = True
    try:
        from sqlalchemy import text

        db.execute(text("ALTER TABLE auto_mode_escalations ADD COLUMN details TEXT"))
        db.commit()
        log.info("[Executor][auto] added column 'details' to auto_mode_escalations")
    except Exception:  # колонка уже есть или БД недоступна
        db.rollback()


class AgentExecutor:
    """Исполнитель агента — точка входа"""

    def __init__(self, config: Optional[AgentConfig] = None, llm_agent: Optional[Any] = None):
        self.config = config or DEFAULT_CONFIG
        self._graph = None
        self._repository = None
        self._llm = None
        self._llm_agent = llm_agent
        self._active_refine_iterations: Optional[list] = None

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
        request_id = request_id or str(uuid.uuid4())
        log.info("[Executor] Execute query=%r mode=%s request_id=%s", query, mode, request_id)

        # LLM-вызовы внутри запроса привязываются к request_id (для diagnostics)
        set_llm_request_context(request_id, mode)

        answer: Optional[AgentAnswer] = None
        try:
            if mode == "llm":
                if not self.config.use_llm and self._llm_agent is None:
                    log.warning(
                        "[Executor] mode='llm' запрошен, но AGENT_LLM_MODE != 'on' "
                        "и LLM-агент не инжектирован. Откат к deterministic."
                    )
                else:
                    answer = self._execute_llm(query, parsed, start, request_id=request_id)

            if answer is None and mode == "auto":
                answer = self._execute_auto(query, parsed, start, request_id=request_id)

            if answer is None:
                if parsed is None:
                    parsed = self._parse_query(query)
                answer = self._execute_deterministic(
                    query, parsed, start, thread_id=thread_id, request_id=request_id
                )
        finally:
            try:
                if answer is not None:
                    self._finalize_llm_diagnostics(answer, request_id)
            finally:
                reset_llm_request_context()
        return answer

    def _parse_query(self, query: str) -> ParsedQuery:
        log.info("[Executor] No parsed query, running HybridParser...")
        parser_start = time.time()
        global_llm = self._global_llm()
        metrics_before = self._llm_metrics_snapshot(global_llm)
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
        metrics_after = self._llm_metrics_snapshot(global_llm)
        if parsed.parser_diagnostics is not None:
            # LLM-доизвлечение §1F происходит в _enrich_parsed — считаем дельту
            parsed.parser_diagnostics.llm_extractor = self._extractor_delta(
                metrics_before, metrics_after
            )
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
        """Режим 3 (auto): deterministic → quality gate → C1+ (цикл с инструментами).

        После 3 неудачных итераций C1+ (или LLM-ошибки) — возврат ответа с
        предложением C2 пользователю (offer_full_llm), НЕ автоматической перезапуск.
        """
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

        log.info(
            "[Executor][auto] verdict=%s reasons=%s",
            verification.verdict,
            verification.reasons,
        )

        tokens_before = self._llm_tokens_used()

        from .llm.refine_loop import run_refine_loop

        loop = run_refine_loop(
            llm_client=self.llm,
            query=query,
            parsed=parsed,
            answer=answer,
            gaps=verification.gaps,
            repository=self.repository,
            request_id=request_id,
        )
        self._active_refine_iterations = self._loop_details(loop)
        answer.llm_tokens_used = loop.llm_tokens_used or (self._llm_tokens_used() - tokens_before)

        self._log_loop_iterations(query, request_id, loop, verification, start)

        if loop.passed:
            log.info(
                "[Executor][auto] C1+ loop passed after %d iterations",
                len(loop.iterations),
            )
            answer.mode_refined = "auto_llm_refine"
            answer.llm_refine_failed = False
            self._reverify_after_escalation(parsed, answer, verification)
            self._log_escalation(query, request_id, mode_used="refine_loop",
                                 gaps=verification.gaps, verdict=verification.verdict,
                                 llm_tokens_used=answer.llm_tokens_used,
                                 details=self._loop_details(loop), start=start)
            return answer

        if self.llm is None:
            log.warning(
                "[Executor][auto] LLM недоступен, эскалация невозможна. "
                "Помечаем ответ как требующий проверки (fallback deterministic)."
            )
            self._mark_review(answer, "quality_gate")
            self._log_escalation(query, request_id, mode_used="refine_loop_skipped_no_llm",
                                 gaps=verification.gaps, verdict=verification.verdict,
                                 start=start)
            return answer

        # 3 неудачные итерации → предложить C2 пользователю (без авто-перехода).
        answer.llm_refine_failed = True
        self._mark_review(answer, "quality_gate")
        if loop.llm_error:
            answer.offer_full_llm = False
            answer.offer_question = ""
            mode_used = "refine_loop_llm_error"
            log.warning("[Executor][auto] C1+ loop LLM error: %s", loop.llm_error)
        else:
            answer.offer_full_llm = True
            answer.offer_question = _OFFER_FULL_LLM_QUESTION
            answer.offer_endpoint = _CONTINUE_ENDPOINT
            mode_used = "refine_loop_failed_offer_c2"
        self._log_escalation(query, request_id, mode_used=mode_used,
                             gaps=verification.gaps, verdict=verification.verdict,
                             llm_tokens_used=answer.llm_tokens_used,
                             details=self._loop_details(loop), start=start)
        log.info(
            "[Executor][auto] mode_refined=%s offer_full_llm=%s iterations=%d",
            answer.mode_refined, answer.offer_full_llm, len(loop.iterations),
        )
        return answer

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

    # ---------------------------------------------------------------- диагностика LLM
    @staticmethod
    def _global_llm():
        """Глобальный LLM-клиент (модульный синглтон) — его зовёт LLMExtractor §1F."""
        try:
            return get_llm_client()
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _llm_metrics_snapshot(client) -> Optional[Dict[str, Any]]:
        if client is None or not hasattr(client, "get_metrics"):
            return None
        try:
            return dict(client.get_metrics())
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _extractor_delta(before: Optional[dict], after: Optional[dict]) -> Dict[str, Any]:
        """Дельта метрик LLM-экстрактора (§1F) на время парсинга."""
        if not before or not after:
            return {"enabled": bool(after), "calls": 0, "hits": 0, "errors": 0, "tokens": 0}
        return {
            "enabled": True,
            "calls": max(0, int(after.get("extractor_calls", 0)) - int(before.get("extractor_calls", 0))),
            "hits": max(0, int(after.get("extractor_hits", 0)) - int(before.get("extractor_hits", 0))),
            "errors": max(0, int(after.get("extractor_errors", 0)) - int(before.get("extractor_errors", 0))),
            "tokens": max(0, int(after.get("total_tokens", 0)) - int(before.get("total_tokens", 0))),
        }

    @staticmethod
    def _estimate_cost(model: Optional[str], prompt_tokens: int, completion_tokens: int) -> Optional[float]:
        """Оценка стоимости в USD для диагностики (бесплатные модели — 0, иначе неизвестно)."""
        if not isinstance(model, str) or not model:
            return None
        if ":free" in model:
            return 0.0
        return None

    def _finalize_llm_diagnostics(self, answer: AgentAnswer, request_id: Optional[str]) -> None:
        """Собирает answer.llm: вызовы LLM по запросу, токены, кэш, итерации C1+."""
        clients: List[Any] = []
        if getattr(self, "_llm", None) is not None:
            clients.append(self._llm)
        global_llm = self._global_llm()
        if global_llm is not None and global_llm not in clients:
            clients.append(global_llm)

        use_llm = bool(getattr(self.config, "use_llm", False))
        model_cfg = getattr(self.config, "llm_model", None)
        model = model_cfg if isinstance(model_cfg, str) else None
        diag = LLMDiagnostics(available=use_llm or bool(clients), model=model)

        raw_calls: List[Dict[str, Any]] = []
        for client in clients:
            if hasattr(client, "request_calls"):
                try:
                    raw_calls.extend(client.request_calls(request_id) or [])
                except Exception:  # noqa: BLE001
                    pass
            if hasattr(client, "reset_request"):
                try:
                    client.reset_request(request_id)
                except Exception:  # noqa: BLE001
                    pass

        for rec in raw_calls:
            if not isinstance(rec, dict):
                continue
            try:
                diag.calls.append(LLMCallRecord(**rec))
            except Exception:  # noqa: BLE001
                continue

        for c in diag.calls:
            diag.total_calls += 1
            diag.cache_hits += 1 if c.cache_hit else 0
            diag.cache_misses += 1 if (not c.cache_hit and not c.error) else 0
            diag.prompt_tokens += c.prompt_tokens
            diag.completion_tokens += c.completion_tokens
            diag.total_tokens += c.total_tokens
            diag.duration_ms += c.duration_ms

        refine = getattr(self, "_active_refine_iterations", None) or []
        diag.refine_iterations = [
            RefineIterationRecord(**it) for it in refine if isinstance(it, dict)
        ]
        self._active_refine_iterations = None

        diag.used = bool(diag.calls) or bool(diag.refine_iterations)

        if not diag.available:
            diag.reason = "LLM отключён (AGENT_LLM_MODE != 'on' / клиент недоступен)"
        elif not diag.used:
            mode_now = getattr(answer, "mode", None)
            verdict = getattr(answer, "verification_verdict", None)
            if mode_now == "auto" and verdict == "pass":
                diag.reason = (
                    "LLM не вызывался: детерминированный auto-ответ прошёл quality gate "
                    "(verdict=pass)"
                )
            elif mode_now == "auto" and getattr(answer, "offer_full_llm", False):
                diag.reason = "LLM-вызовы C1+ не дали результата — предложено C2 пользователю"
            else:
                diag.reason = "LLM не вызывался в рамках запроса"
        else:
            diag.reason = (
                f"LLM использовался: {len(diag.calls)} вызовов, "
                f"{diag.prompt_tokens}+{diag.completion_tokens} токенов "
                f"(всего {diag.total_tokens}), cache {diag.cache_hits}/{diag.cache_misses}"
            )

        diag.cost_estimate_usd = self._estimate_cost(
            model, diag.prompt_tokens, diag.completion_tokens
        )
        answer.llm = diag

    def _apply_refine(self, query: str, answer: AgentAnswer, gaps: List) -> bool:
        """Выполняет LLM-дооформление (С1). Возвращает True если успешно.

        Устаревший одношаговый refine (формат answer_text/confidence_gate);
        в _execute_auto заменён циклом C1+ (refine_loop). Оставлен для совместимости.
        """
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

    def _log_loop_iterations(self, query, request_id, loop, verification, start) -> None:
        """Пишет сводку итераций C1+-цикла в лог; детали — в auto_mode_escalations."""
        log.info(
            "[Executor][auto] C1+ loop finished: passed=%s iterations=%d "
            "final_answer_len=%d verdict=%s",
            loop.passed, len(loop.iterations), len(loop.final_answer or ""),
            verification.verdict,
        )
        for it in loop.iterations:
            log.info(
                "[Executor][auto]   it#%d action=%s tool=%s error=%r verdict=%s (%.0fms)",
                it.n, it.action, it.tool_name, it.error, it.verdict, it.duration_ms,
            )

    @staticmethod
    def _loop_details(loop) -> Optional[list]:
        """Сериализация итераций C1+-цикла для details (auto_mode_escalations)."""
        if not loop.iterations:
            return None
        return [
            {
                "n": it.n,
                "action": it.action,
                "tool_name": it.tool_name,
                "tool_input": it.tool_input,
                "error": it.error,
                "verdict": it.verdict,
                "gaps": it.gaps,
                "duration_ms": it.duration_ms,
            }
            for it in loop.iterations
        ]

    def _log_escalation(self, query, request_id, mode_used, gaps, verdict,
                        llm_tokens_used=None, details=None, start: Optional[float] = None) -> None:
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
                _ensure_details_column(db)
                entry = AutoModeEscalation(
                    request_id=str(request_id) if request_id else None,
                    query=query,
                    mode_used=mode_used,
                    gaps=gap_types,
                    verdict=verdict,
                    duration_ms=int((time.time() - start) * 1000)
                    if start else None,
                    llm_tokens_used=llm_tokens_used,
                    details=details,
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
