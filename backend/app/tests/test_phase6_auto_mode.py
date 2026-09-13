# tests/test_phase6_auto_mode.py
"""E2E-проверка Фазы 6: авто-режим (deterministic → quality gate → LLM-refine С1)."""

from unittest.mock import MagicMock, patch

from app.schemas import AgentAnswer, ParsedQuery
from app.services.agent.executor import AgentExecutor
from app.services.agent.verify.policy import escalate_type
from app.services.agent.verify.verifier import verify_answer

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
        explanation=explanation or (answer_text or None),
        recommendations=recommendations or [],
        components=components or [],
        sources=[],
        warnings=warnings or [],
        status="Готово",
        mode="deterministic",
    )


class _FakeLLM:
    """LLM-заглушка для C1: возвращает JSON дооформления (refine-формат)."""
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


class _ActionLLM:
    """LLM-заглушка для C2: возвращает действие finish (action-формат LLMAgent)."""
    def __init__(self, final_answer="Полный ответ от LLM"):
        self._final_answer = final_answer
        self.calls = []

    def invoke(self, prompt):
        self.calls.append(prompt)
        import json
        return json.dumps({
            "action": "finish",
            "final_answer": self._final_answer,
        }, ensure_ascii=False)


class _BrokenLLM:
    """LLM-заглушка, которая падает на первом вызове (для C2-fallback)."""
    def __init__(self, exc=None):
        self._exc = exc or RuntimeError("LLM недоступен")
        self.calls = []

    def invoke(self, prompt):
        self.calls.append(prompt)
        raise self._exc


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
        assert escalate_type(vr.gaps) == "full_llm"

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

    def test_sufficiency_verdict_in_explanation_passes(self):
        """Стадия recheck: вердикт только в тексте explanation закрывает quantity_unmet."""
        parsed = _parsed(
            query="хватает ли труб по две штуки",
            item_types=["труба"],
            units_count=2,
            intents=["CHECK_SUFFICIENCY"],
        )
        answer = _answer(
            components=[_comp("Труба DN100", item_type="труба", quantity=5)],
            answer_text="Трубы: хватает, есть в наличии.",
        )
        vr = verify_answer(parsed, answer)
        assert vr.verdict == "pass"

    def test_sufficiency_no_verdict_text_reviews(self):
        """Ни в components, ни в тексте вердикта нет → review сохраняется."""
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
           return_value=AgentAnswer(query="тест", explanation="Отлично", mode="deterministic"))
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
    def test_auto_c2_full_llm_closes_gap_passes(self, mock_get_graph):
        """C2: quantity_unmet HIGH → полный LLM; LLM дал вердикт → re-verify PASS."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Задвижка DN100", item_type="задвижка", quantity=0,
                   status="отсутствует")],
            answer_text="Задвижка: отсутствует.")
        mock_get_graph.return_value = mock_graph

        fake_llm = _ActionLLM(final_answer="Не хватает 2 шт. задвижек.")
        executor = self._make_executor(fake_llm)
        parsed = _parsed(query="хватает ли задвижек по две штуки",
                         item_types=["задвижка"], units_count=2,
                         intents=["CHECK_SUFFICIENCY"])
        answer = executor.execute(
            "хватает ли задвижек по две штуки", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "pass"
        assert answer.verification_reasons == []
        assert answer.mode == "auto"
        assert answer.mode_refined == "auto_llm_full"
        assert answer.human_review_required is False
        assert "Не хватает" in (answer.explanation or "")
        assert fake_llm.calls, "C2 должен был вызвать LLM"

    @patch("app.services.agent.executor.get_graph")
    def test_auto_c2_full_llm_not_closed_reviews(self, mock_get_graph):
        """C2: LLM не дал verdict по достаточности → review остаётся."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Задвижка DN100", item_type="задвижка", quantity=0,
                   status="отсутствует")],
            answer_text="Задвижка: отсутствует.")
        mock_get_graph.return_value = mock_graph

        fake_llm = _ActionLLM(final_answer="Задвижка отсутствует по коду.")
        executor = self._make_executor(fake_llm)
        parsed = _parsed(query="хватает ли задвижек по две штуки",
                         item_types=["задвижка"], units_count=2,
                         intents=["CHECK_SUFFICIENCY"])
        answer = executor.execute(
            "хватает ли задвижек по две штуки", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "review"
        assert answer.mode_refined == "auto_llm_full"
        assert answer.human_review_required is True

    @patch("app.services.agent.executor.get_graph")
    def test_auto_c2_ask_user_never_passes(self, mock_get_graph):
        """C2 вернул уточняющий вопрос вместо ответа → НЕ pass, review."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Задвижка DN100", item_type="задвижка", quantity=0,
                   status="отсутствует")],
            answer_text="Задвижка: отсутствует.")
        mock_get_graph.return_value = mock_graph

        fake_llm = _ActionLLM(
            final_answer="Для подбора деталей необходимы параметры. Пожалуйста, укажите DN.")
        executor = self._make_executor(fake_llm)
        parsed = _parsed(query="хватает ли задвижек по две штуки",
                         item_types=["задвижка"], units_count=2,
                         intents=["CHECK_SUFFICIENCY"])
        answer = executor.execute(
            "хватает ли задвижек по две штуки", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "review"
        assert answer.mode_refined == "auto_llm_full"
        assert answer.human_review_required is True

    @patch("app.services.agent.executor.get_graph")
    def test_auto_c1_refine_preserves_expert_data_review(self, mock_get_graph):
        """Разведение причин: gate pass, но 'expert_data' (review из графа) сохраняется."""
        mock_graph = MagicMock()
        result = _graph_result(
            [_comp("Труба DN100", item_type="труба", quantity=5)],
            answer_text="Найдена труба.",
        )
        result["review_required"] = True
        mock_graph.invoke.return_value = result
        mock_get_graph.return_value = mock_graph

        fake_llm = _FakeLLM(refined_text="Трубы и задвижки найдены.")
        executor = self._make_executor(fake_llm)
        parsed = _parsed(query="найди трубы и задвижки",
                         item_types=["труба", "задвижка"],
                         intents=["FIND_BY_PARAMS"])
        answer = executor.execute("найди трубы и задвижки", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "pass"
        assert answer.mode_refined == "auto_llm_refine"
        assert answer.human_review_required is True
        assert answer.human_review_reasons == ["expert_data"]

    @patch("app.services.agent.executor.get_graph")
    def test_auto_c1_refine_plain_pass_clears_review(self, mock_get_graph):
        """Разведение причин: pass без expert_data → human_review снимается."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Труба DN100", item_type="труба", quantity=5)],
            answer_text="Найдена труба.",
        )
        mock_get_graph.return_value = mock_graph

        fake_llm = _FakeLLM(refined_text="Трубы и задвижки найдены.")
        executor = self._make_executor(fake_llm)
        parsed = _parsed(query="найди трубы и задвижки",
                         item_types=["труба", "задвижка"],
                         intents=["FIND_BY_PARAMS"])
        answer = executor.execute("найди трубы и задвижки", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "pass"
        assert answer.human_review_required is False
        assert answer.human_review_reasons == []

    @patch("app.services.agent.executor.get_graph")
    def test_auto_c1_refine_review_marks_quality_gate(self, mock_get_graph):
        """Разведение причин: gate остаётся review → причина 'quality_gate'."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Задвижка DN100", item_type="задвижка", quantity=5)],
            answer_text="Найдена задвижка.",
        )
        mock_get_graph.return_value = mock_graph

        fake_llm = _FakeLLM(refined_text="Найдены все запрошенные типы по каталогу.")
        executor = self._make_executor(fake_llm)
        parsed = _parsed(query="найди трубы и задвижки",
                         item_types=["труба", "задвижка"],
                         intents=["FIND_BY_PARAMS"])
        answer = executor.execute("найди трубы и задвижки", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "review"
        assert "quality_gate" in answer.human_review_reasons
        assert answer.human_review_required is True

    @patch("app.services.agent.executor.get_graph")
    def test_auto_c1_refine_applies_for_med_gap(self, mock_get_graph):
        """C1: scope_mismatch MED → дооформление (mode_refined=auto_llm_refine)."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Задвижка DN100", item_type="задвижка", quantity=5)],
            answer_text="Найдена задвижка.")
        mock_get_graph.return_value = mock_graph

        fake_llm = _FakeLLM(refined_text="Найдены все запрошенные типы.")
        executor = self._make_executor(fake_llm)
        parsed = _parsed(query="найди трубы и задвижки",
                         item_types=["труба", "задвижка"],
                         intents=["FIND_BY_PARAMS"])
        answer = executor.execute("найди трубы и задвижки", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "review"
        assert answer.mode_refined == "auto_llm_refine"
        assert "Найдены" in (answer.explanation or "")
        assert fake_llm.calls, "C1 должен был вызвать LLM"

    @patch("app.services.agent.executor.get_graph")
    def test_auto_c1_refine_closes_scope_passes(self, mock_get_graph):
        """C1: refine перечислил все запрошенные типы → re-verify PASS."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Труба DN100", item_type="труба", quantity=5)],
            answer_text="Найдена труба.")
        mock_get_graph.return_value = mock_graph

        fake_llm = _FakeLLM(refined_text="Найдены трубы и задвижки.")
        executor = self._make_executor(fake_llm)
        parsed = _parsed(query="найди трубы и задвижки",
                         item_types=["труба", "задвижка"],
                         intents=["FIND_BY_PARAMS"])
        answer = executor.execute("найди трубы и задвижки", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "pass"
        assert answer.verification_reasons == []
        assert answer.mode_refined == "auto_llm_refine"
        assert answer.human_review_required is False

    @patch("app.services.agent.executor.get_graph")
    def test_auto_c2_llm_failure_falls_back(self, mock_get_graph):
        """C2: LLM падает → fallback на deterministic review, human_review_required=True."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = _graph_result(
            [_comp("Задвижка DN100", item_type="задвижка", quantity=0,
                   status="отсутствует")],
            answer_text="Задвижка: отсутствует.")
        mock_get_graph.return_value = mock_graph

        executor = self._make_executor(_BrokenLLM())
        parsed = _parsed(query="хватает ли задвижек по две штуки",
                         item_types=["задвижка"], units_count=2,
                         intents=["CHECK_SUFFICIENCY"])
        answer = executor.execute(
            "хватает ли задвижек по две штуки", parsed=parsed, mode="auto")

        assert answer.verification_verdict == "review"
        assert answer.human_review_required is True
        assert answer.mode_refined == "auto"  # C2 упал, остался deterministic-ответ

    @patch("app.services.agent.executor.get_graph")
    def test_auto_review_no_llm_marks_human_review(self, mock_get_graph):
        """C2 выбран, но LLM недоступен → human_review_required=True, LLM не падает."""
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
