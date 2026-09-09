"""Справочный маршрут (5.2): equipment_guidance без объектного контекста.

Ожидание: catalog_search → regulation_lookup (ровно 2 инструмента), источники
catalog + standard, review pass. Запросы с объектным контекстом (граф/склад)
остаются на тяжёлом маршруте.
"""
import json
import os
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.agent.executor import execute_agent_query

_REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_FILE = _REPO_ROOT / "data" / "evaluation" / "complex_questions_40.jsonl"

REFERENCE_CASES = ("AQ021", "AQ022", "AQ024", "AQ025")
OBJECT_CASES = ("AQ023",)


def _load_cases():
    with open(DATA_FILE, encoding="utf-8") as fh:
        return {c["case_id"]: c for c in (json.loads(l) for l in fh if l.strip())}


class TestReferenceRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _load_cases()
        cls.ref_answers = {
            cid: execute_agent_query(cls.cases[cid]["question"])
            for cid in REFERENCE_CASES
        }

    def test_reference_uses_exactly_two_tools(self):
        for cid, answer in self.ref_answers.items():
            self.assertEqual(
                set(answer.tools_used),
                {"catalog_search", "regulation_lookup"},
                f"{cid}: инструменты должны быть ровно catalog+regulation",
            )

    def test_reference_has_catalog_and_standard_sources(self):
        for cid, answer in self.ref_answers.items():
            kinds = {s.kind for s in answer.sources}
            self.assertTrue(
                {"catalog", "standard"}.issubset(kinds),
                f"{cid}: источники {kinds} не содержат catalog+standard",
            )

    def test_reference_pass_review_and_non_empty(self):
        for cid, answer in self.ref_answers.items():
            self.assertEqual(answer.review_verdict, "pass", cid)
            self.assertTrue(answer.explanation and answer.explanation.strip(), cid)

    def test_object_context_stays_heavy(self):
        case = self.cases["AQ023"]
        answer = execute_agent_query(case["question"])
        tools = set(answer.tools_used)
        self.assertIn("graph_search", tools)
        self.assertIn("stock_query", tools)
        # Справочные тулы могут присутствовать, но маршрут обязан остаться тяжёлым.
        self.assertTrue(len(tools) >= 4)


if __name__ == "__main__":
    unittest.main()