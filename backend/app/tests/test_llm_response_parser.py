# tests/test_llm_response_parser.py
"""Юнит-тесты LLMResponseParser (ЭТАП 4, секция 4C.2)."""

import json

import pytest

from app.services.agent.llm.response_parser import LLMResponseParser, extract_json_object
from app.services.agent.core.exceptions import LLMResponseError
from app.services.agent.tools.registry import get_instrument


def _parser() -> LLMResponseParser:
    return LLMResponseParser(
        available_tools={"search_catalog", "get_component", "check_stock"},
        get_schema=lambda name: (get_instrument(name) or {}).get("input_schema"),
    )


def _wrap(payload: dict) -> str:
    return "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"


def test_extract_json_from_code_fence():
    data = extract_json_object("Вот ответ:\n```json\n{\"action\": \"finish\"}\n```")
    assert data["action"] == "finish"


def test_parse_finish():
    action = _parser().parse(_wrap({"action": "finish", "final_answer": "Готово"}))
    assert action.action == "finish"
    assert action.final_answer == "Готово"


def test_parse_ask_user():
    action = _parser().parse(_wrap({"action": "ask_user", "question": "Какой DN?"}))
    assert action.action == "ask_user"
    assert action.question == "Какой DN?"


def test_parse_call_tool_valid():
    action = _parser().parse(_wrap({
        "action": "call_tool",
        "tool_name": "search_catalog",
        "input": {"params": {"item_type": "отвод", "dn": 159}},
    }))
    assert action.tool_name == "search_catalog"
    assert action.input["params"]["dn"] == 159


def test_call_tool_unknown_tool_rejected():
    with pytest.raises(LLMResponseError, match="не найден"):
        _parser().parse(_wrap({"action": "call_tool", "tool_name": "nope", "input": {}}))


def test_call_tool_invalid_input_rejected():
    # get_component требует обязательное поле identifier
    with pytest.raises(LLMResponseError, match="невалидный input"):
        _parser().parse(_wrap({"action": "call_tool", "tool_name": "get_component", "input": {}}))


def test_missing_action_rejected():
    with pytest.raises(LLMResponseError, match="action"):
        _parser().parse(_wrap({"foo": 1}))


def test_unknown_action_rejected():
    with pytest.raises(LLMResponseError, match="Неизвестное действие"):
        _parser().parse(_wrap({"action": "explode"}))


def test_ask_user_without_question_rejected():
    with pytest.raises(LLMResponseError, match="question"):
        _parser().parse(_wrap({"action": "ask_user"}))


def test_finish_without_answer_rejected():
    with pytest.raises(LLMResponseError, match="final_answer"):
        _parser().parse(_wrap({"action": "finish"}))


def test_non_json_rejected():
    with pytest.raises(LLMResponseError, match="JSON"):
        _parser().parse("просто текст без структуры")


def test_parser_without_tools_skips_registry_check():
    # Без available_tools реестр не проверяется.
    parser = LLMResponseParser()
    action = parser.parse(json.dumps({"action": "call_tool", "tool_name": "whatever", "input": {}}))
    assert action.tool_name == "whatever"