# test_sufficiency_check.py

"""sufficiency_check: проверка достаточности «хватает ли по N штук»."""

import unittest

from app.schemas import ParsedQuery
from app.services.agent.tools.analytic_tools import sufficiency_check


def _parsed(**kw):
    base = dict(
        original_query="хватает ли по 2 штуки",
        operations=[],
        item_types=[],
        component_ids=[],
        unit_ids=[],
        proposed_changes={},
        technical_filters={},
        references=[],
        intents=["CHECK_SUFFICIENCY"],
        units_count=2,
    )
    base.update(kw)
    return ParsedQuery(**base)


def _target(item_type, ksm, qty=None):
    card = {
        "card_id": f"id-{ksm}",
        "name": item_type,
        "item_type": item_type,
        "codes": {"ksm_code": ksm, "mtr_code": f"MTR-{ksm}"},
    }
    return {"card": card}


class SufficiencyTest(unittest.TestCase):
    def test_sufficient_types(self):
        state = {
            "parsed": _parsed(item_types=["задвижка", "труба"]),
            "ksm_targets": [_target("задвижка", "KS1"), _target("труба", "KS2")],
            "stock_rows": [
                {"ksm_code": "KS1", "quantity": 5},
                {"ksm_code": "KS2", "quantity": 10},
            ],
        }
        result = sufficiency_check(state)
        self.assertEqual(len(result["components"]), 2)
        verdicts = {c["item_type"]: c["verdict"] for c in result["components"]}
        self.assertEqual(verdicts["задвижка"], "хватает")
        self.assertEqual(verdicts["труба"], "хватает")
        self.assertFalse(result["review"])

    def test_insufficient_deficit(self):
        state = {
            "parsed": _parsed(item_types=["задвижка"]),
            "ksm_targets": [_target("задвижка", "KS1")],
            "stock_rows": [{"ksm_code": "KS1", "quantity": 1}],
        }
        result = sufficiency_check(state)
        comp = result["components"][0]
        self.assertEqual(comp["verdict"], "не хватает")
        self.assertEqual(comp["deficit"], 1)
        self.assertTrue(result["review"])

    def test_typed_stock_rows_without_targets(self):
        """stock_rows несут item_type — агрегируем без графа объекта (каталог-путь)."""
        state = {
            "parsed": _parsed(item_types=["труба", "задвижка"], units_count=2),
            "ksm_targets": [],
            "stock_rows": [
                {"ksm_code": "T1", "item_type": "труба", "quantity": 5},
                {"ksm_code": "T2", "item_type": "труба", "quantity": 3},
                {"ksm_code": "Z1", "item_type": "задвижка", "quantity": 1},
            ],
        }
        result = sufficiency_check(state)
        verdicts = {c["item_type"]: c["verdict"] for c in result["components"]}
        self.assertEqual(verdicts, {"труба": "хватает", "задвижка": "не хватает"})
        deficit = {c["item_type"]: c["deficit"] for c in result["components"]}
        self.assertEqual(deficit["задвижка"], 1)
        self.assertTrue(result["review"])


if __name__ == "__main__":
    unittest.main()
