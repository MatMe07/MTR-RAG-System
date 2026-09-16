# app/tests/test_verifier_safety.py

"""P0: verifier gap safety_unconfirmed для H2S/CO2-сред.

- Запрос с технич. фильтром H2S/CO2 и позициями без подтверждения → gap
  severity=high, verdict=review.
- Позиция с подтверждением (H2S-совместимость стали / «пригодность… подтверждена»)
  снимает gap.
- Безопасный/обычный запрос безопасности не трогает.
- Explanation не закрывает gap без явного положительного подтверждения.
"""

from app.schemas import AgentAnswer, AgentComponent, ParsedQuery
from app.services.agent.verify.policy import FULL_LLM_TYPES, escalate_type
from app.services.agent.verify.verifier import verify_answer


def _parsed(medium=None, h2s_confirmed=None, co2_confirmed=None):
    tf = {}
    if medium is not None:
        tf["medium"] = medium
    if h2s_confirmed is not None:
        tf["h2s_confirmed"] = h2s_confirmed
    if co2_confirmed is not None:
        tf["co2_confirmed"] = co2_confirmed
    return ParsedQuery(original_query="детали для опасной среды", technical_filters=tf)


def _comp(name, matched=None, mismatched=None, status="", detail=""):
    return AgentComponent(
        name=name, item_type="отвод", status=status or None,
        detail=detail or None, matched_params=matched or [],
        mismatched_params=mismatched or [],
    )


def _answer(components, explanation="", recommendations=None):
    return AgentAnswer(
        query="q", components=components, explanation=explanation,
        recommendations=recommendations or [],
    )


class TestSafetyUnconfirmed:
    def test_h2s_query_with_unconfirmed_components_gaps(self):
        parsed = _parsed(medium="H2S", h2s_confirmed=True)
        answer = _answer([_comp("Отвод 09ГСФ", matched=[]),
                          _comp("Отвод 13ХФА", matched=["H2S-совместимость стали"])])
        result = verify_answer(parsed, answer)
        assert result.verdict == "review"
        types = [g.type for g in result.gaps]
        assert "safety_unconfirmed" in types
        gap = next(g for g in result.gaps if g.type == "safety_unconfirmed")
        assert gap.severity == "high"

    def test_all_components_confirmed_no_gap(self):
        parsed = _parsed(medium="H2S", h2s_confirmed=True)
        answer = _answer([_comp("Отвод 13ХФА", matched=["H2S-совместимость стали"])])
        result = verify_answer(parsed, answer)
        assert "safety_unconfirmed" not in [g.type for g in result.gaps]

    def test_safety_flag_without_medium_word(self):
        parsed = _parsed(h2s_confirmed=True)
        answer = _answer([_comp("Задвижка")])
        result = verify_answer(parsed, answer)
        assert result.verdict == "review"
        assert "safety_unconfirmed" in [g.type for g in result.gaps]

    def test_non_safety_query_untouched(self):
        parsed = _parsed(medium="пар")
        answer = _answer([_comp("Отвод", matched=["гладкие без швов"])])
        result = verify_answer(parsed, answer)
        assert "safety_unconfirmed" not in [g.type for g in result.gaps]

    def test_no_components_no_gap(self):
        parsed = _parsed(medium="H2S", h2s_confirmed=True)
        result = verify_answer(parsed, _answer([]))
        assert "safety_unconfirmed" not in [g.type for g in result.gaps]

    def test_negative_wording_not_confirmation(self):
        parsed = _parsed(medium="H2S", h2s_confirmed=True)
        answer = _answer(
            [_comp("Отвод", detail="пригодность к H2S не подтверждена")],
            explanation="пригодность к H2S не подтверждена документами",
        )
        result = verify_answer(parsed, answer)
        assert "safety_unconfirmed" in [g.type for g in result.gaps]

    def test_explicit_positive_confirmation_closes(self):
        parsed = _parsed(medium="H2S", h2s_confirmed=True)
        answer = _answer(
            [_comp("Отвод 13ХФА", matched=["H2S-совместимость стали"])],
            explanation="",
        )
        answer2 = _answer(
            [_comp("Отвод 13ХФА")],
            explanation="Пригодность отвода к H2S подтверждена сертификатом",
        )
        assert verify_answer(parsed, answer).verdict == "pass"
        assert verify_answer(parsed, answer2).verdict == "pass"


class TestCO2Safety:
    def test_co2_medium(self):
        parsed = _parsed(medium="CO2")
        answer = _answer([_comp("Труба")])
        result = verify_answer(parsed, answer)
        assert "safety_unconfirmed" in [g.type for g in result.gaps]

    def test_co2_explicit_confirmation(self):
        parsed = _parsed(medium="CO2")
        answer = _answer(
            [_comp("Труба", detail="пригодность к CO2 подтверждена ТУ")],
        )
        assert verify_answer(parsed, answer).verdict == "pass"


class TestPolicy:
    def test_safety_is_full_llm_type(self):
        assert "safety_unconfirmed" in FULL_LLM_TYPES

    def test_safety_high_escalates_to_c2(self):
        from app.services.agent.verify.verifier import Gap

        gap = Gap(type="safety_unconfirmed", detail="x", severity="high")
        assert escalate_type([gap]) == "full_llm"
