# tests/test_normative_parser.py

import pytest
# from query_parser.parsers.normative_parser import NormativeParser


class TestNormativeParser:
    """Тесты для NormativeParser"""

    def test_parse_gost_full(self, normative_parser):
        """Тест полного ГОСТа"""
        result = normative_parser.parse("ГОСТ 12345-67")
        assert result["gost_tu"] == "ГОСТ 12345-67"

    def test_parse_gost_full_with_year(self, normative_parser):
        """Тест ГОСТа с годом"""
        result = normative_parser.parse("ГОСТ 12345-67-89")
        assert result["gost_tu"] == "ГОСТ 12345-67-89"

    def test_parse_tu_full(self, normative_parser):
        """Тест полного ТУ"""
        result = normative_parser.parse("ТУ 1234-567-89")
        assert result["gost_tu"] == "ТУ 1234-567-89"

    def test_parse_tu_with_dot(self, normative_parser):
        """Тест ТУ с точкой"""
        result = normative_parser.parse("ТУ 1234.567-89")
        assert result["gost_tu"] == "ТУ 1234.567-89"

    def test_parse_sto(self, normative_parser):
        """Тест СТО"""
        result = normative_parser.parse("СТО 12345-67")
        assert result["sto"] == "СТО 12345-67"

    def test_parse_lnd(self, normative_parser):
        """Тест ЛНД"""
        result = normative_parser.parse("согласно ЛНД раздел 5.2")
        assert "ЛНД раздел 5.2" in result["lnd_sections"]

    def test_parse_passport(self, normative_parser):
        """Тест паспорта"""
        result = normative_parser.parse("паспорт 12345")
        assert result["passport"] == "паспорт 12345"

    def test_parse_certificate(self, normative_parser):
        """Тест сертификата"""
        result = normative_parser.parse("сертификат 12345")
        assert result["certificate"] == "сертификат 12345"

    def test_parse_multiple(self, normative_parser):
        """Тест нескольких нормативов"""
        result = normative_parser.parse("ГОСТ 12345-67 и ТУ 1234-567-89")
        assert result["gost_tu"] == "ГОСТ 12345-67"

    def test_parse_no_normative(self, normative_parser):
        """Тест без нормативов"""
        result = normative_parser.parse("отвод 90")
        assert result is None

    def test_is_valid_gost_tu(self, normative_parser):
        """Тест валидности ГОСТ/ТУ"""
        assert normative_parser.is_valid_gost_tu("ГОСТ 12345-67") is True
        assert normative_parser.is_valid_gost_tu("ТУ 1234-567") is True
        assert normative_parser.is_valid_gost_tu("невалидный") is False

    def test_extract_gost_number(self, normative_parser):
        """Тест структурированного извлечения ГОСТа"""
        result = normative_parser.extract_gost_number("ГОСТ 12345-67")
        assert result["prefix"] == "ГОСТ"
        assert result["number"] == "12345"
        assert result["year"] == "67"
