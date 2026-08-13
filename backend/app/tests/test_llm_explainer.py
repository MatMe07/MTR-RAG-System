import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings
from app.services.llm_explainer import (
    CandidateExplanation,
    LlmExplainer,
    rule_fallback,
)


class FakeLLM:
    def __init__(self, explanation: CandidateExplanation):
        self._explanation = explanation
        self.calls = []

    def structured_invoke(self, prompt, schema):
        self.calls.append((prompt, schema))
        return self._explanation


CARD = {
    "codes": {"mtr_code": "MTR-ELB-0001", "ksm_code": "KSM-1"},
    "name": "Отвод 90",
    "item_type": "отвод",
    "properties": {
        "dn": {"value": 150},
        "angle": {"value": 90},
        "material": {"value": "09Г2С"},
        "medium_h2s": {"value": True},
    },
}


class LlmExplainerTest(unittest.TestCase):
    def tearDown(self):
        settings.AGENT_LLM_MODE = "off"

    def test_off_mode_uses_rule_fallback_without_llm(self):
        llm = FakeLLM(CandidateExplanation(mtr_code="MTR-ELB-0001", reasons=["x"]))
        result = LlmExplainer(llm=llm).explain("нужен отвод 90", CARD)
        self.assertFalse(result["llm"])
        self.assertEqual(llm.calls, [])
        self.assertIn("угол", "; ".join(result["reasons"]))

    def test_llm_reasons_are_used(self):
        with mock.patch.object(settings, "AGENT_LLM_MODE", "on"):
            llm = FakeLLM(CandidateExplanation(
                mtr_code="MTR-ELB-0001",
                reasons=["Совпадение по углу 90 и DN150", "Материал 09Г2С подходит"],
                confidence=0.9,
            ))
            result = LlmExplainer(llm=llm).explain("нужен отвод 90 DN150", CARD)
            self.assertTrue(result["llm"])
            self.assertEqual(result["mtr_code"], "MTR-ELB-0001")
            self.assertEqual(len(result["reasons"]), 2)
            self.assertEqual(result["confidence"], 0.9)

    def test_llm_failure_falls_back_to_rule(self):
        class FailingLLM:
            def structured_invoke(self, prompt, schema):
                raise RuntimeError("no llm")

        with mock.patch.object(settings, "AGENT_LLM_MODE", "on"):
            result = LlmExplainer(llm=FailingLLM()).explain("нужен отвод 90", CARD)
            self.assertFalse(result["llm"])
            self.assertIn("отвод", "; ".join(result["reasons"]))

    def test_empty_llm_reasons_falls_back(self):
        with mock.patch.object(settings, "AGENT_LLM_MODE", "on"):
            llm = FakeLLM(CandidateExplanation(mtr_code="MTR-ELB-0001", reasons=[]))
            result = LlmExplainer(llm=llm).explain("нужен отвод 90", CARD)
            self.assertFalse(result["llm"])

    def test_prompt_contains_query_and_card(self):
        with mock.patch.object(settings, "AGENT_LLM_MODE", "on"):
            llm = FakeLLM(CandidateExplanation(mtr_code="MTR-ELB-0001", reasons=["ok"]))
            LlmExplainer(llm=llm).explain("нужен отвод 90", CARD)
            prompt, schema = llm.calls[0]
            self.assertIn("нужен отвод 90", prompt)
            self.assertIn("MTR-ELB-0001", prompt)
            self.assertIs(schema, CandidateExplanation)

    def test_rule_fallback_fills_codes_and_type(self):
        result = rule_fallback(CARD)
        self.assertEqual(result["mtr_code"], "MTR-ELB-0001")
        self.assertTrue(result["reasons"])


if __name__ == "__main__":
    unittest.main()
