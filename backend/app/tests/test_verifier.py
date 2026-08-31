# test_verifier.py

"""Quality gate (auto-режим): эвристики verify_answer (§3.2 плана)."""

import unittest

from app.schemas import AgentAnswer, AgentComponent, ParsedQuery
from app.services.agent.verify.verifier import verify_answer


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
        intents=[],
        ambiguities=[],
        status="",
        units_count=None,
    )
    base.update(kw)
    return ParsedQuery(**base)


def _answer(components=None, answer_text="", warnings=None, status=""):
    return AgentAnswer(
        query="тест",
        components=components or [],
        answer=answer_text,
        warnings=warnings or [],
    )


def _comp(item_type=None, quantity=None, status="", detail=""):
    return AgentComponent(
        mtr_code="MTR-1",
        ksm_code="KS1",
        name="Деталь",
        item_type=item_type,
        quantity=quantity,
        status=status,
        detail=detail,
    )


class IntentMismatchTest(unittest.TestCase):
    def test_missing_item_type_review(self):
        parsed = _parsed(item_types=["задвижка", "труба"], intents=["CHECK_SUFFICIENCY"])
        answer = _answer([_comp(item_type="задвижка", quantity=5)])
        vr = verify_answer(parsed, answer)
        self.assertEqual(vr.verdict, "review")
        types = {g.type for g in vr.gaps}
        self.assertIn("intent_mismatch", types)

    def test_all_types_covered_pass(self):
        parsed = _parsed(item_types=["задвижка", "труба"])
        answer = _answer([
            _comp(item_type="задвижка"),
            _comp(item_type="труба"),
        ])
        vr = verify_answer(parsed, answer)
        self.assertEqual(vr.verdict, "pass")


class QuantityUnmetTest(unittest.TestCase):
    def test_check_sufficiency_no_verdict(self):
        parsed = _parsed(
            units_count=2,
            item_types=["задвижка"],
            intents=["CHECK_SUFFICIENCY"],
        )
        answer = _answer([_comp(item_type="задвижка", quantity=5)])
        vr = verify_answer(parsed, answer)
        types = {g.type for g in vr.gaps}
        self.assertIn("quantity_unmet", types)

    def test_with_verdict_pass(self):
        parsed = _parsed(
            units_count=2,
            item_types=["задвижка"],
            intents=["CHECK_SUFFICIENCY"],
        )
        answer = _answer([_comp(item_type="задвижка", quantity=5, status="хватает")])
        vr = verify_answer(parsed, answer)
        self.assertEqual(vr.verdict, "pass")


class ScopeMismatchTest(unittest.TestCase):
    def test_one_type_only(self):
        parsed = _parsed(item_types=["труба", "отвод", "задвижка"])
        answer = _answer([_comp(item_type="труба")])
        vr = verify_answer(parsed, answer)
        types = {g.type for g in vr.gaps}
        self.assertIn("scope_mismatch", types)

    def test_multi_type_pass(self):
        parsed = _parsed(item_types=["труба", "отвод"])
        answer = _answer([_comp(item_type="труба"), _comp(item_type="отвод")])
        vr = verify_answer(parsed, answer)
        self.assertEqual(vr.verdict, "pass")


class ZeroStockMissingTest(unittest.TestCase):
    def test_in_stock_leak(self):
        parsed = _parsed(intents=["LIST_OUT_OF_STOCK"])
        answer = _answer([_comp(item_type="труба", quantity=10)])
        vr = verify_answer(parsed, answer)
        types = {g.type for g in vr.gaps}
        self.assertIn("zero_stock_missing", types)

    def test_zero_stock_ok(self):
        parsed = _parsed(intents=["LIST_OUT_OF_STOCK"])
        answer = _answer([_comp(item_type="труба", quantity=0)])
        vr = verify_answer(parsed, answer)
        self.assertEqual(vr.verdict, "pass")


class ParameterMissTest(unittest.TestCase):
    def test_ambiguity_no_clarification(self):
        parsed = _parsed(ambiguities=["Не удалось определить тип детали"])
        answer = _answer([_comp(item_type="труба")])
        vr = verify_answer(parsed, answer)
        types = {g.type for g in vr.gaps}
        self.assertIn("parameter_miss", types)

    def test_ambiguity_with_clarification_pass(self):
        parsed = _parsed(ambiguities=["Не удалось определить тип детали"])
        answer = _answer([_comp(item_type="труба", status="требует уточнения: тип?")])
        vr = verify_answer(parsed, answer)
        types = {g.type for g in vr.gaps}
        self.assertNotIn("parameter_miss", types)


class EmptyOrExpertSilentTest(unittest.TestCase):
    def test_expert_empty(self):
        parsed = _parsed(status="REQUIRES_EXPERT")
        answer = _answer([], answer_text="")
        vr = verify_answer(parsed, answer)
        types = {g.type for g in vr.gaps}
        self.assertIn("empty_or_expert_silent", types)


if __name__ == "__main__":
    unittest.main()
