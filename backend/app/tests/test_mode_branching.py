# tests/test_mode_branching.py
"""Ветвление по request.mode и рекомендация переключения на LLM-режим (4D)."""

import json

import pytest

from app.schemas import ParsedQuery
from app.services.agent.answer.builder import build_answer
from app.services.agent.executor import AgentExecutor
from app.services.agent.llm.agent import LLMAgent
from app.services.agent.repository.json_repository import JsonRepository
from app.services.agent.tools.tool_dal import ToolDAL


class _FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def invoke(self, prompt):
        self.calls.append(prompt)
        idx = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[idx]


def _parsed(query: str = "отвод 90 DN159") -> ParsedQuery:
    return ParsedQuery(original_query=query)


# ---------------------------------------------------------------------------
# Рекомендация переключения при UNCLEAR / REQUIRES_EXPERT (4D.3)
# ---------------------------------------------------------------------------

def test_deterministic_unclear_suggests_llm_mode():
    parsed = _parsed("что-то совсем непонятное")
    answer = build_answer(parsed, "search", {
        "components": [],
        "sources": [],
        "warnings": [],
        "missing": [],
        "mode": "offline_rules",
    })
    assert answer.status == "требует проверки"
    assert any("LLM-режим" in rec for rec in answer.recommendations)


def test_unclear_in_llm_mode_has_no_switch_recommendation():
    parsed = _parsed()
    answer = build_answer(parsed, "search", {
        "components": [],
        "sources": [],
        "warnings": ["Не удалось найти"],
        "missing": [],
        "mode": "llm",
    })
    assert not any("LLM-режим" in rec for rec in answer.recommendations)


def test_empty_answers_use_fallback_text():
    # Пустые строки в answers (например, last_text="") не дают пустой ответ.
    parsed = _parsed()
    answer = build_answer(parsed, "search", {
        "components": [{
            "mtr_code": "MTR-TEST-1",
            "ksm_code": "KSM-TEST-1",
            "name": "Тест",
            "item_type": "отвод",
        }],
        "sources": [],
        "warnings": [],
        "missing": [],
        "answers": [""],
        "mode": "offline_rules",
    })
    assert answer.answer
    assert "недостаточно данных" in answer.answer


def test_answer_text_prioritized_over_answers():
    # Результат LLM-агента: final_answer в "answer" — должен попасть в ответ.
    parsed = _parsed()
    answer = build_answer(parsed, "search", {
        "components": [],
        "sources": [],
        "warnings": [],
        "missing": [],
        "answer": "Отвод DN159 найден",
        "mode": "llm",
    })
    assert answer.answer == "Отвод DN159 найден"


def test_expert_status_suggests_llm_mode():
    parsed = _parsed()
    answer = build_answer(parsed, "search", {
        "components": [{
            "mtr_code": "MTR-TEST-1",
            "ksm_code": "KSM-TEST-1",
            "name": "Тест",
            "item_type": "отвод",
        }],
        "sources": [],
        "warnings": ["критич дисрепанс"],
        "review": True,
        "missing": [],
        "mode": "offline_rules",
    })
    assert answer.status == "требует экспертной проверки"
    assert any("LLM-режим" in rec for rec in answer.recommendations)


# ---------------------------------------------------------------------------
# Ветвление в AgentExecutor (4D.1/4D.2)
# ---------------------------------------------------------------------------

def test_executor_llm_mode_uses_llm_agent():
    responses = [
        json.dumps({
            "action": "call_tool",
            "tool_name": "search_catalog",
            "input": {"params": {"item_type": "отвод", "dn": 159, "angle": 90, "limit": 20}},
        }, ensure_ascii=False),
        json.dumps({"action": "finish", "final_answer": "Отвод DN159 найден"}),
    ]
    dal = ToolDAL(JsonRepository())
    fake_agent = LLMAgent(llm=_FakeLLM(responses), dal=dal)
    executor = AgentExecutor(llm_agent=fake_agent)

    answer = executor.execute("отвод 90 DN159", parsed=_parsed(), mode="llm")

    assert answer.mode == "llm"
    assert answer.answer == "Отвод DN159 найден"
    assert answer.components, "LLM-агент должен найти компоненты"


def test_executor_deterministic_default_mode():
    # Без явного mode по умолчанию — детерминированный путь (не падает).
    executor = AgentExecutor()
    answer = executor.execute("отвод 90", parsed=_parsed("отвод 90"))
    assert answer.mode in ("offline_rules", "llm")
    assert isinstance(answer.status, str)