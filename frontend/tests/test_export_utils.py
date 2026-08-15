import unittest

from frontend.export_utils import (
    agent_component_export_rows,
    candidate_export_rows,
    result_to_json,
    rows_to_csv,
)


class ExportUtilsTest(unittest.TestCase):
    def test_json_keeps_russian_text(self):
        exported = result_to_json({"answer": "Нужна проверка эксперта"})

        self.assertIn("Нужна проверка эксперта", exported)
        self.assertNotIn("\\u041d", exported)

    def test_agent_components_can_be_downloaded_as_csv(self):
        result = {
            "agent": {
                "components": [
                    {"ksm_code": "KSM-1", "name": "Отвод", "quantity": 2}
                ]
            }
        }

        csv_text = rows_to_csv(agent_component_export_rows(result))

        self.assertIn("ksm_code", csv_text)
        self.assertIn("KSM-1", csv_text)
        self.assertIn("Отвод", csv_text)

    def test_candidates_keep_warnings(self):
        rows = candidate_export_rows(
            {"candidates": [{"rank": 1, "ksm_code": "KSM-2", "warnings": ["H2S"]}]}
        )

        self.assertEqual(["H2S"], rows[0]["warnings"])


if __name__ == "__main__":
    unittest.main()
