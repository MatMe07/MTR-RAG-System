# app/tests/test_llm_extractor.py

"""§1F: LLM-доизвлечение недостающих параметров (офлайн, мок LLM-клиента)."""

import json
import unittest
from unittest.mock import patch

from app.services.agent.parsing.llm_extractor import (
    get_llm_extractor,
    reset_llm_extractor,
    LLMExtractor,
)
from app.services.agent.intent.detect import enrich_parsed
from app.schemas import ParsedQuery


class FakeClient:
    """Заглушка LLM-клиента: возвращает заданный JSON."""

    def __init__(self, payload, metrics=None):
        self.payload = payload
        self._metrics = metrics if metrics is not None else {
            "extractor_calls": 0, "extractor_hits": 0, "extractor_errors": 0,
        }
        self.calls = []

    def invoke(self, prompt, use_cache=True):
        self.calls.append(prompt)
        return self.payload


class LLMExtractorUnitTest(unittest.TestCase):
    def setUp(self):
        reset_llm_extractor()

    def tearDown(self):
        reset_llm_extractor()

    def _make(self, payload):
        client = FakeClient(json.dumps(payload))
        return LLMExtractor(client=client), client

    def test_extracts_missing_fields(self):
        ex, client = self._make({"dn": 159, "material": "сталь 20"})
        got = ex.extract_missing(
            "FIND_BY_PARAMS", "нужен отвод 159 из стали 20", ["material"], {}
        )
        # Приоритет нормализации §1E: материал → «Сталь 20».
        self.assertEqual(got["material"], "Сталь 20")
        self.assertEqual(client._metrics["extractor_calls"], 1)
        self.assertIn("FIND_BY_PARAMS", client.calls[0])

    def test_does_not_override_known(self):
        ex, client = self._make({"dn": 159, "material": "09Г2С"})
        got = ex.extract_missing(
            "FIND_BY_PARAMS", "нужен отвод 159", ["dn", "material"], {"dn": 150}
        )
        self.assertNotIn("dn", got)
        self.assertEqual(got["material"], "09Г2С")

    def test_drops_garbage_keys(self):
        ex, client = self._make({"dn": 50, "color": "red", "explanation": "x"})
        got = ex.extract_missing("FIND_BY_PARAMS", "отвод 50", ["dn"], {})
        self.assertEqual(got, {"dn": 50})

    def test_bad_json_is_silent(self):
        ex, client = self._make("не JSON")
        got = ex.extract_missing("FIND_BY_PARAMS", "отвод", ["dn"], {})
        self.assertEqual(got, {})
        self.assertEqual(client._metrics["extractor_errors"], 1)

    def test_not_a_dict_is_silent(self):
        ex, client = self._make("[1, 2]")
        got = ex.extract_missing("FIND_BY_PARAMS", "отвод", ["dn"], {})
        self.assertEqual(got, {})

    def test_disabled_when_no_client(self):
        ex = LLMExtractor(client=None)
        with patch("app.services.agent.parsing.llm_extractor.get_llm_client", return_value=None):
            got = ex.extract_missing("FIND_BY_PARAMS", "отвод", ["dn"], {})
            self.assertEqual(got, {})
            self.assertFalse(ex.enabled)

    def test_numeric_coercion(self):
        ex, client = self._make({"dn": "200", "units_count": "3"})
        got = ex.extract_missing(
            "CHECK_SUFFICIENCY", "хватит ли 3 отвода дн200", ["dn", "units_count"], {}
        )
        self.assertEqual(got["dn"], 200.0)
        self.assertEqual(got["units_count"], 3)


def _parsed(query, **extra):
    fields = dict(
        original_query=query,
        operations=["search"],
        item_types=[],
        component_ids=[],
        unit_ids=[],
        technical_filters={},
        stock_filters={},
        card=None,
        cards=[],
        references=[],
        ambiguities=[],
        proposed_changes={},
        units_count=None,
        quantity=None,
    )
    fields.update(extra)
    return ParsedQuery(**fields)


class EnrichHookTest(unittest.TestCase):
    def setUp(self):
        reset_llm_extractor()

    def tearDown(self):
        reset_llm_extractor()

    def test_llm_completes_find_by_params(self):
        client = FakeClient(json.dumps({"dn": 200}))
        ex = LLMExtractor(client=client)
        with patch(
            "app.services.agent.parsing.llm_extractor.get_llm_extractor",
            return_value=ex,
        ):
            parsed = _parsed("нужен отвод", item_types=["отвод"])
            enrich_parsed(parsed)
        self.assertEqual(parsed.technical_filters.get("dn"), 200)
        self.assertIn("FIND_BY_PARAMS", parsed.intents)
        self.assertEqual(parsed.status, "COMPLETE")

    def test_no_llm_call_when_complete(self):
        client = FakeClient(json.dumps({"dn": 150}))
        ex = LLMExtractor(client=client)
        with patch(
            "app.services.agent.parsing.llm_extractor.get_llm_extractor",
            return_value=ex,
        ):
            parsed = _parsed(
                "отвод dn150",
                item_types=["отвод"],
                technical_filters={"dn": 150},
            )
            enrich_parsed(parsed)
        self.assertEqual(client.calls, [])

    def test_extractor_error_never_crashes_pipeline(self):
        class Boom:
            _metrics = {"extractor_calls": 0, "extractor_hits": 0, "extractor_errors": 0}

            def invoke(self, prompt, use_cache=True):
                raise RuntimeError("llm down")

        ex = LLMExtractor(client=Boom())
        with patch(
            "app.services.agent.parsing.llm_extractor.get_llm_extractor",
            return_value=ex,
        ):
            parsed = _parsed("отвод 200", item_types=["отвод"])
            enrich_parsed(parsed)
        # Пайплайн жив: интенты посчитаны, статус установлен.
        self.assertIsInstance(parsed.intents, list)
        self.assertTrue(parsed.status)

    def test_default_disabled_mode(self):
        with patch("app.services.agent.parsing.llm_extractor.get_llm_client", return_value=None):
            parsed = _parsed("нужен отвод", item_types=["отвод"])
            enrich_parsed(parsed)
        # Без LLM (нет ключа / deterministic) — не падает, статус считает rule-путь.
        self.assertIsInstance(parsed.intents, list)


if __name__ == "__main__":
    unittest.main()