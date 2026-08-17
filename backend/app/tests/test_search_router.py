import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from backend.app.services.routing.search_router import route_query_text, route_search


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

    def test_plain_analogue_query_with_stock_uses_agent(self):
        decision = route_query_text(
            "Какой аналог отвода 90 426 на 10 подойдет для H2S, "
            "покажи из наличия"
        )

        self.assertEqual(decision["intent"], "replacement")
        self.assertEqual(decision["route"], "agent")
        self.assertEqual(decision["mode"], "inventory_and_match")
        self.assertIn("stock_query", decision["required_tools"])
        self.assertIn("rules_engine", decision["required_tools"])

    def test_repair_plan_uses_graph_stock_and_planner(self):
        decision = route_query_text(
            "У меня сломался отвод COMP-SYN-008, "
            "составь план ремонта"
        )

        self.assertEqual(decision["intent"], "maintenance")
        self.assertEqual(decision["route"], "agent")
        self.assertEqual(decision["mode"], "maintenance_plan")
        self.assertIn("graph_search", decision["required_tools"])
        self.assertIn("maintenance_planner", decision["required_tools"])

    def test_equipment_explanation_by_code_is_ordinary(self):
        decision = route_query_text(
            "Расскажи про задвижку KSM-SYN-REG-000591"
        )

        self.assertEqual(decision["intent"], "equipment_guidance")
        self.assertEqual(decision["route"], "ordinary")
        self.assertEqual(decision["mode"], "exact")

    def test_incomplete_elbow_request_asks_for_parameters(self):
        decision = route_query_text("Нужен аналог отвода DN159")

        self.assertEqual(decision["route"], "clarification")
        self.assertIn("angle", decision["missing_parameters"])
        self.assertIn("wall_thickness", decision["missing_parameters"])


if __name__ == "__main__":
    unittest.main()
