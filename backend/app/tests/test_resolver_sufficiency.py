# test_resolver_sufficiency.py

"""P1: top-level резолвинг CHECK_SUFFICIENCY → inventory (а не каталог).

Запрос «хватает ли ... по N штук» должен идти в склад→sufficiency,
а не в поиск по каталогу.
"""

import unittest

from app.schemas import ParsedQuery
from app.services.agent.intent.resolver import resolve_top_level_intent


def _q(**kw):
    base = dict(
        original_query="хватает ли по 2 штуки",
        operations=[],
        item_types=[],
        component_ids=[],
        unit_ids=[],
        proposed_changes={},
        technical_filters={},
        references=[],
        intents=[],
        units_count=2,
    )
    base.update(kw)
    return ParsedQuery(**base)


class ResolverSufficiencyTest(unittest.TestCase):
    def test_check_sufficiency_maps_to_inventory(self):
        parsed = _q(item_types=["труба"], intents=["CHECK_SUFFICIENCY"])
        self.assertEqual(resolve_top_level_intent(parsed), "inventory")

    def test_hybrid_parser_full_route(self):
        """«хватает ли по две штуки труб» → CHECK_SUFFICIENCY → inventory."""
        from app.services.agent.intent.detect import detect_intents, enrich_parsed
        from app.services.agent.parsing.hybrid_parser import HybridParser

        parsed = HybridParser().parse("хватает ли по две штуки труб")
        enrich_parsed(parsed)
        intents = detect_intents(parsed)
        self.assertIn("CHECK_SUFFICIENCY", intents)
        top = resolve_top_level_intent(parsed, intents=intents)
        self.assertEqual(top, "inventory")

    def test_plain_stock_still_inventory(self):
        parsed = _q(intents=["CHECK_STOCK"])
        self.assertEqual(resolve_top_level_intent(parsed), "inventory")

    def test_catalog_query_unaffected(self):
        parsed = _q(item_types=["задвижка"], intents=["FIND_BY_PARAMS"])
        self.assertEqual(resolve_top_level_intent(parsed, intents=["FIND_BY_PARAMS"]), "search")


if __name__ == "__main__":
    unittest.main()
