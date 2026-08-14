import unittest

from frontend.agent_view import agent_quality_notes, component_rows, parsed_query_rows


class AgentViewModelTest(unittest.TestCase):
    def test_nested_parsed_query_is_shown_as_readable_rows(self):
        rows = parsed_query_rows(
            {
                "card": {
                    "item_type": "отвод",
                    "geometry": {"dn": 426, "angle": 90, "wall_thickness": 10},
                    "environment": {"medium": "H2S", "h2s_confirmed": None},
                    "coating": {"inner_coating": False},
                }
            }
        )
        by_name = {row["Параметр"]: row["Значение"] for row in rows}

        self.assertEqual("отвод", by_name["Тип изделия"])
        self.assertEqual("426", by_name["DN"])
        self.assertEqual("Не указано", by_name["H2S подтверждён"])
        self.assertEqual("Нет", by_name["Внутреннее покрытие"])

    def test_property_wrappers_are_unpacked(self):
        rows = parsed_query_rows(
            {
                "card": {
                    "properties": {
                        "pn": {"value": 40, "unit": "bar"},
                        "outer": {"value": True},
                    }
                }
            }
        )
        by_name = {row["Параметр"]: row["Значение"] for row in rows}

        self.assertEqual("40", by_name["PN"])
        self.assertEqual("Да", by_name["Наружное покрытие"])

    def test_component_rows_keep_codes_and_quantity(self):
        rows = component_rows(
            [
                {
                    "ksm_code": "KSM-1",
                    "mtr_code": "MTR-1",
                    "name": "Задвижка",
                    "item_type": "задвижка",
                    "quantity": 4,
                }
            ]
        )

        self.assertEqual("KSM-1", rows[0]["Код КСМ"])
        self.assertEqual(4, rows[0]["Количество"])

    def test_quality_notes_find_missing_evidence(self):
        notes = agent_quality_notes(
            {
                "answer": "",
                "sources": [],
                "components": [{"ksm_code": "KSM-1"}],
                "warnings": [],
                "human_review_required": True,
            }
        )

        self.assertEqual(4, len(notes))
        self.assertIn("источников", " ".join(notes))


if __name__ == "__main__":
    unittest.main()
