import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = PROJECT_ROOT / "docs" / "schemas" / "item_card.schema.json"
EXAMPLES_DIR = PROJECT_ROOT / "docs" / "schemas" / "examples"


class ItemCardSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(
            cls.schema,
            format_checker=FormatChecker(),
        )

    def load_example(self, name):
        path = EXAMPLES_DIR / name
        return json.loads(path.read_text(encoding="utf-8"))

    def test_v2_examples_match_schema(self):
        example_paths = sorted(EXAMPLES_DIR.glob("item_card_v2_*.json"))
        self.assertEqual(4, len(example_paths))

        for path in example_paths:
            with self.subTest(example=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                errors = sorted(
                    self.validator.iter_errors(data),
                    key=lambda error: list(error.path),
                )
                self.assertEqual([], errors)

    def test_property_sources_reference_existing_fragments(self):
        for path in sorted(EXAMPLES_DIR.glob("item_card_v2_*.json")):
            with self.subTest(example=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                fragment_ids = {
                    source["source_fragment"]["fragment_id"]
                    for source in data["sources"]
                    if source["source_fragment"] is not None
                }
                referenced_ids = {
                    fragment_id
                    for characteristic in data["properties"].values()
                    for fragment_id in characteristic["source_fragment_ids"]
                }
                self.assertEqual(set(), referenced_ids - fragment_ids)

    def test_boolean_true_false_and_unknown_are_distinct(self):
        pipe = self.load_example("item_card_v2_pipe.json")

        self.assertIs(pipe["properties"]["inner_coating"]["value"], True)
        self.assertIs(pipe["properties"]["outer_coating"]["value"], False)
        self.assertIsNone(pipe["properties"]["h2s_confirmed"]["value"])
        self.assertEqual(
            "unknown",
            pipe["properties"]["h2s_confirmed"]["status"],
        )


if __name__ == "__main__":
    unittest.main()
