import unittest

from frontend.demo_scenarios import DEMO_SCENARIOS, scenario_by_id
from frontend.expert_history_view import history_rows


class SupportViewsTest(unittest.TestCase):
    def test_four_demo_scenarios_have_unique_ids(self):
        scenario_ids = [item["id"] for item in DEMO_SCENARIOS]

        self.assertEqual(4, len(DEMO_SCENARIOS))
        self.assertEqual(len(scenario_ids), len(set(scenario_ids)))
        self.assertIn("H2S", scenario_by_id("replacement")["query"])

    def test_expert_history_has_readable_decision(self):
        rows = history_rows(
            [
                {
                    "candidate_ksm_code": "KSM-1",
                    "decision": "need_more_info",
                    "reviewed_by": "Эксперт",
                }
            ]
        )

        self.assertEqual("Нужны сведения", rows[0]["Решение"])
        self.assertEqual("KSM-1", rows[0]["КСМ"])


if __name__ == "__main__":
    unittest.main()
