# agent/llm/response_parser.py
"""Парсер ответов LLM в LLM-режиме (ЭТАП 4, секция 4C.2 LLMResponseParser).

Разрешает три типа действий:
  {"action": "call_tool", "tool_name": "...", "input": {...}}
  {"action": "ask_user", "question": "..."}
  {"action": "finish", "final_answer": "..."}

Проверки (4C.2):
- Валидность JSON и наличие поля action.
- call_tool: tool_name есть в реестре, input валиден по input_schema.
- ask_user: непустой question.
- finish: непустой final_answer.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ..core.exceptions import LLMResponseError


@dataclass
class ParsedAction:
    """Разобранное и провалидированное действие LLM."""

    action: str
    tool_name: Optional[str] = None
    input: Dict[str, Any] = field(default_factory=dict)
    question: Optional[str] = None
    final_answer: Optional[str] = None


ALLOWED_ACTIONS = ("call_tool", "ask_user", "finish")

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(text: str) -> Dict[str, Any]:
    """Извлекает первый JSON-объект из текста (включая код-фенсы ```json)."""
    match = _JSON_RE.search(text or "")
    if not match:
        raise LLMResponseError("JSON-объект не найден в ответе", response=text)
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError as e:
        raise LLMResponseError(f"Невалидный JSON: {e}", response=text) from e
    if not isinstance(data, dict):
        raise LLMResponseError("Ожидался JSON-объект", response=text)
    return data


class LLMResponseParser:
    """Валидатор ответов LLM с учётом реестра инструментов."""

    def __init__(
        self,
        available_tools: Optional[Set[str]] = None,
        get_schema: Optional[Any] = None,
    ):
        self._tools = available_tools or set()
        self._get_schema = get_schema

    def parse(self, text: str) -> ParsedAction:
        """Возвращает ParsedAction или бросает LLMResponseError с причиной."""
        data = extract_json_object(text)

        action = data.get("action")
        if not action:
            raise LLMResponseError("Отсутствует поле action", response=text)
        if action not in ALLOWED_ACTIONS:
            raise LLMResponseError(
                f"Неизвестное действие '{action}'; ожидается одно из: "
                + ", ".join(ALLOWED_ACTIONS),
                response=text,
            )

        if action == "call_tool":
            return self._parse_call_tool(data, text)
        if action == "ask_user":
            question = data.get("question")
            if not isinstance(question, str) or not question.strip():
                raise LLMResponseError("call ask_user: поле question пустое", response=text)
            return ParsedAction(action=action, question=question.strip())
        # finish
        final_answer = data.get("final_answer")
        if not isinstance(final_answer, str) or not final_answer.strip():
            raise LLMResponseError("call finish: поле final_answer пустое", response=text)
        return ParsedAction(action=action, final_answer=final_answer.strip())

    def _parse_call_tool(self, data: Dict[str, Any], text: str) -> ParsedAction:
        tool_name = data.get("tool_name")
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise LLMResponseError("call_tool: отсутствует tool_name", response=text)
        tool_name = tool_name.strip()
        if self._tools and tool_name not in self._tools:
            raise LLMResponseError(
                f"call_tool: инструмент '{tool_name}' не найден в реестре",
                response=text,
            )

        action_input = data.get("input") or {}
        if not isinstance(action_input, dict):
            raise LLMResponseError("call_tool: поле input должно быть объектом", response=text)

        # Валидация по input_schema (3C).
        if self._get_schema is not None:
            try:
                schema = self._get_schema(tool_name)
            except Exception:  # noqa: BLE001
                schema = None
            if schema is not None:
                from app.services.agent.tools.validation import validate_input
                from app.services.agent.tools.errors import ToolError

                try:
                    validate_input(schema, action_input)
                except ToolError as e:
                    raise LLMResponseError(
                        f"call_tool: {tool_name} — невалидный input: {e.message}",
                        response=text,
                    ) from e

        return ParsedAction(action="call_tool", tool_name=tool_name, input=action_input)