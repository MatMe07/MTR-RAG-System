import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings
from backend.app.services.routing.llm_router import LlmRouter, RoutingDecision
from backend.app.services.routing.search_router import route_query_text


class FakeLLM:
    def __init__(self, decision: RoutingDecision):
        self._decision = decision
        self.calls = []

    def structured_invoke(self, prompt, schema):
        self.calls.append((prompt, schema))
        return self._decision


class LlmRouterTest(unittest.TestCase):
    def tearDown(self):
        settings.AGENT_LLM_MODE = "off"

    def _decision(self, route="agent", intent="replacement", mode="multi_step",
                  confidence=0.9, reasons=("нужно связать склад и каталог",)):
        return RoutingDecision(
            route=route, intent=intent, mode=mode,
            confidence=confidence, reasons=list(reasons),
        )

    def test_off_mode_returns_deterministic_without_llm(self):
        llm = FakeLLM(self._decision())
        decision = LlmRouter(llm=llm).route("найди задвижку DN150 PN40")
        self.assertFalse(decision["llm_refined"])
        self.assertEqual(llm.calls, [])

    def test_llm_refines_ambiguous_route(self):
        with mock.patch.object(settings, "AGENT_LLM_MODE", "on"):
            llm = FakeLLM(self._decision())
            decision = LlmRouter(llm=llm).route(
                "посчитай остатки задвижек на участке газопровода")
            self.assertTrue(decision["llm_refined"])
            self.assertEqual(decision["route"], "agent")
            self.assertEqual(decision["intent"], "replacement")
            self.assertIn("LLM: нужно связать склад и каталог", decision["reasons"][-1])

    def test_exact_code_not_overridden_by_llm(self):
        with mock.patch.object(settings, "AGENT_LLM_MODE", "on"):
            llm = FakeLLM(self._decision(route="agent", intent="replacement"))
            decision = LlmRouter(llm=llm).route(
                "найди MTR-PIP-000123 в каталоге")
            self.assertEqual(decision["route"], "ordinary")
            self.assertFalse(decision["llm_refined"])
            self.assertEqual(llm.calls, [])

    def test_missing_parameters_not_overridden(self):
        with mock.patch.object(settings, "AGENT_LLM_MODE", "on"):
            llm = FakeLLM(self._decision(route="agent"))
            decision = LlmRouter(llm=llm).route("найди отвод")
            self.assertEqual(decision["route"], "clarification")
            self.assertFalse(decision["llm_refined"])
            self.assertEqual(llm.calls, [])

    def test_low_confidence_keeps_deterministic(self):
        with mock.patch.object(settings, "AGENT_LLM_MODE", "on"):
            llm = FakeLLM(self._decision(route="agent", confidence=0.3))
            decision = LlmRouter(llm=llm).route("найди задвижку DN150 PN40")
            self.assertFalse(decision["llm_refined"])
            self.assertEqual(decision["route"], "ordinary")

    def test_invalid_route_falls_back(self):
        with mock.patch.object(settings, "AGENT_LLM_MODE", "on"):
            llm = FakeLLM(self._decision(route="teleport", confidence=0.9))
            decision = LlmRouter(llm=llm).route("найди задвижку DN150 PN40")
            self.assertFalse(decision["llm_refined"])

    def test_llm_failure_falls_back_to_deterministic(self):
        class FailingLLM:
            def structured_invoke(self, prompt, schema):
                raise RuntimeError("no llm")

        with mock.patch.object(settings, "AGENT_LLM_MODE", "on"):
            decision = LlmRouter(llm=FailingLLM()).route("найди задвижку DN150 PN40")
            self.assertFalse(decision["llm_refined"])
            self.assertEqual(decision["route"], "ordinary")

    def test_route_prompt_contains_query_and_deterministic(self):
        with mock.patch.object(settings, "AGENT_LLM_MODE", "on"):
            llm = FakeLLM(self._decision())
            LlmRouter(llm=llm).route("найди задвижку DN150 PN40")
            prompt, schema = llm.calls[0]
            self.assertIn("найди задвижку DN150 PN40", prompt)
            self.assertIn("ordinary", prompt)
            self.assertIs(schema, RoutingDecision)

    def test_deterministic_baseline_has_no_llm_flags(self):
        decision = route_query_text("найди задвижку DN150 PN40")
        self.assertFalse(decision.get("llm_refined", False))
        self.assertNotIn("router_confidence", decision)


if __name__ == "__main__":
    unittest.main()
