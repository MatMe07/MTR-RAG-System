# test_intent_matrix.py

"""Фаза C (Этап 1): матрица интентов, статусы ParsedQuery, диалог 1G."""

import unittest

from app.services.agent.intent.matrix import (
    INTENT_ORDER,
    INTENT_REQUIREMENTS,
    INCOMPATIBLE_INTENTS,
    PARAMETER_VALIDATION_RULES,
    BLOCKER_FIELDS,
)
from app.services.agent.intent.detect import (
    detect_intents,
    filter_params_for_intent,
    missing_required_for_intent,
    params_from_parsed,
    enrich_parsed,
    determine_parsed_status,
    incompatible_detected,
    PARSED_STATUS_COMPLETE,
    PARSED_STATUS_PARTIAL,
    PARSED_STATUS_REQUIRES_EXPERT,
    PARSED_STATUS_UNCLEAR,
)
from app.services.agent.intent.clarify import (
    ClarificationManager,
    RequireClarification,
    build_question,
)

# Тестовые объекты ParsedQuery с полями из одного источника
def _q(**kw):
    from app.schemas import ParsedQuery

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
    )
    base.update(kw)
    return ParsedQuery(**base)


class MatrixTest(unittest.TestCase):
    def test_all_intents_have_requirements(self):
        for it in INTENT_ORDER:
            self.assertIn(it, INTENT_REQUIREMENTS, it)
            req = INTENT_REQUIREMENTS[it]
            self.assertIsInstance(req["required"], list, it)
            self.assertIsInstance(req["optional"], list, it)
            self.assertTrue(req["required"] or req["optional"], it)
            for group in req["required"]:
                self.assertTrue(group, f"{it}: пустая AND-группа")

    def test_incompatible_refs_valid(self):
        names = set(INTENT_ORDER)
        for a, bs in INCOMPATIBLE_INTENTS.items():
            self.assertIn(a, names)
            for b in bs:
                self.assertIn(b, names)

    def test_validation_rules_product_types(self):
        self.assertIn("задвижка", PARAMETER_VALIDATION_RULES)
        self.assertIn("отвод", PARAMETER_VALIDATION_RULES)
        self.assertIn("unknown", PARAMETER_VALIDATION_RULES)

    def test_blocker_fields_core(self):
        self.assertTrue({"dn", "pn", "medium", "item_type"} <= BLOCKER_FIELDS)


class FilterParamsTest(unittest.TestCase):
    def test_filters_keep_required_and_optional(self):
        params = {"item_type": "задвижка", "dn": 150, "pn": 2.5, "term": "x"}
        out = filter_params_for_intent(params, "FIND_ALTERNATIVE")
        self.assertIn("item_type", out)
        self.assertIn("dn", out)
        self.assertIn("pn", out)
        self.assertNotIn("term", out)


class DetectIntentsTest(unittest.TestCase):
    def test_find_by_params(self):
        parsed = _q(
            item_types=["задвижка"],
            technical_filters={"dn": 150.0, "pn": 2.5},
        )
        self.assertIn("FIND_BY_PARAMS", detect_intents(parsed))

    def test_replace_with_different_size(self):
        parsed = _q(proposed_changes={"dn_from": 200.0, "dn_to": 150.0})
        intents = detect_intents(parsed)
        self.assertIn("REPLACE_WITH_DIFFERENT_SIZE", intents)
        self.assertIn("IMPACT_DIAMETER_CHANGE", intents)

    def test_plan_repair_primary(self):
        parsed = _q(original_query="составь план ремонта COMP-SYN-010",
                    operations=["repair"], component_ids=["COMP-SYN-010"])
        intents = detect_intents(parsed)
        self.assertEqual(intents[0], "PLAN_REPAIR")

    def test_unclear_when_empty(self):
        self.assertEqual(detect_intents(_q()), [])

    def test_incompatible_detected(self):
        parsed = _q(
            original_query="найди и замени на составную",
            item_types=["отвод"], technical_filters={"dn": 100, "pn": 2.5},
            proposed_changes={"dn_from": 100.0, "dn_to": 80.0},
        )
        parsed.operations = ["replace"]
        reasons = incompatible_detected(detect_intents(parsed))
        self.assertTrue(any("FIND_ALTERNATIVE" in r or "REPLACE" in r for r in reasons))

    def test_check_sufficiency_detected(self):
        parsed = _q(
            original_query="хватает ли по две штуки задвижек",
            item_types=["задвижка"],
            units_count=2,
        )
        self.assertIn("CHECK_SUFFICIENCY", detect_intents(parsed))

    def test_check_sufficiency_no_units_absent(self):
        parsed = _q(original_query="хватает ли задвижек", item_types=["задвижка"])
        self.assertNotIn("CHECK_SUFFICIENCY", detect_intents(parsed))


class StatusTest(unittest.TestCase):
    def test_complete(self):
        p = _q(item_types=["задвижка"], technical_filters={"dn": 150.0})
        self.assertEqual(
            determine_parsed_status(p, detect_intents(p)), PARSED_STATUS_COMPLETE
        )

    def test_requires_expert(self):
        p = _q(original_query="составь план ремонта", operations=["repair"])
        intents = detect_intents(p)
        self.assertEqual(intents, ["PLAN_REPAIR"])
        self.assertEqual(determine_parsed_status(p, intents), PARSED_STATUS_REQUIRES_EXPERT)

    def test_unclear(self):
        self.assertEqual(determine_parsed_status(_q(), []), PARSED_STATUS_UNCLEAR)

    def test_enrich_parsed_fills_fields(self):
        p = _q(item_types=["задвижка"], technical_filters={"dn": 150.0})
        enrich_parsed(p)
        self.assertEqual(p.status, PARSED_STATUS_COMPLETE)
        self.assertIn("FIND_BY_PARAMS", p.intents)
        self.assertEqual(p.missing_params["FIND_BY_PARAMS"], [])

    def test_params_defaults(self):
        p = _q()
        params = params_from_parsed(p)
        self.assertEqual(params.get("min_stock"), 50)
        self.assertEqual(params.get("quantity"), 2)


class ClarifyTest(unittest.TestCase):
    def test_first_turn_asks_question(self):
        mgr = ClarificationManager()
        p = _q(original_query="план ремонта", operations=["repair"])
        with self.assertRaises(RequireClarification) as ctx:
            mgr.process("s1", p, "план ремонта")
        self.assertEqual(ctx.exception.turn, 1)
        self.assertTrue(ctx.exception.question)
        self.assertEqual(ctx.exception.status, PARSED_STATUS_REQUIRES_EXPERT)

    def test_complete_proceeds(self):
        mgr = ClarificationManager()
        p = _q(item_types=["задвижка"], technical_filters={"dn": 150.0})
        self.assertEqual(mgr.process("s2", p, "задвижка DN150"), "proceed")

    def test_three_turns_then_expert(self):
        mgr = ClarificationManager(max_turns=3)
        for expected_turn in (1, 2, 3):
            p = _q(original_query="план ремонта", operations=["repair"])
            try:
                mgr.process("s3", p, f"уточнение {expected_turn}")
                self.fail("ожидали RequireClarification")
            except RequireClarification as rc:
                self.assertEqual(rc.turn, expected_turn)
        p = _q(original_query="план ремонта", operations=["repair"])
        self.assertEqual(mgr.process("s3", p, "ещё"), "expert")

    def test_build_question_covers_missing(self):
        q = build_question("FIND_ALTERNATIVE", ["dn"])
        self.assertIn("DN", q)
        q2 = build_question("PLAN_REPAIR", ["component_id"])
        self.assertIn("COMP-SYN", q2)


if __name__ == "__main__":
    unittest.main()