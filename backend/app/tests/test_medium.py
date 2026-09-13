# test_medium.py

"""Проверка распознавания сред для маршрутизации (P3.2).

Гарантии:
- токен-логика не даёт ложных сред: H2S ≠ H2SO4, «вода» ≠ «водород*»;
- префикс-ключи («углекисл», «природн», «нефт», «вод») ловят словоформы;
- «сероводород» распознаётся как сероводородная среда, но не как вода;
- medium_match bind: подстрока слов + общий код графа (канон CORR).
"""

import unittest

from app.services.agent.medium import (
    medium_keyword_in,
    medium_match,
    medium_unit_codes,
)


class MediumUnitCodesTest(unittest.TestCase):
    def test_h2so4_not_h2s(self):
        self.assertEqual(medium_unit_codes("H2SO4"), set())

    def test_h2s_detected(self):
        self.assertIn("gas_h2s", medium_unit_codes("среда H2S"))

    def test_vodorod_not_water(self):
        self.assertEqual(medium_unit_codes("водород"), set())

    def test_vodorod_inflections_not_water(self):
        self.assertEqual(medium_unit_codes("техническая водородная смесь"), set())

    def test_water_detected(self):
        self.assertEqual(medium_unit_codes("техническая вода"), {"process_water"})

    def test_serovodorod_is_h2s_but_not_water(self):
        codes = medium_unit_codes("сероводород")
        self.assertIn("gas_h2s", codes)
        self.assertNotIn("process_water", codes)

    def test_co2_codes(self):
        codes = medium_unit_codes("углекислый газ")
        self.assertTrue({"gas_co2", "gas_h2s_co2"} & codes)


class MediumKeywordInTest(unittest.TestCase):
    def test_vodorod_not_water(self):
        self.assertIsNone(medium_keyword_in("участок с водородом"))

    def test_voda_is_water(self):
        self.assertEqual(medium_keyword_in("техническая вода"), "вод")

    def test_serovodorod(self):
        self.assertEqual(medium_keyword_in("сероводородная среда"), "сероводород")


class MediumMatchTest(unittest.TestCase):
    def test_h2s_not_h2so4(self):
        self.assertFalse(medium_match("H2S", "H2SO4"))

    def test_h2s_serovodorod(self):
        self.assertTrue(medium_match("H2S", "сероводород"))

    def test_water_substring(self):
        self.assertTrue(medium_match("вода", "техническая вода"))

    def test_water_not_vodorod(self):
        self.assertFalse(medium_match("вода", "техническая водородная смесь"))

    def test_corr_canon(self):
        self.assertTrue(medium_match("CORR", "коррозионно-активная среда"))


if __name__ == "__main__":
    unittest.main()
