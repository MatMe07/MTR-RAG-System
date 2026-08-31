# test_policy.py

"""Политика эскалации auto-режима (C1/C2, severity)."""

import unittest

from app.services.agent.verify.policy import should_full_llm, should_refine, escalate_type
from app.services.agent.verify.verifier import Gap


class PolicyTest(unittest.TestCase):
    def test_should_full_llm_always_false_v1(self):
        gaps = [Gap(type="quantity_unmet", detail="x", severity="high")]
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


if __name__ == "__main__":
    unittest.main()
