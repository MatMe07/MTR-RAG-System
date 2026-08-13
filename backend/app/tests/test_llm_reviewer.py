import unittest
from pathlib import Path
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.schemas import AgentAnswer, AgentComponent, AgentSource
from app.services.agents.llm_reviewer import LLMReviewer, ReviewVerdict, apply_llm_review
from app.services.agents.reviewer import review_answer


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


class FakeLLM:
    def __init__(self, verdict: ReviewVerdict):
        self._verdict = verdict
        self.calls = []

    def structured_invoke(self, prompt, schema):
        self.calls.append((prompt, schema))
        return self._verdict


class LLMReviewerTest(unittest.TestCase):
    def test_llm_pass_keeps_deterministic_pass(self):
        llm = FakeLLM(ReviewVerdict(verdict="pass", issues=[]))
        reviewer = LLMReviewer(llm=llm)
        res = reviewer.review(_answer())
        self.assertEqual(res.verdict, "pass")
        self.assertEqual(res.checks.get("llm_review"), True)

    def test_llm_issues_are_added_to_deterministic(self):
        llm = FakeLLM(ReviewVerdict(verdict="needs_review", issues=["Возможно выдуман документ."]))
        reviewer = LLMReviewer(llm=llm)
        res = reviewer.review(_answer())
        self.assertEqual(res.verdict, "needs_review")
        self.assertIn("Возможно выдуман документ.", res.issues)

    def test_llm_failure_falls_back_to_deterministic(self):
        class FailingLLM:
            def structured_invoke(self, prompt, schema):
                raise RuntimeError("no llm")

        reviewer = LLMReviewer(llm=FailingLLM())
        det = review_answer(_answer())
        res = reviewer.review(_answer())
        self.assertEqual(res.verdict, det.verdict)
        self.assertEqual(res.issues, det.issues)

    def test_apply_llm_review_sets_fields_and_flags(self):
        llm = FakeLLM(ReviewVerdict(verdict="needs_review", issues=["Проверьте материал корпуса."]))
        ans = apply_llm_review(_answer(), reviewer=LLMReviewer(llm=llm))
        self.assertEqual(ans.review_verdict, "needs_review")
        self.assertIn("Проверьте материал корпуса.", ans.review_issues)
        self.assertTrue(ans.human_review_required)

    def test_llm_review_prompt_contains_answer_json(self):
        llm = FakeLLM(ReviewVerdict(verdict="pass", issues=[]))
        LLMReviewer(llm=llm).review(_answer())
        prompt, schema = llm.calls[0]
        self.assertIn("Кандидаты со склада", prompt)
        self.assertIn("задвижка", prompt)
        self.assertIs(schema, ReviewVerdict)


if __name__ == "__main__":
    unittest.main()
