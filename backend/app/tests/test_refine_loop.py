# tests/test_refine_loop.py
"""C1+ LLM-цикл (refine_loop): unit-тесты без сети и БД."""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.services.agent.llm.refine_loop import run_refine_loop
from app.services.agent.verify.verifier import VerificationResult

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

@dataclass
class _FakeComponent:
    name: str = ""
    item_type: str = ""
    status: str = ""
    quantity: Optional[float] = None
    match_score: float = 0.0
    match_percent: float = 0.0


class _FakeAnswer:
    def __init__(self, *, components=None, explanation="", warnings=None, recommendations=None,
                 review_verdict=None, review_issues=None):
        self.components = components or []
        self.explanation = explanation
        self.warnings = warnings or []
        self.recommendations = recommendations or []
        self.review_verdict = review_verdict
        self.review_issues = review_issues or []
        self.verification_verdict = None
        self.verification_reasons = []
        self.llm_refine_failed = None
        self.human_review_reasons = []
        self.human_review_required = False


class _Parsed:
    def __init__(self, *, item_types=None, technical_filters=None, units_count=None,
                 intents=None, operations=None):
        self.item_types = item_types or []
        self.technical_filters = technical_filters or {}
        self.units_count = units_count
        self.intents = intents or []
        self.operations = operations or ["search"]
        self.component_ids = []
        self.unit_ids = []
        self.ambiguities = []


class _FakeLLM:
    """LLM-заглушка: список JSON-строк, возвращаемых по очереди."""

    def __init__(self, actions: List[Dict[str, Any]]):
        self._actions = actions
        self._idx = 0
        self.calls: List[str] = []
        self._total_tokens = 0

    def invoke(self, prompt, **kwargs):
        self.calls.append(prompt)
        if self._idx >= len(self._actions):
            raise RuntimeError("_FakeLLM: все действия исчерпаны")
        action = self._actions[self._idx]
        self._idx += 1
        return json.dumps(action, ensure_ascii=False)

    def get_metrics(self):
        self._total_tokens += 10
        return {"total_tokens": self._total_tokens}


class _RaiseOnFirstLLM:
    """LLM, падающий на первом вызове."""

    def __init__(self):
        self.calls: List[str] = []

    def invoke(self, prompt, **kwargs):
        self.calls.append(prompt)
        raise RuntimeError("LLM недоступен")


class _FakeVerifier:
    """Зависимый от текста verifier: verdict pass, если explanation содержит ключевое слово."""

    def __init__(self, pass_keyword: str = "хватает"):
        self._pass_keyword = pass_keyword

    def __call__(self, parsed, answer):
        text = (getattr(answer, "explanation", "") or "").lower()
        if self._pass_keyword in text:
            return VerificationResult(verdict="pass", reasons=[], gaps=[])
        from app.services.agent.verify.verifier import Gap
        return VerificationResult(
            verdict="review",
            reasons=["[low] test: заглушка"],
            gaps=[Gap(type="test_gap", detail="test", severity="low")],
        )


# fake repository for ToolDAL (search_catalog needs get_catalog)
class _FakeRepo:
    def __init__(self, catalog=None):
        self._catalog = catalog or []

    def get_catalog(self):
        return self._catalog

    def get_card_by_ksm(self, ksm):
        for c in self._catalog:
            if (c.get("codes") or {}).get("ksm_code") == ksm:
                return c
        return None

    def get_card_by_id(self, card_id):
        return None

    def get_stock_quantity(self, ksm):
        c = self.get_card_by_ksm(ksm)
        if c is None:
            return None
        return ((c.get("properties") or {}).get("stock_qty") or {}).get("value", 0.0)

    def get_stock_cost(self, ksm):
        return None

    def get_graph(self):
        return {"components": []}

    def get_regulation(self):
        return {"important_limitations": [], "medium_profiles": [], "replaced_standards": []}

    def get_components_by_unit(self, unit_code):
        return []

    def close(self):
        pass


def _parsed(**kw):
    return _Parsed(**kw)


def _answer(*, explanation="", components=None, **kw):
    return _FakeAnswer(explanation=explanation, components=components or [], **kw)


def _simple_answer(types: List[str] = None):
    comps = [_FakeComponent(name=t, item_type=t, status="на складе") for t in (types or ["задвижка"])]
    return _answer(explanation="Найдены задвижки.", components=comps)


# ---------------------------------------------------------------------------
# тесты
# ---------------------------------------------------------------------------

class TestRefineLoopBasic:
    def test_none_llm_returns_immediately(self):
        parsed = _parsed(item_types=["задвижка"], intents=["FIND_BY_PARAMS"])
        answer = _simple_answer()
        result = run_refine_loop(llm_client=None, query="q", parsed=parsed, answer=answer, gaps=[])
        assert result.passed is False
        assert result.iterations == []
        assert result.llm_error is None

    def test_finish_passes_on_first_iteration(self):
        parsed = _parsed(item_types=["труба", "задвижка"], intents=["FIND_BY_PARAMS"])
        answer = _answer(
            explanation="Найдена только труба.",
            components=[_FakeComponent(name="Труба DN100", item_type="труба", quantity=5)],
        )
        verifier = _FakeVerifier(pass_keyword="трубы и задвижки")
        llm = _FakeLLM([{"action": "finish", "final_answer": "Найдены трубы и задвижки."}])
        result = run_refine_loop(
            llm_client=llm, query="найди трубы и задвижки", parsed=parsed,
            answer=answer, gaps=[], verifier=verifier,
        )
        assert result.passed is True
        assert len(result.iterations) == 1
        assert result.iterations[0].verdict == "pass"
        assert answer.explanation == "Найдены трубы и задвижки."
        assert len(llm.calls) == 1

    def test_finish_three_failures_ends_loop(self):
        verifier = _FakeVerifier(pass_keyword="никогда")
        llm = _FakeLLM([
            {"action": "finish", "final_answer": "Ответ без вердикта."},
            {"action": "finish", "final_answer": "Ответ без вердикта 2."},
            {"action": "finish", "final_answer": "Ответ без вердикта 3."},
        ])
        parsed = _parsed(intents=["FIND_BY_PARAMS"])
        answer = _answer(explanation="старый текст")
        result = run_refine_loop(
            llm_client=llm, query="q", parsed=parsed, answer=answer,
            gaps=[], verifier=verifier, max_iterations=3,
        )
        assert result.passed is False
        assert len(result.iterations) == 3
        assert all(it.verdict == "review" for it in result.iterations)
        assert all(it.action == "finish" for it in result.iterations)
        assert result.final_answer == "Ответ без вердикта 3."
        assert len(llm.calls) == 3


class TestRefineLoopBlockedActions:
    def test_ask_user_blocked(self):
        verifier = _FakeVerifier("никогда")
        llm = _FakeLLM([
            {"action": "ask_user", "question": "Укажите DN?"},
            {"action": "ask_user", "question": "Укажите PN?"},
            {"action": "ask_user", "question": "Укажите материал?"},
        ])
        result = run_refine_loop(
            llm_client=llm, query="q", parsed=_parsed(), answer=_answer(),
            gaps=[], verifier=verifier, max_iterations=3,
        )
        assert result.passed is False
        assert len(result.iterations) == 3
        for it in result.iterations:
            assert it.action == "ask_user"
            assert "запрещён" in (it.error or "")
        assert len(llm.calls) == 3

    def test_invalid_json_marks_invalid(self):
        verifier = _FakeVerifier("никогда")
        llm = _FakeLLM([
            {"action": "finish", "final_answer": "ok"},
        ])
        # Override invoke to return raw garbage instead of parsed JSON
        original_invoke = llm.invoke
        calls_made = [0]

        def _bad_invoke(prompt, **kwargs):
            calls_made[0] += 1
            if calls_made[0] == 1:
                return "Это не JSON, просто текст."
            return original_invoke(prompt)

        llm.invoke = _bad_invoke
        result = run_refine_loop(
            llm_client=llm, query="q", parsed=_parsed(), answer=_answer(),
            gaps=[], verifier=verifier, max_iterations=3,
        )
        assert result.passed is False
        assert any(it.action == "invalid" for it in result.iterations)

    def test_anti_repeat_blocks_second_identical_call(self):
        call_tool = {"action": "call_tool", "tool_name": "search_catalog",
                     "input": {"params": {"item_type": "труба"}}}
        llm = _FakeLLM([call_tool, call_tool])
        repo = _FakeRepo(catalog=[{
            "card_id": "001", "item_type": "труба", "name": "Труба",
            "codes": {"ksm_code": "KSM1"}, "properties": {},
        }])
        result = run_refine_loop(
            llm_client=llm, query="q", parsed=_parsed(), answer=_answer(),
            gaps=[], verifier=_FakeVerifier("никогда"), repository=repo,
            max_iterations=2,
        )
        assert len(result.iterations) == 2
        assert result.iterations[0].error is None  # first call executed
        assert result.iterations[1].error is not None
        assert "повторный вызов" in result.iterations[1].error


class TestRefineLoopCallTool:
    def test_call_tool_then_finish(self):
        """LLM сначала вызывает инструмент, потом finish — итерации записаны."""
        call_action = {"action": "call_tool", "tool_name": "search_catalog",
                       "input": {"params": {"item_type": "труба"}}}
        finish_action = {"action": "finish", "final_answer": "Трубы найдены."}
        llm = _FakeLLM([call_action, finish_action])
        repo = _FakeRepo(catalog=[{
            "card_id": "001", "item_type": "труба", "name": "Труба DN100",
            "codes": {"ksm_code": "KSM1"}, "properties": {"stock_qty": {"value": 10.0}},
        }])
        answer = _answer(explanation="")
        result = run_refine_loop(
            llm_client=llm, query="q", parsed=_parsed(item_types=["труба"]),
            answer=answer, gaps=[], repository=repo,
            verifier=_FakeVerifier("трубы найдены"), max_iterations=3,
        )
        assert len(result.iterations) == 2
        assert result.iterations[0].action == "call_tool"
        assert result.iterations[0].tool_name == "search_catalog"
        assert result.iterations[1].action == "finish"
        assert result.passed is True

    def test_call_tool_error_recorded(self):
        """LLM вызывает несуществующий инструмент — парсер отклоняет (invalid), цикл продолжается."""
        bad_call = {"action": "call_tool", "tool_name": "nonexistent_tool",
                    "input": {"q": 1}}
        finish = {"action": "finish", "final_answer": "Данных нет."}
        llm = _FakeLLM([bad_call, finish, finish])
        answer = _answer(explanation="")
        result = run_refine_loop(
            llm_client=llm, query="q", parsed=_parsed(), answer=answer,
            gaps=[], verifier=_FakeVerifier("никогда"),
        )
        assert result.iterations[0].action == "invalid"
        assert "не найден в реестре" in result.iterations[0].error
        assert len(result.iterations) == 3


class TestRefineLoopTokensAndTime:
    def test_tokens_measured_when_get_metrics_exists(self):
        verifier = _FakeVerifier("pass")
        llm = _FakeLLM([{"action": "finish", "final_answer": "pass"}])
        result = run_refine_loop(
            llm_client=llm, query="q", parsed=_parsed(), answer=_answer(),
            gaps=[], verifier=verifier,
        )
        assert result.llm_tokens_used == 10

    def test_tokens_zero_when_no_get_metrics(self):
        class _NoMetricsLLM:
            def __init__(self):
                self.calls = []
            def invoke(self, prompt, **kwargs):
                self.calls.append(prompt)
                return json.dumps({"action": "finish", "final_answer": "pass"})

        llm = _NoMetricsLLM()
        result = run_refine_loop(
            llm_client=llm, query="q", parsed=_parsed(), answer=_answer(),
            gaps=[], verifier=_FakeVerifier("pass"),
        )
        assert result.llm_tokens_used == 0

    def test_time_limit_stops_immediately(self):
        """total_seconds=0.0 → цикл не выполняет ни одной итерации (лимит времени)."""
        verifier = _FakeVerifier("никогда")
        llm = _FakeLLM([{"action": "finish", "final_answer": "q"}])
        result = run_refine_loop(
            llm_client=llm, query="q", parsed=_parsed(), answer=_answer(),
            gaps=[], verifier=verifier, max_iterations=50, total_seconds=0.0,
        )
        assert len(result.iterations) == 0


class TestRefineLoopLlmError:
    def test_llm_error_on_first_iteration(self):
        llm = _RaiseOnFirstLLM()
        result = run_refine_loop(
            llm_client=llm, query="q", parsed=_parsed(), answer=_answer(),
            gaps=[], verifier=_FakeVerifier("никогда"),
        )
        assert result.passed is False
        assert result.llm_error is not None
        assert "недоступен" in result.llm_error
        assert len(result.iterations) == 1
        assert result.iterations[0].action == "llm_error"

    def test_llm_error_on_second_iteration(self):
        llm = _FakeLLM([{"action": "finish", "final_answer": "q"}])
        first_invoke = llm.invoke

        call_count = [0]
        def _flaky(prompt, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return first_invoke(prompt)
            raise RuntimeError("Drop")
        llm.invoke = _flaky
        result = run_refine_loop(
            llm_client=llm, query="q", parsed=_parsed(), answer=_answer(),
            gaps=[], verifier=_FakeVerifier("никогда"),
        )
        assert len(result.iterations) == 2
        assert result.iterations[1].action == "llm_error"
        assert result.llm_error is not None
