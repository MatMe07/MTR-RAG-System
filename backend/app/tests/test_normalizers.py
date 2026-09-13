# test_normalizers.py

"""Фаза 1, §1E: нормализация параметров."""

import unittest

from app.services.agent.parsing.normalizers import (
    MorphNormalizer,
    normalize_climate,
    normalize_dn,
    normalize_item_type,
    normalize_material,
    normalize_medium,
    normalize_pressure,
)


class NormalizeDnTest(unittest.TestCase):
    def test_nominal_stays(self):
        for v in (50, 80, 100, 125, 150, 200, 250, 300, 400, 500, 600):
            self.assertEqual(normalize_dn(v), v)

    def test_float_nominal_rounded(self):
        self.assertEqual(normalize_dn(150.0), 150)

    def test_actual_od_kept(self):
        self.assertEqual(normalize_dn(159), 159)
        self.assertEqual(normalize_dn(219), 219)

    def test_none_and_str(self):
        self.assertIsNone(normalize_dn(None))
        self.assertEqual(normalize_dn("DN150"), "DN150")


class NormalizePressureTest(unittest.TestCase):
    def test_bar_to_mpa(self):
        self.assertEqual(normalize_pressure(160, "бар"), 16.0)
        self.assertEqual(normalize_pressure(10, "bar"), 1.0)

    def test_kgcm2_to_mpa(self):
        self.assertEqual(normalize_pressure(160, "кгс/см2"), 16.0)
        self.assertEqual(normalize_pressure(160, "кг/см2"), 16.0)

    def test_mpa_identity(self):
        self.assertEqual(normalize_pressure(4.0, "МПа"), 4.0)

    def test_comma_decimal(self):
        self.assertEqual(normalize_pressure("16,0", "бар"), 1.6)


class NormalizeMaterialTest(unittest.TestCase):
    def test_steel_20_forms(self):
        self.assertEqual(normalize_material("20"), "Сталь 20")
        self.assertEqual(normalize_material("ст20"), "Сталь 20")
        self.assertEqual(normalize_material("сталь 20"), "Сталь 20")

    def test_grade_dash_stripped(self):
        self.assertEqual(normalize_material("09Г2С-12"), "09Г2С")

    def test_none(self):
        self.assertIsNone(normalize_material(None))


class NormalizeMediumClimateTest(unittest.TestCase):
    def test_medium(self):
        self.assertEqual(normalize_medium("сероводород"), "H2S")
        self.assertEqual(normalize_medium("углекислый газ"), "CO2")
        self.assertEqual(normalize_medium("нефть"), "нефть")

    def test_climate(self):
        self.assertEqual(normalize_climate("северный"), "ХЛ")
        self.assertEqual(normalize_climate("у"), "У")
        self.assertEqual(normalize_climate("т"), "Т")

    def test_item_type(self):
        self.assertEqual(normalize_item_type("колено"), "отвод")
        self.assertEqual(normalize_item_type("задвижка клиновая"), "задвижка")


class MorphNormalizerTest(unittest.TestCase):
    def test_lemmatize(self):
        mn = MorphNormalizer()
        self.assertEqual(mn.normalize("задвижки"), "задвижка")
        self.assertEqual(mn.normalize("отводы"), "отвод")

    def test_existing_normalizers_intact(self):
        from app.services.agent.parsing.normalizers import normalize_steel

        self.assertEqual(normalize_steel("09г2с"), "09Г2С")


class PressureParserIntegrationTest(unittest.TestCase):
    def test_bar_kgcm2_in_parser(self):
        from app.services.agent.parsing.parsers.pressure_parser import PressureParser

        p = PressureParser()
        self.assertEqual(p.parse("160 бар")["working_pressure_mpa"], 16.0)
        self.assertEqual(p.parse("160 кгс/см2")["working_pressure_mpa"], 16.0)


if __name__ == "__main__":
    unittest.main()
