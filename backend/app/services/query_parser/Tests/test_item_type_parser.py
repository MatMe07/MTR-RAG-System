# tests/test_item_type_parser.py

import pytest
# from query_parser.parsers.item_type_parser import ItemTypeParser


class TestItemTypeParser:
    """Тесты для ItemTypeParser"""

    def test_parse_elbow(self, item_type_parser):
        """Тест отвода"""
        result = item_type_parser.parse_all("отвод 90")
        assert "отвод" in result

    def test_parse_pipe(self, item_type_parser):
        """Тест трубы"""
        result = item_type_parser.parse_all("труба DN200")
        assert "труба" in result

    def test_parse_valve(self, item_type_parser):
        """Тест задвижки"""
        result = item_type_parser.parse_all("задвижка DN150")
        assert "задвижка" in result

    def test_parse_cap(self, item_type_parser):
        """Тест заглушки"""
        result = item_type_parser.parse_all("заглушка DN100")
        assert "заглушка" in result

    def test_parse_transition(self, item_type_parser):
        """Тест перехода"""
        result = item_type_parser.parse_all("переход 219x159")
        assert "переход" in result

    def test_parse_tee(self, item_type_parser):
        """Тест тройника"""
        result = item_type_parser.parse_all("тройник 159x89")
        assert "тройник" in result

    def test_parse_crane(self, item_type_parser):
        """Тест крана"""
        result = item_type_parser.parse_all("кран шаровой")
        assert "кран" in result

    def test_parse_alias(self, item_type_parser):
        """Тест алиасов"""
        result = item_type_parser.parse_all("кш DN200")  # кш -> кран
        assert "кран" in result

    def test_parse_multiple_types(self, item_type_parser):
        """Тест нескольких типов"""
        result = item_type_parser.parse_all("труба и задвижка")
        assert "труба" in result
        assert "задвижка" in result

    def test_parse_subtype_valve(self, item_type_parser):
        """Тест подтипа задвижки"""
        result = item_type_parser.parse_subtype("задвижка клиновая")
        assert result == "клиновая"

    def test_parse_subtype_elbow(self, item_type_parser):
        """Тест подтипа отвода"""
        result = item_type_parser.parse_subtype("отвод крутоизогнутый")
        assert result == "крутоизогнутый"

    def test_parse_subtype_pipe(self, item_type_parser):
        """Тест подтипа трубы"""
        result = item_type_parser.parse_subtype("труба бесшовная")
        assert result == "бесшовная"

    def test_is_valid_type(self, item_type_parser):
        """Тест валидности типа"""
        assert item_type_parser.is_valid_type("отвод") is True
        assert item_type_parser.is_valid_type("несуществующий") is False

    def test_get_all_item_types(self, item_type_parser):
        """Тест получения всех типов"""
        types = item_type_parser.get_all_item_types()
        assert "отвод" in types
        assert "труба" in types
        assert len(types) >= 6
    def test_parse_item_type_cap(self, item_type_parser):
        """Тест заглушки"""
        result = item_type_parser.parse_all("Найди заглушку 426 на 12")
        assert "заглушка" in result

    def test_parse_item_type_elbow(self, item_type_parser):
        """Тест отвода"""
        result = item_type_parser.parse_all("найди отвод 90 426 на 10")
        assert "отвод" in result

    def test_parse_item_type_valve(self, item_type_parser):
        """Тест задвижки"""
        result = item_type_parser.parse_all("Найди замину задвижке DN150 PN40")
        assert "задвижка" in result

    def test_parse_item_type_pipe(self, item_type_parser):
        """Тест трубы"""
        result = item_type_parser.parse_all("Нужна замена бесшовной трубы 108 на 6")
        assert "труба" in result

    def test_parse_item_type_transition(self, item_type_parser):
        """Тест перехода"""
        result = item_type_parser.parse_all("Подбери переход с 219 на 159")
        assert "переход" in result

    def test_parse_item_type_tee(self, item_type_parser):
        """Тест тройника"""
        result = item_type_parser.parse_all("проверь, хватает ли тройников по две штуки")
        assert "тройник" in result

    def test_parse_multiple_item_types(self, item_type_parser):
        """Тест нескольких типов деталей"""
        result = item_type_parser.parse_all("проверь, хватает ли труб, отводов, переходов, задвижек, заглушек и тройников")
        assert "труба" in result
        assert "отвод" in result
        assert "переход" in result
        assert "задвижка" in result
        assert "заглушка" in result
        assert "тройник" in result
