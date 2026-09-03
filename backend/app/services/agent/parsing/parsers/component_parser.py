# query_parser/parsers/component_parser.py

import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from functools import lru_cache

from ..utils.fuzzy_utils import FuzzyMatcher


@dataclass
class IdentifierPattern:
    """Паттерн для извлечения идентификаторов"""
    pattern: str
    prefix: str
    description: str = ""
    priority: int = 0


class ComponentParser:
    """
    Универсальный парсер для идентификаторов компонентов и участков.
    Поддерживает:
    - COMP-XXX (компоненты)
    - UNIT-XXX (участки)
    - KSM-XXX (коды КСМ)
    - MTR-XXX (коды МТР)
    - Различные форматы записи
    - Множественные идентификаторы в одном запросе
    """
    
    # Паттерны для извлечения идентификаторов
    IDENTIFIER_PATTERNS = {
        'component': [
            (r'\bCOMP[-_]([A-Z0-9-]+)\b', 'COMP', "COMP-XXX", 100),
            (r'\bCOMPONENT[-_]([A-Z0-9-]+)\b', 'COMP', "COMPONENT-XXX", 90),
            (r'\bC[-_]([A-Z0-9-]+)\b', 'COMP', "C-XXX", 70),  # Краткая форма
        ],
        'unit': [
            (r'\bUNIT[-_]([A-Z0-9-]+)\b', 'UNIT', "UNIT-XXX", 100),
            (r'\bU[-_]([A-Z0-9-]+)\b', 'UNIT', "U-XXX", 70),  # Краткая форма
        ],
        'ksm': [
            (r'\bKSM[-_]([A-Z0-9-]+)\b', 'KSM', "KSM-XXX", 100),
            (r'\bКСМ[-_]([A-Z0-9-]+)\b', 'KSM', "КСМ-XXX", 95),
        ],
        'mtr': [
            (r'\bMTR[-_]([A-Z0-9-]+)\b', 'MTR', "MTR-XXX", 100),
            (r'\bМТР[-_]([A-Z0-9-]+)\b', 'MTR', "МТР-XXX", 95),
        ],
        'equipment': [
            (r'\bEQ[-_]([A-Z0-9-]+)\b', 'EQ', "EQ-XXX", 80),
            (r'\bEQUIPMENT[-_]([A-Z0-9-]+)\b', 'EQ', "EQUIPMENT-XXX", 85),
        ],
        'pipeline': [
            (r'\bPL[-_]([A-Z0-9-]+)\b', 'PL', "PL-XXX", 80),
            (r'\bPIPELINE[-_]([A-Z0-9-]+)\b', 'PL', "PIPELINE-XXX", 85),
        ],
    }
    
    # Контекстные паттерны для поиска без явного префикса
    CONTEXT_PATTERNS = {
        'component': [
            (r'(?:деталь|компонент|элемент)\s+([A-Z0-9-]+)', 90),
            (r'(?:COMP|компонент)\s*[:;]\s*([A-Z0-9-]+)', 85),
        ],
        'unit': [
            (r'(?:участок|секция|блок)\s+([A-Z0-9-]+)', 90),
            (r'(?:UNIT|участок)\s*[:;]\s*([A-Z0-9-]+)', 85),
        ],
        'ksm': [
            (r'(?:КСМ|код)\s+([A-Z0-9-]+)', 90),
        ],
        'mtr': [
            (r'(?:МТР|материал)\s+([A-Z0-9-]+)', 90),
        ],
    }
    
    # Стоп-слова для фильтрации ложных срабатываний
    STOP_WORDS = {
        'COMP', 'UNIT', 'KSM', 'MTR', 'EQ', 'PL',
        'COMPONENT', 'EQUIPMENT', 'PIPELINE',
        'ГОСТ', 'ТУ', 'СТО', 'ЛНД',  # Нормативные документы
        'DN', 'PN', 'РУ',  # Технические параметры
    }
    
    def __init__(self):
        self.fuzzy_matcher = FuzzyMatcher(threshold=75)
        self._cache: Dict[str, Dict[str, Any]] = {}

    # =========================================================
    # ОСНОВНЫЕ МЕТОДЫ
    # =========================================================

    def parse(self, text: str) -> Optional[str]:
        """
        Парсинг первого найденного идентификатора (любого типа)
        """
        result = self.parse_all(text)
        if result:
            # Возвращаем первый найденный
            for key in ['component_ids', 'unit_ids', 'ksm_codes', 'mtr_codes']:
                if result.get(key) and result[key]:
                    return result[key][0]
        return None

    def parse_all(self, text: str) -> Dict[str, List[str]]:
        """
        Парсинг всех идентификаторов из текста
        Возвращает словарь с разделением по типам
        """
        if not text or not text.strip():
            return self._empty_result()
        
        # Проверка кеша
        cache_key = text.strip()
        if cache_key in self._cache:
            return self._cache[cache_key].copy()
        
        result = self._parse_impl(text)
        
        # Сохраняем в кеш
        self._cache[cache_key] = result.copy()
        return result

    def _parse_impl(self, text: str) -> Dict[str, List[str]]:
        """
        Реализация парсинга без кеширования
        """
        result = self._empty_result()
        text_upper = text.upper()
        
        # 1. Извлечение по паттернам
        self._apply_identifier_patterns(text_upper, result)
        
        # 2. Контекстный поиск
        if not self._has_any_identifiers(result):
            self._apply_context_patterns(text_upper, result)
        
        # 3. Поиск числовых кодов без префикса
        if not self._has_any_identifiers(result):
            self._apply_numeric_search(text_upper, result)
        
        # 4. Очистка от дубликатов и валидация
        result = self._clean_result(result)
        
        return result

    # =========================================================
    # ПРИМЕНЕНИЕ ПАТТЕРНОВ
    # =========================================================

    def _apply_identifier_patterns(self, text: str, result: Dict[str, List[str]]) -> None:
        """
        Применение всех паттернов для идентификаторов
        """
        for id_type, patterns in self.IDENTIFIER_PATTERNS.items():
            # Сортируем по приоритету
            sorted_patterns = sorted(patterns, key=lambda x: x[3], reverse=True)
            
            for pattern, prefix, description, priority in sorted_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        # Формируем полный идентификатор
                        full_id = f"{prefix}-{match}"
                        # Проверяем, что это не стоп-слово
                        if not self._is_stop_word(full_id):
                            self._add_identifier(result, id_type, full_id)
                    # После первого найденного паттерна для этого типа можно выйти
                    # (если не хотим собирать все варианты)
                    if result.get(self._get_result_key(id_type)):
                        break

    def _apply_context_patterns(self, text: str, result: Dict[str, List[str]]) -> None:
        """
        Применение контекстных паттернов
        """
        for id_type, patterns in self.CONTEXT_PATTERNS.items():
            for pattern, priority in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        # Определяем префикс по типу
                        prefix = self._get_prefix_for_type(id_type)
                        if prefix:
                            full_id = f"{prefix}-{match}"
                            if not self._is_stop_word(full_id):
                                self._add_identifier(result, id_type, full_id)

    def _apply_numeric_search(self, text: str, result: Dict[str, List[str]]) -> None:
        """
        Поиск числовых кодов без префикса
        """
        # Ищем числа, которые могут быть кодами
        numbers = re.findall(r'\b(\d{3,6})\b', text)
        
        if numbers:
            # Проверяем контекст для определения типа
            text_lower = text.lower()
            
            for number in numbers:
                # Пропускаем, если число может быть параметром
                if self._is_parameter_number(number, text_lower):
                    continue
                
                # Определяем тип по контексту
                id_type = self._determine_type_by_context(text_lower, number)
                if id_type:
                    prefix = self._get_prefix_for_type(id_type)
                    if prefix:
                        full_id = f"{prefix}-{number}"
                        self._add_identifier(result, id_type, full_id)

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def _get_result_key(self, id_type: str) -> str:
        """
        Получить ключ для результата по типу идентификатора
        """
        mapping = {
            'component': 'component_ids',
            'unit': 'unit_ids',
            'ksm': 'ksm_codes',
            'mtr': 'mtr_codes',
            'equipment': 'equipment_ids',
            'pipeline': 'pipeline_ids',
        }
        return mapping.get(id_type, f"{id_type}_ids")

    def _get_prefix_for_type(self, id_type: str) -> Optional[str]:
        """
        Получить префикс для типа идентификатора
        """
        mapping = {
            'component': 'COMP',
            'unit': 'UNIT',
            'ksm': 'KSM',
            'mtr': 'MTR',
            'equipment': 'EQ',
            'pipeline': 'PL',
        }
        return mapping.get(id_type)

    def _add_identifier(self, result: Dict[str, List[str]], id_type: str, identifier: str) -> None:
        """
        Добавить идентификатор в результат
        """
        key = self._get_result_key(id_type)
        if key and identifier not in result.get(key, []):
            result[key].append(identifier)

    def _is_stop_word(self, identifier: str) -> bool:
        """
        Проверка, является ли идентификатор стоп-словом
        """
        # Проверяем точное совпадение
        if identifier in self.STOP_WORDS:
            return True
        
        # Проверяем, не является ли идентификатор нормативным документом
        if re.match(r'^(ГОСТ|ТУ|СТО)\s+\d+', identifier):
            return True
        
        # Проверяем, не является ли идентификатор техническим параметром
        if re.match(r'^(DN|PN|РУ)\d+', identifier):
            return True
        
        return False

    def _is_parameter_number(self, number: str, text: str) -> bool:
        """
        Проверка, является ли число параметром (DN, PN и т.д.)
        """
        # Если рядом с числом есть "DN", "PN", "РУ" - это параметр
        if re.search(rf'(?:DN|PN|РУ|Ду)\s*{number}', text, re.IGNORECASE):
            return True
        
        # Если число от 10 до 400 - может быть PN
        num = int(number)
        if 10 <= num <= 400 and num % 10 == 0:
            return True
        
        return False

    def _determine_type_by_context(self, text: str, number: str) -> Optional[str]:
        """
        Определение типа идентификатора по контексту
        """
        # Проверяем контекст для каждого типа
        for id_type, patterns in self.CONTEXT_PATTERNS.items():
            for pattern, priority in patterns:
                # Проверяем, есть ли число в контексте
                if re.search(pattern.replace(r'([A-Z0-9-]+)', number), text, re.IGNORECASE):
                    return id_type
        
        # Если не определился - проверяем по ключевым словам
        if re.search(r'\b(?:деталь|компонент)\b', text):
            return 'component'
        elif re.search(r'\b(?:участок|секция|блок)\b', text):
            return 'unit'
        elif re.search(r'\b(?:КСМ|код)\b', text):
            return 'ksm'
        elif re.search(r'\b(?:МТР|материал)\b', text):
            return 'mtr'
        
        return None

    def _has_any_identifiers(self, result: Dict[str, List[str]]) -> bool:
        """
        Проверка, есть ли какие-либо идентификаторы в результате
        """
        return any([
            result.get('component_ids'),
            result.get('unit_ids'),
            result.get('ksm_codes'),
            result.get('mtr_codes'),
            result.get('equipment_ids'),
            result.get('pipeline_ids'),
        ])

    def _clean_result(self, result: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Очистка результата от дубликатов
        """
        cleaned = {}
        for key, values in result.items():
            if values:
                # Удаляем дубликаты
                unique_values = list(dict.fromkeys(values))
                # Фильтруем стоп-слова
                filtered_values = [v for v in unique_values if not self._is_stop_word(v)]
                if filtered_values:
                    cleaned[key] = filtered_values
                else:
                    cleaned[key] = []
            else:
                cleaned[key] = []
        
        return cleaned

    def _empty_result(self) -> Dict[str, List[str]]:
        """
        Пустой результат
        """
        return {
            'component_ids': [],
            'unit_ids': [],
            'ksm_codes': [],
            'mtr_codes': [],
            'equipment_ids': [],
            'pipeline_ids': [],
        }

    # =========================================================
    # ОЧИСТКА КЕША
    # =========================================================

    def clear_cache(self):
        """
        Очистка кеша
        """
        self._cache.clear()
