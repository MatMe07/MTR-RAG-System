import unittest
from pathlib import Path

from frontend.agent_quality import build_report, evaluate_responses, load_cases


ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "data" / "evaluation" / "agent_stress_cases_50.jsonl"


class AgentStressDatasetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases(CASES_PATH)

    def test_dataset_has_50_unique_cases(self):
        self.assertEqual(50, len(self.cases))
        self.assertEqual(50, len({case["case_id"] for case in self.cases}))

    def test_dataset_covers_all_stress_groups(self):
        groups = {case["group"] for case in self.cases}
        self.assertEqual(
            {
                "negation",
                "uncertainty",
                "typos",
                "conflict",
                "multiple_actions",
                "incomplete",
            },
            groups,
        )

    def test_every_case_has_a_route_and_intent(self):
        for case in self.cases:
            self.assertIn(
                case["expected_route"],
                {"ordinary", "agent", "clarification"},
                case["case_id"],
            )
            self.assertTrue(case.get("expected_intents"), case["case_id"])


class AgentQualityEvaluationTest(unittest.TestCase):
    def test_complete_agent_response_passes(self):
        case = {
            "case_id": "TEST-1",
            "query": "остатки",
            "expected_route": "agent",
            "expected_intents": ["inventory"],
            "required_tools": ["catalog_search", "stock_query"],
            "required_source_kinds": ["catalog", "stock"],
            "required_warning_terms": ["эксперт"],
            "human_review_required": True,
            "expected_extraction": {"card.geometry.dn": 150},
        }
        result = evaluate_responses(
            case,
            {
                "route": "agent",
                "intent": "inventory",
                "required_tools": ["catalog_search", "stock_query"],
                "parsed_query": {"card": {"geometry": {"dn": 150}}},
            },
            {
                "intent": "inventory",
                "tools_used": ["catalog_search", "stock_query"],
                "sources": [{"kind": "catalog"}, {"kind": "stock"}],
                "warnings": ["Результат должен проверить эксперт"],
                "human_review_required": True,
            },
            latency_ms=100,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.extraction_checked)
        self.assertEqual([], result.issues)

    def test_missing_source_and_warning_are_reported(self):
        result = evaluate_responses(
            {
                "case_id": "TEST-2",
                "query": "замена для H2S",
                "expected_route": "agent",
                "expected_intents": ["replacement"],
                "required_tools": ["rules_engine"],
                "required_source_kinds": ["passport"],
                "required_warning_terms": ["H2S"],
                "human_review_required": True,
            },
            {"route": "agent", "intent": "replacement"},
            {
                "intent": "replacement",
                "tools_used": [],
                "sources": [],
                "warnings": [],
                "human_review_required": False,
            },
            latency_ms=100,
        )

        self.assertFalse(result.passed)
        self.assertIn("не запущены инструменты", " ".join(result.issues))
        self.assertIn("не хватает источников", " ".join(result.issues))
        self.assertIn("H2S", " ".join(result.issues))

    def test_extraction_is_deferred_when_api_does_not_return_parsed_query(self):
        result = evaluate_responses(
            {
                "case_id": "TEST-3",
                "query": "труба 426 на 10",
                "expected_route": "ordinary",
                "expected_intents": ["catalog_search"],
                "expected_extraction": {"card.geometry.dn": 426},
            },
            {"route": "ordinary", "intent": "catalog_search"},
            None,
            latency_ms=50,
        )

        self.assertFalse(result.extraction_checked)
        self.assertTrue(result.extraction_ok)
        self.assertTrue(result.passed)

    def test_report_calculates_summary(self):
        first = evaluate_responses(
            {
                "case_id": "PASS",
                "query": "q1",
                "expected_route": "ordinary",
                "expected_intents": ["catalog_search"],
            },
            {"route": "ordinary", "intent": "catalog_search"},
            None,
            latency_ms=10,
        )
        second = evaluate_responses(
            {
                "case_id": "FAIL",
                "query": "q2",
                "expected_route": "agent",
                "expected_intents": ["inventory"],
            },
            {"route": "ordinary", "intent": "catalog_search"},
            None,
            latency_ms=30,
        )

        report = build_report([first, second])

        self.assertEqual(2, report["summary"]["total"])
        self.assertEqual(1, report["summary"]["passed"])
        self.assertEqual(0.5, report["summary"]["pass_rate"])
        self.assertEqual(20, report["summary"]["mean_latency_ms"])


if __name__ == "__main__":
    unittest.main()
