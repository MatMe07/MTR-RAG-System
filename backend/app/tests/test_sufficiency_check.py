# test_sufficiency_check.py

"""sufficiency_check: проверка достаточности «хватает ли по N штук»."""

import unittest

from app.schemas import ParsedQuery
from app.services.agent.llm.refine_loop import run_refine_loop  # noqa: F401,E402  # порядок импорта (circular import)
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

    def test_no_deficit_verdict_and_residual_table(self):
        """P1-10/P2-26: при полной достаточности verdict=no_deficit + residual_table."""
        state = {
            "parsed": _parsed(item_types=["задвижка"], units_count=2),
            "ksm_targets": [_target("задвижка", "KS1")],
            "stock_rows": [
                {"ksm_code": "KS1", "quantity": 5},
                {"ksm_code": "KS2", "quantity": 10},
            ],
        }
        result = sufficiency_check(state)
        self.assertEqual(result["verdict"], "no_deficit")
        self.assertFalse(result["review"])
        table = result["residual_table"]
        codes = {r["ksm_code"]: r for r in table}
        self.assertEqual(codes["KS1"]["current_qty"], 5)
        self.assertEqual(codes["KS1"]["item_type"], "задвижка")
        self.assertEqual(codes["KS2"]["current_qty"], 10)
        self.assertTrue(all(r["threshold"] >= 2 for r in table))

    def test_deficit_verdict(self):
        """P1-10: при дефиците verdict=deficit, а residual_table всё равно строится."""
        state = {
            "parsed": _parsed(item_types=["задвижка"], units_count=2),
            "ksm_targets": [_target("задвижка", "KS1")],
            "stock_rows": [{"ksm_code": "KS1", "quantity": 1}],
        }
        result = sufficiency_check(state)
        self.assertEqual(result["verdict"], "deficit")
        self.assertTrue(result["review"])
        self.assertEqual(result["residual_table"][0]["current_qty"], 1)

    def test_quantity_min_threshold_applies(self):
        """P1-10: порог quantity_min (≥N) учитывается даже если потребность закрыта."""
        state = {
            "parsed": _parsed(
                item_types=["задвижка"],
                units_count=2,
                stock_filters={"quantity_min": 5},
            ),
            "ksm_targets": [_target("задвижка", "KS1")],
            "stock_rows": [{"ksm_code": "KS1", "quantity": 3}],
        }
        result = sufficiency_check(state)
        comp = result["components"][0]
        self.assertEqual(comp["verdict"], "не хватает")
        self.assertEqual(comp["threshold"], 5)
        self.assertEqual(result["verdict"], "deficit")
        self.assertTrue(result["review"])


if __name__ == "__main__":
    unittest.main()
