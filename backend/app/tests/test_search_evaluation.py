import unittest

from app.scripts.evaluate_search_results import evaluate_cases


class SearchEvaluationTest(unittest.TestCase):
    def test_ranked_metrics_use_top3_and_top20_windows(self):
        golden = [
            {"case_id": "A", "expected_top1_mtr": "MTR-A"},
            {"case_id": "B", "expected_top1_mtr": "MTR-B"},
            {"case_id": "C", "expected_top1_mtr": "MTR-C"},
        ]
        results = [
            {
                "case_id": "A",
                "ranked_mtr_codes": ["X", "Y", "MTR-A"],
                "warnings": [],
                "explanation": "",
                "sources": [],
            },
            {
                "case_id": "B",
                "ranked_mtr_codes": [f"X-{index}" for index in range(10)]
                + ["MTR-B"],
                "warnings": [],
                "explanation": "",
                "sources": [],
            },
            {
                "case_id": "C",
                "ranked_mtr_codes": ["X", "Y", "Z"],
                "warnings": [],
                "explanation": "",
                "sources": [],
            },
        ]

        report = evaluate_cases(golden, results, [])

        self.assertAlmostEqual(report["metrics"]["top3_hit_rate"], 1 / 3)
        self.assertAlmostEqual(report["metrics"]["top20_hit_rate"], 2 / 3)
        self.assertFalse(report["cases"][2]["top20_hit"])

    def test_warning_explanation_source_and_exact_assertions(self):
        golden = [{"case_id": "Q", "expected_top1_mtr": "MTR-1"}]
        assertions = [
            {
                "case_id": "Q",
                "exact_code_case": True,
                "required_warning_terms": ["H2S", "не подтверж"],
                "required_explanation_terms": ["провер", "паспорт"],
                "required_sources": ["passport.md", "lnd.md"],
            }
        ]
        results = [
            {
                "case_id": "Q",
                "ranked_mtr_codes": ["MTR-1"],
                "warnings": ["H2S не подтверждён"],
                "explanation": "Нужно проверить паспорт.",
                "sources": ["passport.md", "lnd.md"],
            }
        ]

        report = evaluate_cases(golden, results, assertions)

        self.assertEqual(report["metrics"]["exact_code_top1_rate"], 1)
        self.assertEqual(report["metrics"]["warning_coverage"], 1)
        self.assertEqual(report["metrics"]["explanation_coverage"], 1)
        self.assertEqual(report["metrics"]["source_coverage"], 1)

    def test_missing_result_is_counted_as_failed_retrieval(self):
        golden = [{"case_id": "Q", "expected_top1_mtr": "MTR-1"}]

        report = evaluate_cases(golden, [], [])

        self.assertEqual(report["metrics"]["top3_hit_rate"], 0)
        self.assertFalse(report["cases"][0]["has_result"])


if __name__ == "__main__":
    unittest.main()
