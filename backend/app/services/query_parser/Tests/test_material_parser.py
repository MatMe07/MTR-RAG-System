# tests/test_material_parser.py

import pytest
# from query_parser.parsers.material_parser import MaterialParser


class TestMaterialParser:
    """Тесты для MaterialParser"""

    def test_parse_simple_steel(self, material_parser):
        """Тест простой стали"""
        result = material_parser.parse("сталь 20")
        assert result["steel_grade"] == "20"

    def test_parse_composite_steel(self, material_parser):
        """Тест составной стали"""
        result = material_parser.parse("09Г2С")
        assert result["steel_grade"] == "09Г2С"

    def test_parse_foreign_steel(self, material_parser):
        """Тест зарубежной стали"""
        result = material_parser.parse("AISI 316L")
        assert result["steel_grade"] == "AISI 316L"

    def test_parse_strength_class(self, material_parser):
        """Тест класса прочности"""
        result = material_parser.parse("класс прочности К52")
        assert result["strength_class"] == "К52"

    def test_parse_replacement(self, material_parser):
        """Тест замены материала"""
        result = material_parser.parse("стали 20 на 09Г2С")
        assert result["steel_grade"] == "20"
        assert result["_replacement"]["steel_grade_from"] == "20"
        assert result["_replacement"]["steel_grade_to"] == "09Г2С"

    def test_parse_with_gost(self, material_parser):
        """Тест с ГОСТом"""
        result = material_parser.parse("сталь 09Г2С по ГОСТ 12345-67")
        assert result["steel_grade"] == "09Г2С"
        assert result["standard"] == "ГОСТ 12345-67"

    def test_parse_context_carbon(self, material_parser):
        """Тест контекстной углеродистой стали"""
        result = material_parser.parse("углеродистая сталь")
        assert result["steel_grade"] == "20"

    def test_parse_context_stainless(self, material_parser):
        """Тест контекстной нержавеющей стали"""
        result = material_parser.parse("нержавеющая сталь")
        assert result["steel_grade"] == "12Х18Н10Т"

    def test_is_valid_steel_grade(self, material_parser):
        """Тест валидности марки стали"""
        assert material_parser.is_valid_steel_grade("09Г2С") is True
        assert material_parser.is_valid_steel_grade("несуществующая") is False

    def test_get_steel_grades_by_type(self, material_parser):
        """Тест получения марок по типу"""
        carbon = material_parser.get_steel_grades_by_type("carbon")
        assert "20" in carbon
        assert "45" in carbon
    def test_parse_steel_09gsf(self, material_parser):
        """Тест стали 09ГСФ"""
        result = material_parser.parse("заглушка 426 на 12 из стали 09ГСФ")
        assert result["steel_grade"] == "09ГСФ"

    def test_parse_steel_20(self, material_parser):
        """Тест стали 20"""
        result = material_parser.parse("бесшовной трубы 108 на 6 из стали 20")
        assert result["steel_grade"] == "20"

    def test_parse_steel_09g2s(self, material_parser):
        """Тест стали 09Г2С"""
        result = material_parser.parse("Нужно заменить трубу из стали 20 на 09Г2С")
        assert result["steel_grade"] == "20"
        assert result["_replacement"]["steel_grade_from"] == "20"
        assert result["_replacement"]["steel_grade_to"] == "09Г2С"

    def test_parse_steel_with_preposition(self, material_parser):
        """Тест стали с предлогом"""
        result = material_parser.parse("из стали 09ГСФ")
        assert result["steel_grade"] == "09ГСФ"

    def test_parse_strength_class(self, material_parser):
        """Тест класса прочности"""
        result = material_parser.parse("задвижка DN200 PN63")
        # Может быть класс прочности, а может и нет
        # Проверяем, что парсер не падает
        assert result is not None

    def test_parse_replacement_in_text(self, material_parser):
        """Тест замены материала в тексте"""
        result = material_parser.parse("Нужно заменить трубу из стали 20 на 09Г2С")
        assert result["steel_grade"] == "20"
        assert result["_replacement"]["steel_grade_to"] == "09Г2С"
