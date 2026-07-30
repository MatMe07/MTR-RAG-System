import json
import unittest
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
QUESTIONS_PATH = (
    REPO_ROOT / "data" / "evaluation" / "complex_questions_40.jsonl"
)


class AgentQuestionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions = [
            json.loads(line)
            for line in QUESTIONS_PATH.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]
        cls.catalog = [
            json.loads(line)
            for line in (
                REPO_ROOT
                / "data"
                / "catalog"
                / "regulated_mtr_catalog_1000.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cls.object_graph = json.loads(
            (
                REPO_ROOT
                / "data"
                / "graph"
                / "gas_pipeline_object.json"
            ).read_text(encoding="utf-8")
        )

    def test_contains_40_unique_questions(self):
        self.assertEqual(len(self.questions), 40)
        self.assertEqual(
            len({question["case_id"] for question in self.questions}),
            40,
        )
        self.assertEqual(
            {question["case_id"] for question in self.questions},
            {f"AQ{index:03d}" for index in range(1, 41)},
        )

    def test_covers_revised_user_scenarios(self):
        self.assertEqual(
            Counter(question["category"] for question in self.questions),
            {
                "replacement": 7,
                "inventory": 8,
                "toir": 5,
                "equipment_guidance": 5,
                "object_configuration": 4,
                "composite_replacement": 6,
                "impact_analysis": 3,
                "document_search": 2,
            },
        )

    def test_questions_use_plain_user_language(self):
        for question in self.questions:
            text = question["question"]
            self.assertNotIn("?", text)
            self.assertNotIn("°", text)
            self.assertNotIn("source_conflict", question["category"])
            self.assertLessEqual(len(text), 180)

    def test_all_questions_require_sources_and_human_review(self):
        for question in self.questions:
            self.assertEqual(question["expected_route"], "agent")
            self.assertTrue(question["required_tools"])
            self.assertTrue(question["required_sources"])
            self.assertTrue(question["answer_must_include"])
            self.assertTrue(question["mandatory_warning"])
            self.assertTrue(question["human_review_required"])

    def test_catalog_and_graph_targets_really_exist(self):
        ksm_codes = {
            card["codes"]["ksm_code"] for card in self.catalog
        }
        component_ids = {
            component["component_id"]
            for component in self.object_graph["components"]
        }
        unit_ids = {
            component["unit_id"]
            for component in self.object_graph["components"]
        }

        for question in self.questions:
            for target in question["target_entities"]:
                if target.startswith("KSM-SYN-REG-"):
                    self.assertIn(target, ksm_codes)
                elif target.startswith("COMP-SYN-"):
                    self.assertIn(target, component_ids)
                elif target.startswith("UNIT-SYN-"):
                    self.assertIn(target, unit_ids)


if __name__ == "__main__":
    unittest.main()
