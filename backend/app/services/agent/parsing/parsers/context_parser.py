# query_parser/parsers/context_parser.py

import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from functools import lru_cache

from ..utils.fuzzy_utils import FuzzyMatcher


@dataclass
class ContextReference:
    """Ссылка на контекстный объект"""
    reference_type: str  # component, unit, implicit
    value: str
    raw_text: str
    confidence: float = 1.0


@dataclass
class ContextPattern:
    """Паттерн для извлечения контекста"""
    pattern: str
    field: str
    priority: int = 0
    description: str = ""
    normalize_func: Optional[callable] = None


class ContextParser:
    """
    Парсер контекстной информации из запроса.
    Поддерживает:
    - Количество штук
    - Длина в метрах
    - Временные рамки
    - Срочность
    - Ссылки на компоненты и участки
    - Имплицитные ссылки
    - Количество участков
    """
    
    # Паттерны для извлечения количества штук
    QUANTITY_PATTERNS = [
        # Цифры + штуки
        (r'(\d+)\s*(?:штук|шт|ед|штуки|штука|штуку)', 'quantity', 100, "X штук"),
        # Слова + штуки
        (r'по\s+(одна|один|одно|одну|две|два|двух|три|трёх|четыре|четырёх|пять|пяти|шесть|шести|семь|семи|восемь|восьми|девять|девяти|десять|десяти)\s+штук',
         'quantity_words', 90, "по X штук"),
        # Слова + деталь
        (r'(два|две|три|четыре|пять|шесть|семь|восемь|девять|десять)\s+(?:отвода|трубы|задвижки|перехода|заглушки|тройника)',
         'quantity_words', 85, "X деталей"),
        # Количество без указания единиц
        (r'\b(\d+)\s+(?:отвод|труба|задвижка|заглушка|переход|тройник)',
         'quantity', 80, "X деталей"),
    ]
    
    # Паттерны для извлечения длины
    LENGTH_PATTERNS = [
        # Цифры + метры
        (r'(\d+)\s*(?:м|метр|метров|метра|метре)', 'length_meters', 100, "X м"),
        # Слова + метры
        (r'(сто|двести|триста|четыреста|пятьсот|шестьсот|семьсот|восемьсот|девятьсот|тысяча)\s*(?:м|метр|метров|метра)',
         'length_words', 90, "X метров"),
        # Километры
        (r'(\d+)\s*(?:км|километр|километров|километра)', 'length_meters', 80, "X км"),
    ]
    
    # Паттерны для извлечения временных рамок
    TIMEFRAME_PATTERNS = [
        (r'следующ(?:ая|ей|ую|их)?\s*(?:недел[ея]|месяц|год)', 'timeframe', 100, "следующая неделя"),
        (r'сегодня|сейчас|немедленно|срочно', 'timeframe', 90, "сейчас"),
        (r'завтра|утром|вечером', 'timeframe', 80, "завтра"),
        (r'(?:в\s+)?течени[ея]\s+(\d+)\s*(?:дн[ей]|час[ов]|минут)', 'timeframe_days', 70, "в течение X дней"),
    ]
    
    # Паттерны для извлечения срочности
    URGENCY_PATTERNS = [
        (r'срочн(?:о|ый|ая|ое|ые|ых)', 'urgency', 100, "срочно"),
        (r'важн(?:о|ый|ая|ое|ые|ых)', 'urgency', 90, "важно"),
        (r'критич(?:ески|но|ный|ная|ное|ные)', 'urgency', 90, "критично"),
        (r'аварийн(?:о|ый|ая|ое|ые|ых)', 'urgency', 95, "аварийно"),
        (r'немедленн(?:о|ый|ая|ое|ые|ых)', 'urgency', 95, "немедленно"),
    ]
    
    # Паттерны для извлечения количества участков
    UNITS_COUNT_PATTERNS = [
        # Слова + участков
        (r'(одн|дв|трёх|тр|четырёх|четыр|пяти|пят|шести|шест|семи|сем|восьми|вос|девяти|девят|десяти|десят)\s*(?:таких же\s*)?участков',
         'units_count_words', 100, "X участков"),
        # Цифры + участков
        (r'(\d+)\s*(?:таких же\s*)?участков', 'units_count', 90, "X участков"),
        # Участки без явного количества
        (r'несколько\s+участков', 'units_count_implicit', 80, "несколько участков"),
    ]
    
    # Паттерны для извлечения ссылок
    REFERENCE_PATTERNS = {
        'explicit': [
            (r'\bCOMP[-_][A-Z0-9-]+\b', 'component', 100),
            (r'\bUNIT[-_][A-Z0-9-]+\b', 'unit', 100),
            (r'\bKSM[-_][A-Z0-9-]+\b', 'ksm', 100),
            (r'\bMTR[-_][A-Z0-9-]+\b', 'mtr', 100),
        ],
        'implicit': [
            (r'такой же', 'implicit_reference', 90),
            (r'такую же', 'implicit_reference', 90),
            (r'такая же', 'implicit_reference', 90),
            (r'аналог', 'implicit_reference', 85),
            (r'как у', 'implicit_reference', 85),
            (r'как на', 'implicit_reference', 85),
            (r'как в', 'implicit_reference', 85),
            (r'соседн(?:ий|яя|ее|ие)', 'implicit_reference', 80),
            (r'этой детали', 'implicit_reference', 80),
            (r'этого участка', 'implicit_reference', 80),
        ],
    }
    
    # Словари числительных
    NUM_WORDS = {
        'одна': 1, 'один': 1, 'одно': 1, 'одну': 1,
        'две': 2, 'два': 2, 'двух': 2,
        'три': 3, 'трёх': 3,
        'четыре': 4, 'четырёх': 4,
        'пять': 5, 'пяти': 5,
        'шесть': 6, 'шести': 6,
        'семь': 7, 'семи': 7,
        'восемь': 8, 'восьми': 8,
        'девять': 9, 'девяти': 9,
        'десять': 10, 'десяти': 10,
        'сто': 100, 'двести': 200, 'триста': 300,
        'четыреста': 400, 'пятьсот': 500,
        'шестьсот': 600, 'семьсот': 700,
        'восемьсот': 800, 'девятьсот': 900,
        'тысяча': 1000,
    }
    
    UNITS_COUNT_WORDS = {
        'одн': 1, 'дв': 2, 'трёх': 3, 'тр': 3,
        'четырёх': 4, 'четыр': 4,
        'пяти': 5, 'пят': 5,
        'шести': 6, 'шест': 6,
        'семи': 7, 'сем': 7,
        'восьми': 8, 'вос': 8,
        'девяти': 9, 'девят': 9,
        'десяти': 10, 'десят': 10,
    }
    
    def __init__(self):
        self.fuzzy_matcher = FuzzyMatcher(threshold=75)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Основной метод парсинга контекста
        """
        if not text or not text.strip():
            return {}
        
        # Проверка кеша
        cache_key = text.strip()
        if cache_key in self._cache:
            return self._cache[cache_key].copy()
        
        result = self._parse_impl(text)
        
        # Сохраняем в кеш
        self._cache[cache_key] = result.copy()
        return result

    def _parse_impl(self, text: str) -> Dict[str, Any]:
        """
        Реализация парсинга без кеширования
        """
        result = {}
        text_lower = text.lower()
        
        # 1. Количество штук
        self._apply_quantity_patterns(text_lower, result)
        
        # 2. Количество участков
        self._apply_units_count_patterns(text_lower, result)
        
        # 3. Длина
        self._apply_length_patterns(text_lower, result)
        
        # 4. Временные рамки
        self._apply_timeframe_patterns(text_lower, result)
        
        # 5. Срочность
        self._apply_urgency_patterns(text_lower, result)
        
        # 6. Ссылки
        references = self._extract_references(text)
        if references:
            result['references'] = references
        
        # 7. Имплицитные ссылки
        implicit_refs = self._extract_implicit_references(text)
        if implicit_refs:
            if 'references' not in result:
                result['references'] = []
            result['references'].extend(implicit_refs)
        
        # 8. Чистка результата
        result = self._clean_result(result)
        
        return result

    # =========================================================
    # ПРИМЕНЕНИЕ ПАТТЕРНОВ
    # =========================================================

    def _apply_quantity_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для количества
        """
        for pattern, field, priority, _ in self.QUANTITY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if field == 'quantity_words':
                    # Преобразуем слово в число
                    word = match.group(1).lower()
                    if word in self.NUM_WORDS:
                        result['quantity'] = self.NUM_WORDS[word]
                        break
                elif field == 'quantity':
                    result['quantity'] = int(match.group(1))
                    break

    def _apply_units_count_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для количества участков
        """
        for pattern, field, priority, _ in self.UNITS_COUNT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if field == 'units_count_words':
                    word = match.group(1).lower()
                    if word in self.UNITS_COUNT_WORDS:
                        result['units_count'] = self.UNITS_COUNT_WORDS[word]
                        break
                elif field == 'units_count':
                    result['units_count'] = int(match.group(1))
                    break
                elif field == 'units_count_implicit':
                    result['units_count'] = 2  # По умолчанию несколько = 2
                    break

    def _apply_length_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для длины
        """
        for pattern, field, priority, _ in self.LENGTH_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if field == 'length_words':
                    word = match.group(1).lower()
                    if word in self.NUM_WORDS:
                        result['length_meters'] = float(self.NUM_WORDS[word])
                        break
                elif field == 'length_meters':
                    value = match.group(1)
                    # Если это километры, умножаем на 1000
                    if 'км' in match.group(0).lower() or 'километр' in match.group(0).lower():
                        result['length_meters'] = float(value) * 1000
                    else:
                        result['length_meters'] = float(value)
                    break

    def _apply_timeframe_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для временных рамок
        """
        for pattern, field, priority, _ in self.TIMEFRAME_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if field == 'timeframe_days':
                    days = int(match.group(1))
                    if days <= 1:
                        result['timeframe'] = 'immediate'
                    elif days <= 7:
                        result['timeframe'] = 'this_week'
                    else:
                        result['timeframe'] = 'future'
                else:
                    result['timeframe'] = match.group(0).lower()
                break

    def _apply_urgency_patterns(self, text: str, result: Dict[str, Any]) -> None:
        """
        Применение паттернов для срочности
        """
        for pattern, field, priority, _ in self.URGENCY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                result['urgency'] = 'high'
                break

    # =========================================================
    # ИЗВЛЕЧЕНИЕ ССЫЛОК
    # =========================================================

    def _extract_references(self, text: str) -> List[ContextReference]:
        """
        Извлечение явных ссылок
        """
        references = []
        
        for pattern, ref_type, priority in self.REFERENCE_PATTERNS['explicit']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                ref = ContextReference(
                    reference_type=ref_type,
                    value=match.upper(),
                    raw_text=match,
                    confidence=priority / 100.0
                )
                references.append(ref)
        
        return references

    def _extract_implicit_references(self, text: str) -> List[ContextReference]:
        """
        Извлечение имплицитных ссылок
        """
        references = []
        text_lower = text.lower()
        
        for pattern, ref_type, priority in self.REFERENCE_PATTERNS['implicit']:
            if re.search(pattern, text_lower):
                ref = ContextReference(
                    reference_type=ref_type,
                    value=pattern,
                    raw_text=pattern,
                    confidence=priority / 100.0
                )
                references.append(ref)
                break  # Достаточно одной имплицитной ссылки
        
        return references

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def _clean_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Очистка результата
        """
        # Удаляем None значения
        cleaned = {k: v for k, v in result.items() if v is not None}
        
        # Удаляем пустые списки
        if 'references' in cleaned and not cleaned['references']:
            del cleaned['references']
        
        return cleaned

    # =========================================================
    # ОЧИСТКА КЕША
    # =========================================================

    def clear_cache(self):
        """
        Очистка кеша
        """
        self._cache.clear()
