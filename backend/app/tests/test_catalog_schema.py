import json
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.schemas import CatalogCard, RouterDecision

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog" / "regulated_mtr_catalog_1000.jsonl"


class CatalogCardSchemaTest(unittest.TestCase):
    """Фаза 7: каждая карточка каталога проходит Pydantic-схему CatalogCard."""

    @classmethod
    def setUpClass(cls):
        cls.cards = []
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    cls.cards.append(json.loads(line))

    def test_all_cards_valid(self):
        bad = []
        for i, raw in enumerate(self.cards, start=1):
            try:
                CatalogCard.model_validate(raw)
            except Exception as e:
                bad.append((i, raw.get("card_id"), str(e)[:100]))
        self.assertEqual(len(bad), 0, msg=f"Невалидные карточки: {bad[:5]}")

    def test_required_card_id(self):
        with self.assertRaises(Exception):
            CatalogCard.model_validate({"item_type": "труба"})


class RouterDecisionSchemaTest(unittest.TestCase):
    """Фаза 7: RouterDecision допускает лишние ключи (extra=ignore)."""

    def test_parses_with_extra_keys(self):
        d = RouterDecision.model_validate(
            {
                "route": "agent",
                "mode": "agent",
                "intent": "replacement",
                "intent_label": "Замена",
                "reasons": ["h2s"],
                "required_tools": ["catalog"],
                "exact_codes": ["MTR-1"],
                "parsed_query": {"dn": 150},
            }
        )
        self.assertEqual(d.route, "agent")
        self.assertEqual(d.intent, "replacement")

    def test_requires_route(self):
        with self.assertRaises(Exception):
            RouterDecision.model_validate({"intent": "replacement"})


if __name__ == "__main__":
    unittest.main()