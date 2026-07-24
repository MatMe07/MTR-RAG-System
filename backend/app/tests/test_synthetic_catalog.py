import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from app.scripts.generate_synthetic_catalog import (
    DEFAULT_CONFIG,
    calculate_allocations,
    generate_catalog,
    load_config,
)


class SyntheticCatalogTest(unittest.TestCase):
    def test_million_distribution_has_exact_total(self):
        config = load_config(DEFAULT_CONFIG)
        allocations = calculate_allocations(config, 1_000_000)

        self.assertEqual(sum(allocations.values()), 1_000_000)
        self.assertEqual(allocations["pipes"], 260_000)
        self.assertEqual(allocations["elbows"], 300_000)
        self.assertEqual(allocations["reducers"], 160_000)
        self.assertEqual(allocations["valves"], 180_000)
        self.assertEqual(allocations["plugs"], 100_000)

    def test_small_catalog_is_unique_and_preserves_dynamic_properties(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "catalog.jsonl"
            summary = generate_catalog(output, count=500, seed=42)
            cards = [
                json.loads(line)
                for line in output.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(summary["count"], 500)
        self.assertEqual(len(cards), 500)
        self.assertEqual(len({card["card_id"] for card in cards}), 500)
        self.assertEqual(
            len({card["codes"]["mtr_code"] for card in cards}),
            500,
        )
        self.assertEqual(
            len({card["codes"]["ksm_code"] for card in cards}),
            500,
        )

        by_type = {card["item_type"]: card for card in cards}
        self.assertIn("dn", by_type["труба"]["properties"])
        self.assertIn("angle", by_type["отвод"]["properties"])
        self.assertIn("d1", by_type["переход"]["properties"])
        self.assertIn("d2", by_type["переход"]["properties"])
        self.assertIn("drive_type", by_type["задвижка"]["properties"])
        self.assertIn("dn", by_type["заглушка"]["properties"])

        schema_path = Path(__file__).resolve().parents[3] / "docs/schemas/item_card.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for card in by_type.values():
            validator.validate(card)

        coating_values = [
            card["properties"]["inner_coating"]["value"]
            for card in cards
        ]
        self.assertIn(False, coating_values)
        self.assertIn(None, coating_values)


if __name__ == "__main__":
    unittest.main()
