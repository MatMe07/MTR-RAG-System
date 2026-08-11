# tests/test_parser.py

import pytest
# from query_parser.parser import QueryParser


class TestQueryParser:
    """Интеграционные тесты для QueryParser на реальных запросах"""

    def test_query_1_cap(self, query_parser):
        """Тест: Найди заглушку 426 на 12 из стали 09ГСФ"""
        result = query_parser.parse("Найди заглушку 426 на 12 из стали 09ГСФ")
        assert "search" in result.operations
        assert "заглушка" in result.item_types
        assert result.card.geometry.dn == 426.0
        assert result.card.geometry.wall_thickness == 12.0
        assert result.card.material.steel_grade == "09ГСФ"

    def test_query_2_elbow_h2s(self, query_parser):
        """Тест: найди отвод 90 426 на 10 для H2S"""
        result = query_parser.parse("найди отвод 90 426 на 10 для H2S")
        assert "search" in result.operations
        assert "отвод" in result.item_types
        assert result.card.geometry.angle == 90.0
        assert result.card.geometry.dn == 426.0
        assert result.card.geometry.wall_thickness == 10.0
        assert result.card.environment.medium == "H2S"

    def test_query_3_valve_replacement(self, query_parser):
        """Тест: Найди замину задвижке DN150 PN40 для участка с H2S"""
        result = query_parser.parse("Найди замину задвижке DN150 PN40 для участка с H2S")
        assert "replace" in result.operations
        assert "задвижка" in result.item_types
        assert result.card.geometry.dn == 150.0
        assert result.card.pressure.pn == 4.0
        assert result.card.environment.medium == "H2S"

    def test_query_4_elbow_analog_stock(self, query_parser):
        """Тест: Какой аналог отвода 90 426 на 10 подойдёт для H2S, покажи сначала то, что есть на складе"""
        result = query_parser.parse("Какой аналог отвода 90 426 на 10 подойдёт для H2S, покажи сначала то, что есть на складе")
        assert "replace" in result.operations
        assert "search" in result.operations
        assert "отвод" in result.item_types
        assert result.card.geometry.angle == 90.0
        assert result.card.geometry.dn == 426.0
        assert result.card.geometry.wall_thickness == 10.0

    def test_query_5_repair_plan(self, query_parser):
        """Тест: У меня сломался отвод 90 426 на 10 на участке с H2S, предложи план замены и список деталей для ремонта"""
        result = query_parser.parse("У меня сломался отвод 90 426 на 10 на участке с H2S, предложи план замены и список деталей для ремонта")
        assert "repair" in result.operations
        assert "plan" in result.operations
        assert "отвод" in result.item_types
        assert result.card.geometry.angle == 90.0
        assert result.card.geometry.dn == 426.0
        assert result.card.geometry.wall_thickness == 10.0
        assert result.card.environment.medium == "H2S"

    def test_query_6_pipe_replacement(self, query_parser):
        """Тест: Нужна замена бесшовной трубы 108 на 6 из стали 20 на участке с H2S"""
        result = query_parser.parse("Нужна замена бесшовной трубы 108 на 6 из стали 20 на участке с H2S")
        assert "replace" in result.operations
        assert "труба" in result.item_types
        assert result.card.geometry.dn == 108.0
        assert result.card.geometry.wall_thickness == 6.0
        assert result.card.material.steel_grade == "20"
        assert result.card.environment.medium == "H2S"

    def test_query_7_valve_replacement_stock(self, query_parser):
        """Тест: На складе нет задвижки DN200 PN63, найди подходящую замену и проверь, подойдёт ли она к соседним деталям"""
        result = query_parser.parse("На складе нет задвижки DN200 PN63, найди подходящую замену и проверь, подойдёт ли она к соседним деталям")
        assert "replace" in result.operations
        assert "check" in result.operations
        assert "задвижка" in result.item_types
        assert result.card.geometry.dn == 200.0
        assert result.card.pressure.pn == 6.3

    def test_query_8_transition_analog(self, query_parser):
        """Тест: Подбери переход с 219 на 159 для газа с CO2, нужен вариант из наличия и с объяснением отличий"""
        result = query_parser.parse("Подбери переход с 219 на 159 для газа с CO2, нужен вариант из наличия и с объяснением отличий")
        assert "replace" in result.operations
        assert "explain" in result.operations
        assert "переход" in result.item_types
        assert result.card.geometry.d1 == 219.0
        assert result.card.geometry.d2 == 159.0
        assert result.card.environment.medium == "CO2"

    def test_query_31_assembly(self, query_parser):
        """Тест: Собери список деталей для нового участка DN150 PN40 с газом H2S длиной сто метров"""
        result = query_parser.parse("Собери список деталей для нового участка DN150 PN40 с газом H2S длиной сто метров")
        assert "assemble" in result.operations
        assert "plan" in result.operations
        assert result.card.geometry.dn == 150.0
        assert result.card.pressure.pn == 4.0
        assert result.card.environment.medium == "H2S"

    def test_query_38_impact_analysis(self, query_parser):
        """Тест: Хотим поставить задвижку DN200 вместо DN150, покажи, какие соседние детали придётся заменить или проверить"""
        result = query_parser.parse("Хотим поставить задвижку DN200 вместо DN150, покажи, какие соседние детали придётся заменить или проверить")
        assert "impact" in result.operations
        assert "replace" in result.operations
        assert "задвижка" in result.item_types
        assert result.proposed_changes.get("dn_from") == 150.0
        assert result.proposed_changes.get("dn_to") == 200.0
