# test_inventory_calculator.py

"""Фаза C: фильтрация по наличию и ранжирование по срочности в inventory_calculator."""

import unittest

from app.schemas import ParsedQuery
from app.services.agent.tools.analytic_tools import inventory_calculator


def _parsed(**kw):
    base = dict(
        original_query="тест",
        operations=[],
        item_types=[],
        component_ids=[],
        unit_ids=[],
        proposed_changes={},
        technical_filters={},
        references=[],
        limit=None,
        on_stock=None,
        not_installed=None,
        units_count=1,
        intents=[],
    )
    base.update(kw)
    return ParsedQuery(**base)


def _target(ksm, name="деталь", item_type="фланец"):
    return {
        "card": {
            "card_id": f"id-{ksm}",
            "name": name,
            "item_type": item_type,
            "codes": {"ksm_code": ksm, "mtr_code": f"MTR-{ksm}"},
        }
    }


class InventoryFilterByStockTest(unittest.TestCase):
    def test_out_of_stock_only_excludes_available(self):
        parsed = _parsed(on_stock=False)
        state = {
            "parsed": parsed,
            "ksm_targets": [_target("KS1"), _target("KS2")],
            "stock_rows": [
                {"ksm_code": "KS1", "quantity": 10},
                {"ksm_code": "KS2", "quantity": 0},
            ],
        }
        result = inventory_calculator(state)
        ksms = [c["ksm_code"] for c in result["components"]]
        self.assertIn("KS2", ksms)
        self.assertNotIn("KS1", ksms)

    def test_list_out_of_stock_intent(self):
        parsed = _parsed(intents=["LIST_OUT_OF_STOCK"])
        state = {
            "parsed": parsed,
            "ksm_targets": [_target("KS1"), _target("KS2")],
            "stock_rows": [
                {"ksm_code": "KS1", "quantity": 5},
                {"ksm_code": "KS2", "quantity": 0},
            ],
        }
        result = inventory_calculator(state)
        ksms = [c["ksm_code"] for c in result["components"]]
        self.assertIn("KS2", ksms)
        self.assertNotIn("KS1", ksms)

    def test_no_filter_returns_all(self):
        parsed = _parsed(on_stock=None)
        state = {
            "parsed": parsed,
            "ksm_targets": [_target("KS1"), _target("KS2")],
            "stock_rows": [
                {"ksm_code": "KS1", "quantity": 10},
                {"ksm_code": "KS2", "quantity": 0},
            ],
        }
        result = inventory_calculator(state)
        self.assertEqual(len(result["components"]), 2)


class InventoryUrgencySortTest(unittest.TestCase):
    def test_zero_stock_critical_sorted_first(self):
        parsed = _parsed()
        state = {
            "parsed": parsed,
            "ksm_targets": [
                _target("KS_HIGH", item_type="задвижка"),
                _target("KS_LOW"),
            ],
            "stock_rows": [
                {"ksm_code": "KS_HIGH", "quantity": 0},
                {"ksm_code": "KS_LOW", "quantity": 10},
            ],
        }
        result = inventory_calculator(state)
        self.assertEqual(result["components"][0]["ksm_code"], "KS_HIGH")
        self.assertIn("критично", result["components"][0]["detail"])

    def test_status_marks_no_stock(self):
        parsed = _parsed()
        state = {
            "parsed": parsed,
            "ksm_targets": [_target("KS1")],
            "stock_rows": [{"ksm_code": "KS1", "quantity": 0}],
        }
        result = inventory_calculator(state)
        self.assertIn("нет на складе", result["components"][0]["status"])


class InventoryUrgencyScaleTest(unittest.TestCase):
    def test_zero_stock_differentiated_by_item_type(self):
        parsed = _parsed(on_stock=False)
        state = {
            "parsed": parsed,
            "ksm_targets": [
                _target("KS_VALVE", item_type="задвижка"),
                _target("KS_BEND", item_type="отвод"),
                _target("KS_CAP", item_type="заглушка"),
            ],
            "stock_rows": [
                {"ksm_code": "KS_VALVE", "quantity": 0},
                {"ksm_code": "KS_BEND", "quantity": 0},
                {"ksm_code": "KS_CAP", "quantity": 0},
            ],
        }
        result = inventory_calculator(state)
        by_ksm = {c["ksm_code"]: c["status"] for c in result["components"]}
        self.assertIn("критическая", by_ksm["KS_VALVE"])
        self.assertIn("высокая", by_ksm["KS_BEND"])
        self.assertIn("средняя", by_ksm["KS_CAP"])

    def test_purchase_recommendation_present(self):
        parsed = _parsed(on_stock=False)
        state = {
            "parsed": parsed,
            "ksm_targets": [
                _target("KS_VALVE", item_type="задвижка"),
                _target("KS_CAP", item_type="заглушка"),
            ],
            "stock_rows": [
                {"ksm_code": "KS_VALVE", "quantity": 0},
                {"ksm_code": "KS_CAP", "quantity": 0},
            ],
        }
        result = inventory_calculator(state)
        rec = result["purchase_recommendation"]
        self.assertIsNotNone(rec)
        self.assertIn("критически", rec.lower() or rec)
        self.assertIn("задвижк", rec)
        self.assertIn("заглушк", rec)

    def test_urgency_score_field_is_logged_reason(self):
        parsed = _parsed(on_stock=False)
        state = {
            "parsed": parsed,
            "ksm_targets": [_target("KS_VALVE", item_type="задвижка")],
            "stock_rows": [{"ksm_code": "KS_VALVE", "quantity": 0}],
        }
        result = inventory_calculator(state)
        self.assertEqual(result["components"][0].get("_urgency_score"), 5)


if __name__ == "__main__":
    unittest.main()
