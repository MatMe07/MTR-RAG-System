# agent/llm/agent.py
"""LLM-управляемый режим (ЭТАП 4, секция 4C) — LLMAgent.

Цикл: LLM выбирает одно из трёх действий:
  {"action": "call_tool", "tool_name": "...", "input": {...}}
  {"action": "ask_user", "question": "..."}
  {"action": "finish", "final_answer": "..."}

Защита (4C.3): максимум 10 итераций, 60 секунд, запрет повторного вызова
одного инструмента с одинаковыми параметрами более 2 раз подряд.

Логирование (4C.4): каждая итерация пишется в llm_agent_logs (или память).
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from ..core.config import DEFAULT_CONFIG, AgentConfig
from ..core.exceptions import AgentError, LLMResponseError
from ..tools.error_handler import ErrorHandler, REQUIRED_TOOLS
from ..tools.instruments import run_instrument
from ..tools.tool_dal import ToolDAL
from .log import get_llm_logger
from .response_parser import LLMResponseParser

log = logging.getLogger("mtr.agent.llm_agent")

MAX_ITERATIONS = 10
MAX_TOTAL_SECONDS = 60.0
MAX_REPEAT = 2  # не более 2 повторных вызовов одного инструмента подряд

# Критерии остановки (4C.5): LLM должна завершить цикл, если выполнен
# любой из них — найдена деталь с совпадением >= 95% или 3+ кандидата >= 80%.
STOP_MATCH_SCORE = 0.95
STOP_CANDIDATE_SCORE = 0.80
STOP_CANDIDATE_COUNT = 3

_STOP_HINT_TEMPLATES = {
    "match": (
        "Стоп-критерий достигнут: найдена деталь с совпадением >= 95% "
        "(«{name}», совпадение {score:.0%}). Если данных достаточно — "
        "заверши цикл действием finish."
    ),
    "candidates": (
        "Стоп-критерий достигнут: найдено {count} кандидата с совпадением "
        ">= 80%. Если данных достаточно — заверши цикл действием finish."
    ),
}

_FORCED_FINISH_MESSAGE = (
    "Достигнут лимит попыток. Попробуйте детерминированный режим или уточните запрос."
)

_INSTRUCTION = (
    "Ты — инженерный агент MTR. Выбери одно действие и верни строго JSON:\n"
    '- {"action": "call_tool", "tool_name": "...", "input": {...}}\n'
    '- {"action": "ask_user", "question": "..."}\n'
    '- {"action": "finish", "final_answer": "..."}\n\n'
    "Правила:\n"
    "- Используй инструменты из списка ниже, когда нужно получить данные.\n"
    "- Если данных не хватает и они могут быть у пользователя — action=ask_user.\n"
    "- Когда ответ готов — action=finish с итоговым текстом.\n"
    "- Завершай цикл (action=finish), если найдена деталь с совпадением >= 95% "
    "или 3+ кандидата с совпадением >= 80%.\n"
)


class LLMAgent:
    """Главный класс LLM-режима (4C.2)."""

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        llm: Optional[Any] = None,
        dal: Optional[ToolDAL] = None,
        logger: Optional[Any] = None,
        error_handler: Optional[ErrorHandler] = None,
        request_id: Optional[str] = None,
    ):
        self.config = config or DEFAULT_CONFIG
        if llm is None:
            from .client import LLMClient
            llm = LLMClient(self.config)
        self._llm = llm
        self._dal = dal or ToolDAL()
        self._logger = logger or get_llm_logger()
        self._error_handler = error_handler or ErrorHandler()
        self._request_id = request_id or str(uuid.uuid4())
        self.iterations = 0

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------
    def run(self, query: str, parsed: Any = None) -> Dict[str, Any]:
        """Запуск цикла LLM. Возвращает результат, совместимый со сборщиком ответа."""
        self.iterations = 0
        tools = self._available_tools()
        parser = LLMResponseParser(
            available_tools={t["name"] for t in tools},
            get_schema=self._schema_for,
        )

        history: List[str] = []
        tool_results: Dict[str, List[Dict[str, Any]]] = {}
        components: List[Dict[str, Any]] = []
        sources: List[Dict[str, Any]] = []
        warnings: List[str] = []
        errors: List[Dict[str, Any]] = []
        last_repeat: List[tuple] = []
        forced_reason: Optional[str] = None

        history.append(_build_initial_prompt(query, parsed, tools))
        start = time.monotonic()

        while True:
            elapsed = time.monotonic() - start
            if elapsed > MAX_TOTAL_SECONDS:
                forced_reason = "Достигнут лимит времени (60 секунд)"
                break
            if self.iterations >= MAX_ITERATIONS:
                forced_reason = "Достигнут лимит итераций (10)"
                break

            self.iterations += 1
            prompt = _build_turn_prompt(history)
            iter_start = time.monotonic()
            try:
                llm_text = self._llm.invoke(prompt)
            except AgentError as e:
                warnings.append(f"Ошибка LLM: {e}")
                self._logger.record(prompt, {"error": str(e)}, _ms(time.monotonic() - iter_start),
                                    self.iterations, request_id=self._request_id)
                forced_reason = "Ошибка LLM: " + str(e)
                break

            duration_ms = _ms(time.monotonic() - iter_start)
            try:
                action = parser.parse(llm_text)
            except LLMResponseError as e:
                warnings.append(f"Невалидный ответ LLM: {e}")
                self._logger.record(
                    prompt, {"raw": llm_text, "error": str(e)}, duration_ms,
                    self.iterations, request_id=self._request_id,
                )
                history.append("Ответ был невалидным. Верни корректный JSON по схеме.")
                continue

            response = {"action": action.action}
            if action.tool_name:
                response["tool_name"] = action.tool_name
            self._logger.record(
                prompt, response, duration_ms, self.iterations,
                request_id=self._request_id,
            )

            if action.action == "call_tool":
                key = (action.tool_name, json.dumps(action.input, sort_keys=True, ensure_ascii=False))
                last_repeat = [k for k in last_repeat if k == key]
                last_repeat.append(key)
                if len(last_repeat) > MAX_REPEAT:
                    warnings.append(
                        f"Инструмент «{action.tool_name}» повторялся с одинаковыми параметрами."
                    )
                    forced_reason = _FORCED_FINISH_MESSAGE
                    break

                outcome, tool_error = self._execute_instrument(action, self._request_id)
                tool_results.setdefault(action.tool_name, []).append(outcome)
                if tool_error:
                    errors.append(tool_error)
                    warnings.append(
                        f"Инструмент «{action.tool_name}»: {tool_error.get('message', 'ошибка')}"
                    )
                else:
                    rows = _normalize_result(outcome, action.tool_name)
                    components.extend(rows)
                    hint = _stop_criteria_hint(rows)
                    if hint:
                        history.append(hint)
                history.append(_summarize_tool(action, outcome, tool_error))
                continue

            if action.action == "ask_user":
                return self._build_result(
                    tools_used=list(tool_results.keys()),
                    components=components,
                    sources=sources,
                    warnings=warnings,
                    errors=errors,
                    question=action.question,
                    elapsed_ms=_ms(time.monotonic() - start),
                )

            # finish
            return self._build_result(
                tools_used=list(tool_results.keys()),
                components=components,
                sources=sources,
                warnings=warnings,
                errors=errors,
                final_answer=action.final_answer,
                elapsed_ms=_ms(time.monotonic() - start),
            )

        # Лимиты / ошибки → принудительное завершение.
        return self._build_result(
            tools_used=list(tool_results.keys()),
            components=components,
            sources=sources,
            warnings=warnings,
            errors=errors,
            final_answer=_FORCED_FINISH_MESSAGE,
            forced_reason=forced_reason or _FORCED_FINISH_MESSAGE,
            elapsed_ms=_ms(time.monotonic() - start),
        )

    # ------------------------------------------------------------------
    # Внутренние помощники
    # ------------------------------------------------------------------
    def _available_tools(self) -> List[Dict[str, Any]]:
        from ..tools.registry import get_instruments_for_llm

        try:
            return get_instruments_for_llm()
        except Exception:  # noqa: BLE001
            return []

    def _schema_for(self, tool_name: str) -> Optional[Dict[str, Any]]:
        from ..tools.registry import get_instrument

        inst = get_instrument(tool_name)
        return (inst or {}).get("input_schema")

    def _execute_instrument(
        self,
        action: Any,
        request_id: str,
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Выполняет инструмент c обработчиком ошибок (4B ErrorHandler)."""
        def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
            return run_instrument(
                action.tool_name,
                input_data,
                request_id=request_id,
                dal=self._dal,
            )

        required = action.tool_name in REQUIRED_TOOLS
        result = self._error_handler.run(
            execute,
            tool_name=action.tool_name,
            input_data=action.input,
            required=required,
        )
        return result, result.get("error")

    def _build_result(
        self,
        tools_used: List[str],
        components: List[Dict[str, Any]],
        sources: List[Dict[str, Any]],
        warnings: List[str],
        errors: List[Dict[str, Any]],
        final_answer: str = "",
        question: Optional[str] = None,
        forced_reason: Optional[str] = None,
        elapsed_ms: int = 0,
    ) -> Dict[str, Any]:
        warnings = list(dict.fromkeys(w for w in warnings if w))
        review = bool(errors) or bool(question) or bool(forced_reason)
        if question:
            warnings.append(f"Требуется уточнение: {question}")
        if forced_reason:
            warnings.append(forced_reason)

        return {
            "request_id": self._request_id,
            "components": components,
            "sources": sources,
            "warnings": warnings,
            "missing": [],
            "review": review,
            "errors": errors,
            "mode": "llm",
            "tools_used": tools_used,
            "llm_iterations": self.iterations,
            "execution_time_ms": elapsed_ms,
            "answer": final_answer or (question or ""),
        }


# ---------------------------------------------------------------------------
# Промпты
# ---------------------------------------------------------------------------

def _build_initial_prompt(query: str, parsed: Any, tools: List[Dict[str, Any]]) -> str:
    lines = [_INSTRUCTION]
    if tools:
        lines.append("Доступные инструменты (JSON Schema для input):")
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
    return "\n".join(lines)


def _build_turn_prompt(history: List[str]) -> str:
    return "\n\n".join(history) + "\n\nВыбери следующее действие (JSON)."


def _summarize_tool(action: Any, outcome: Dict[str, Any], tool_error: Optional[Dict[str, Any]]) -> str:
    if tool_error:
        return (
            f"Результат {action.tool_name}: ОШИБКА {tool_error.get('code')} — "
            f"{tool_error.get('message')}"
        )
    payload = outcome.get("result")
    if isinstance(payload, dict) and "value" in payload:
        payload = payload["value"]
    try:
        text = json.dumps(payload, ensure_ascii=False, default=str)[:2000]
    except TypeError:
        text = str(payload)[:2000]
    return f"Результат {action.tool_name}: {text}"


def _parsed_context(parsed: Any) -> Dict[str, Any]:
    return {
        "item_types": getattr(parsed, "item_types", []),
        "technical_filters": getattr(parsed, "technical_filters", {}),
        "component_ids": getattr(parsed, "component_ids", []),
        "unit_ids": getattr(parsed, "unit_ids", []),
        "operations": getattr(parsed, "operations", []),
    }


def _normalize_result(outcome: Dict[str, Any], tool_name: str) -> List[Dict[str, Any]]:
    """Преобразует результат инструмента в строки-компоненты для сборщика."""
    payload = outcome.get("result")
    if isinstance(payload, dict) and "value" in payload:
        payload = payload["value"]

    rows: List[Dict[str, Any]] = []

    def card_row(component: Dict[str, Any], score: float = 0.0) -> Dict[str, Any]:
        codes = component.get("codes") or {}
        mtr_code = component.get("mtr_code") or codes.get("mtr_code")
        ksm_code = component.get("ksm_code") or codes.get("ksm_code")
        return {
            "name": component.get("name") or component.get("designation"),
            "item_type": component.get("item_type"),
            "mtr_code": mtr_code,
            "ksm_code": ksm_code,
            "match_score": float(score or 0.0),
            "match_percent": float((score or 0.0) * 100),
            "source_id": mtr_code,
        }

    if tool_name == "search_catalog":
        for item in (payload or {}).get("items", []):
            if isinstance(item, dict):
                comp = item.get("component") or item
                rows.append(card_row(comp, item.get("match_score", 0.0)))
    elif tool_name == "get_component":
        comp = (payload or {}).get("component") or payload
        if isinstance(comp, dict):
            rows.append(card_row(comp, (payload or {}).get("match_score", 0.0)))
    elif tool_name == "get_neighbors":
        for n in payload or []:
            if isinstance(n, dict):
                rows.append({
                    "name": n.get("name"),
                    "ksm_code": n.get("ksm_code"),
                    "mtr_code": n.get("mtr_code"),
                    "item_type": n.get("item_type"),
                    "match_score": 0.0,
                })
    return rows


def _ms(seconds: float) -> int:
    return int(seconds * 1000)


def _stop_criteria_hint(rows: List[Dict[str, Any]]) -> Optional[str]:
    """Возвращает текст-подсказку о достижении стоп-критерия (4C.5), либо None."""
    best = None
    for row in rows:
        score = row.get("match_score")
        if isinstance(score, (int, float)):
            if best is None or float(score) > best[1]:
                best = (row, float(score))
    if best is not None and best[1] >= STOP_MATCH_SCORE:
        return _STOP_HINT_TEMPLATES["match"].format(
            name=best[0].get("name") or "деталь",
            score=best[1],
        )

    count = sum(
        1 for row in rows
        if isinstance(row.get("match_score"), (int, float)) and float(row["match_score"]) >= STOP_CANDIDATE_SCORE
    )
    if count >= STOP_CANDIDATE_COUNT:
        return _STOP_HINT_TEMPLATES["candidates"].format(count=count)
    return None