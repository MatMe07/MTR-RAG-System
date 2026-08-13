import unittest
from pathlib import Path
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings
from app.services.llm_service import LLMService
from app.services.entity_extractor import EntityExtractor
from app.services.agents.executor import execute_agent_query
from app.schemas import ParsedQuery


class FakeResponse:
    def __init__(self, text):
        self.content = text


class FakeLLM:
    def __init__(self, name, fail=False):
        self.name = name
        self.fail = fail
        self.calls = []

    def invoke(self, prompt):
        self.calls.append(prompt)
        if self.fail:
            raise RuntimeError("primary failed")
        return FakeResponse(f"<{self.name}>{prompt}")

    def with_structured_output(self, schema):
        return self


class ConfigAndFallbackTest(unittest.TestCase):
    def setUp(self):
        self._old_use_local = getattr(settings, "USE_LOCAL_LLM", False)

    def tearDown(self):
        settings.USE_LOCAL_LLM = self._old_use_local

    def test_env_loaded_from_repo_root(self):
        # .env лежит в корне репозитория; без фикса config.py ключи были бы None.
        self.assertTrue(settings.OPENROUTER_API_KEY)
        self.assertTrue(settings.OPENROUTER_BASE_URL)
        self.assertTrue(settings.LLM_MODEL)
        self.assertIsInstance(settings.USE_LOCAL_LLM, bool)

    def test_primary_is_openrouter_when_key_set(self):
        llm = LLMService()
        self.assertFalse(llm.use_local)
        self.assertTrue(llm.api_key)
        self.assertIsNotNone(llm.fallback_llm)

    def test_invoke_falls_back_to_ollama_when_primary_fails(self):
        primary = FakeLLM("openrouter", fail=True)
        fallback = FakeLLM("ollama")
        svc = LLMService()
        with mock.patch.object(LLMService, "_make_client", side_effect=[primary, fallback]):
            result = svc.invoke("промпт")
        self.assertEqual(result.content, "<ollama>промпт")
        self.assertEqual(primary.calls, ["промпт"])
        self.assertEqual(fallback.calls, ["промпт"])

    def test_invoke_reraises_without_fallback(self):
        settings.USE_LOCAL_LLM = True
        svc = LLMService()
        primary = FakeLLM("ollama", fail=True)
        with mock.patch.object(LLMService, "_make_client", return_value=primary):
            with self.assertRaises(RuntimeError):
                svc.invoke("промпт")

    def test_structured_invoke_falls_back(self):
        primary = FakeLLM("openrouter", fail=True)
        fallback = FakeLLM("ollama")
        svc = LLMService()
        with mock.patch.object(LLMService, "_make_client", side_effect=[primary, fallback]):
            result = svc.structured_invoke("промпт", ParsedQuery)
        self.assertEqual(result.content, "<ollama>промпт")


class EntityExtractorTest(unittest.TestCase):
    def setUp(self):
        self._old_mode = getattr(settings, "AGENT_LLM_MODE", "auto")
        settings.AGENT_LLM_MODE = "auto"  # conftest ставит off — включаем для теста LLM

    def tearDown(self):
        settings.AGENT_LLM_MODE = self._old_mode

    def test_injectable_llm_is_used_on_low_confidence(self):
        llm = mock.Mock()
        llm.validate_and_correct_query.return_value = ParsedQuery(
            original_query="замени задвижку",
            operations=["replace"],
            confidence=0.9,
        )
        ex = EntityExtractor(llm=llm)
        parsed = ex.extract("замени задвижку")
        self.assertIsNotNone(parsed)
        llm.validate_and_correct_query.assert_called_once()
        self.assertEqual(parsed.confidence, 0.9)

    def test_llm_cannot_drop_rule_based_facts(self):
        # Имитируем LLM, которая "ухудшила" парсинг: потеряла unit_id и операцию.
        class DegradingLLM:
            def validate_and_correct_query(self, parsed):
                parsed.unit_ids = []
                parsed.operations = ["search"]
                parsed.confidence = 0.5
                return parsed

        ex = EntityExtractor(llm=DegradingLLM())
        parsed = ex.extract("Состав участка UNIT-SYN-GAS-001 и складские остатки")
        self.assertIn("UNIT-SYN-GAS-001", parsed.unit_ids)
        self.assertIn("inventory", parsed.operations)
        self.assertIn("plan", parsed.operations)
        # Операции не теряются: поиск и сохранённые объединены.
        self.assertIn("search", parsed.operations)


class ExecuteAgentQueryTest(unittest.TestCase):
    def test_injected_extractor_drives_agent_plan(self):
        class FakeExtractor:
            def extract(self, query):
                return ParsedQuery(
                    original_query=query,
                    operations=["inventory"],
                    unit_ids=["UNIT-SYN-GAS-001"],
                    confidence=0.95,
                )

        ans = execute_agent_query("остатки по участку", extractor=FakeExtractor())
        self.assertEqual(ans.intent, "inventory")
        self.assertEqual(ans.tools_used[0], "graph_search")
        self.assertIn("stock_query", ans.tools_used)
        self.assertGreaterEqual(len(ans.components), 1)


if __name__ == "__main__":
    unittest.main()
