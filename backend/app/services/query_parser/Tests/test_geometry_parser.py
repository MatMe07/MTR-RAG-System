# tests/test_geometry_parser.py

import pytest
# from query_parser.parsers.geometry_parser import GeometryParser


class TestGeometryParser:
    """Тесты для GeometryParser"""

    def test_parse_elbow_simple(self, geometry_parser):
        """Тест простого отвода"""
        result = geometry_parser.parse("отвод 90 DN200")
        assert result["angle"] == 90.0
        assert result["dn"] == 200.0

    def test_parse_elbow_full(self, geometry_parser):
        """Тест полного отвода"""
        result = geometry_parser.parse("отвод 90 426 на 10")
        assert result["angle"] == 90.0
        assert result["dn"] == 426.0
        assert result["wall_thickness"] == 10.0

    def test_parse_transition(self, geometry_parser):
        """Тест перехода"""
        result = geometry_parser.parse("переход 219x159")
        assert result["d1"] == 219.0
        assert result["d2"] == 159.0
        assert result["dn"] == 219.0

    def test_parse_tee(self, geometry_parser):
        """Тест тройника"""
        result = geometry_parser.parse("тройник 159x89")
        assert result["d1"] == 159.0
        assert result["d2"] == 89.0

    def test_parse_pipe(self, geometry_parser):
        """Тест трубы"""
        result = geometry_parser.parse("труба DN200 стенка 8")
        assert result["dn"] == 200.0
        assert result["wall_thickness"] == 8.0

    def test_parse_angle_degrees(self, geometry_parser):
        """Тест угла в градусах"""
        result = geometry_parser.parse("отвод 45°")
        assert result["angle"] == 45.0

    def test_parse_angle_without_degrees(self, geometry_parser):
        """Тест угла без знака градусов"""
        result = geometry_parser.parse("отвод 90")
        assert result["angle"] == 90.0

    def test_parse_angle_word(self, geometry_parser):
        """Тест угла словом"""
        result = geometry_parser.parse("прямой угол")
        assert result["angle"] == 90.0

    def test_parse_dn_with_du(self, geometry_parser):
        """Тест DN с Ду"""
        result = geometry_parser.parse("Ду 200")
        assert result["dn"] == 200.0

    def test_parse_wall_thickness(self, geometry_parser):
        """Тест толщины стенки"""
        result = geometry_parser.parse("стенка 10")
        assert result["wall_thickness"] == 10.0

    def test_parse_empty(self, geometry_parser):
        """Тест пустого запроса"""
        result = geometry_parser.parse("")
        assert result["dn"] is None
        assert result["angle"] is None

    def test_get_item_types(self, geometry_parser):
        """Тест получения типов деталей"""
        types = geometry_parser.get_item_types()
        assert "elbow" in types
        assert "transition" in types
        assert "pipe" in types
    def test_parse_cap_geometry(self, geometry_parser):
        """Тест геометрии заглушки"""
        result = geometry_parser.parse("заглушка 426 на 12")
        assert result["dn"] == 426.0
        assert result["wall_thickness"] == 12.0

    def test_parse_elbow_geometry(self, geometry_parser):
        """Тест геометрии отвода"""
        result = geometry_parser.parse("отвод 90 426 на 10")
        assert result["angle"] == 90.0
        assert result["dn"] == 426.0
        assert result["wall_thickness"] == 10.0

    def test_parse_valve_geometry(self, geometry_parser):
        """Тест геометрии задвижки"""
        result = geometry_parser.parse("задвижка DN150 PN40")
        assert result["dn"] == 150.0

    def test_parse_pipe_geometry(self, geometry_parser):
        """Тест геометрии трубы"""
        result = geometry_parser.parse("труба 108 на 6")
        assert result["dn"] == 108.0
        assert result["wall_thickness"] == 6.0

    def test_parse_transition_geometry(self, geometry_parser):
        """Тест геометрии перехода"""
        result = geometry_parser.parse("переход с 219 на 159")
        assert result["d1"] == 219.0
        assert result["d2"] == 159.0

    def test_parse_pipe_dn_wall(self, geometry_parser):
        """Тест трубы с DN и стенкой"""
        result = geometry_parser.parse("бесшовной трубы 108 на 6")
        assert result["dn"] == 108.0
        assert result["wall_thickness"] == 6.0

    def test_parse_elbow_angle_in_text(self, geometry_parser):
        """Тест отвода с углом в тексте"""
        result = geometry_parser.parse("отвод 90 426 на 10")
        assert result["angle"] == 90.0

    def test_parse_transition_with_preposition(self, geometry_parser):
        """Тест перехода с предлогом"""
        result = geometry_parser.parse("переход с 219 на 159")
        assert result["d1"] == 219.0
        assert result["d2"] == 159.0
