# tests/test_operation_parser.py

import pytest
# from query_parser.parsers.operation_parser import OperationParser


class TestOperationParser:
    """Тесты для OperationParser"""

    def test_parse_search(self, operation_parser):
        """Тест поиска"""
        result = operation_parser.parse_all("найди отвод 90")
        assert "search" in result

    def test_parse_replace(self, operation_parser):
        """Тест замены"""
        result = operation_parser.parse_all("замени DN150 на DN200")
        assert "replace" in result

    def test_parse_repair(self, operation_parser):
        """Тест ремонта"""
        result = operation_parser.parse_all("отвод сломался, нужен ремонт")
        assert "repair" in result

    def test_parse_check(self, operation_parser):
        """Тест проверки"""
        result = operation_parser.parse_all("проверь наличие на складе")
        assert "check" in result

    def test_parse_inventory(self, operation_parser):
        """Тест склада"""
        result = operation_parser.parse_all("сколько на складе")
        assert "inventory" in result

    def test_parse_explain(self, operation_parser):
        """Тест объяснения"""
        result = operation_parser.parse_all("объясни чем отличается")
        assert "explain" in result

    def test_parse_document(self, operation_parser):
        """Тест документов"""
        result = operation_parser.parse_all("найди паспорт на задвижку")
        assert "document" in result

    def test_parse_multiple_operations(self, operation_parser):
        """Тест нескольких операций"""
        result = operation_parser.parse_all("проверь наличие и найди замену")
        assert "check" in result
        assert "inventory" in result
        assert "replace" in result

    def test_parse_priority(self, operation_parser):
        """Тест приоритетов"""
        result = operation_parser.parse_all("замени и проверь")
        # replace должен быть выше check
        assert result[0] == "replace"
        assert "check" in result

    def test_parse_unknown(self, operation_parser):
        """Тест неизвестной операции"""
        result = operation_parser.parse_all("непонятный запрос")
        assert result == ["unknown"] or "unknown" in result

    def test_parse_empty(self, operation_parser):
        """Тест пустого запроса"""
        result = operation_parser.parse_all("")
        assert result == ["unknown"]

    def test_get_operation_priority(self, operation_parser):
        """Тест получения приоритета"""
        assert operation_parser.get_operation_priority("repair") == 100
        assert operation_parser.get_operation_priority("unknown") == 0

    def test_parse_search_find(self, operation_parser):
        """Тест поиска (найди)"""
        result = operation_parser.parse_all("Найди заглушку 426 на 12 из стали 09ГСФ")
        assert "search" in result

    def test_parse_search_find_replacement(self, operation_parser):
        """Тест поиска замены"""
        result = operation_parser.parse_all("Найди замину задвижке DN150 PN40 для участка с H2S")
        assert "replace" in result
        assert "search" in result

    def test_parse_check_inventory(self, operation_parser):
        """Тест проверки склада"""
        result = operation_parser.parse_all("проверь, хватает ли труб, отводов, переходов")
        assert "check" in result
        assert "inventory" in result

    def test_parse_inventory_count(self, operation_parser):
        """Тест подсчёта на складе"""
        result = operation_parser.parse_all("Сколько отводов 90 426 на 10 есть на складе")
        assert "inventory" in result

    def test_parse_repair_plan(self, operation_parser):
        """Тест плана ремонта"""
        result = operation_parser.parse_all("У меня сломался отвод 90 426 на 10, предложи план замены")
        assert "repair" in result
        assert "plan" in result

    def test_parse_explain(self, operation_parser):
        """Тест объяснения"""
        result = operation_parser.parse_all("Расскажи простыми словами про задвижку")
        assert "explain" in result

    def test_parse_impact_analysis(self, operation_parser):
        """Тест анализа влияния"""
        result = operation_parser.parse_all("Хотим поставить задвижку DN200 вместо DN150, покажи, какие соседние детали придётся заменить")
        assert "impact" in result
        assert "replace" in result

    def test_parse_assemble(self, operation_parser):
        """Тест сборки комплекта"""
        result = operation_parser.parse_all("Собери список деталей для нового участка DN150 PN40")
        assert "assemble" in result
        assert "plan" in result

    def test_parse_document_passport(self, operation_parser):
        """Тест поиска паспортов"""
        result = operation_parser.parse_all("Найди паспорта и ТУ для всех деталей участка")
        assert "document" in result
        assert "search" in result

    def test_parse_calculate(self, operation_parser):
        """Тест расчёта"""
        result = operation_parser.parse_all("Посчитай запас деталей для ремонта трёх таких же участков")
        assert "calculate" in result
        assert "inventory" in result
