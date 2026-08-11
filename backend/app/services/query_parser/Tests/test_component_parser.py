# tests/test_component_parser.py

import pytest
# from query_parser.parsers.component_parser import ComponentParser


class TestComponentParser:
    """Тесты для ComponentParser (объединённый)"""

    # ============ IDENTIFIERS ============
    
    def test_parse_component(self, component_parser):
        """Тест COMP-идентификатора"""
        result = component_parser.parse_all("COMP-1234")
        assert result["component_ids"] == ["COMP-1234"]

    def test_parse_unit(self, component_parser):
        """Тест UNIT-идентификатора"""
        result = component_parser.parse_all("UNIT-001")
        assert result["unit_ids"] == ["UNIT-001"]

    def test_parse_ksm(self, component_parser):
        """Тест KSM-идентификатора"""
        result = component_parser.parse_all("KSM-001")
        assert result["ksm_codes"] == ["KSM-001"]

    def test_parse_mtr(self, component_parser):
        """Тест MTR-идентификатора"""
        result = component_parser.parse_all("MTR-002")
        assert result["mtr_codes"] == ["MTR-002"]

    def test_parse_multiple_ids(self, component_parser):
        """Тест нескольких идентификаторов"""
        result = component_parser.parse_all("COMP-1234 и UNIT-001")
        assert "COMP-1234" in result["component_ids"]
        assert "UNIT-001" in result["unit_ids"]

    def test_parse_component_lowercase(self, component_parser):
        """Тест COMP в нижнем регистре"""
        result = component_parser.parse_all("comp-1234")
        assert "COMP-1234" in result["component_ids"]

    def test_parse_unit_lowercase(self, component_parser):
        """Тест UNIT в нижнем регистре"""
        result = component_parser.parse_all("unit-001")
        assert "UNIT-001" in result["unit_ids"]

    def test_parse_ksm_complex(self, component_parser):
        """Тест KSM с длинным кодом"""
        result = component_parser.parse_all("KSM-SYN-REG-000591")
        assert "KSM-SYN-REG-000591" in result["ksm_codes"]

    def test_parse_no_ids(self, component_parser):
        """Тест без идентификаторов"""
        result = component_parser.parse_all("отвод 90")
        assert result["component_ids"] == []
        assert result["unit_ids"] == []

    # ============ CONTEXT SEARCH ============

    def test_parse_component_context(self, component_parser):
        """Тест контекстного поиска COMP"""
        result = component_parser.parse_all("деталь 12345")
        assert "COMP-12345" in result["component_ids"]

    def test_parse_unit_context(self, component_parser):
        """Тест контекстного поиска UNIT"""
        result = component_parser.parse_all("участок 67890")
        assert "UNIT-67890" in result["unit_ids"]

    # ============ SINGLE METHODS ============

    def test_parse_component_single(self, component_parser):
        """Тест parse_component"""
        result = component_parser.parse_component("COMP-1234")
        assert result == "COMP-1234"

    def test_parse_unit_single(self, component_parser):
        """Тест parse_unit"""
        result = component_parser.parse_unit("UNIT-001")
        assert result == "UNIT-001"

    def test_parse_ksm_single(self, component_parser):
        """Тест parse_ksm"""
        result = component_parser.parse_ksm("KSM-001")
        assert result == "KSM-001"

    def test_parse_mtr_single(self, component_parser):
        """Тест parse_mtr"""
        result = component_parser.parse_mtr("MTR-002")
        assert result == "MTR-002"

    # ============ REAL QUERIES FROM DATASET ============

    @pytest.mark.parametrize("query, expected_components, expected_units, expected_ksm", [
        # UNIT ссылки
        (
            "Посчитай запас деталей для ремонта трёх таких же участков, как UNIT-SYN-GAS-001",
            [],
            ["UNIT-SYN-GAS-001"],
            []
        ),
        (
            "Составь план обслуживания участка UNIT-SYN-H2S-001 на следующий месяц",
            [],
            ["UNIT-SYN-H2S-001"],
            []
        ),
        (
            "Подготовь список деталей для замены задвижки на участке UNIT-SYN-GAS-001",
            [],
            ["UNIT-SYN-GAS-001"],
            []
        ),
        (
            "Покажи, из каких деталей состоит участок UNIT-SYN-H2S-001",
            [],
            ["UNIT-SYN-H2S-001"],
            []
        ),
        (
            "Проверь весь участок UNIT-SYN-CO2-001",
            [],
            ["UNIT-SYN-CO2-001"],
            []
        ),
        (
            "Найди паспорта для всех деталей участка UNIT-SYN-H2S-001",
            [],
            ["UNIT-SYN-H2S-001"],
            []
        ),
        (
            "Участок UNIT-SYN-GAS-001 переводят с природного газа на H2S",
            [],
            ["UNIT-SYN-GAS-001"],
            []
        ),
        
        # COMP ссылки
        (
            "На участке с H2S отказала задвижка COMP-SYN-010",
            ["COMP-SYN-010"],
            [],
            []
        ),
        (
            "У меня сломался отвод COMP-SYN-008",
            ["COMP-SYN-008"],
            [],
            []
        ),
        (
            "Задвижка COMP-SYN-010 сломалась",
            ["COMP-SYN-010"],
            [],
            []
        ),
        (
            "Повреждён переход COMP-SYN-009",
            ["COMP-SYN-009"],
            [],
            []
        ),
        (
            "Заглушка COMP-SYN-011 повреждена",
            ["COMP-SYN-011"],
            [],
            []
        ),
        (
            "Покажи, что стоит до и после задвижки COMP-SYN-010",
            ["COMP-SYN-010"],
            [],
            []
        ),
        
        # KSM ссылки
        (
            "Расскажи про задвижку KSM-SYN-REG-000591",
            [],
            [],
            ["KSM-SYN-REG-000591"]
        ),
        (
            "Объясни параметры трубы KSM-SYN-REG-000004",
            [],
            [],
            ["KSM-SYN-REG-000004"]
        ),
        (
            "Покажи ГОСТы для отвода KSM-SYN-REG-000242",
            [],
            [],
            ["KSM-SYN-REG-000242"]
        ),
        
        # Смешанные ссылки
        (
            "Покажи участок UNIT-SYN-H2S-001 и задвижку COMP-SYN-010",
            ["COMP-SYN-010"],
            ["UNIT-SYN-H2S-001"],
            []
        ),
        (
            "На участке UNIT-SYN-H2S-001 сломалась задвижка COMP-SYN-010",
            ["COMP-SYN-010"],
            ["UNIT-SYN-H2S-001"],
            []
        ),
        (
            "Повреждён переход COMP-SYN-009 на участке UNIT-SYN-CO2-001",
            ["COMP-SYN-009"],
            ["UNIT-SYN-CO2-001"],
            []
        ),
        (
            "Найди паспорта для COMP-SYN-010 и UNIT-SYN-H2S-001",
            ["COMP-SYN-010"],
            ["UNIT-SYN-H2S-001"],
            []
        ),
        
        # Нет ссылок
        (
            "Найди заглушку 426 на 12 из стали 09ГСФ",
            [],
            [],
            []
        ),
        (
            "найди отвод 90 426 на 10 для H2S",
            [],
            [],
            []
        ),
        (
            "Подбери переход с 219 на 159 для газа с CO2",
            [],
            [],
            []
        ),
        (
            "Объясни, что означает отвод 90 426 на 10",
            [],
            [],
            []
        ),
        (
            "Сколько отводов 90 426 на 10 есть на складе",
            [],
            [],
            []
        ),
        (
            "Нужно заменить шесть метров трубы 108 на 6",
            [],
            [],
            []
        ),
    ])
    def test_real_queries(self, component_parser, query, expected_components, expected_units, expected_ksm):
        """Тест реальных запросов из датасета"""
        result = component_parser.parse_all(query)
        
        # Проверяем COMP
        for comp in expected_components:
            assert comp in result["component_ids"], f"COMP {comp} not found in {query}"
        
        # Проверяем UNIT
        for unit in expected_units:
            assert unit in result["unit_ids"], f"UNIT {unit} not found in {query}"
        
        # Проверяем KSM
        for ksm in expected_ksm:
            assert ksm in result["ksm_codes"], f"KSM {ksm} not found in {query}"
        
        # Проверяем, что лишних нет
        if not expected_components:
            assert result["component_ids"] == [], f"Unexpected COMP in {query}: {result['component_ids']}"
        if not expected_units:
            assert result["unit_ids"] == [], f"Unexpected UNIT in {query}: {result['unit_ids']}"
        if not expected_ksm:
            assert result["ksm_codes"] == [], f"Unexpected KSM in {query}: {result['ksm_codes']}"

    # ============ EDGE CASES ============
    @pytest.mark.parametrize("query, expected_components, expected_units, expected_ksm", [
        ("COMP-001 и UNIT-002 и KSM-003", ["COMP-001"], ["UNIT-002"], ["KSM-003"]),
    ])
    def test_multiple_ids(self, component_parser, query, expected_components, expected_units, expected_ksm):
        """Тест множественных идентификаторов"""
        result = component_parser.parse_all(query)
        
        # Проверяем COMP
        if expected_components:
            for comp in expected_components:
                assert comp in result["component_ids"]
        else:
            assert result["component_ids"] == []
        
        # Проверяем UNIT
        if expected_units:
            for unit in expected_units:
                assert unit in result["unit_ids"]
        else:
            assert result["unit_ids"] == []
        
        # Проверяем KSM
        if expected_ksm:
            for ksm in expected_ksm:
                assert ksm in result["ksm_codes"]
        else:
            assert result["ksm_codes"] == []


    @pytest.mark.parametrize("query", [
    "comp-1234",  # только латиница
    "unit-001",
    "ksm-001",
    "mtr-001",
    ])
    def test_cyrillic_prefixes(self, component_parser, query):
        """Тест lowercase префиксов"""
        result = component_parser.parse_all(query)
        
        if "comp" in query:
            assert "COMP-1234" in result["component_ids"]
        elif "unit" in query:
            assert "UNIT-001" in result["unit_ids"]
        elif "ksm" in query:
            assert "KSM-001" in result["ksm_codes"]
        elif "mtr" in query:
            assert "MTR-001" in result["mtr_codes"]

    @pytest.mark.parametrize("query, expected_type, expected_id", [
        ("задвижка COMP-SYN-010", "component", "COMP-SYN-010"),
        ("участок UNIT-SYN-H2S-001", "unit", "UNIT-SYN-H2S-001"),
        ("код KSM-SYN-REG-000591", "ksm", "KSM-SYN-REG-000591"),
        ("МТР MTR-001", "mtr", "MTR-001"),
    ])
    def test_context_extraction(self, component_parser, query, expected_type, expected_id):
        """Тест извлечения из контекста"""
        result = component_parser.parse_all(query)
        if expected_type == "component":
            assert expected_id in result["component_ids"]
        elif expected_type == "unit":
            assert expected_id in result["unit_ids"]
        elif expected_type == "ksm":
            assert expected_id in result["ksm_codes"]
        elif expected_type == "mtr":
            assert expected_id in result["mtr_codes"]

    # ============ NEGATIVE TESTS ============

    @pytest.mark.parametrize("query", [
        "COMP",
        "UNIT",
        "KSM",
        "MTR",
        "COMP-",
        "UNIT-",
        "KSM-",
        "MTR-",
        "com",
        "unit",
        "ksm",
        "mtr",
        "comp-",
        "unit-",
        "ksm-",
        "mtr-",
    ])
    def test_invalid_ids(self, component_parser, query):
        """Тест невалидных идентификаторов"""
        result = component_parser.parse_all(query)
        assert result["component_ids"] == []
        assert result["unit_ids"] == []
        assert result["ksm_codes"] == []
        assert result["mtr_codes"] == []

    @pytest.mark.parametrize("query", [
        "COMP-1234 и COMP-5678",
        "UNIT-001 и UNIT-002",
        "KSM-001 и KSM-002",
        "MTR-001 и MTR-002",
    ])
    def test_multiple_same_type(self, component_parser, query):
        """Тест множественных однотипных идентификаторов"""
        result = component_parser.parse_all(query)
        if "COMP" in query:
            assert len(result["component_ids"]) >= 2
        elif "UNIT" in query:
            assert len(result["unit_ids"]) >= 2
        elif "KSM" in query:
            assert len(result["ksm_codes"]) >= 2
        elif "MTR" in query:
            assert len(result["mtr_codes"]) >= 2

    @pytest.mark.parametrize("query, expected_count", [
        ("COMP-001 COMP-002 COMP-003", 3),
        ("UNIT-001 UNIT-002", 2),
        ("KSM-001 KSM-002 KSM-003 KSM-004", 4),
        ("MTR-001 MTR-002 MTR-003", 3),
    ])
    def test_multiple_count(self, component_parser, query, expected_count):
        """Тест подсчёта множественных идентификаторов"""
        result = component_parser.parse_all(query)
        if "COMP" in query:
            assert len(result["component_ids"]) == expected_count
        elif "UNIT" in query:
            assert len(result["unit_ids"]) == expected_count
        elif "KSM" in query:
            assert len(result["ksm_codes"]) == expected_count
        elif "MTR" in query:
            assert len(result["mtr_codes"]) == expected_count

    def test_parse_component_syn_010(self, component_parser):
        """Тест COMP-SYN-010"""
        result = component_parser.parse_all("COMP-SYN-010")
        assert "COMP-SYN-010" in result["component_ids"]

    def test_parse_unit_syn_h2s_001(self, component_parser):
        """Тест UNIT-SYN-H2S-001"""
        result = component_parser.parse_all("участок UNIT-SYN-H2S-001")
        assert "UNIT-SYN-H2S-001" in result["unit_ids"]

    def test_parse_unit_syn_gas_001(self, component_parser):
        """Тест UNIT-SYN-GAS-001"""
        result = component_parser.parse_all("участок UNIT-SYN-GAS-001")
        assert "UNIT-SYN-GAS-001" in result["unit_ids"]

    def test_parse_unit_syn_co2_001(self, component_parser):
        """Тест UNIT-SYN-CO2-001"""
        result = component_parser.parse_all("участок UNIT-SYN-CO2-001")
        assert "UNIT-SYN-CO2-001" in result["unit_ids"]

    def test_parse_ksm_syn_reg_000591(self, component_parser):
        """Тест KSM-SYN-REG-000591"""
        result = component_parser.parse_all("KSM-SYN-REG-000591")
        assert "KSM-SYN-REG-000591" in result["ksm_codes"]

    def test_parse_ksm_syn_reg_000242(self, component_parser):
        """Тест KSM-SYN-REG-000242"""
        result = component_parser.parse_all("KSM-SYN-REG-000242")
        assert "KSM-SYN-REG-000242" in result["ksm_codes"]

    def test_parse_ksm_syn_reg_000004(self, component_parser):
        """Тест KSM-SYN-REG-000004"""
        result = component_parser.parse_all("KSM-SYN-REG-000004")
        assert "KSM-SYN-REG-000004" in result["ksm_codes"]

    def test_parse_multiple_component_ids(self, component_parser):
        """Тест нескольких COMP ID"""
        result = component_parser.parse_all("COMP-SYN-008 и COMP-SYN-009")
        assert "COMP-SYN-008" in result["component_ids"]
        assert "COMP-SYN-009" in result["component_ids"]

    def test_parse_all_ids_in_context(self, component_parser):
        """Тест всех ID в контексте"""
        result = component_parser.parse_all("COMP-SYN-010 сломалась на участке UNIT-SYN-H2S-001")
        assert "COMP-SYN-010" in result["component_ids"]
        assert "UNIT-SYN-H2S-001" in result["unit_ids"]
# @pytest.fixture
# def component_parser():
#     """Фикстура для ComponentParser"""
#     return ComponentParser()
