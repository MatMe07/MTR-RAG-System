# test_answer_tz.py

"""Фаза B (ЭТАП 5): ТЗ-статусы, детерминация статуса, результаты ТЗ 11.2.

Покрывает 5A.2 StatusDeterminator, 5A.3 ExplanationGenerator, 5A.4 SourceFormatter,
5B структуру results.
"""

import unittest

from app.schemas import (
    AgentAnswer,
    AgentComponent,
    AgentSource,
    ParsedQuery,
)

from app.services.agent.answer.status import (
    STATUS_MATCH,
    STATUS_ANALOG,
    STATUS_MISMATCH,
    STATUS_NOT_FOUND,
    STATUS_UNCLEAR,
    STATUS_EXPERT,
    determine_status,
    candidate_tz_status,
    evaluate_candidate,
    build_recommendations,
    format_sources,
)
from app.services.agent.answer.explanation import (
    build_explanation,
    build_explanation_prompt,
    default_generator,
    should_use_llm,
    ExplanationGenerator,
)
from app.services.agent.answer.builder import AnswerBuilder
from app.services.agent.answer.tz_result import (
    build_tz_result_items,
    component_to_tz_result,
)


def _parsed(**kwargs):
    return ParsedQuery(original_query=kwargs.get("query", "Испытать задвижку"))


def _comp(score=0.9, percent=None, matched=None, mismatched=None, missing=None):
    return AgentComponent(
        ksm_code="KSM-1",
        mtr_code="MTR-1",
        name="Задвижка",
        item_type="задвижка",
        quantity=12.0,
        match_score=score,
        match_percent=percent,
        matched_params=matched or ["DN", "среда"],
        mismatched_params=mismatched or ["стандарт"],
        missing_params=missing or ["покрытие"],
        tz_status=candidate_tz_status(percent if percent is not None else score * 100),
    )


class CandidateTzStatusTest(unittest.TestCase):
    def test_match(self):
        self.assertEqual(candidate_tz_status(95), STATUS_MATCH)

    def test_analog(self):
        self.assertEqual(candidate_tz_status(80), STATUS_ANALOG)

    def test_mismatch(self):
        self.assertEqual(candidate_tz_status(50), STATUS_MISMATCH)


class StatusDeterminatorTest(unittest.TestCase):
    def test_match_no_warnings(self):
        self.assertEqual(
            determine_status([AgentComponent(match_score=0.96)], []),
            STATUS_MATCH,
        )

    def test_analog(self):
        self.assertEqual(
            determine_status([AgentComponent(match_score=0.8)], []),
            STATUS_ANALOG,
        )

    def test_mismatch_low_score(self):
        self.assertEqual(
            determine_status([AgentComponent(match_score=0.5)], []),
            STATUS_MISMATCH,
        )

    def test_not_found_when_request(self):
        self.assertEqual(determine_status([], [], has_request=True), STATUS_NOT_FOUND)

    def test_unclear_without_request(self):
        self.assertEqual(determine_status([], [], has_request=False), STATUS_UNCLEAR)

    def test_expert_on_critical_warning(self):
        self.assertEqual(
            determine_status(
                [AgentComponent(match_score=0.9)],
                ["Недостаточно данных по среде H2S"],
            ),
            STATUS_EXPERT,
        )

    def test_no_expert_on_generic_disclaimer(self):
        self.assertEqual(
            determine_status(
                [AgentComponent(match_score=0.96)],
                [
                    "ГОСТ не присваивает внутренний код КСМ.",
                    "Соответствие H2S нельзя подтверждать только ГОСТом: "
                    "нужны паспорт, ТУ, проектная документация.",
                ],
            ),
            STATUS_MATCH,
        )

    def test_analog_kept_on_noncritical_warning(self):
        self.assertEqual(
            determine_status(
                [AgentComponent(match_score=0.8)],
                ["Нестандартный тип присоединения"],
            ),
            STATUS_ANALOG,
        )

    def test_expert_on_stop_error(self):
        self.assertEqual(
            determine_status(
                [AgentComponent(match_score=0.9)],
                [],
                errors=[{"code": "STOP_NEED_REVIEW"}],
            ),
            STATUS_EXPERT,
        )

    def test_unclear_on_invalid_params(self):
        self.assertEqual(
            determine_status([], [], errors=["INVALID_PARAMS"], has_request=True),
            STATUS_UNCLEAR,
        )


class EvaluateCandidateTest(unittest.TestCase):
    def _card(self, props, item_type="задвижка"):
        return {"item_type": item_type, "properties": props}

    def test_matched_mismatched_missing(self):
        card = self._card(
            {
                "dn": {"value": 150},
                "pn": {"value": 40},
            }
        )
        parsed = _parsed()
        parsed.technical_filters = {"dn": 150, "pn": 25, "medium": "H2S"}
        parsed.item_types = ["задвижка"]
        matched, mismatched, missing = evaluate_candidate(card, parsed)
        self.assertIn("DN", matched)
        self.assertIn("тип изделия", matched)
        self.assertIn("PN", mismatched)
        self.assertIn("среда", missing)

    def test_numeric_tolerance(self):
        card = self._card({"dn": {"value": 156.0}})
        parsed = _parsed()
        parsed.technical_filters = {"dn": 150}
        matched, mismatched, _ = evaluate_candidate(card, parsed)
        self.assertIn("DN", matched)


class ExplanationTest(unittest.TestCase):
    def test_match_explanation(self):
        text = build_explanation(STATUS_MATCH, matched=["DN"], mismatched=[], missing=[])
        self.assertIn("Совпали все критические параметры", text)

    def test_analog_explanation_lists_params(self):
        text = build_explanation(
            STATUS_ANALOG,
            matched=["DN"],
            mismatched=["стандарт"],
            missing=["покрытие"],
        )
        self.assertIn("расхождение", text.lower())
        self.assertIn("стандарт", text)

    def test_not_found_explanation(self):
        self.assertIn("нет подходящих", build_explanation(STATUS_NOT_FOUND))


class ExplanationGeneratorLlmTest(unittest.TestCase):
    """5A.3 LLM-режим: триггеры, fallback, инъекция генератора, builder-wiring."""

    _COMP = _comp(score=0.8, percent=80)

    def _gen(self, calls, text="Инженерное объяснение"):
        def generator(context):
            calls.append(context)
            return text
        return generator

    def test_explanation_generator_llm(self):
        calls = []
        gen = ExplanationGenerator(generator=self._gen(calls))
        text = gen.generate(
            status=STATUS_UNCLEAR,
            query="Нужен уголок 30",
            components=[self._COMP],
            warnings=["Неоднозначный параметр"],
        )
        self.assertEqual(text, "Инженерное объяснение")
        self.assertEqual(len(calls), 1)
        ctx = calls[0]
        self.assertIn("Нужен уголок 30", ctx["query"])
        self.assertIn("DN", ctx["critical_params"])
        self.assertIn("Задвижка", ctx["candidates"])

    def test_no_trigger_for_header_status(self):
        calls = []
        gen = ExplanationGenerator(generator=self._gen(calls))
        text = gen.generate(status=STATUS_MATCH, query="Найди задвижку DN150")
        self.assertIsNone(text)
        self.assertEqual(calls, [])

    def test_trigger_by_explain_marker(self):
        calls = []
        gen = ExplanationGenerator(generator=self._gen(calls))
        text = gen.generate(status=STATUS_MATCH, query="Объясни, что значит DN")
        self.assertEqual(text, "Инженерное объяснение")
        self.assertEqual(len(calls), 1)

    def test_trigger_by_difference_marker(self):
        self.assertTrue(should_use_llm(STATUS_MATCH, "Чем отличается переход от отвода?"))
        self.assertFalse(should_use_llm(STATUS_MATCH, "Подбери отвод 90 на DN159"))
        self.assertTrue(should_use_llm(STATUS_EXPERT, "Подбери отвод"))

    def test_generator_exception_falls_back(self):
        def boom(context):
            raise RuntimeError("llm down")
        gen = ExplanationGenerator(generator=boom)
        self.assertIsNone(gen.generate(status=STATUS_UNCLEAR, query="эй"))

    def test_prompt_contains_critical_params_and_requirements(self):
        prompt = build_explanation_prompt(
            {
                "query": "замена задвижки для H2S",
                "critical_params": ["PN", "среда"],
                "candidates": "- Задвижка: 80%",
                "compatibility": "Совпало: DN",
                "warnings": ["H2S не подтверждён"],
                "errors": [],
            }
        )
        self.assertIn("Критические параметры", prompt)
        self.assertIn("PN", prompt)
        self.assertIn("не совпал", prompt)

    def test_default_generator_off_without_key(self):
        import os
        saved = {
            "OPENROUTER_API_KEY": os.environ.pop("OPENROUTER_API_KEY", None),
            "LLM_API_KEY": os.environ.pop("LLM_API_KEY", None),
        }
        try:
            gen = ExplanationGenerator()
            self.assertIsNone(gen.generate(status=STATUS_UNCLEAR, query="эй"))
            self.assertIsNone(default_generator({}))
        finally:
            for k, v in saved.items():
                if v is not None:
                    os.environ[k] = v

    def test_builder_wiring_llm_explanation(self):
        gen = self._gen([])
        result = {
            "components": [],
            "warnings": ["Недостаточно данных"],
            "sources": [],
            "missing": [],
            "review": False,
            "answers": ["Уточните параметры"],
            "tools_used": ["search_catalog"],
        }
        answer = AnswerBuilder(generator=gen).build(
            _parsed(query="Нужен уголок 30"), "search", result
        )
        self.assertEqual(answer.status, STATUS_UNCLEAR)
        self.assertEqual(answer.explanation, "Инженерное объяснение")

    def test_builder_wiring_no_explanation_on_header(self):
        result = {
            "components": [{"match_score": 0.96, "match_percent": 96, "name": "Задвижка"}],
            "warnings": [],
            "sources": [],
            "missing": [],
            "review": False,
            "answers": ["Найдено 1 позиций"],
            "tools_used": ["search_catalog"],
        }
        answer = AnswerBuilder(generator=self._gen([])).build(
            _parsed(query="Найди задвижку DN150"), "search", result
        )
        self.assertEqual(answer.status, STATUS_MATCH)
        self.assertIsNone(answer.explanation)


class SourceFormatterTest(unittest.TestCase):
    def test_format_sources(self):
        srcs = [
            AgentSource(kind="catalog", id="card_1", fragment="карточка"),
            AgentSource(kind="passport", id="doc_1", fragment="стр.2"),
            AgentSource(kind="lnd", id="лнд-7", fragment="раздел 4"),
        ]
        items = format_sources(srcs)
        by_type = {i["type"]: i for i in items}
        self.assertEqual(by_type["excel"]["row"], "card_1")
        self.assertEqual(by_type["passport"]["document_id"], "doc_1")
        self.assertEqual(by_type["lnd"]["lnd_section"], "лнд-7")


class TzResultTest(unittest.TestCase):
    def test_component_to_tz_result(self):
        item = component_to_tz_result(_comp(percent=94))
        self.assertEqual(item["match_percent"], 94)
        self.assertEqual(item["status"], STATUS_ANALOG)
        self.assertIn("matched_params", item)
        self.assertIn("mismatched_params", item)
        self.assertIn("missing_params", item)
        self.assertIn("explanation", item)
        self.assertEqual(item["stock"]["quantity"], 12.0)

    def test_build_tz_result_items(self):
        answer = AgentAnswer(
            query="Тест",
            components=[_comp(0.9)],
            sources=[AgentSource(kind="catalog", id="c1", fragment="карточка")],
        )
        items = build_tz_result_items(answer)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["sources"][0]["type"], "excel")
        self.assertIn("explanation", item)


class RecommendationsTest(unittest.TestCase):
    def test_recommendations_for_statuses(self):
        self.assertTrue(build_recommendations(STATUS_NOT_FOUND, [], []))
        self.assertTrue(build_recommendations(STATUS_EXPERT, [], []))
        self.assertTrue(build_recommendations(STATUS_UNCLEAR, [], []))


if __name__ == "__main__":
    unittest.main()