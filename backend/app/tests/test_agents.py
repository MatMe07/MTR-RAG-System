import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.agents.executor import run_agent
from app.services.agents.registry import plan_for_operations
from app.services.query_parser.hybrid_parser import HybridParser


def _answer(query: str):
    parsed = HybridParser().parse(query)
    return run_agent(parsed)


class AgentExecutorTest(unittest.TestCase):
    def test_unit_inventory_query_runs_graph_first(self):
        ans = _answer("Состав участка UNIT-SYN-GAS-001 и складские остатки")
        self.assertEqual(ans.tools_used[0], "graph_search")
        self.assertIn("stock_query", ans.tools_used)
        self.assertGreaterEqual(len(ans.components), 6)
        self.assertIsNotNone(ans.parsed_query)
        self.assertEqual(["UNIT-SYN-GAS-001"], ans.parsed_query.unit_ids)

    def test_catalog_stock_query_with_filters(self):
        ans = _answer("Какие отводы DN150 есть на складе для газа с H2S")
        self.assertIn("catalog_search", ans.tools_used)
        self.assertIn("stock_query", ans.tools_used)
        self.assertLessEqual(len(ans.components), 20)
        self.assertEqual("отвод", ans.parsed_query.card.item_type)
        self.assertEqual(150, ans.parsed_query.card.geometry.dn)

    def test_object_builder_assembles_new_unit(self):
        ans = _answer("Составь перечень деталей нового участка DN200 PN25 природный газ")
        self.assertEqual(ans.intent, "object_configuration")
        self.assertIn("object_builder", ans.tools_used)
        self.assertGreater(len(ans.components), 0)

    def test_duplicate_keyword_runs_duplicate_detector(self):
        ans = _answer("Проверь дубли в каталоге по задвижкам")
        self.assertIn("duplicate_detector", ans.tools_used)

    def test_impact_change_adds_impact_analyzer(self):
        ans = _answer("Переход с DN150 на DN200 на участке UNIT-SYN-GAS-001")
        self.assertEqual(ans.intent, "impact_analysis")
        self.assertIn("impact_analyzer", ans.tools_used)

    def test_plan_priority_impact_over_search(self):
        plan = plan_for_operations(["check", "impact"], [], [])
        self.assertIn("impact_analyzer", plan)
        self.assertIn("graph_search", plan)

    def test_maintenance_plan_for_h2s_unit(self):
        ans = _answer("Составь план ТО для участка UNIT-SYN-H2S-001")
        self.assertEqual(ans.intent, "maintenance")
        self.assertIn("maintenance_planner", ans.tools_used)
        self.assertGreaterEqual(len(ans.components), 6)


if __name__ == "__main__":
    unittest.main()
