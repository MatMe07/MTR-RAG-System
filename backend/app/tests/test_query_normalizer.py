import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.services.query_normalizer import normalize_query


class QueryNormalizerTest(unittest.TestCase):
    def test_normalizes_russian_parameter_aliases_and_dimensions(self):
        result = normalize_query(
            "Нужна задвишка ДУ 150 Ру 40 и труба 426 на 10"
        )

        self.assertIn("задвижка", result["normalized_text"])
        self.assertIn("dn 150", result["normalized_text"])
        self.assertIn("pn 40", result["normalized_text"])
        self.assertIn("426x10", result["normalized_text"])

    def test_normalizes_coleno_and_h2s_wording(self):
        result = normalize_query(
            "Какое колено подойдет для газа с сероводородом"
        )

        self.assertIn("отвод", result["normalized_text"])
        self.assertIn("h2s", result["normalized_text"])

    def test_does_not_automatically_replace_ambiguous_sour_gas(self):
        result = normalize_query("Деталь для кислого газа")

        self.assertIn("кислого газа", result["normalized_text"])
        ambiguous = [
            alias
            for alias in result["detected_aliases"]
            if alias["canonical"] == "corrosive_gas"
        ]
        self.assertEqual(ambiguous[0]["automatic"], False)


if __name__ == "__main__":
    unittest.main()
