# tests/test_pressure_parser.py

import pytest
# from query_parser.parsers.pressure_parser import PressureParser



class TestPressureParser:
    """Тесты для PressureParser"""

    def test_parse_pn_standard(self, pressure_parser):
        """Тест стандартного PN"""
        result = pressure_parser.parse("PN40")
        assert result["pn"] == 4.0
        assert result["raw_value"] == "PN40"

    def test_parse_pn_ru(self, pressure_parser):
        """Тест PN с Ру"""
        result = pressure_parser.parse("Ру16")
        assert result["pn"] == 1.6
        assert result["raw_value"] == "PN16"

    def test_parse_pn_working_pressure(self, pressure_parser):
        """Тест PN с рабочим давлением"""
        result = pressure_parser.parse("PN40 рабочее давление 3.0 МПа")
        assert result["pn"] == 4.0
        assert result["working_pressure_mpa"] == 3.0

    def test_parse_test_pressure(self, pressure_parser):
        """Тест испытательного давления"""
        result = pressure_parser.parse("опрессовка 6.0 МПа")
        assert result["test_pressure_mpa"] == 6.0

    def test_parse_mpa(self, pressure_parser):
        """Тест давления в МПа"""
        result = pressure_parser.parse("давление 4.0 МПа")
        assert result["working_pressure_mpa"] == 4.0
        assert result["pn"] == 4.0

    def test_parse_kgcm2(self, pressure_parser):
        """Тест давления в кгс/см2"""
        result = pressure_parser.parse("40 кгс/см2")
        assert result["working_pressure_mpa"] == pytest.approx(3.92, 0.01)

    def test_parse_bar(self, pressure_parser):
        """Тест давления в барах"""
        result = pressure_parser.parse("40 бар")
        assert result["working_pressure_mpa"] == 4.0

    def test_parse_context_high(self, pressure_parser):
        """Тест контекстного высокого давления"""
        result = pressure_parser.parse("высокое давление")
        assert result["pn"] == 10.0

    def test_parse_context_low(self, pressure_parser):
        """Тест контекстного низкого давления"""
        result = pressure_parser.parse("низкое давление")
        assert result["pn"] == 1.6

    def test_is_valid_pn(self, pressure_parser):
        """Тест валидности PN"""
        assert pressure_parser.is_valid_pn(4.0) is True   # PN40
        assert pressure_parser.is_valid_pn(1.6) is True   # PN16
        assert pressure_parser.is_valid_pn(5.0) is False  # Нестандартный

    def test_parse_empty(self, pressure_parser):
        """Тест пустого запроса"""
        result = pressure_parser.parse("")
        assert result["pn"] is None
        assert result["working_pressure_mpa"] is None

    def test_parse_valve_pressure(self, pressure_parser):
        """Тест давления задвижки"""
        result = pressure_parser.parse("задвижка DN150 PN40")
        assert result["pn"] == 4.0
        assert result["raw_value"] == "PN40"

    def test_parse_valve_pressure_ru(self, pressure_parser):
        """Тест давления задвижки (Ру)"""
        result = pressure_parser.parse("задвижка DN150 PN40")
        assert result["pn"] == 4.0

    # ✅ Исправлен тест - теперь проверяем, что парсер корректно обрабатывает запрос без давления
    def test_parse_pressure_with_environment(self, pressure_parser):
        """Тест давления с указанием среды (без явного давления)"""
        result = pressure_parser.parse("для участка с H2S, исходной задвижки на складе нет")
        # Давление не указано явно, поэтому должно быть None
        # Проверяем, что парсер вернул корректный результат и не упал
        assert result is not None
        assert "pn" in result
        assert "working_pressure_mpa" in result
        # Давление должно быть None, так как не указано
        assert result["pn"] is None
        assert result["working_pressure_mpa"] is None

    def test_parse_pressure_in_context(self, pressure_parser):
        """Тест давления в контексте"""
        result = pressure_parser.parse("задвижка DN200 PN63")
        assert result["pn"] == 6.3
        assert result["raw_value"] == "PN63"

    def test_parse_pressure_gas(self, pressure_parser):
        """Тест давления для газа"""
        result = pressure_parser.parse("для газа с CO2")
        # Давление не указано явно, поэтому должно быть None
        assert result["pn"] is None
        assert result["working_pressure_mpa"] is None
