# tests/test_sufficiency_parsing.py
"""«по N штук» → parsed.quantity → units_count → CHECK_SUFFICIENCY (план §7.1)."""

from app.services.agent.parsing.hybrid_parser import HybridParser
from app.services.agent.intent.detect import enrich_parsed


class TestSufficiencyParsing:
    def test_units_count_from_quantity_words(self):
        p = HybridParser().parse("хватает ли труб по две штуки")
        enrich_parsed(p)
        assert p.quantity == 2, p.quantity
        assert p.units_count == 2, p.units_count
        assert "CHECK_SUFFICIENCY" in p.intents, p.intents

    def test_units_count_from_quantity_digits(self):
        p = HybridParser().parse("проверь достаточность задвижек по 3 штуки")
        enrich_parsed(p)
        assert p.units_count == 3, p.units_count
        assert "CHECK_SUFFICIENCY" in p.intents, p.intents

    def test_no_quantity_for_plain_query(self):
        p = HybridParser().parse("найди задвижку DN100")
        enrich_parsed(p)
        assert p.units_count is None
        assert "CHECK_SUFFICIENCY" not in p.intents

    def test_check_sufficiency_intent_after_enrich(self):
        p = HybridParser().parse("хватает ли по 5 штук отводов на складе")
        enrich_parsed(p)
        assert p.quantity == 5
        assert p.units_count == 5
        assert "CHECK_SUFFICIENCY" in p.intents
