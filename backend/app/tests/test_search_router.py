import unittest

from app.services.search_router import route_search


class SearchRouterTest(unittest.TestCase):
    def test_exact_code_uses_ordinary_search(self):
        decision = route_search(
            {"exact_codes": ["MTR-0013"], "collections": ["elbows"]}
        )

        self.assertEqual(decision["route"], "ordinary")
        self.assertEqual(decision["mode"], "exact")

    def test_missing_parameters_request_clarification(self):
        decision = route_search(
            {
                "collections": ["elbows"],
                "missing_critical_parameters": ["angle", "wall_thickness"],
            }
        )

        self.assertEqual(decision["route"], "clarification")
        self.assertIn("angle", decision["reasons"][0])

    def test_multi_collection_query_uses_agent(self):
        decision = route_search(
            {
                "collections": ["pipes", "elbows", "valves"],
                "required_source_types": ["catalog"],
                "agent_mode": "object_configuration",
            }
        )

        self.assertEqual(decision["route"], "agent")
        self.assertEqual(decision["mode"], "object_configuration")

    def test_composite_replacement_uses_agent(self):
        decision = route_search(
            {
                "collections": ["elbows"],
                "composite_replacement": True,
                "agent_mode": "composite_replacement",
            }
        )

        self.assertEqual(decision["route"], "agent")
        self.assertTrue(any("составная" in reason.lower() for reason in decision["reasons"]))

    def test_single_collection_search_stays_ordinary(self):
        decision = route_search(
            {
                "collections": ["pipes"],
                "required_source_types": ["catalog"],
                "ordinary_mode": "hybrid",
            }
        )

        self.assertEqual(decision["route"], "ordinary")
        self.assertEqual(decision["mode"], "hybrid")


if __name__ == "__main__":
    unittest.main()
