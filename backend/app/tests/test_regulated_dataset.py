import csv
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.scripts.GEN.generate_regulated_dataset import (
    DEFAULT_REGULATION,
    generate_regulated_dataset,
    iter_cards,
    load_regulation,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


class RegulatedDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.regulation = load_regulation(DEFAULT_REGULATION)
        cls.cards = list(iter_cards(cls.regulation))

    def test_regulation_uses_official_sources_and_current_pipe_standards(self):
        sources = {
            source["source_id"]: source
            for source in self.regulation["sources"]
        }
        self.assertEqual(
            sources["RST-GOST-8732-2025"]["status"],
            "Действует",
        )
        self.assertEqual(
            sources["RST-GOST-8732-2025"]["replaces"],
            "ГОСТ 8732-78",
        )
        for source_id, source in sources.items():
            if source_id.startswith("RST-"):
                self.assertTrue(
                    source["official_url"].startswith(
                        "https://protect.gost.ru/"
                    )
                )

    def test_catalog_has_exactly_1000_unique_synthetic_cards(self):
        self.assertEqual(len(self.cards), 1_000)
        self.assertEqual(
            len({card["card_id"] for card in self.cards}),
            1_000,
        )
        self.assertEqual(
            len({card["codes"]["mtr_code"] for card in self.cards}),
            1_000,
        )
        self.assertEqual(
            len({card["codes"]["ksm_code"] for card in self.cards}),
            1_000,
        )
        self.assertTrue(
            all(
                card["codes"]["ksm_code"].startswith("KSM-SYN-REG-")
                for card in self.cards
            )
        )
        self.assertTrue(
            all(
                card["properties"]["synthetic"]["value"] is True
                for card in self.cards
            )
        )
        self.assertTrue(
            all(
                card["properties"]["conformity_status"]["value"]
                == "synthetic_not_certified"
                for card in self.cards
            )
        )

    def test_catalog_covers_required_classes_and_mediums(self):
        self.assertEqual(
            {card["item_type"] for card in self.cards},
            {
                "труба",
                "отвод",
                "переход",
                "задвижка",
                "заглушка",
                "тройник",
            },
        )
        self.assertEqual(
            {
                card["properties"]["medium_code"]["value"]
                for card in self.cards
            },
            {
                "natural_gas",
                "gas_h2s",
                "gas_co2",
                "gas_h2s_co2",
                "oil",
                "process_water",
                "corrosive_medium",
            },
        )

    def test_dn_is_not_confused_with_outer_diameter(self):
        elbow = next(
            card
            for card in self.cards
            if card["item_type"] == "отвод"
            and card["properties"]["outer_diameter"]["value"] == 159
        )
        self.assertEqual(elbow["properties"]["dn"]["value"], 150)
        self.assertNotEqual(
            elbow["properties"]["dn"]["value"],
            elbow["properties"]["outer_diameter"]["value"],
        )

    def test_subtypes_are_consistent_with_structural_properties(self):
        for card in self.cards:
            if card["item_type"] == "труба":
                weld_type = card["properties"]["weld_type"]["value"]
                if "бесшовная" in card["subtype"]:
                    self.assertEqual(weld_type, "нет")
                elif "прямошовная" in card["subtype"]:
                    self.assertEqual(weld_type, "прямой шов")
                else:
                    self.assertEqual(weld_type, "спиральный шов")
            if card["item_type"] == "тройник":
                main = card["properties"]["outer_diameter_main"]["value"]
                branch = card["properties"]["outer_diameter_branch"]["value"]
                self.assertEqual(
                    main == branch,
                    card["subtype"] == "равнопроходной",
                )

    def test_each_card_points_to_known_regulation_rule_and_standard(self):
        rule_ids = {
            rule["rule_id"] for rule in self.regulation["class_rules"]
        }
        standard_source_ids = {
            source["source_id"]
            for source in self.regulation["sources"]
            if source["source_type"] == "official_standard_card"
        }
        for card in self.cards:
            self.assertIn(
                card["properties"]["regulation_rule_id"]["value"],
                rule_ids,
            )
            standard_sources = {
                source["source_id"]
                for source in card["sources"]
                if source["type"] == "standard"
            }
            self.assertTrue(standard_sources)
            self.assertTrue(standard_sources.issubset(standard_source_ids))

    def test_cards_keep_backend_search_contract(self):
        for card in self.cards:
            properties = card["properties"]
            self.assertIn("pn", properties)
            self.assertIn("gost_tu", properties)
            self.assertIn("h2s_confirmed", properties)
            self.assertIn("co2_confirmed", properties)
            self.assertIsNone(properties["h2s_confirmed"]["value"])
            self.assertIsNone(properties["co2_confirmed"]["value"])
            self.assertEqual(
                properties["gost_tu"]["value"],
                properties["standard"]["value"],
            )

    def test_all_cards_validate_against_item_card_v2(self):
        schema = json.loads(
            (REPO_ROOT / "docs/schemas/item_card.schema.json").read_text(
                encoding="utf-8"
            )
        )
        validator = Draft202012Validator(schema)
        for card in self.cards:
            validator.validate(card)

    def test_generator_writes_catalog_and_linked_object(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            catalog_jsonl = root / "catalog.jsonl"
            catalog_csv = root / "catalog.csv"
            object_output = root / "object.json"
            relations_output = root / "relations.csv"
            summary = generate_regulated_dataset(
                catalog_jsonl=catalog_jsonl,
                catalog_csv=catalog_csv,
                object_output=object_output,
                relations_output=relations_output,
            )
            graph = json.loads(object_output.read_text(encoding="utf-8"))
            with relations_output.open(
                "r", encoding="utf-8-sig", newline=""
            ) as file:
                relations = list(csv.DictReader(file, delimiter=";"))

        self.assertEqual(summary["catalog_count"], 1_000)
        self.assertEqual(len(graph["components"]), 42)
        self.assertEqual(len(relations), 126)
        card_ids = {card["card_id"] for card in self.cards}
        self.assertTrue(
            all(
                component["installed_card_id"] in card_ids
                for component in graph["components"]
            )
        )
        self.assertTrue(graph["synthetic"])


if __name__ == "__main__":
    unittest.main()
