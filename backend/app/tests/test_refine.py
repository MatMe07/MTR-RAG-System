# test_refine.py

"""LLM-дооформление ответа (вариант С1): refine_answer."""

import unittest

from app.schemas import AgentAnswer, AgentComponent
from app.services.agent.llm.refine import refine_answer


class _FakeLLM:
    """Мок LLMClient, возвращающий фиксированный JSON."""

    def __init__(self, payload):
        self.payload = payload

    def invoke(self, prompt):
        import json
        return json.dumps(self.payload, ensure_ascii=False)


def _answer():
    return AgentAnswer(
        query="хватает ли по 2 штуки",
        components=[AgentComponent(name="задвижка", item_type="задвижка", quantity=1)],
        answer="Список позиций",
        warnings=["Расчёт — черновик"],
    )


class RefineTest(unittest.TestCase):
    def test_refine_updates_text_keeps_components(self):
        llm = _FakeLLM({
            "answer_text": "Не хватает задвижек 2 шт.",
            "explanation": "Потребность выше остатка",
            "extra_recommendations": ["Закупить задвижки"],
            "confidence_gate": "pass",
        })
        answer = _answer()
        result = refine_answer(llm, "хватает ли по 2 штуки", answer, [
            {"type": "quantity_unmet", "detail": "x", "severity": "high"},
        ])
        self.assertIsNotNone(result)
        self.assertEqual(result.answer_text, "Не хватает задвижек 2 шт.")
        self.assertEqual(result.confidence_gate, "pass")
        self.assertEqual(result.extra_recommendations, ["Закупить задвижки"])

    def test_refine_none_when_no_llm(self):
        result = refine_answer(None, "q", _answer(), [])
        self.assertIsNone(result)

    def test_still_unclear_flag(self):
        llm = _FakeLLM({
            "answer_text": "недостаточно данных",
            "explanation": "",
            "extra_recommendations": [],
            "confidence_gate": "still_unclear",
        })
        result = refine_answer(llm, "q", _answer(), [{"type": "x"}])
        self.assertEqual(result.confidence_gate, "still_unclear")


if __name__ == "__main__":
    unittest.main()
