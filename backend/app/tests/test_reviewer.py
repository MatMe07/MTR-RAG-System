import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.schemas import AgentAnswer, AgentComponent, AgentSource
from app.services.agent.reviewer import review_answer, apply_review


def _answer(**kw):
    base = dict(
        query="q",
        intent="replacement",
        answer=("Кандидаты со склада: задвижка. DN и PN: 150/40. "
                "Проверьте подтверждение H2S и материал корпуса."),
        components=[AgentComponent(mtr_code="MTR-X", status="candidate")],
        sources=[AgentSource(kind="catalog", id="c1"),
                 AgentSource(kind="stock", id="s1"),
                 AgentSource(kind="standard", id="st1"),
                 AgentSource(kind="passport_or_tu", id="p1")],
        warnings=["Пригодность к H2S нельзя подтверждать только по совпадению DN и PN."],
        human_review_required=True,
    )
    base.update(kw)
    return AgentAnswer(**base)


class ReviewerTest(unittest.TestCase):
    def test_pass_when_all_criteria_met(self):
        expected = {
            "mandatory_warning": "Пригодность к H2S нельзя подтверждать только по совпадению DN и PN.",
            "required_sources": ["catalog", "stock", "standard", "passport_or_tu"],
            "answer_must_include": ["кандидаты со склада", "DN и PN", "подтверждение H2S"],
        }
        res = review_answer(_answer(), expected=expected)
        self.assertEqual(res.verdict, "pass")
        self.assertEqual(res.issues, [])

    def test_missing_mandatory_warning_flags_review(self):
        expected = {
            "mandatory_warning": "Пригодность к H2S нельзя подтверждать только по совпадению DN и PN.",
            "required_sources": [],
            "answer_must_include": [],
        }
        res = review_answer(_answer(warnings=[]), expected=expected)
        self.assertEqual(res.verdict, "needs_review")
        self.assertTrue(any("предупреждение" in i for i in res.issues))

    def test_missing_required_sources_flags_review(self):
        expected = {
            "required_sources": ["catalog", "stock", "standard", "passport_or_tu"],
            "answer_must_include": [],
        }
        res = review_answer(_answer(sources=[AgentSource(kind="catalog", id="c1")]), expected=expected)
        self.assertEqual(res.verdict, "needs_review")
        self.assertTrue(any("источник" in i for i in res.issues))

    def test_answer_must_include_check(self):
        expected = {"answer_must_include": ["материал корпуса", "что проверить эксперту"]}
        res = review_answer(_answer(), expected=expected)
        self.assertEqual(res.verdict, "needs_review")

    def test_components_without_sources_flags_review(self):
        res = review_answer(_answer(sources=[]))
        self.assertEqual(res.verdict, "needs_review")
        self.assertTrue(any("источников" in i for i in res.issues))

    def test_expert_decision_required_for_expert_intents(self):
        res = review_answer(_answer(intent="replacement", human_review_required=False))
        self.assertTrue(any("эксперта" in i for i in res.issues))

    def test_apply_review_sets_fields(self):
        ans = apply_review(_answer(sources=[], human_review_required=False))
        self.assertEqual(ans.review_verdict, "needs_review")
        self.assertGreater(len(ans.review_issues), 0)
        self.assertTrue(ans.human_review_required)


if __name__ == "__main__":
    unittest.main()
