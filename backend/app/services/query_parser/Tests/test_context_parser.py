# tests/test_context_parser.py

import pytest
# from query_parser.parsers.context_parser import ContextParser


class TestContextParser:
    """Тесты для ContextParser"""

    def test_parse_quantity(self, context_parser):
        """Тест количества штук"""
        result = context_parser.parse("нужно 5 штук")
        assert result["quantity"] == 5

    def test_parse_quantity_words(self, context_parser):
        """Тест количества словами"""
        result = context_parser.parse("по две штуки")
        assert result["quantity"] == 2

    def test_parse_quantity_with_item(self, context_parser):
        """Тест количества с типом детали"""
        result = context_parser.parse("два отвода")
        assert result["quantity"] == 2

    def test_parse_units_count(self, context_parser):
        """Тест количества участков"""
        result = context_parser.parse("трёх участков")
        assert result["units_count"] == 3

    def test_parse_units_count_words(self, context_parser):
        """Тест количества участков словами"""
        result = context_parser.parse("трёх таких же участков")
        assert result["units_count"] == 3

    def test_parse_length_meters(self, context_parser):
        """Тест длины в метрах"""
        result = context_parser.parse("длина 50 метров")
        assert result["length_meters"] == 50.0

    def test_parse_length_km(self, context_parser):
        """Тест длины в километрах"""
        result = context_parser.parse("2 км")
        assert result["length_meters"] == 2000.0

    def test_parse_timeframe_week(self, context_parser):
        """Тест временных рамок (неделя)"""
        result = context_parser.parse("следующая неделя")
        assert result["timeframe"] == "следующая неделя"

    def test_parse_timeframe_now(self, context_parser):
        """Тест временных рамок (сейчас)"""
        result = context_parser.parse("сегодня")
        assert result["timeframe"] == "сегодня"

    def test_parse_urgency(self, context_parser):
        """Тест срочности"""
        result = context_parser.parse("срочно нужно")
        assert result["urgency"] == "high"

    def test_parse_reference_implicit(self, context_parser):
        """Тест имплицитной ссылки"""
        result = context_parser.parse("такой же как у")
        refs = result.get("references", [])
        assert len(refs) > 0
        assert refs[0].reference_type == "implicit_reference"

    def test_parse_full(self, context_parser):
        """Тест полного контекста"""
        result = context_parser.parse("срочно нужно 5 штук на участке UNIT-001")
        assert result["quantity"] == 5
        assert result["urgency"] == "high"
        refs = result.get("references", [])
        assert any(r.reference_type == "unit" for r in refs)
    def test_parse_context_quantity_two(self, context_parser):
        """Тест количества 'по две штуки'"""
        result = context_parser.parse("по две штуки")
        assert result["quantity"] == 2

    def test_parse_context_units_count_three(self, context_parser):
        """Тест количества участков 'трёх таких же участков'"""
        result = context_parser.parse("для ремонта трёх таких же участков")
        assert result["units_count"] == 3

    def test_parse_context_length_100m(self, context_parser):
        """Тест длины 100 метров"""
        result = context_parser.parse("для нового участка DN150 PN40 с газом H2S длиной сто метров")
        assert result["length_meters"] == 100.0

    def test_parse_context_urgency_schedule(self, context_parser):
        """Тест срочности 'На следующей неделе'"""
        result = context_parser.parse("На следующей неделе ремонт участка с H2S")
        assert "timeframe" in result

    def test_parse_context_urgency_high(self, context_parser):
        """Тест срочности 'срочно'"""
        result = context_parser.parse("срочно нужно")
        assert result["urgency"] == "high"

    def test_parse_context_implicit_reference_same(self, context_parser):
        """Тест имплицитной ссылки 'таких же'"""
        result = context_parser.parse("трёх таких же участков")
        refs = result.get("references", [])
        assert len(refs) > 0
        assert any(r.reference_type == "implicit_reference" for r in refs)

    def test_parse_context_complex(self, context_parser):
        """Тест сложного контекста"""
        result = context_parser.parse("На следующей неделе ремонт участка с H2S, проверь, хватает ли труб, отводов, переходов, задвижек, заглушек и тройников по две штуки")
        assert result["timeframe"] == "следующая неделя" or "week" in str(result)
        assert result["quantity"] == 2
