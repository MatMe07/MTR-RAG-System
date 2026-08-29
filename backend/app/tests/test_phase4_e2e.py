# tests/test_phase4_e2e.py
"""E2E-проверка Этапа 4: оба режима на наборе из 20 запросов (критерий DOD Фазы E)."""

import json

import pytest

from app.services.agent.executor import AgentExecutor
from app.services.agent.llm.agent import LLMAgent
from app.services.agent.repository.json_repository import JsonRepository
from app.services.agent.tools.tool_dal import ToolDAL

E2E_QUERIES = [
    "подбери отвод 90 на DN159",
    "найди задвижку DN100",
    "покажи вентиль муфтовый DN50",
    "складской остаток по коду KSM-SYN-REG-000240",
    "план ТО и ТР насоса на год",
    "подбери замену трубопроводной арматуре DN200",
    "проверь дубли в каталоге",
    "рассчитай запас на складе за год",
    "собери участок насосной установки",
    "какие нормативы регулируют испытание трубопроводов",
    "узел учета тепловой энергии с трубопроводами",
    "есть ли в наличии отвод 45 на DN80",
    "комплектующие для задвижки клиновой DN150",
    "найди фланец по ГОСТ 12820",
    "влияние замены арматуры на участок",
    "документы по шаровому крану DN25",
    "объясни как работает предохранительный клапан",
    "справка по трубопроводу DN500",
    "оснастка для монтажа трубопровода",
    "ремонт запорной арматуры DN300",
]


class _E2ELFake:
    """LLM-заглушка: поиск в каталоге, затем finish."""

    def __init__(self):
        self.calls = []

    def invoke(self, prompt):
        self.calls.append(prompt)
        if len(self.calls) % 2 == 1:
            return json.dumps({
                "action": "call_tool",
                "tool_name": "search_catalog",
                "input": {
                    "params": {"item_type": "отвод", "dn": 159, "angle": 90, "limit": 20},
                },
            }, ensure_ascii=False)
        return json.dumps({"action": "finish", "final_answer": "Запрос обработан."})


@pytest.mark.parametrize("query", E2E_QUERIES)
def test_deterministic_mode_20_queries(query):
    answer = AgentExecutor().execute(query, mode="deterministic")
    assert answer.query == query
    assert answer.mode
    assert isinstance(answer.components, list)
    assert answer.status
    assert answer.answer is not None


@pytest.mark.parametrize("query", E2E_QUERIES)
def test_llm_mode_20_queries(query):
    dal = ToolDAL(JsonRepository())
    fake = _E2ELFake()
    agent = LLMAgent(llm=fake, dal=dal)
    result = agent.run(query)
    assert result["mode"] == "llm"
    assert result["answer"]
    assert not any("лимит" in w.lower() for w in result["warnings"])
    assert result["llm_iterations"] <= 10
    assert result["tools_used"] == ["search_catalog"]