# tests/conftest.py

import pytest
from typing import Dict, Any


@pytest.fixture
def sample_queries() -> Dict[str, str]:
    """Образцы запросов для тестирования"""
    return {
        "elbow_simple": "отвод 90 DN200",
        "elbow_full": "отвод 90 426 на 10 сталь 20",
        "transition": "переход 219x159",
        "tee": "тройник 159x89",
        "pipe": "труба DN200 стенка 8",
        "valve": "задвижка DN150 PN16",
        "cap": "заглушка DN100 PN25",
        "with_environment": "отвод 90 DN200 среда H2S температура -40°C",
        "with_component": "COMP-1234 на участке UNIT-001",
        "with_gost": "по ГОСТ 12345-67",
        "complex": "срочно нужно 5 штук отводов 90 DN200 PN16 сталь 20 для H2S среды",
    }


@pytest.fixture
def expected_results() -> Dict[str, Any]:
    """Ожидаемые результаты для sample_queries"""
    return {
        "elbow_simple": {
            "item_type": "отвод",
            "dn": 200.0,
            "angle": 90.0,
        },
        "transition": {
            "item_type": "переход",
            "d1": 219.0,
            "d2": 159.0,
        },
        "valve": {
            "item_type": "задвижка",
            "dn": 150.0,
            "pn": 1.6,
        },
    }


@pytest.fixture
def component_parser():
    """Фикстура для ComponentParser"""
    from query_parser.parsers.component_parser import ComponentParser
    return ComponentParser()


@pytest.fixture
def operation_parser():
    """Фикстура для OperationParser"""
    from query_parser.parsers.operation_parser import OperationParser
    return OperationParser()


@pytest.fixture
def item_type_parser():
    """Фикстура для ItemTypeParser"""
    from query_parser.parsers.item_type_parser import ItemTypeParser
    return ItemTypeParser()


@pytest.fixture
def geometry_parser():
    """Фикстура для GeometryParser"""
    from query_parser.parsers.geometry_parser import GeometryParser
    return GeometryParser()


@pytest.fixture
def pressure_parser():
    """Фикстура для PressureParser"""
    from query_parser.parsers.pressure_parser import PressureParser
    return PressureParser()


@pytest.fixture
def material_parser():
    """Фикстура для MaterialParser"""
    from query_parser.parsers.material_parser import MaterialParser
    return MaterialParser()


@pytest.fixture
def environment_parser():
    """Фикстура для EnvironmentParser"""
    from query_parser.parsers.environment_parser import EnvironmentParser
    return EnvironmentParser()


@pytest.fixture
def normative_parser():
    """Фикстура для NormativeParser"""
    from query_parser.parsers.normative_parser import NormativeParser
    return NormativeParser()


@pytest.fixture
def context_parser():
    """Фикстура для ContextParser"""
    from query_parser.parsers.context_parser import ContextParser
    return ContextParser()


@pytest.fixture
def ambiguity_detector():
    """Фикстура для AmbiguityDetector"""
    from query_parser.ambiguity_detector import AmbiguityDetector
    return AmbiguityDetector()


@pytest.fixture
def query_parser():
    """Фикстура для QueryParser"""
    from query_parser.parser import QueryParser
    return QueryParser()


@pytest.fixture
def hybrid_parser():
    """Фикстура для HybridParser"""
    from query_parser.hybrid_parser import HybridParser
    return HybridParser()
