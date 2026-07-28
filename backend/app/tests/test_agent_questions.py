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

    def test_balanced_across_eight_agent_scenarios(self):
        self.assertEqual(
            Counter(question["category"] for question in self.questions),
            {
                "replacement": 5,
                "inventory": 5,
                "toir": 5,
                "source_conflict": 5,
                "object_configuration": 5,
                "composite_replacement": 5,
                "impact_analysis": 5,
                "missing_evidence": 5,
            },
        )

    def test_all_questions_require_sources_and_human_review(self):
        for question in self.questions:
            self.assertEqual(question["expected_route"], "agent")
            self.assertTrue(question["required_tools"])
            self.assertTrue(question["required_sources"])
            self.assertTrue(question["answer_must_include"])
            self.assertTrue(question["mandatory_warning"])
            self.assertTrue(question["human_review_required"])


if __name__ == "__main__":
    unittest.main()
