import unittest

from frontend.clarification_view import build_clarified_query, normalize_missing_fields


class ClarificationViewTest(unittest.TestCase):
    def test_backend_field_aliases_are_normalized_without_duplicates(self):
        fields = normalize_missing_fields(
            [
                "geometry.dn",
                "dn_or_diameter",
                "pressure.pn",
                "material.steel_grade",
                "d1_d2",
            ]
        )

        self.assertEqual(
            ["dn", "pn", "steel_grade", "d1", "d2"],
            [field.key for field in fields],
        )

    def test_query_contains_only_values_supplied_by_user(self):
        query = build_clarified_query(
            "Найди замену отводу",
            {
                "dn": 426.0,
                "angle": 90.0,
                "medium": "H2S",
                "inner_coating": "Не указано",
                "outer_coating": "Нет",
            },
        )

        self.assertIn("DN 426", query)
        self.assertIn("угол 90", query)
        self.assertIn("среда H2S", query)
        self.assertIn("наружное покрытие нет", query)
        self.assertNotIn("внутреннее покрытие", query)


if __name__ == "__main__":
    unittest.main()
