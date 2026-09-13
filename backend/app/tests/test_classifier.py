# test_classifier.py

"""Фаза 1, §1A: групповая классификация (GroupClassifier)."""

import unittest

from app.services.agent.parsing.classifier import (
    GroupClassifier,
    reset_group_classifier,
)


class _FakeRules:
    """DynamicRules-заглушка: БД недоступна → только дефолты кода."""

    def get_keywords(self, group, limit=None):
        return []

    def get_overrides(self):
        return []


class ClassifierTest(unittest.TestCase):
    def setUp(self):
        reset_group_classifier()
        self.cls = GroupClassifier(rules=_FakeRules())

    def test_search_words(self):
        r = self.cls.classify("Найди задвижку DN150")
        self.assertEqual(r["status"], "DETERMINED")
        self.assertEqual(r["top_group"], "ПОИСК")
        self.assertGreaterEqual(r["confidence"], 0.7)

    def test_stock_words(self):
        r = self.cls.classify("Проверь наличие и остатки на складе")
        self.assertEqual(r["top_group"], "СКЛАД")

    def test_documents_words(self):
        r = self.cls.classify("Найди паспорт для COMP-SYN-010")
        self.assertEqual(r["top_group"], "ДОКУМЕНТЫ")

    def test_documents_tu_reference(self):
        r = self.cls.classify("какой ТУ 14-3-1234 применяется для отвода?")
        self.assertEqual(r["top_group"], "ДОКУМЕНТЫ")

    def test_replace_analog(self):
        r = self.cls.classify("Подбери замену задвижке DN150")
        self.assertEqual(r["top_group"], "ЗАМЕНА")

    def test_dn_to_dn_override(self):
        r = self.cls.classify("Замени DN150 на DN200")
        self.assertEqual(r["top_group"], "ЗАМЕНА")

    def test_broken_and_replace_goes_repair(self):
        r = self.cls.classify("Сломался отвод, замени его")
        self.assertEqual(r["top_group"], "РЕМОНТ")

    def test_empty_query_unclear(self):
        r = self.cls.classify("")
        self.assertEqual(r["status"], "UNCLEAR")
        self.assertIsNone(r["top_group"])

    def test_groups_shape(self):
        r = self.cls.classify("Найди задвижку DN150")
        self.assertTrue(r["groups"])
        for g in r["groups"]:
            self.assertIn("group", g)
            self.assertIn("score", g)
            self.assertIn("confidence", g)
            self.assertIn("matched", g)

    def test_llm_fallback_on_tie(self):
        cls = GroupClassifier(rules=_FakeRules(), llm=lambda text: "ЗАМЕНА")
        r = cls.classify("найди аналог")  # ПОИСК=1 (найди) vs ЗАМЕНА=1 (аналог)
        self.assertEqual(r["status"], "DETERMINED")
        self.assertEqual(r["top_group"], "ЗАМЕНА")
        self.assertTrue(r.get("llm_fallback"))

    def test_tie_without_llm_unclear(self):
        r = self.cls.classify("найди аналог")
        self.assertEqual(r["status"], "UNCLEAR")


class EnrichGroupsTest(unittest.TestCase):
    def test_enrich_parsed_fills_groups(self):
        from app.schemas import ParsedQuery
        from app.services.agent.intent.detect import enrich_parsed

        p = ParsedQuery(
            original_query="Найди задвижку DN150",
            operations=[],
            item_types=["задвижка"],
            component_ids=[],
            unit_ids=[],
            proposed_changes={},
            technical_filters={"dn": 150.0},
            references=[],
            limit=None,
            on_stock=None,
            not_installed=None,
        )
        enrich_parsed(p)
        self.assertTrue(p.groups)
        self.assertEqual(p.groups[0]["group"], "ПОИСК")


if __name__ == "__main__":
    unittest.main()
