# tests/test_phase6_auto_mode.py
"""E2E-проверка Фазы 6: авто-режим (deterministic → quality gate → LLM-refine С1)."""

from unittest.mock import patch, MagicMock

from app.schemas import AgentAnswer, ParsedQuery
from app.services.agent.executor import AgentExecutor
from app.services.agent.verify.verifier import verify_answer
from app.services.agent.verify.policy import escalate_type


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parsed(
    *,
    query: str = "тест",
    item_types=None,
    technical_filters=None,
    units_count: int = 0,
    intents=None,
    status: str = "COMPLETE",
) -> ParsedQuery:
    pq = ParsedQuery(
        original_query=query,
        operations=["search"],
        item_types=item_types or [],
        component_ids=[],
        unit_ids=[],
        proposed_changes={},
        technical_filters=technical_filters or {},
        references=[],
        limit=None,
        on_stock=None,
        not_installed=None,
        units_count=units_count,
    )
    pq.intents = intents or []
    pq.status = status
    return pq


def _comp(name, *, item_type, quantity, status="на складе"):
    return {
        "name": name,
        "item_type": item_type,
        "quantity": quantity,
        "status": status,
        "match_score": 1.0,
    }


def _answer(components=None, answer_text="", explanation="", recommendations=None,
            warnings=None) -> AgentAnswer:
    return AgentAnswer(
        query="тест",
        answer=answer_text,
        explanation=explanation,
        recommendations=recommendations or [],
        components=components or [],
        sources=[],
        warnings=warnings or [],
        status="Готово",
        mode="deterministic",
    )


class _FakeLLM:
    """LLM-заглушка: возвращает JSON с улучшенным текстом."""
    def __init__(self, refined_text="Уточнённый ответ"):
        self._refined_text = refined_text
        self.calls = []

    def invoke(self, prompt):
        self.calls.append(prompt)
        import json
        return json.dumps({
            "answer_text": self._refined_text,
            "explanation": "LLM дооформил ответ.",
            "extra_recommendations": ["доп рекомендация от LLM"],
            "confidence_gate": "pass",
        }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# §9.2 Verifier кейсы по плану
# ---------------------------------------------------------------------------

class TestSufficiencyVerifierE2E:
    """H2S «хватает ли ... по 2 шт.» → quantity_unmet → REVIEW."""

    def test_sufficiency_without_verdict_reviews(self):
        parsed = _parsed(
            query="хватает ли труб по две штуки",
            item_types=["труба"],
            units_count=2,
            intents=["CHECK_SUFFICIENCY"],
        )
        answer = _answer(
            components=[_comp("Труба DN100", item_type="труба", quantity=5)],
            answer_text="Найдены трубы.",
        )
        vr = verify_answer(parsed, answer)
        assert vr.verdict == "review"
        assert any(g.type == "quantity_unmet" for g in vr.gaps)
        assert escalate_type(vr.gaps) == "refine"

    def test_sufficiency_with_verdict_passes(self):
        parsed = _parsed(
            query="хватает ли труб по две штуки",
            item_types=["труба"],
            units_count=2,
            intents=["CHECK_SUFFICIENCY"],
        )
        answer = _answer(
            components=[_comp("Труба DN100", item_type="труба", quantity=5,
                              status="хватает 5 шт., нужно 2")],
            answer_text="Трубы: хватает.",
        )
        vr = verify_answer(parsed, answer)
        assert vr.verdict == "pass"


class TestOutOfStockVerifierE2E:
    """H2S «нет на складе / срочность»."""

    def test_out_of_stock_correct_filter_passes(self):
        parsed = _parsed(
            query="которых нет на складе, расставь по срочности",
            item_types=["задвижка"],
            intents=["LIST_OUT_OF_STOCK"],
        )
        answer = _answer(
            components=[_comp("Задвижка DN100", item_type="задвижка", quantity=0,
                              status="срочно, отсутствует")],
            answer_text="Позиции без остатка.",
        )
        vr = verify_answer(parsed, answer)
        assert vr.verdict == "pass"

    def test_out_of_stock_with_in_stock_items_reviews(self):
        parsed = _parsed(
            query="которых нет на складе, расставь по срочности",
            item_types=["задвижка"],
            intents=["LIST_OUT_OF_STOCK"],
        )
        answer = _answer(
            components=[
                _comp("Задвижка DN100", item_type="задвижка", quantity=0),
                _comp("Задвижка DN50", item_type="задвижка", quantity=3),
            ],
            answer_text="Все позиции.",
        )
        vr = verify_answer(parsed, answer)
        assert vr.verdict == "review"
        assert any(g.type == "zero_stock_missing" for g in vr.gaps)


class TestScopeMismatchE2E:
    def test_scope_mismatch_detected(self):
        parsed = _parsed(
            query="найди трубы, отводы, задвижки, фланцы, муфты, краны",
            item_types=["труба", "отвод", "задвижка", "фланец", "муфта", "кран"],
            intents=["FIND_BY_PARAMS"],
        )
        answer = _answer(
            components=[_comp("Труба DN100", item_type="труба", quantity=5)],
            answer_text="Найдена труба.",
        )
        vr = verify_answer(parsed, answer)
        assert vr.verdict == "review"
        assert any(g.type == "scope_mismatch" for g in vr.gaps)


# ---------------------------------------------------------------------------
# Executor auto mode integration
# ---------------------------------------------------------------------------

class TestAnswerNodeCompleted:
    """answer_node корректно возвращает completed=True (LAN-фикс completed=False)."""

    @patch("app.services.agent.graph.nodes.build_answer",
           return_value=AgentAnswer(query="тест", answer="Отлично", mode="deterministic"))
    def test_answer_node_returns_completed(self, mock_build):
        from app.services.agent.core.state import create_initial_state
        from app.services.agent.graph.nodes import answer_node
        pq = _parsed(query="найди задвижку", item_types=["задвижка"])
        state = create_initial_state(query="найди задвижку", parsed=pq)
        state["context"]["intent"] = "search"
        out = answer_node(state)
        assert out.get("completed") is True
        assert out.get("answer") is not None


def _graph_result(components, answer_text="Ответ."):
    return {
        "components": components,
        "sources": [],
        "warnings": [],
        "missing": [],
        "review": False,
        "answers": [answer_text],
        "context": {"intent": "search", "tools_used": ["search_catalog"],
                    "mode": "offline_rules", "last_text": answer_text},
        "results": {},
    }


class TestExecutorAutoE2E:
    def _make_executor(self, fake_llm=None):
        cfg = MagicMock()
        cfg.auto_verify = True
        cfg.use_llm = fake_llm is not None
        cfg.storage = "json"
        cfg.checkpoint_thread_id = "t"
        cfg.recursion_limit = 50
        executor = AgentExecutor(config=cfg)
        executor._llm = fake_llm  # принудительно подставляем заглушку
        return executor

    @patch("app.services.agent.executor.get_graph")
    def test_auto_fills_verification_fields(self, mock_get_graph):
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Труба DN100", item_type="труба", quantity=5)])
        mock_get_graph.return_value = mock_graph

        executor = self._make_executor()
        parsed = _parsed(query="найди трубу", item_types=["труба"],
                         intents=["FIND_BY_PARAMS"])
        answer = executor.execute("найди трубу", parsed=parsed, mode="auto")

        assert answer.mode == "auto"
        assert answer.verification_verdict in ("pass", "review")
        assert isinstance(answer.verification_reasons, list)

    @patch("app.services.agent.executor.get_graph")
    def test_auto_pass_skips_refine(self, mock_get_graph):
        """PASS → LLM-refine не вызывается (mode_refined остаётся 'auto')."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Труба DN100", item_type="труба", quantity=5,
                   status="хватает, есть на складе")],
            answer_text="Труба: есть на складе.")
        mock_get_graph.return_value = mock_graph

        fake_llm = _FakeLLM()
        executor = self._make_executor(fake_llm)
        parsed = _parsed(query="хватает ли трубы", item_types=["труба"],
                         units_count=1, intents=["CHECK_SUFFICIENCY"])
        answer = executor.execute("хватает ли трубы", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "pass"
        assert answer.mode_refined == "auto"
        assert fake_llm.calls == []

    @patch("app.services.agent.executor.get_graph")
    def test_auto_review_applies_refine_with_llm(self, mock_get_graph):
        """REVIEW + LLM доступен → refine применяется (mode_refined=auto_llm_refine)."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Задвижка DN100", item_type="задвижка", quantity=0,
                   status="отсутствует")],
            answer_text="Задвижка: отсутствует.")
        mock_get_graph.return_value = mock_graph

        fake_llm = _FakeLLM(refined_text="Не хватает 2 шт. задвижек.")
        executor = self._make_executor(fake_llm)
        parsed = _parsed(query="хватает ли задвижек по две штуки",
                         item_types=["задвижка"], units_count=2,
                         intents=["CHECK_SUFFICIENCY"])
        answer = executor.execute(
            "хватает ли задвижек по две штуки", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "review"
        assert answer.mode_refined == "auto_llm_refine"
        assert "Не хватает" in answer.answer
        assert fake_llm.calls, "refine должен был вызвать LLM"

    @patch("app.services.agent.executor.get_graph")
    def test_auto_review_no_llm_marks_human_review(self, mock_get_graph):
        """REVIEW + LLM недоступен → human_review_required=True, LLM не падает."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Задвижка DN100", item_type="задвижка", quantity=0,
                   status="отсутствует")],
            answer_text="Задвижка: отсутствует.")
        mock_get_graph.return_value = mock_graph

        executor = self._make_executor(fake_llm=None)  # llm отсутствует
        parsed = _parsed(query="хватает ли задвижек по две штуки",
                         item_types=["задвижка"], units_count=2,
                         intents=["CHECK_SUFFICIENCY"])
        answer = executor.execute(
            "хватает ли задвижек по две штуки", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "review"
        assert answer.human_review_required is True


class TestDeterministicUnaffectedE2E:
    @patch("app.services.agent.executor.get_graph")
    def test_deterministic_no_verification_fields(self, mock_get_graph):
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result([], answer_text="ОК")
        mock_get_graph.return_value = mock_graph

        executor = AgentExecutor()
        answer = executor.execute("тест", mode="deterministic")
        # auto-логика не должна трогать deterministic
        assert answer.verification_verdict is None
        assert answer.mode_refined != "auto"
