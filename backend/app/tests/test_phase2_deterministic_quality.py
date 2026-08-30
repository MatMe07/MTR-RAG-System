# test_phase2_deterministic_quality.py

"""Фаза 2: качество детерминированного пути.

Точечный код-поиск (FIND_BY_CODE), сужение ADD_COMPONENT-таргета,
детекция смены среды (H2S/CO2), эскалация на экспертную проверку,
комплекты по графу, честный скоринг (без параметров — не «соответствует»),
пропагация review_required/sources в LangGraph и корректный отказ
search_by_passport при пустом паспорте.
"""

import os
import unittest

os.environ.setdefault("AGENT_STORAGE", "json")
os.environ.setdefault("AGENT_LLM_MODE", "off")

import logging

logging.disable(logging.CRITICAL)

from app.schemas import AgentComponent
from app.services.agent.executor import AgentExecutor
from app.services.agent.parsing.hybrid_parser import HybridParser
from app.services.agent.intent.detect import enrich_parsed
from app.services.agent.repository.json_repository import JsonRepository
from app.services.agent.answer.status import STATUS_EXPERT, STATUS_MATCH, determine_status
from app.services.agent.tools.core_tools import _match_score, _parsed_codes, catalog_search
from app.services.agent.tools.analytic_tools import impact_analyzer, maintenance_planner
from app.services.agent.parsing.parsers.item_type_parser import narrow_add_target_types


def _parse(text: str):
    p = HybridParser().parse(text)
    enrich_parsed(p)
    return p


class FindByCodeTest(unittest.TestCase):
    def test_parsed_codes_extracts_codes(self):
        p = _parse("найди деталь по коду KSM-SYN-REG-000003 и MTR-X")
        self.assertEqual(_parsed_codes(p), ["KSM-SYN-REG-000003", "MTR-X"])

    def test_code_search_narrows_to_single_card(self):
        ctx = JsonRepository()
        p = _parse("найди деталь по коду KSM-SYN-REG-000003")
        r = catalog_search({"parsed": p}, ctx)
        self.assertEqual(len(r["components"]), 1)
        self.assertEqual(r["components"][0]["ksm_code"], "KSM-SYN-REG-000003")
        self.assertEqual(r["components"][0]["match_score"], 1.0)

    def test_code_search_keeps_match_status(self):
        ex = AgentExecutor()
        a = ex.execute("найди деталь по коду KSM-SYN-REG-000003", mode="deterministic")
        self.assertEqual(a.status, STATUS_MATCH)


class AddComponentNarrowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.query = "В схеме есть труба, отвод, переход, заглушка и тройник, добавь деталь для перекрытия потока"

    def test_narrow_drops_pre_marker_types(self):
        types = ["труба", "отвод", "переход", "заглушка", "тройник"]
        self.assertEqual(narrow_add_target_types(self.query, types), ["задвижка"])

    def test_narrow_keeps_plain_add(self):
        self.assertEqual(narrow_add_target_types("добавь задвижку DN100", ["задвижка"]), ["задвижка"])

    def test_narrow_without_marker_unchanged(self):
        self.assertEqual(narrow_add_target_types("нужна задвижка", ["задвижка"]), ["задвижка"])

    def test_catalog_search_uses_narrowed_type(self):
        ctx = JsonRepository()
        p = _parse(self.query)
        self.assertIn("ADD_COMPONENT", p.intents)
        r = catalog_search({"parsed": p}, ctx)
        self.assertTrue(r["components"])
        self.assertEqual(p.item_types, ["задвижка"])
        self.assertTrue(all(c["item_type"] == "задвижка" for c in r["components"]))


class MediumChangeDetectionTest(unittest.TestCase):
    def test_medium_to_h2s(self):
        p = _parse("влияние замены среды на сероводород на участке")
        self.assertEqual(p.proposed_changes.get("medium"), "H2S")

    def test_medium_to_co2(self):
        p = _parse("перевод участка на co2")
        self.assertEqual(p.proposed_changes.get("medium"), "CO2")

    def test_h2s_in_search_is_not_change(self):
        p = _parse("нужна задвижка KSM-SYN-REG-000003 100мм H2S")
        self.assertEqual(p.proposed_changes.get("medium"), None)

    def test_replace_type_is_not_change(self):
        p = _parse("замени вентиль на задвижку DN100")
        self.assertEqual(p.proposed_changes, {})


class EscalationTest(unittest.TestCase):
    @staticmethod
    def _component():
        return [AgentComponent(ksm_code="KSM-X", name="деталь", status="затронуто")]

    @staticmethod
    def _parsed_h2s():
        p = _parse("влияние замены среды на сероводород на участке")
        p.technical_filters = {"medium": "H2S"}
        p.proposed_changes = {"medium": "H2S"}
        return p

    def test_impact_h2s_expert(self):
        self.assertEqual(
            determine_status(self._component(), [], parsed=self._parsed_h2s(), intent="impact_analysis"),
            STATUS_EXPERT,
        )

    def test_maintenance_h2s_expert(self):
        self.assertEqual(
            determine_status(self._component(), [], parsed=self._parsed_h2s(), intent="maintenance"),
            STATUS_EXPERT,
        )

    def test_search_h2s_no_escalation(self):
        self.assertNotEqual(
            determine_status(self._component(), [], parsed=self._parsed_h2s(), intent="search"),
            STATUS_EXPERT,
        )

    def test_impact_no_medium_no_escalation(self):
        p = _parse("влияние DN")
        self.assertNotEqual(
            determine_status(self._component(), [], parsed=p, intent="impact_analysis"),
            STATUS_EXPERT,
        )


class KitQualityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ctx = JsonRepository()
        p = _parse("покажи COMP-SYN-001")
        cls.parsed = p
        cls.ctx = ctx

    def _state_with_targets(self):
        from app.services.agent.tools.core_tools import graph_search

        state = {"parsed": self.parsed, "ksm_targets": [], "context": {"repository": self.ctx}}
        graph_search(state, self.ctx)
        self.assertTrue(state.get("ksm_targets"))
        return {"parsed": self.parsed, "ksm_targets": state["ksm_targets"], "context": {"repository": self.ctx}}

    def test_maintenance_kit_has_consumables_and_sources(self):
        r = maintenance_planner(self._state_with_targets())
        self.assertTrue(r["review"])
        statuses = [c["status"] for c in r["components"]]
        self.assertTrue(any("комплект" in s for s in statuses))
        self.assertTrue(any(c["name"] and "Расходные" in c["name"] for c in r["components"]))
        self.assertTrue(any(c.get("source_id") for c in r["components"]))

    def test_impact_review_and_graph_sources(self):
        r = impact_analyzer(self._state_with_targets())
        self.assertTrue(r["review"])
        self.assertTrue(any(c.get("source_id") for c in r["components"]))

    def test_impact_h2s_warning(self):
        parsed = self.parsed
        parsed.proposed_changes = {"medium": "H2S"}
        r = impact_analyzer(self._state_with_targets())
        self.assertTrue(any("H2S" in str(c.get("detail") or "") for c in r["components"]))


class MatchScoreHonestyTest(unittest.TestCase):
    def test_item_type_only_is_none(self):
        ctx = JsonRepository()
        card = next(c for c in ctx.get_catalog() if c.get("item_type") == "отвод")
        p = _parse("сломался отвод COMP-SYN-008, полный комплект замены")
        self.assertIsNone(_match_score(card, p))

    def test_params_give_score(self):
        ctx = JsonRepository()
        card = next(c for c in ctx.get_catalog() if c.get("item_type") == "отвод")
        p = _parse("подбери отвод 90 на DN159")
        self.assertIsNotNone(_match_score(card, p))
        self.assertLess(_match_score(card, p), 1.0)


class LangGraphChannelsTest(unittest.TestCase):
    def test_review_required_reaches_answer(self):
        ex = AgentExecutor()
        a = ex.execute(
            "У меня сломался отвод COMP-SYN-008, составь полный комплект замены и план работ",
            mode="deterministic",
        )
        self.assertEqual(a.intent, "maintenance")
        self.assertTrue(a.human_review_required)
        self.assertTrue(a.sources)
        self.assertIn(a.status, ("требует проверки", "требует экспертной проверки"))


class PassportSearchTest(unittest.TestCase):
    def test_blank_passport_is_not_found_not_zero_match(self):
        from app.services.agent.tools.instruments import run_instrument

        r = run_instrument("search_by_passport", {"document_id": "passport_blank", "limit": 5})
        self.assertIsNotNone(r["error"])
        self.assertEqual(r["error"]["code"], "NOT_FOUND")
        self.assertEqual(r["result"], None)


if __name__ == "__main__":
    unittest.main()