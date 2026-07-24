import unittest
from types import SimpleNamespace
from unittest.mock import patch

from frontend import app


class FrontendAppTest(unittest.TestCase):
    def test_search_mode_labels_map_to_backend_codes(self):
        self.assertEqual("hybrid", app.mode_code("Гибридный поиск"))
        self.assertEqual("exact", app.mode_code("Точный поиск"))
        self.assertEqual("vector", app.mode_code("Семантический поиск"))
        self.assertEqual("passport", app.mode_code("Поиск по паспорту"))
        self.assertEqual("filter", app.mode_code("Проверка аналога"))

    def test_transform_backend_response_keeps_card_and_ocr_source(self):
        data = {
            "search_id": "search-001",
            "requested_card": {
                "item_type": "отвод",
                "properties": {
                    "dn": {
                        "value": 159,
                    }
                },
            },
            "total_found": 1,
            "search_time_ms": 42,
            "candidates": [
                {
                    "rank": 1,
                    "mtr_code": "MTR-001",
                    "ksm_code": "KSM-001",
                    "candidate_name": "Отвод DN159",
                    "match_percent": 91,
                    "status": "требует проверки",
                    "sources": [
                        {
                            "type": "passport",
                            "file_name": "passport.pdf",
                            "page": 2,
                            "source_fragment": {
                                "fragment_id": "fragment-001",
                                "text": "DN 159, угол 90 градусов",
                            },
                        }
                    ],
                }
            ],
        }

        result = app.transform_backend_response(
            data,
            query="отвод DN159",
            mode_label="Гибридный поиск",
        )

        self.assertEqual("search-001", result["search_id"])
        self.assertEqual("отвод", result["query_card"]["item_type"])
        self.assertEqual(1, len(result["candidates"]))
        source = result["candidates"][0]["sources"][0]
        self.assertEqual(2, source["page"])
        self.assertEqual("fragment-001", source["fragment_id"])
        self.assertIn("угол 90", source["fragment"])

    def test_transform_backend_response_handles_empty_results(self):
        result = app.transform_backend_response(
            {
                "search_id": "search-empty",
                "requested_card": {},
                "total_found": 0,
                "search_time_ms": 10,
                "candidates": [],
            },
            query="неполный запрос",
            mode_label="hybrid",
        )

        self.assertEqual([], result["candidates"])
        self.assertEqual(0, result["total_found"])
        self.assertTrue(result["backend_connected"])

    def test_corrected_card_builds_new_query_and_keeps_unknown_omitted(self):
        query = app.build_query_from_fields(
            {
                "item_type": "отвод",
                "subtype": "ОКШ",
                "dn": 159,
                "angle": 90,
                "wall_thickness": 10,
                "pn": 160,
                "steel_grade": "09Г2С",
                "strength_class": "К48",
                "medium": "газ с H2S",
                "h2s_confirmed": "Не указано",
                "inner_coating": "Да",
                "outer_coating": "Нет",
                "gost_tu": "ТУ 001",
            }
        )

        self.assertIn("отвод", query)
        self.assertIn("DN 159", query)
        self.assertIn("внутреннее покрытие", query)
        self.assertIn("наружное покрытие отсутствует", query)
        self.assertNotIn("пригодность к H2S подтверждена", query)

    @patch("frontend.app.post_json")
    @patch("frontend.app.upload_passport")
    def test_passport_is_uploaded_before_search(
        self,
        upload_mock,
        post_mock,
    ):
        upload_mock.return_value = {"document_id": 77}
        post_mock.return_value = {
            "search_id": "search-passport",
            "requested_card": {},
            "candidates": [],
            "total_found": 0,
            "search_time_ms": 5,
        }
        uploaded_file = SimpleNamespace(
            name="passport.pdf",
            type="application/pdf",
            getvalue=lambda: b"pdf",
        )

        result = app.search_backend(
            query="",
            mode_label="Поиск по паспорту",
            uploaded_file=uploaded_file,
        )

        upload_mock.assert_called_once_with(uploaded_file)
        payload = post_mock.call_args.args[1]
        self.assertEqual("passport", payload["mode"])
        self.assertEqual(77, payload["document_id"])
        self.assertEqual("search-passport", result["search_id"])

    @patch("frontend.app.post_json")
    def test_expert_review_is_sent_to_backend(self, post_mock):
        post_mock.return_value = {
            "success": True,
            "message": "Решение сохранено",
            "review_id": 5,
        }

        result = app.save_expert_review(
            search_id="search-001",
            candidate_ksm_code="KSM-001",
            decision_label="Подтвердить",
            comment="Паспорт проверен",
            reviewer="Эксперт 1",
        )

        payload = post_mock.call_args.args[1]
        self.assertEqual("approve", payload["decision"])
        self.assertEqual("KSM-001", payload["candidate_ksm_code"])
        self.assertEqual("Эксперт 1", payload["reviewer"])
        self.assertTrue(result["success"])

    def test_expert_review_requires_reviewer_and_ksm(self):
        with self.assertRaises(app.BackendAPIError):
            app.save_expert_review(
                search_id="search-001",
                candidate_ksm_code="KSM-001",
                decision_label="Подтвердить",
                comment="",
                reviewer="",
            )

        with self.assertRaises(app.BackendAPIError):
            app.save_expert_review(
                search_id="search-001",
                candidate_ksm_code="",
                decision_label="Подтвердить",
                comment="",
                reviewer="Эксперт",
            )


if __name__ == "__main__":
    unittest.main()
