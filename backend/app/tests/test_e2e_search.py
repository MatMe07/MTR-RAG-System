# backend/app/tests/test_e2e_search.py

import asyncio
import json
import os
import shutil
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app, upload_passport
from app.models import MTRItem, Document
from app.schemas import SearchRequest
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.ocr_service import OCRService
from app.services.rules_engine import RulesEngine
from app.services.search_service import SearchService


class E2ESearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db: Session = SessionLocal()
        cls.llm = LLMService()
        cls.embeddings = EmbeddingService()
        cls.rules = RulesEngine(cls.db)
        cls.search = SearchService(cls.db, cls.rules, cls.llm, cls.embeddings)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.temp_dir, "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.db.rollback()

    def create_test_passport(self, content: str) -> str:
        path = os.path.join(self.temp_dir, "test_passport.pdf")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_full_text_search_flow(self):
        request = SearchRequest(
            query="отвод 90 DN159 К48 для H2S",
            mode="hybrid",
            top_k=10
        )
        response = self.search.search(request)

        self.assertGreater(len(response.candidates), 0)
        first = response.candidates[0]
        self.assertIsNotNone(first.match_percent)
        self.assertIn(first.status, ["соответствует", "потенциальный аналог", "требует проверки"])


    def test_exact_code_search(self):
        item = self.db.query(MTRItem).first()
        if not item:
            self.skipTest("Нет данных в БД")

        request = SearchRequest(
            query=item.mtr_code,
            mode="exact",
            top_k=10
        )
        response = self.search.search(request)

        self.assertGreater(len(response.candidates), 0)
        self.assertEqual(response.candidates[0].mtr_code, item.mtr_code)
        self.assertEqual(response.candidates[0].match_percent, 100)

    @patch("app.main.ocr")
    def test_passport_upload_and_search_flow(self, mock_ocr):
        mock_ocr.extract_text_from_pdf.return_value = [
            {
                "page_number": 1,
                "text": "ОТВОД ОКШ 90° DN 159 мм PN 160 09Г2С К48",
                "tables": [],
                "confidence": 0.95
            }
        ]

        pdf_content = "ОТВОД ОКШ 90° DN 159 мм PN 160 09Г2С К48"
        pdf_path = self.create_test_passport(pdf_content)

        with open(pdf_path, "rb") as f:
            file_bytes = f.read()

        file = UploadFile(filename="test_passport.pdf", file=BytesIO(file_bytes))

        with patch("app.main.UPLOAD_DIR", self.upload_dir):
            response = asyncio.run(upload_passport(file, self.db))

        self.assertTrue(response["success"])
        self.assertIsNotNone(response["document_id"])

        request = SearchRequest(
            query="",
            mode="passport",
            document_id=response["document_id"],
            top_k=10
        )
        search_response = self.search.search(request)

        # Паспорт загружен, карточка извлечена
        self.assertIsNotNone(search_response.requested_card)
        
        # Документ сохранен
        doc = self.db.query(Document).filter(Document.id == response["document_id"]).first()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.file_name, "test_passport.pdf")
        self.assertEqual(doc.ocr_status, "done")

    def test_hybrid_search_returns_scored_candidates(self):
        request = SearchRequest(
            query="отвод 90 DN159 К48",
            mode="hybrid",
            top_k=10
        )
        response = self.search.search(request)

        for candidate in response.candidates:
            self.assertIn(candidate.status, [
                "соответствует",
                "потенциальный аналог",
                "требует проверки",
                "низкая релевантность"
            ])
            self.assertIsNotNone(candidate.match_percent)

    def test_search_returns_sources_for_candidates(self):
        request = SearchRequest(
            query="отвод",
            mode="hybrid",
            top_k=5
        )
        response = self.search.search(request)

        for candidate in response.candidates:
            self.assertTrue(candidate.sources)
            for source in candidate.sources:
                self.assertIn(source.type, ["excel", "passport", "catalog", "standard"])

    def test_search_id_is_unique(self):
        request = SearchRequest(query="отвод", mode="hybrid")
        response1 = self.search.search(request)
        response2 = self.search.search(request)

        self.assertIsNotNone(response1.search_id)
        self.assertIsNotNone(response2.search_id)
        self.assertNotEqual(response1.search_id, response2.search_id)

    def test_empty_query_returns_empty_response(self):
        request = SearchRequest(query="", mode="hybrid")
        response = self.search.search(request)

        self.assertEqual(len(response.candidates), 0)
        self.assertEqual(response.total_found, 0)

    def test_search_time_measured(self):
        request = SearchRequest(query="отвод 90", mode="hybrid")
        response = self.search.search(request)

        self.assertGreater(response.search_time_ms, 0)
        self.assertLess(response.search_time_ms, 30000)


if __name__ == "__main__":
    unittest.main()
