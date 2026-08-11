# tests/test_hybrid_parser.py

import pytest
# from query_parser.hybrid_parser import HybridParser


class TestHybridParser:
    """Интеграционные тесты для HybridParser на реальных запросах"""

    def test_hybrid_query_1(self, hybrid_parser):
        """Тест: Найди заглушку 426 на 12 из стали 09ГСФ"""
        result = hybrid_parser.parse("Найди заглушку 426 на 12 из стали 09ГСФ")
        assert "search" in result.operations
        assert "заглушка" in result.item_types
        assert result.card.geometry.dn == 426.0
        assert result.card.geometry.wall_thickness == 12.0
        assert result.card.material.steel_grade == "09ГСФ"

    def test_hybrid_query_2(self, hybrid_parser):
        """Тест: найди отвод 90 426 на 10 для H2S"""
        result = hybrid_parser.parse("найди отвод 90 426 на 10 для H2S")
        assert "search" in result.operations
        assert "отвод" in result.item_types
        assert result.card.geometry.angle == 90.0
        assert result.card.geometry.dn == 426.0
        assert result.card.environment.medium == "H2S"

    def test_hybrid_query_4(self, hybrid_parser):
        """Тест: Какой аналог отвода 90 426 на 10 подойдёт для H2S"""
        result = hybrid_parser.parse("Какой аналог отвода 90 426 на 10 подойдёт для H2S, покажи сначала то, что есть на складе")
        assert "replace" in result.operations
        assert "search" in result.operations
        assert "отвод" in result.item_types
        assert result.card.geometry.angle == 90.0
        assert result.card.geometry.dn == 426.0
        assert result.card.environment.medium == "H2S"

    def test_hybrid_query_5(self, hybrid_parser):
        """Тест: У меня сломался отвод 90 426 на 10 на участке с H2S"""
        result = hybrid_parser.parse("У меня сломался отвод 90 426 на 10 на участке с H2S, предложи план замены и список деталей для ремонта")
        assert "repair" in result.operations
        assert "plan" in result.operations
        assert "отвод" in result.item_types
        assert result.card.geometry.angle == 90.0
        assert result.card.geometry.dn == 426.0
        assert result.card.environment.medium == "H2S"

    def test_hybrid_query_8(self, hybrid_parser):
        """Тест: Подбери переход с 219 на 159 для газа с CO2"""
        result = hybrid_parser.parse("Подбери переход с 219 на 159 для газа с CO2, нужен вариант из наличия и с объяснением отличий")
        assert "replace" in result.operations
        assert "explain" in result.operations
        assert "переход" in result.item_types
        assert result.card.geometry.d1 == 219.0
        assert result.card.geometry.d2 == 159.0
        assert result.card.environment.medium == "CO2"

    def test_hybrid_query_38(self, hybrid_parser):
        """Тест: Хотим поставить задвижку DN200 вместо DN150"""
        result = hybrid_parser.parse("Хотим поставить задвижку DN200 вместо DN150, покажи, какие соседние детали придётся заменить или проверить")
        
        # Отладочный вывод
        print(f"Operations: {result.operations}")
        print(f"Natasha operations: {hybrid_parser.natasha_parser.parse('Хотим поставить задвижку DN200 вместо DN150, покажи, какие соседние детали придётся заменить или проверить')['operations']}")
        
        assert "impact" in result.operations
        assert "replace" in result.operations
        assert "задвижка" in result.item_types
        assert result.proposed_changes.get("dn_from") == 150.0
        assert result.proposed_changes.get("dn_to") == 200.0
