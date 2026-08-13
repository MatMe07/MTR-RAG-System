# tests/test_environment_parser.py

import pytest
# from query_parser.parsers.environment_parser import EnvironmentParser


class TestEnvironmentParser:
    """Тесты для EnvironmentParser"""

    def test_parse_medium_h2s(self, environment_parser):
        """Тест среды H2S"""
        result = environment_parser.parse("среда H2S")
        assert result["medium"] == "H2S"
        assert result["h2s_confirmed"] is True

    def test_parse_medium_co2(self, environment_parser):
        """Тест среды CO2"""
        result = environment_parser.parse("среда CO2")
        assert result["medium"] == "CO2"
        assert result["co2_confirmed"] is True

    def test_parse_medium_oil(self, environment_parser):
        """Тест среды нефть"""
        result = environment_parser.parse("нефтяная среда")
        assert result["medium"] == "нефть"

    def test_parse_medium_gas(self, environment_parser):
        """Тест среды газ"""
        result = environment_parser.parse("природный газ")
        assert result["medium"] == "природный газ"

    def test_parse_medium_water(self, environment_parser):
        """Тест среды вода"""
        result = environment_parser.parse("водная среда")
        assert result["medium"] == "вода"

    def test_parse_climate_uhl(self, environment_parser):
        """Тест климатики УХЛ"""
        result = environment_parser.parse("исполнение УХЛ1")
        assert result["climate_version"] == "УХЛ"

    def test_parse_climate_hl(self, environment_parser):
        """Тест климатики ХЛ"""
        result = environment_parser.parse("северное исполнение")
        assert result["climate_version"] == "ХЛ"

    def test_parse_climate_t(self, environment_parser):
        """Тест климатики Т"""
        result = environment_parser.parse("тропическое исполнение")
        assert result["climate_version"] == "Т"

    def test_parse_temperature(self, environment_parser):
        """Тест температуры"""
        result = environment_parser.parse("температура -40°C")
        assert result["temperature_min_c"] == -40.0

    def test_parse_full(self, environment_parser):
        """Тест полного запроса"""
        result = environment_parser.parse("среда H2S, температура -40°C, климат УХЛ1")
        assert result["medium"] == "H2S"
        assert result["h2s_confirmed"] is True
        assert result["temperature_min_c"] == -40.0
        assert result["climate_version"] == "УХЛ"

    def test_is_valid_medium(self, environment_parser):
        """Тест валидности среды"""
        assert environment_parser.is_valid_medium("H2S") is True
        assert environment_parser.is_valid_medium("нефть") is True
        assert environment_parser.is_valid_medium("воздух") is False
    def test_parse_h2s_environment(self, environment_parser):
        """Тест среды H2S"""
        result = environment_parser.parse("для H2S")
        assert result["medium"] == "H2S"
        assert result["h2s_confirmed"] is True

    def test_parse_h2s_with_context(self, environment_parser):
        """Тест H2S с контекстом"""
        result = environment_parser.parse("для участка с H2S")
        assert result["medium"] == "H2S"
        assert result["h2s_confirmed"] is True

    def test_parse_co2_environment(self, environment_parser):
        """Тест среды CO2"""
        result = environment_parser.parse("для газа с CO2")
        assert result["medium"] == "CO2"
        assert result["co2_confirmed"] is True

    def test_parse_corrosion_environment(self, environment_parser):
        """Тест коррозионной среды"""
        result = environment_parser.parse("для коррозионного участка")
        # Должна определиться как H2S или аналогичная среда
        assert result["medium"] in ["H2S", "CO2", None]

    def test_parse_environment_with_unit(self, environment_parser):
        """Тест среды с UNIT"""
        result = environment_parser.parse("участок UNIT-SYN-H2S-001")
        assert result["medium"] == "H2S" or result["h2s_confirmed"] is True

    def test_parse_temperature_with_environment(self, environment_parser):
        """Тест температуры со средой"""
        result = environment_parser.parse("для H2S температура -40°C")
        assert result["medium"] == "H2S"
        assert result["temperature_min_c"] == -40.0

    def test_parse_co2_confirmed(self, environment_parser):
        """«для CO2» → co2_confirmed True"""
        result = environment_parser.parse("позиции с остатком меньше трёх штук для участка с CO2")
        assert result["medium"] == "CO2"
        assert result["co2_confirmed"] is True

    def test_parse_co2_not_confirmed_negation(self, environment_parser):
        """«ещё не подтверждены для CO2» → co2_confirmed False"""
        result = environment_parser.parse("какие детали подходят по размерам, но ещё не подтверждены для CO2")
        assert result["medium"] == "CO2"
        assert result["co2_confirmed"] is False

    def test_parse_h2s_not_confirmed_negation(self, environment_parser):
        """«не подтверждены для H2S» → h2s_confirmed False"""
        result = environment_parser.parse("детали, которые не подтверждены для H2S")
        assert result["medium"] == "H2S"
        assert result["h2s_confirmed"] is False
