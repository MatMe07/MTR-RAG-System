# agent/llm/refine_loop.py
"""Авто-режим C1+: ограниченный LLM-цикл с инструментами (замена C1-refine).

Отличия от C2 (LLMAgent):
- инструменты НЕ меняют components/sources (структура детерминированного ответа
  остаётся нетронутой) — цикл уточняет только факты и итоговый текст;
- максимум MAX_ITERATIONS итераций — после исчерпания возврат управляющему
  коду (executor) с passed=False, который решает: предложить C2 пользователю;
- повторный вызов инструмента с теми же параметрами запрещён (анти-зацикливание);
- запрещено ask_user: данные спрашивать нельзя, честный finish с указанием
  отсутствующих данных вместо этого;
- после КАЖДОЙ итерации — повторная верификация (quality gate, §3.2 плана);
- каждая итерация логируется (details для auto_mode_escalations).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..core.exceptions import LLMResponseError
from ..tools.error_handler import REQUIRED_TOOLS, ErrorHandler
from ..tools.instruments import run_instrument
from ..tools.tool_dal import ToolDAL
from .response_parser import LLMResponseParser

log = logging.getLogger("mtr.agent.llm.refine_loop")

MAX_ITERATIONS = 3
MAX_TOTAL_SECONDS = 60.0


_LOOP_INSTRUCTION = (
    "Ты — инженерный агент MTR, режим дооформления ответа (C1+). "
    "Детерминированный пайплайн уже собрал структурированный ответ "
    "(components/sources/warnings) и черновой текст. Твоя задача — инструментами "
    "проверить и уточнить факты, затем итоговым текстом закрыть перечисленные ниже "
    "недостатки ответа. Структуру components НЕ меняй: ты влияешь только на текст.\n"
    "\n"
    "Возможные действия (верни строго один JSON):\n"
    '- {"action": "call_tool", "tool_name": "...", "input": {...}}\n'
    '- {"action": "finish", "final_answer": "..."}\n'
    "\n"
    "Запрещено действие ask_user: в этом режиме нельзя спрашивать пользователя. "
    "Если данных не хватает — честно напиши об этом в final_answer.\n"
    "\n"
    "Правила:\n"
    "- Используй ТОЛЬКО данные из структурированного ответа и результатов "
    "инструментов: не выдумывай коды, остатки, параметры, позиции.\n"
    "- Отвечай прямо на запрос (да/нет и число для «хватает ли», перечень для "
    "«покажи все», вердикт для складских интентов).\n"
    "- Сначала получай недостающие данные инструментами (call_tool), затем "
    "завершай цикл качественным текстом (finish). Если инструменты не помогают — "
    "finish с указанием, чего не хватает.\n"
    "- Не вызывай один и тот же инструмент с одинаковыми параметрами повторно.\n"
)


def _format_gaps(gaps: List[Any]) -> str:
    lines = []
    for g in gaps:
        if isinstance(g, dict):
            severity, gtype, detail = g.get("severity", "?"), g.get("type", "?"), g.get("detail", "")
        else:
            severity, gtype, detail = g.severity, g.type, g.detail
        lines.append(f"- [{severity}] {gtype}: {detail}")
    return "\n".join(lines) if lines else "- нет явных недостатков"


def _format_structured_answer(answer: Any) -> str:
    parts = []
    for c in (answer.components or [])[:10]:
        name = getattr(c, "name", None) or (c.get("name") if isinstance(c, dict) else None) or "?"
        status = getattr(c, "status", "") or (c.get("status") if isinstance(c, dict) else "")
        qty = getattr(c, "quantity", None)
        if isinstance(c, dict):
            qty = c.get("quantity")
        parts.append(f"  - {name}: {status} (кол-во: {qty})")
    if getattr(answer, "review_verdict", None):
        issues = getattr(answer, "review_issues", None) or []
        parts.append(
            f"  Проверка качества: {answer.review_verdict} "
            + (f"({'; '.join(issues[:3])})" if issues else "")
        )
    warnings = getattr(answer, "warnings", None) or []
    if warnings:
        parts.append(f"  Предупреждения: {'; '.join(warnings[:5])}")
    return "\n".join(parts) if parts else "  (пусто)"


def _parsed_context(parsed: Any) -> Dict[str, Any]:
    return {
        "item_types": getattr(parsed, "item_types", []),
        "technical_filters": getattr(parsed, "technical_filters", {}),
        "component_ids": getattr(parsed, "component_ids", []),
        "unit_ids": getattr(parsed, "unit_ids", []),
        "operations": getattr(parsed, "operations", []),
        "units_count": getattr(parsed, "units_count", None),
        "intents": getattr(parsed, "intents", []),
    }


def _build_initial_prompt(
    query: str,
    parsed: Any,
    answer: Any,
    gaps: List[Any],
    tools: List[Dict[str, Any]],
) -> str:
    lines = [_LOOP_INSTRUCTION]
    if tools:
        lines.append("Доступные инструменты (input_schema):")
        for t in tools:
            lines.append("- {name}: {desc}; input_schema={schema}".format(
                name=t.get("name"),
                desc=t.get("description"),
                schema=json.dumps(t.get("input_schema", {}), ensure_ascii=False),
            ))
    if parsed is not None:
        lines.append("Разобранный запрос (контекст):")
        lines.append(json.dumps(_parsed_context(parsed), ensure_ascii=False, default=str))
    lines.append("Запрос пользователя: " + query)
    lines.append("Структурированный ответ (НЕ менять components):")
    lines.append(_format_structured_answer(answer))
    lines.append("Недостатки, которые нужно закрыть (gaps):")
    lines.append(_format_gaps(gaps))
    return "\n".join(lines)


def _build_turn_prompt(history: List[str], feedback: Optional[str] = None) -> str:
    turn = "\n\n".join(history)
    if feedback:
        turn += "\n\n" + feedback
    return turn + "\n\nВыбери следующее действие (JSON)."


def _summarize_tool(
    tool_name: str,
    outcome: Dict[str, Any],
    tool_error: Optional[Dict[str, Any]],
) -> str:
    if tool_error:
        return (
            f"Результат {tool_name}: ОШИБКА {tool_error.get('code')} — "
            f"{tool_error.get('message')}"
        )
    payload = outcome.get("result")
    if isinstance(payload, dict) and "value" in payload:
        payload = payload["value"]
    try:
        text = json.dumps(payload, ensure_ascii=False, default=str)[:2000]
    except TypeError:
        text = str(payload)[:2000]
    return f"Результат {tool_name}: {text}"


def _gap_feedback(gaps: List[Any]) -> str:
    if not gaps:
        return "Повторная проверка после шага: гейт пройден (verdict=pass)."
    return (
        "Повторная проверка после шага: гейт НЕ пройден. Оставшиеся недостатки:\n"
        + _format_gaps(gaps)
    )


@dataclass
class IterationRecord:
    """Отчёт по одной итерации C1+-цикла (для логирования в БД)."""

    n: int
    action: str = ""
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    verdict: str = "pending"
    gaps: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class RefineLoopResult:
    passed: bool = False
    iterations: List[IterationRecord] = field(default_factory=list)
    final_answer: Optional[str] = None
    llm_error: Optional[str] = None
    llm_tokens_used: int = 0


def _schema_for(tool_name: str) -> Optional[Dict[str, Any]]:
    from ..tools.registry import get_instrument

    inst = get_instrument(tool_name)
    return (inst or {}).get("input_schema")


def _available_tools() -> List[Dict[str, Any]]:
    from ..tools.registry import get_instruments_for_llm

    try:
        return get_instruments_for_llm()
    except Exception:  # noqa: BLE001
        return []


def _llm_tokens_used(llm_client: Any) -> int:
    if llm_client is not None and hasattr(llm_client, "get_metrics"):
        try:
            return int(llm_client.get_metrics().get("total_tokens", 0) or 0)
        except Exception:  # noqa: BLE001
            return 0
    return 0


def run_refine_loop(
    llm_client: Any,
    query: str,
    parsed: Any,
    answer: Any,
    gaps: List[Any],
    repository: Optional[Any] = None,
    dal: Optional[ToolDAL] = None,
    request_id: Optional[str] = None,
    verifier: Optional[Callable[..., Any]] = None,
    parser: Optional[LLMResponseParser] = None,
    max_iterations: int = MAX_ITERATIONS,
    total_seconds: float = MAX_TOTAL_SECONDS,
) -> RefineLoopResult:
    """Ограниченный C1+-цикл: LLM может звать инструменты и переписывать текст.

    После каждой итерации — повторная верификация (quality gate). Возвращает
    RefineLoopResult: passed=True, если хотя бы после одной итерации verdict=pass,
    иначе passed=False со списком итераций (следующий шаг решает executor).
    """
    result = RefineLoopResult()
    if llm_client is None:
        log.warning("[RefineLoop] LLM client unavailable, skipping loop")
        return result

    if verifier is None:
        from ..verify.verifier import verify_answer

        verifier = verify_answer

    if dal is None and repository is not None:
        dal = ToolDAL(repository)
    error_handler = ErrorHandler()

    parser = parser or LLMResponseParser(
        available_tools={t["name"] for t in _available_tools()},
        get_schema=_schema_for,
    )

    history: List[str] = []

    def build_turn(feedback: Optional[str] = None) -> str:
        return _build_turn_prompt(history, feedback)

    def record_and_verify(it: IterationRecord) -> None:
        """Логирует итерацию и запускает повторную верификацию (гейт)."""
        verification = verifier(parsed, answer)
        it.verdict = verification.verdict
        it.gaps = [
            {"type": g.type, "detail": g.detail, "severity": g.severity}
            for g in (verification.gaps or [])
        ]
        answer.verification_verdict = verification.verdict
        answer.verification_reasons = verification.reasons
        if verification.verdict == "pass":
            result.passed = True
            log.info("[RefineLoop] iteration %d: verdict=PASS", it.n)
        else:
            log.info(
                "[RefineLoop] iteration %d: verdict=REVIEW gaps=%s",
                it.n, [g.type for g in verification.gaps],
            )
        result.iterations.append(it)

    history.append(_build_initial_prompt(query, parsed, answer, gaps, _available_tools()))
    used_signatures: set = set()
    start = time.monotonic()
    tokens_start = _llm_tokens_used(llm_client)

    for n in range(1, max_iterations + 1):
        if time.monotonic() - start > total_seconds:
            log.info("[RefineLoop] time limit exceeded after %d iterations", n - 1)
            break

        it = IterationRecord(n=n)
        iter_start = time.monotonic()
        try:
            llm_text = llm_client.invoke(build_turn())
        except Exception as e:  # noqa: BLE001
            it.action = "llm_error"
            it.error = str(e)
            it.duration_ms = int((time.monotonic() - iter_start) * 1000)
            result.iterations.append(it)
            result.llm_error = str(e)
            log.warning("[RefineLoop] LLM call failed on iteration %d: %s", n, e)
            break

        it.duration_ms = int((time.monotonic() - iter_start) * 1000)
        try:
            action = parser.parse(llm_text)
        except LLMResponseError as e:
            it.action = "invalid"
            it.error = str(e)
            history.append(
                "Ответ был невалидным (ожидается JSON: call_tool или finish). "
                "Верни корректный JSON."
            )
            record_and_verify(it)
            if result.passed:
                break
            history.append(_gap_feedback(it.gaps))
            continue

        it.action = action.action
        it.tool_name = action.tool_name
        it.tool_input = action.input

        if action.action == "ask_user":
            it.error = "ask_user запрещён в C1+ (данные спрашивать нельзя)"
            history.append(
                "Действие ask_user запрещено в этом режиме: используй call_tool "
                "или finish."
            )
            record_and_verify(it)
            if result.passed:
                break
            history.append(_gap_feedback(it.gaps))
            continue

        if action.action == "call_tool":
            signature = (action.tool_name, json.dumps(action.input, sort_keys=True, ensure_ascii=False))
            if signature in used_signatures:
                it.error = (
                    f"повторный вызов «{action.tool_name}» с теми же параметрами "
                    "запрещён (анти-зацикливание)"
                )
                history.append(
                    f"Повторный вызов «{action.tool_name}» с теми же параметрами "
                    "запрещён. Используй другие параметры или заверши цикл finish."
                )
                record_and_verify(it)
                if result.passed:
                    break
                history.append(_gap_feedback(it.gaps))
                continue
            used_signatures.add(signature)
            try:
                _run_instrument_step(action, it, dal, error_handler, request_id, history)
            except Exception as e:  # noqa: BLE001
                it.error = str(e)
                history.append(f"Результат {action.tool_name}: ОШИБКА {e}")
        else:  # finish
            if action.final_answer:
                answer.explanation = action.final_answer
            it.tool_name = None
            it.tool_input = None

        record_and_verify(it)
        if result.passed:
            break
        history.append(_gap_feedback(it.gaps))

    result.final_answer = answer.explanation
    result.llm_tokens_used = max(0, _llm_tokens_used(llm_client) - tokens_start)
    return result


def _run_instrument_step(
    action: Any,
    it: IterationRecord,
    dal: Optional[ToolDAL],
    error_handler: ErrorHandler,
    request_id: Optional[str],
    history: List[str],
) -> None:
    """Выполняет инструмент и дописывает результат в контекст цикла."""
    def _run(input_data: Dict[str, Any]) -> Dict[str, Any]:
        return run_instrument(
            action.tool_name,
            input_data,
            request_id=request_id,
            dal=dal,
        )

    outcome = error_handler.run(
        _run,
        tool_name=action.tool_name,
        input_data=action.input,
        required=action.tool_name in REQUIRED_TOOLS,
    )
    tool_error = outcome.get("error")
    it.error = tool_error.get("message") if tool_error else None
    history.append(_summarize_tool(action.tool_name, outcome, tool_error))
