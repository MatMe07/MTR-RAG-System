import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Тяжёлые модули (torch/docling/qdrant) в этом окружении не установлены.
# Для теста /agent они не нужны — подменяем заглушками до импорта app.main.
STUB_MODULES = {
    "docling": ["document_converter", "datamodel"],
    "docling.document_converter": ["DocumentConverter", "PdfFormatOption"],
    "docling.datamodel": ["pipeline_options", "base_models"],
    "docling.datamodel.pipeline_options": ["PdfPipelineOptions", "AcceleratorOptions", "AcceleratorDevice", "EasyOcrOptions"],
    "docling.datamodel.base_models": ["InputFormat"],
    "langchain_huggingface": ["HuggingFaceEmbeddings"],
    "langchain_qdrant": ["QdrantVectorStore"],
    "qdrant_client": ["QdrantClient", "http"],
    "qdrant_client.http": ["models", "exceptions"],
    "qdrant_client.http.models": ["Distance", "VectorParams"],
    "qdrant_client.http.exceptions": ["UnexpectedResponse"],
}


def _install_stubs():
    saved = {}
    for name, attrs in STUB_MODULES.items():
        saved[name] = sys.modules.get(name)
        mod = types.ModuleType(name)
        for attr in attrs:
            setattr(mod, attr, mock.MagicMock())
        sys.modules[name] = mod
    return saved


def _restore_stubs(saved):
    for name, mod in saved.items():
        if mod is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = mod


class _NoopLLM:
    """Заглушка: валидация не меняет результат (LLM недоступна/не нужна)."""

    def validate_and_correct_query(self, parsed):
        return parsed


class AgentEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved = _install_stubs()
        from app.services import entity_extractor

        # Не даём /agent уходить в сеть: подменяем LLM заглушкой до импорта app.main.
        cls._orig_llm = entity_extractor.LLMService
        entity_extractor.LLMService = _NoopLLM
        cls._patched = entity_extractor

        from app.main import app
        from fastapi.testclient import TestClient

        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._patched.LLMService = cls._orig_llm
        _restore_stubs(cls._saved)

    def test_agent_endpoint_returns_structured_answer(self):
        resp = self.client.post(
            "/agent",
            json={"query": "Состав участка UNIT-SYN-GAS-001 и складские остатки"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["route"], "agent")
        self.assertEqual(data["intent"], "inventory")
        self.assertEqual(data["tools_used"][0], "graph_search")
        self.assertIn("stock_query", data["tools_used"])
        self.assertGreaterEqual(len(data["components"]), 6)
        self.assertEqual(
            ["UNIT-SYN-GAS-001"],
            data["parsed_query"]["unit_ids"],
        )
        self.assertGreater(data["parsed_query"]["confidence"], 0)

    def test_agent_endpoint_handles_unknown_query(self):
        resp = self.client.post("/agent", json={"query": "замени задвижку"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["intent"], "replacement")

    def test_route_endpoint_returns_structured_decision(self):
        resp = self.client.post(
            "/route",
            json={"query": "Состав участка UNIT-SYN-GAS-001 и складские остатки"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["route"], "agent")
        self.assertEqual(data["intent"], "inventory")
        self.assertIn("stock_query", data["required_tools"])
        self.assertIn("reasons", data)
        self.assertFalse(data["llm_refined"])
        self.assertEqual(
            ["UNIT-SYN-GAS-001"],
            data["parsed_query"]["unit_ids"],
        )
        self.assertIn("inventory", data["parsed_query"]["operations"])

    def test_route_endpoint_exact_code_goes_ordinary(self):
        resp = self.client.post(
            "/route",
            json={"query": "найди MTR-PIP-000123 в каталоге"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["route"], "ordinary")
        self.assertEqual(resp.json()["mode"], "exact")
        self.assertEqual(
            "найди MTR-PIP-000123 в каталоге",
            resp.json()["parsed_query"]["original_query"],
        )


if __name__ == "__main__":
    unittest.main()
