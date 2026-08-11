# query_parser/ambiguity_detector.py

import re
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache


class AmbiguitySeverity(Enum):
    """Уровень серьёзности неоднозначности"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Ambiguity:
    """Структура неоднозначности"""
    field: str
    reason: str
    severity: AmbiguitySeverity
    values: List[str] = field(default_factory=list)
    suggestion: Optional[str] = None
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            "field": self.field,
            "reason": self.reason,
            "severity": self.severity.value,
            "values": self.values,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
        }


@dataclass
class AmbiguityPattern:
    """Паттерн для обнаружения неоднозначности"""
    field: str
    pattern: str
    reason: str
    severity: AmbiguitySeverity
    description: str = ""
    priority: int = 0


class AmbiguityDetector:
    """
    Детектор неоднозначностей в запросе.
    Поддерживает:
    - Множественные DN
    - Множественные углы
    - Множественные PN
    - Конфликты параметров
    - Отсутствие обязательных параметров
    - Противоречия в запросе
    """
    
    # Паттерны для обнаружения неоднозначностей
    AMBIGUITY_PATTERNS = {
        'multiple_dn': [
            (r'\b(?:DN|Ду)\s*[:]?\s*(\d+)', 'geometry.dn', 
             "В запросе указано несколько значений DN", AmbiguitySeverity.HIGH),
        ],
        'multiple_angle': [
            (r'\b(30|45|60|90)\s*°?', 'geometry.angle',
             "В запросе указано несколько возможных углов", AmbiguitySeverity.MEDIUM),
        ],
        'multiple_pn': [
            (r'\b(?:PN|Ру)\s*[:]?\s*(\d+)', 'pressure.pn',
             "В запросе указано несколько значений PN", AmbiguitySeverity.HIGH),
        ],
        'multiple_material': [
            (r'\b(?:стал[иь]|марка)\s+([0-9а-яёa-z]+)', 'material.steel_grade',
             "В запросе указано несколько марок стали", AmbiguitySeverity.MEDIUM),
        ],
        'multiple_medium': [
            (r'\b(?:H2S|CO2|нефть|газ|вода)\b', 'environment.medium',
             "В запросе указано несколько сред", AmbiguitySeverity.HIGH),
        ],
    }
    
    # Паттерны для обнаружения конфликтов
    CONFLICT_PATTERNS = [
        # Давление и геометрия
        (r'\b(?:отвод|труба|окш|ог)\b.*\d+\s+(?:на|x|х|×)\s+\d+', 
         'pressure.pn', "Числовое значение может быть частью геометрии изделия",
         AmbiguitySeverity.LOW),
        
        # Материал и среда
        (r'\b(?:стал[иь])\s+([0-9а-яёa-z]+).*H2S', 
         'material.steel_grade', "Марка стали может не подходить для H2S среды",
         AmbiguitySeverity.MEDIUM),
        
        # Температура и климатика
        (r'температур[аы]\s*[-+]?(\d+).*УХЛ', 
         'environment.climate_version', "Температура может не соответствовать климатике",
         AmbiguitySeverity.MEDIUM),
    ]
    
    # Обязательные поля для разных типов деталей
    REQUIRED_FIELDS = {
        'отвод': ['item_type', 'dn', 'angle'],
        'труба': ['item_type', 'dn', 'wall_thickness'],
        'задвижка': ['item_type', 'dn', 'pn'],
        'заглушка': ['item_type', 'dn', 'pn'],
        'переход': ['item_type', 'd1', 'd2'],
        'тройник': ['item_type', 'd1', 'd2'],
    }
    
    # Рекомендации по устранению неоднозначностей
    SUGGESTIONS = {
        'multiple_dn': "Уточните нужный DN",
        'multiple_angle': "Уточните нужный угол (30°, 45°, 60° или 90°)",
        'multiple_pn': "Уточните нужное давление",
        'multiple_material': "Уточните нужную марку стали",
        'multiple_medium': "Уточните рабочую среду",
        'missing_item_type': "Уточните тип детали (отвод, труба, задвижка, заглушка, переход, тройник)",
        'missing_dn': "Уточните условный проход (DN)",
        'missing_angle': "Уточните угол (30°, 45°, 60° или 90°)",
        'missing_wall_thickness': "Уточните толщину стенки",
        'missing_pn': "Уточните давление (PN)",
    }
    
    def __init__(self):
        self._cache: Dict[str, List[Ambiguity]] = {}

    def detect(self, text: str, card_data: Optional[Dict[str, Any]] = None) -> List[Ambiguity]:
        """
        Основной метод обнаружения неоднозначностей
        """
        if not text or not text.strip():
            return []
        
        # Проверка кеша
        cache_key = f"{text.strip()}:{str(card_data)}"
        if cache_key in self._cache:
            return self._cache[cache_key].copy()
        
        result = self._detect_impl(text, card_data or {})
        
        # Сохраняем в кеш
        self._cache[cache_key] = result.copy()
        return result

    def _detect_impl(self, text: str, card_data: Dict[str, Any]) -> List[Ambiguity]:
        """
        Реализация обнаружения без кеширования
        """
        ambiguities: List[Ambiguity] = []
        text_lower = text.lower()
        
        # 1. Множественные значения
        ambiguities.extend(self._detect_multiple_values(text_lower))
        
        # 2. Конфликты
        ambiguities.extend(self._detect_conflicts(text_lower, card_data))
        
        # 3. Отсутствие обязательных полей
        ambiguities.extend(self._detect_missing_fields(card_data))
        
        # 4. Противоречия
        ambiguities.extend(self._detect_contradictions(text_lower, card_data))
        
        # 5. Сортировка по серьёзности и приоритету
        ambiguities.sort(key=lambda x: (
            self._severity_score(x.severity),
            -x.confidence
        ), reverse=True)
        
        return ambiguities

    # =========================================================
    # ОБНАРУЖЕНИЕ МНОЖЕСТВЕННЫХ ЗНАЧЕНИЙ
    # =========================================================

    def _detect_multiple_values(self, text: str) -> List[Ambiguity]:
        """
        Обнаружение множественных значений
        """
        ambiguities: List[Ambiguity] = []
        
        for amb_type, (pattern, field, reason, severity) in self.AMBIGUITY_PATTERNS.items():
            values = re.findall(pattern, text, re.IGNORECASE)
            unique_values = list(dict.fromkeys(values))
            
            if len(unique_values) > 1:
                ambiguity = Ambiguity(
                    field=field,
                    reason=reason,
                    severity=severity,
                    values=unique_values,
                    suggestion=self.SUGGESTIONS.get(amb_type),
                    confidence=0.8
                )
                ambiguities.append(ambiguity)
        
        return ambiguities

    # =========================================================
    # ОБНАРУЖЕНИЕ КОНФЛИКТОВ
    # =========================================================

    def _detect_conflicts(self, text: str, card_data: Dict[str, Any]) -> List[Ambiguity]:
        """
        Обнаружение конфликтов между параметрами
        """
        ambiguities: List[Ambiguity] = []
        
        for pattern, field, reason, severity in self.CONFLICT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                # Проверяем, есть ли конфликтное значение в card_data
                if self._has_conflict_value(card_data, field):
                    ambiguity = Ambiguity(
                        field=field,
                        reason=reason,
                        severity=severity,
                        suggestion="Проверьте соответствие параметров",
                        confidence=0.7
                    )
                    ambiguities.append(ambiguity)
        
        return ambiguities

    def _has_conflict_value(self, card_data: Dict[str, Any], field: str) -> bool:
        """
        Проверка наличия конфликтного значения в card_data
        """
        if not card_data:
            return False
        
        # Разбираем путь поля (например, 'pressure.pn')
        parts = field.split('.')
        current = card_data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return False
        
        return current is not None

    # =========================================================
    # ОБНАРУЖЕНИЕ ОТСУТСТВИЯ ПОЛЕЙ
    # =========================================================

    def _detect_missing_fields(self, card_data: Dict[str, Any]) -> List[Ambiguity]:
        """
        Обнаружение отсутствия обязательных полей
        """
        ambiguities: List[Ambiguity] = []
        
        if not card_data:
            return ambiguities
        
        # Определяем тип детали
        item_type = card_data.get('item_type')
        if not item_type:
            return ambiguities
        
        # Проверяем обязательные поля для типа
        required = self.REQUIRED_FIELDS.get(item_type, [])
        
        for field in required:
            if not self._has_field_value(card_data, field):
                ambiguity = Ambiguity(
                    field=field,
                    reason=f"Отсутствует обязательное поле: {field}",
                    severity=AmbiguitySeverity.HIGH,
                    suggestion=self.SUGGESTIONS.get(f'missing_{field}'),
                    confidence=0.9
                )
                ambiguities.append(ambiguity)
        
        return ambiguities

    def _has_field_value(self, card_data: Dict[str, Any], field: str) -> bool:
        """
        Проверка наличия значения поля
        """
        # Разбираем путь поля
        parts = field.split('.')
        current = card_data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return False
        
        return current is not None and current != ""

    # =========================================================
    # ОБНАРУЖЕНИЕ ПРОТИВОРЕЧИЙ
    # =========================================================

    def _detect_contradictions(self, text: str, card_data: Dict[str, Any]) -> List[Ambiguity]:
        """
        Обнаружение противоречий в запросе
        """
        ambiguities: List[Ambiguity] = []
        
        # Проверка: указан переход, но нет двух диаметров
        if self._is_transition_without_diameters(text, card_data):
            ambiguity = Ambiguity(
                field="geometry",
                reason="Для перехода/тройника указан только один диаметр",
                severity=AmbiguitySeverity.HIGH,
                suggestion="Уточните оба диаметра (например, 219x159)",
                confidence=0.9
            )
            ambiguities.append(ambiguity)
        
        # Проверка: указан отвод, но нет угла
        if self._is_elbow_without_angle(text, card_data):
            ambiguity = Ambiguity(
                field="geometry.angle",
                reason="Для отвода не указан угол",
                severity=AmbiguitySeverity.HIGH,
                suggestion="Уточните угол (30°, 45°, 60° или 90°)",
                confidence=0.9
            )
            ambiguities.append(ambiguity)
        
        # Проверка: указана задвижка, но нет PN
        if self._is_valve_without_pn(text, card_data):
            ambiguity = Ambiguity(
                field="pressure.pn",
                reason="Для задвижки/заглушки не указано давление",
                severity=AmbiguitySeverity.HIGH,
                suggestion="Уточните давление (PN)",
                confidence=0.9
            )
            ambiguities.append(ambiguity)
        
        return ambiguities

    def _is_transition_without_diameters(self, text: str, card_data: Dict[str, Any]) -> bool:
        """
        Проверка: переход/тройник без двух диаметров
        """
        # Проверяем по тексту
        is_transition = bool(re.search(r'\b(?:переход|тройник)\b', text.lower()))
        if not is_transition:
            return False
        
        # Проверяем по card_data
        geometry = card_data.get('geometry', {})
        has_d1 = geometry.get('d1') is not None
        has_d2 = geometry.get('d2') is not None
        
        return not (has_d1 and has_d2)

    def _is_elbow_without_angle(self, text: str, card_data: Dict[str, Any]) -> bool:
        """
        Проверка: отвод без угла
        """
        # Проверяем по тексту
        is_elbow = bool(re.search(r'\b(?:отвод|окш|ог)\b', text.lower()))
        if not is_elbow:
            return False
        
        # Проверяем по card_data
        geometry = card_data.get('geometry', {})
        has_angle = geometry.get('angle') is not None
        
        return not has_angle

    def _is_valve_without_pn(self, text: str, card_data: Dict[str, Any]) -> bool:
        """
        Проверка: задвижка/заглушка без PN
        """
        # Проверяем по тексту
        is_valve = bool(re.search(r'\b(?:задвижка|заглушка)\b', text.lower()))
        if not is_valve:
            return False
        
        # Проверяем по card_data
        pressure = card_data.get('pressure', {})
        has_pn = pressure.get('pn') is not None
        
        return not has_pn

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def _severity_score(self, severity: AmbiguitySeverity) -> int:
        """
        Числовой вес серьёзности
        """
        scores = {
            AmbiguitySeverity.LOW: 1,
            AmbiguitySeverity.MEDIUM: 2,
            AmbiguitySeverity.HIGH: 3,
            AmbiguitySeverity.CRITICAL: 4,
        }
        return scores.get(severity, 0)

    def has_critical_ambiguities(self, ambiguities: List[Ambiguity]) -> bool:
        """
        Проверка наличия критических неоднозначностей
        """
        return any(amb.severity == AmbiguitySeverity.CRITICAL for amb in ambiguities)

    def get_high_priority_ambiguities(self, ambiguities: List[Ambiguity]) -> List[Ambiguity]:
        """
        Получить неоднозначности высокого приоритета
        """
        return [amb for amb in ambiguities if amb.severity in [
            AmbiguitySeverity.HIGH, 
            AmbiguitySeverity.CRITICAL
        ]]

    def format_ambiguities(self, ambiguities: List[Ambiguity]) -> str:
        """
        Форматирование неоднозначностей для пользователя
        """
        if not ambiguities:
            return "Неоднозначностей не обнаружено"
        
        lines = []
        for amb in ambiguities:
            severity_icon = {
                AmbiguitySeverity.LOW: "ℹ️",
                AmbiguitySeverity.MEDIUM: "⚠️",
                AmbiguitySeverity.HIGH: "🔴",
                AmbiguitySeverity.CRITICAL: "🚨",
            }.get(amb.severity, "⚠️")
            
            line = f"{severity_icon} {amb.reason}"
            if amb.values:
                line += f" (найдено: {', '.join(amb.values)})"
            if amb.suggestion:
                line += f"\n   💡 {amb.suggestion}"
            lines.append(line)
        
        return "\n".join(lines)

    # =========================================================
    # ОЧИСТКА КЕША
    # =========================================================

    def clear_cache(self):
        """
        Очистка кеша
        """
        self._cache.clear()
