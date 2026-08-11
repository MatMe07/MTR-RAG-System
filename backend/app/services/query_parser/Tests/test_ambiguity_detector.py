# tests/test_ambiguity_detector.py
import sys
import os
from pathlib import Path
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
print(str(Path(__file__).parent.parent.parent))


import pytest
from query_parser.ambiguity_detector import AmbiguitySeverity


class TestAmbiguityDetector:
    """Тесты для AmbiguityDetector"""

    def test_detect_multiple_dn(self, ambiguity_detector):
        """Тест нескольких DN"""
        ambiguities = ambiguity_detector.detect("отвод DN150 и DN200")
        assert len(ambiguities) > 0
        assert any("DN" in amb.reason for amb in ambiguities)

    def test_detect_multiple_angle(self, ambiguity_detector):
        """Тест нескольких углов"""
        ambiguities = ambiguity_detector.detect("отвод 45 и 90")
        assert len(ambiguities) > 0
        assert any("углов" in amb.reason for amb in ambiguities)

    def test_detect_multiple_pn(self, ambiguity_detector):
        """Тест нескольких PN"""
        ambiguities = ambiguity_detector.detect("PN16 и PN40")
        assert len(ambiguities) > 0
        assert any("PN" in amb.reason for amb in ambiguities)

    def test_detect_missing_fields(self, ambiguity_detector):
        """Тест отсутствия полей"""
        card_data = {"item_type": "отвод", "geometry": {"dn": 200}}
        ambiguities = ambiguity_detector.detect("отвод DN200", card_data)
        # Должна быть неоднозначность об отсутствии угла
        assert any("угол" in amb.reason for amb in ambiguities)

    def test_detect_transition_without_diameters(self, ambiguity_detector):
        """Тест перехода без двух диаметров"""
        ambiguities = ambiguity_detector.detect("переход 219", {})
        assert any("диаметр" in amb.reason for amb in ambiguities)

    def test_detect_elbow_without_angle(self, ambiguity_detector):
        """Тест отвода без угла"""
        ambiguities = ambiguity_detector.detect("отвод DN200", {})
        assert any("угол" in amb.reason for amb in ambiguities)

    def test_has_critical_ambiguities(self, ambiguity_detector):
        """Тест наличия критических неоднозначностей"""
        # Создаём тестовую неоднозначность
        from query_parser.ambiguity_detector import Ambiguity
        critical_amb = Ambiguity(
            field="test",
            reason="Критическая ошибка",
            severity=AmbiguitySeverity.CRITICAL,
            values=[]
        )
        assert ambiguity_detector.has_critical_ambiguities([critical_amb]) is True

    def test_get_high_priority_ambiguities(self, ambiguity_detector):
        """Тест фильтрации по приоритету"""
        from query_parser.ambiguity_detector import Ambiguity
        amb1 = Ambiguity(
            field="test1",
            reason="Высокий приоритет",
            severity=AmbiguitySeverity.HIGH,
            values=[]
        )
        amb2 = Ambiguity(
            field="test2",
            reason="Низкий приоритет",
            severity=AmbiguitySeverity.LOW,
            values=[]
        )
        high = ambiguity_detector.get_high_priority_ambiguities([amb1, amb2])
        assert len(high) == 1
        assert high[0].severity == AmbiguitySeverity.HIGH

    def test_format_ambiguities(self, ambiguity_detector):
        """Тест форматирования неоднозначностей"""
        from query_parser.ambiguity_detector import Ambiguity
        amb = Ambiguity(
            field="test",
            reason="Тестовая неоднозначность",
            severity=AmbiguitySeverity.MEDIUM,
            values=["значение1", "значение2"],
            suggestion="Уточните значение"
        )
        formatted = ambiguity_detector.format_ambiguities([amb])
        assert "Тестовая неоднозначность" in formatted
        assert "значение1" in formatted
        assert "Уточните значение" in formatted
