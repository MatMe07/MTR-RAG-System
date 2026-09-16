# test_unit_scoped_inventory.py

"""P1-11: unit-scoped inventory + excluded_due_to_medium.

Из инвентарного расчёта с активной H2S/CO2-средой исключаются позиции
с ЯВНЫМ «пригодность не подтверждена» и попадают в явный список, а не
отбрасываются молча (семантика filter-only-false, единая с P0).
"""

import unittest
from unittest import mock

from app.schemas import ParsedQuery
from app.services.agent.llm.refine_loop import run_refine_loop  # noqa: F401,E402  # порядок импорта (circular import)
from app.services.agent.tools.analytic_tools import inventory_calculator


def _q(**kw):
    base = dict(
        original_query="проверь запас на участке с H2S",
        operations=["inventory"],
        item_types=[],
        component_ids=[],
        unit_ids=["UNIT-SYN-H2S-001"],
        proposed_changes={},
        technical_filters={"medium": "H2S", "h2s_confirmed": True},
        references=[],
        intents=["CHECK_STOCK"],
        units_count=1,
        on_stock=None,
        not_installed=None,
        stock_filters={},
    )
    base.update(kw)
    return ParsedQuery(**base)


def _target(ksm, item_type, h2s_confirmed=None, co2_confirmed=None):
    card = {
        "card_id": f"id-{ksm}",
        "name": item_type,
        "item_type": item_type,
        "codes": {"ksm_code": ksm, "mtr_code": f"MTR-{ksm}"},
    }
    if h2s_confirmed is not None:
        card["h2s_confirmed"] = h2s_confirmed
    if co2_confirmed is not None:
        card["co2_confirmed"] = co2_confirmed
    return {
        "card": card,
        "component": {"unit_id": "UNIT-SYN-H2S-001", "component_id": f"COMP-{ksm}"},
    }


class _FakeRepo:
    def get_stock_quantity(self, ksm):
        return None


class UnitScopedInventoryTest(unittest.TestCase):
    def _run(self, parsed, targets):
        stock_rows = [
            {"ksm_code": t["card"]["codes"]["ksm_code"], "quantity": 3}
            for t in targets
        ]
        state = {
            "parsed": parsed,
            "ksm_targets": targets,
            "stock_rows": stock_rows,
        }
        with mock.patch(
            "app.services.agent.repository.repository_factory.get_repository",
            return_value=_FakeRepo(),
        ):
            return inventory_calculator(state)

    def test_h2s_excludes_explicit_false(self):
        targets = [
            _target("T1", "задвижка", h2s_confirmed=False),
            _target("T2", "труба", h2s_confirmed=None),
            _target("T3", "отвод", h2s_confirmed=True),
        ]
        result = self._run(_q(), targets)
        excluded = result["excluded_due_to_medium"]
        self.assertEqual([e["ksm_code"] for e in excluded], ["T1"])
        self.assertIn("H2S", excluded[0]["reason"])
        codes = {c["ksm_code"] for c in result["components"]}
        self.assertEqual(codes, {"T2", "T3"})
        self.assertTrue(any("Исключено из-за среды" in w for w in result["warnings"]))

    def test_co2_excludes_explicit_false(self):
        parsed = _q(technical_filters={"medium": "CO2", "co2_confirmed": True},
                    original_query="проверь запас на участке с CO2")
        targets = [
            _target("C1", "задвижка", co2_confirmed=False),
            _target("C2", "труба", co2_confirmed=None),
        ]
        result = self._run(parsed, targets)
        excluded = result["excluded_due_to_medium"]
        self.assertEqual([e["ksm_code"] for e in excluded], ["C1"])
        self.assertIn("CO2", excluded[0]["reason"])
        self.assertEqual({c["ksm_code"] for c in result["components"]}, {"C2"})

    def test_unknown_and_true_are_not_excluded(self):
        targets = [
            _target("T2", "труба", h2s_confirmed=None),
            _target("T3", "отвод", h2s_confirmed=True),
        ]
        result = self._run(_q(), targets)
        self.assertEqual(result["excluded_due_to_medium"], [])
        self.assertEqual(len(result["components"]), 2)

    def test_no_medium_query_has_no_exclusions(self):
        parsed = _q(technical_filters={})
        targets = [_target("T1", "задвижка", h2s_confirmed=False)]
        result = self._run(parsed, targets)
        # Без среды в запросе позиция НЕ исключается (не H2S-запрос).
        self.assertEqual(result["excluded_due_to_medium"], [])
        self.assertEqual(len(result["components"]), 1)


if __name__ == "__main__":
    unittest.main()
