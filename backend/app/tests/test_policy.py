# test_policy.py

"""Политика эскалации auto-режима (C1/C2, severity)."""

import unittest

from app.services.agent.verify.policy import escalate_type, should_full_llm, should_refine
from app.services.agent.verify.verifier import Gap


class PolicyTest(unittest.TestCase):
    def test_should_full_llm_true_c2_for_high_in_set(self):
        gaps = [Gap(type="quantity_unmet", detail="x", severity="high")]
        self.assertTrue(should_full_llm(gaps))

    def test_should_full_llm_true_for_intent_mismatch_high(self):
        gaps = [Gap(type="intent_mismatch", detail="x", severity="high")]
        self.assertTrue(should_full_llm(gaps))

    def test_should_full_llm_false_for_med_in_set(self):
        gaps = [Gap(type="scope_mismatch", detail="x", severity="med")]
        self.assertFalse(should_full_llm(gaps))

    def test_should_full_llm_false_for_high_outside_set(self):
        # zero_stock_missing нет в FULL_LLM_TYPES → только C1
        gaps = [Gap(type="zero_stock_missing", detail="x", severity="high")]
        self.assertFalse(should_full_llm(gaps))

    def test_should_refine_positive(self):
        gaps = [Gap(type="parameter_miss", detail="x", severity="low")]
        self.assertTrue(should_refine(gaps))

    def test_should_refine_empty(self):
        self.assertFalse(should_refine([]))

    def test_escalate_type_none(self):
        self.assertEqual(escalate_type([]), "none")

    def test_escalate_type_refine(self):
        gaps = [Gap(type="scope_mismatch", detail="x", severity="med")]
        self.assertEqual(escalate_type(gaps), "refine")

    def test_escalate_type_full_llm(self):
        gaps = [Gap(type="quantity_unmet", detail="x", severity="high")]
        self.assertEqual(escalate_type(gaps), "full_llm")


if __name__ == "__main__":
    unittest.main()
