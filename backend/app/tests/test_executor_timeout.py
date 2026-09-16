# app/tests/test_executor_timeout.py

"""P0: защитный timeout у graph.invoke (executor.py).

Если граф не укладывается в AgentConfig.tool_timeout, executor возвращает
AgentAnswer с human_review_required=True и предупреждением о таймауте.
"""

import time

from app.schemas import AgentAnswer, ParsedQuery
from app.services.agent.core.config import AgentConfig
from app.services.agent.executor import AgentExecutor


class _SlowGraph:
    """Фейковый граф, который превышает лимит времени."""

    def __init__(self, delay: float):
        self.delay = delay
        self.calls = 0

    def invoke(self, state, config=None):
        self.calls += 1
        time.sleep(self.delay)
        return {"components": [], "sources": [], "warnings": [], "missing": [],
                "context": {"tools_used": [], "last_text": "поздно"}}


def _parsed() -> ParsedQuery:
    return ParsedQuery(original_query="нужен отвод H2S den este тест")


def test_graph_timeout_marks_human_review(tmp_path):
    config = AgentConfig(tool_timeout=0.2)
    executor = AgentExecutor(config=config)
    slow = _SlowGraph(delay=5.0)
    executor._graph = slow  # обходим get_graph()

    start = time.time()
    answer = executor.execute(
        "нужен отвод H2S", parsed=_parsed(), mode="deterministic"
    )
    elapsed = time.time() - start

    assert isinstance(answer, AgentAnswer)
    assert elapsed < 3.0, f"executor не вышел по таймауту вовремя: {elapsed:.1f}s"
    assert answer.components == []
    assert answer.human_review_required is True
    assert "quality_gate" in answer.human_review_reasons
    assert any("времени" in w or "время" in w for w in answer.warnings)


def test_graph_within_timeout_returns_normally(tmp_path):
    config = AgentConfig(tool_timeout=1.0)
    executor = AgentExecutor(config=config)
    fast = _SlowGraph(delay=0.0)
    executor._graph = fast

    answer = executor.execute(
        "нужен отвод DN50", parsed=_parsed(), mode="deterministic"
    )

    assert isinstance(answer, AgentAnswer)
    assert answer.human_review_required is False
    assert not any("времени" in w for w in answer.warnings)
