import unittest
from pathlib import Path
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.schemas import AgentAnswer, AgentComponent, AgentSource
from app.services.agent.llm_agent import AnswerSynthesizer, apply_llm_synthesis


def _answer(**kw):
    base = dict(
        query="q",
        intent="inventory",
        intent_label="Склад и запас",
        answer="offline text",
        mode="offline_rules",
        components=[AgentComponent(mtr_code="MTR-X", ksm_code="KSM-X", quantity=2.0)],
        warnings=["Пригодность к H2S нельзя подтверждать только по совпадению DN и PN."],
        sources=[AgentSource(kind="stock", id="s1")],
        missing_parameters=["материал корпуса"],
    )
    base.update(kw)
    return AgentAnswer(**base)


class FakeLLM:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def invoke(self, prompt):
        self.calls.append(prompt)
        return mock.Mock(content=self._text)


class AnswerSynthesizerTest(unittest.TestCase):
    def test_synthesize_uses_tool_texts(self):
        llm = FakeLLM("Связный ответ: на складе есть MTR-X, проверьте материал корпуса.")
        synth = AnswerSynthesizer(llm=llm)
        ans = _answer()
        text = synth.synthesize(ans, ["тул1: данные", "тул2: остатки"])
        self.assertIn("MTR-X", text)
        prompt = llm.calls[0]
        self.assertIn("тул1: данные", prompt)
        self.assertIn("Склад и запас", prompt)
        self.assertIn("Пригодность к H2S", prompt)

    def test_synthesize_returns_none_without_data(self):
        synth = AnswerSynthesizer(llm=FakeLLM("x"))
        ans = _answer(components=[], warnings=[], missing_parameters=[])
        self.assertIsNone(synth.synthesize(ans, []))

    def test_apply_sets_mode_llm_augmented(self):
        llm = FakeLLM("Краткий вывод по запросу.")
        ans = apply_llm_synthesis(_answer(), tool_texts=["тул"], synthesizer=AnswerSynthesizer(llm=llm))
        self.assertEqual(ans.mode, "llm_augmented")
        self.assertIn("Краткий вывод", ans.answer)

    def test_apply_keeps_offline_on_failure(self):
        class FailingLLM:
            def invoke(self, prompt):
                raise RuntimeError("no llm")

        ans = apply_llm_synthesis(_answer(), tool_texts=["тул"], synthesizer=AnswerSynthesizer(llm=FailingLLM()))
        self.assertEqual(ans.mode, "offline_rules")
        self.assertEqual(ans.answer, "offline text")


if __name__ == "__main__":
    unittest.main()
