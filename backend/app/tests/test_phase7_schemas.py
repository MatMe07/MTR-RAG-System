import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.schemas import CatalogCard, RouterDecision
from app.services.agent.context import AgentContext
from app.services.routing.search_router import route_query_text, validate_route_decision


class CatalogCardSchemaTest(unittest.TestCase):
    """Все карточки каталога проходят Pydantic-валидацию."""

    def test_all_catalog_cards_validate(self):
        ctx = AgentContext()
        cards = ctx.catalog
        self.assertGreaterEqual(len(cards), 1)
        for card in cards:
            CatalogCard.model_validate(card)

    def test_every_card_has_card_id(self):
        ctx = AgentContext()
        for card in ctx.catalog:
            self.assertTrue(card.get("card_id"))

    def test_invalid_card_is_skipped(self):
        # Схема мягкая: без card_id карточка невалидна и не попадает в каталог.
        blank = {"item_type": "отвод", "name": "Без id"}
        with self.assertRaises(Exception):
            CatalogCard.model_validate(blank)


class RouterDecisionSchemaTest(unittest.TestCase):
    """Решения детерминированного роутера соответствуют схеме RouterDecision."""

    def test_route_query_text_matches_schema(self):
        for query in (
            "найди задвижку DN150 PN40",
            "замени отвод 90 на участке UNIT-SYN-GAS-001",
            "сколько отводов на складе и нужен ли план ремонта",
            "переход с DN150 на DN200",
            "MTR-SYN-REG-000001",
        ):
            decision = route_query_text(query)
            validated = RouterDecision.model_validate(decision)
            self.assertEqual(validated.model_dump(), decision, query)

    def test_validate_route_decision_ignores_extra_keys(self):
        decision = route_query_text("найди задвижку DN150 PN40")
        decision["parsed_query"] = {"operations": ["find"]}
        out = validate_route_decision(decision)
        self.assertEqual(out["route"], decision["route"])
        self.assertNotIn("parsed_query", out)


if __name__ == "__main__":
    unittest.main()
