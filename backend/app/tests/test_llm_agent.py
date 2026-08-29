# tests/test_llm_agent.py
"""Интеграционные тесты LLMAgent (ЭТАП 4, секция 4C) на JSON-репозитории."""

import json

import pytest

from app.services.agent.llm.agent import (
    LLMAgent,
    _stop_criteria_hint,
)
from app.services.agent.repository.json_repository import JsonRepository
from app.services.agent.tools.tool_dal import ToolDAL


class FakeScriptedLLM:
    """LLM-заглушка: возвращает ответы из списка по порядку."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def invoke(self, prompt):
        self.calls.append(prompt)
        if len(self.responses) <= len(self.calls) - 1:
            return json.dumps({"action": "finish", "final_answer": "завершено по умолчанию"})
        return self.responses[len(self.calls) - 1]


@pytest.fixture()
def dal():
    return ToolDAL(JsonRepository())


def _agent(dal, responses):
    return LLMAgent(llm=FakeScriptedLLM(responses), dal=dal)


def _call_search(item_type="отвод", dn=159, angle=90):
    return json.dumps({
        "action": "call_tool",
        "tool_name": "search_catalog",
        "input": {"params": {"item_type": item_type, "dn": dn, "angle": angle, "limit": 20}},
    }, ensure_ascii=False)


def test_call_tool_then_finish(dal):
    responses = [
        _call_search(),
        json.dumps({"action": "finish", "final_answer": "Найдены отводы DN159."}),
    ]
    agent = _agent(dal, responses)
    result = agent.run("Отвод 90 градусов DN159")
    assert result["mode"] == "llm"
    assert result["tools_used"] == ["search_catalog"]
    assert result["answer"] == "Найдены отводы DN159."
    assert result["components"], "должны быть найдены компоненты отвода"
    assert any(c.get("item_type") == "отвод" for c in result["components"])
    assert agent.iterations == 2


def test_ask_user_returns_question(dal):
    responses = [
        _call_search(),
        json.dumps({"action": "ask_user", "question": "Уточните DN?"}),
    ]
    agent = _agent(dal, responses)
    result = agent.run("подбери отвод")
    assert result["review"] is True
    assert any("Уточните DN?" in w for w in result["warnings"])


def test_invalid_response_recovered(dal):
    # LLM вернул мусор, затем корректное действие.
    responses = [
        "без json",
        _call_search(),
        json.dumps({"action": "finish", "final_answer": "готово"}),
    ]
    agent = _agent(dal, responses)
    result = agent.run("найди отвод DN159")
    assert result["answer"] == "готово"
    assert any("Невалидный ответ" in w for w in result["warnings"])
    assert len(result["components"]) > 0


def test_unknown_tool_does_not_crash(dal):
    responses = [
        json.dumps({"action": "call_tool", "tool_name": "nope", "input": {}}),
        _call_search(),
        json.dumps({"action": "finish", "final_answer": "ок"}),
    ]
    agent = _agent(dal, responses)
    result = agent.run("отвод")
    # Невалидный инструмент → предупреждение, цикл продолжился.
    assert any("не найден" in w or "Невалидный" in w for w in result["warnings"])
    assert result["answer"] == "ок"


def test_iteration_limit_forced_finish(dal):
    # LLM бесконечно вызывает инструменты → принудительный finish.
    responses = [
        json.dumps({
            "action": "call_tool",
            "tool_name": "search_catalog",
            "input": {"params": {"item_type": "отвод", "limit": i + 1}},
        }, ensure_ascii=False)
        for i in range(15)
    ]
    agent = _agent(dal, responses)
    result = agent.run("отвод")
    assert agent.iterations <= 10
    assert any("лимит" in w.lower() for w in result["warnings"])
    assert result["review"] is True


def test_repeat_guard_stops(dal):
    # Один и тот же вызов повторяется → защита от зацикливания.
    repeat = _call_search()
    responses = [repeat] * 5 + [
        json.dumps({"action": "finish", "final_answer": "готово"}),
    ]
    agent = _agent(dal, responses)
    result = agent.run("отвод DN159 90")
    assert agent.iterations < 5
    assert any("лимит" in w.lower() or "повтор" in w.lower() for w in result["warnings"])


def test_components_normalized_from_search(dal):
    responses = [
        _call_search(),
        json.dumps({"action": "finish", "final_answer": "ок"}),
    ]
    agent = _agent(dal, responses)
    result = agent.run("отвод 90 DN159")
    comp = result["components"][0]
    assert comp["mtr_code"]
    assert comp["ksm_code"]
    assert 0.0 <= comp["match_score"] <= 1.0


def test_agent_reuse_resets_iterations(dal):
    # Повторный run того же агента не должен срабатывать по лимиту итераций.
    responses = [
        _call_search(),
        json.dumps({"action": "finish", "final_answer": "первый запуск"}),
    ]

    class _LoopingFakeLLM:
        def __init__(self, rs):
            self.responses = list(rs)
            self.calls = []

        def invoke(self, prompt):
            self.calls.append(prompt)
            return self.responses[(len(self.calls) - 1) % len(self.responses)]

    agent = LLMAgent(llm=_LoopingFakeLLM(responses), dal=dal)
    first = agent.run("отвод DN159 90")
    assert first["answer"] == "первый запуск"
    assert agent.iterations == 2

    second = agent.run("отвод DN159 90")
    assert second["answer"] == "первый запуск"
    assert not any("лимит" in w.lower() for w in second["warnings"])
    assert agent.iterations == 2


def test_stop_criteria_hint_unit():
    # Прямой юнит функции стоп-критериев (4C.5).
    from app.services.agent.llm import agent as agent_mod

    assert agent_mod._stop_criteria_hint([]) is None
    assert agent_mod._stop_criteria_hint([
        {"name": "ОКШ", "match_score": 0.94},
    ]) is None
    assert agent_mod._stop_criteria_hint([
        {"name": "ОКШ", "match_score": 0.96},
    ]) is not None

    hint = agent_mod._stop_criteria_hint([
        {"name": "А", "match_score": 0.8},
        {"name": "Б", "match_score": 0.81},
        {"name": "В", "match_score": 0.82},
    ])
    assert hint is not None and "3" in hint


def test_stop_criteria_hint_in_prompt(dal):
    # После поиска с совпадением >= 95% в следующий промпт попадает подсказка.
    responses = [
        _call_search(),
        json.dumps({"action": "finish", "final_answer": "Найдены отводы DN159."}),
    ]
    agent = _agent(dal, responses)
    result = agent.run("отвод 90 DN159")
    assert result["mode"] == "llm"
    assert result["answer"] == "Найдены отводы DN159."
    # Второй промпт (история) содержит стоп-критерий.
    assert any("Стоп-критерий" in p for p in agent._llm.calls[1:])


def test_llm_result_has_metadata(dal):
    # Результат LLM-агента содержит поля структуры AgentContext (4F).
    responses = [
        _call_search(),
        json.dumps({"action": "finish", "final_answer": "готово"}),
    ]
    agent = _agent(dal, responses)
    result = agent.run("отвод 90 DN159")
    assert result["llm_iterations"] == 2
    assert isinstance(result["execution_time_ms"], int)
    assert result["request_id"]