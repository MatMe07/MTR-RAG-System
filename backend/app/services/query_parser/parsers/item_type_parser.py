# query_parser/parsers/item_type_parser.py

import re
from typing import List, Optional, Set, Dict, Tuple
from functools import lru_cache

from rapidfuzz import fuzz

from ..dictionaries import ITEM_TYPE_ALIASES
from ..utils.fuzzy_utils import FuzzyMatcher


class ItemTypeParser:
    """
    Парсер для определения типов деталей из запроса.
    Поддерживает:
    - Точные совпадения с алиасами
    - Множественные типы (через союзы "и", ",", "а также")
    - Fuzzy-поиск для опечаток
    - Извлечение подтипов (subtype)
    """
    
    # Порог для fuzzy-поиска
    FUZZY_THRESHOLD = 85
    
    # Минимальная длина слова для fuzzy-поиска
    MIN_WORD_LENGTH = 4
    
    # Слова, которые не должны участвовать в fuzzy-поиске
    STOP_WORDS = {"перед", "после", "около", "возле", "между", "без", "для", "на", "в", "с", "по"}
    
    # Паттерны для извлечения подтипов (subtype)
    SUBTYPE_PATTERNS = [
        # Задвижки
        (r'клинов(?:ая|ой|ую|ые|ых)', "клиновая"),
        (r'\bзкл\b', "клиновая"),  # задвижка клиновая литая
        (r'параллельн(?:ая|ой|ую|ые|ых)', "параллельная"),
        (r'шиберн(?:ая|ой|ую|ые|ых)', "шиберная"),
        # Краны
        (r'шаров(?:ой|ая|ую|ые|ых)', "шаровой"),
        (r'пробков(?:ый|ая|ую|ые|ых)', "пробковый"),
        # Переходы
        (r'концентрическ(?:ий|ая|ое|ие|их)', "концентрический"),
        (r'эксцентрическ(?:ий|ая|ое|ие|их)', "эксцентрический"),
        # Отводы
        (r'крутоизогнут(?:ый|ая|ое|ые|ых)', "крутоизогнутый"),
        (r'гнут(?:ый|ая|ое|ые|ых)', "гнутый"),
        (r'штампованн(?:ый|ая|ое|ые|ых)', "штампованный"),
        (r'сварн(?:ой|ая|ое|ые|ых|ую|ую)', "сварной"),
        # Трубы
        (r'бесшовн(?:ый|ая|ое|ые|ых|ую)', "бесшовная"),
        (r'электросварн(?:ой|ая|ое|ые|ых|ую)', "электросварная"),
        (r'прямошовн(?:ый|ая|ое|ые|ых)', "прямошовная"),
        (r'спиральношовн(?:ый|ая|ое|ые|ых)', "спиральношовная"),
        # Тройники
        (r'равнопроходн(?:ый|ая|ое|ые|ых)', "равнопроходный"),
        (r'переходн(?:ой|ая|ое|ые|ых)', "переходной"),
        # Заглушки
        (r'плоск(?:ая|ой|ую|ие|их)', "плоская"),
        (r'эллиптическ(?:ая|ой|ую|ие|их)', "эллиптическая"),
        (r'сферическ(?:ая|ой|ую|ие|их)', "сферическая"),
    ]
    
    def __init__(self):
        self.fuzzy_matcher = FuzzyMatcher(threshold=self.FUZZY_THRESHOLD)
        self._cache: Dict[str, List[str]] = {}
        self._subtype_cache: Dict[str, Optional[str]] = {}

    def parse_all(self, text: str) -> List[str]:
        """
        Парсинг всех типов деталей из текста
        Возвращает список уникальных типов
        """
        if not text or not text.strip():
            return []
        
        # Проверка кеша
        cache_key = text.strip()
        if cache_key in self._cache:
            return self._cache[cache_key].copy()
        
        text_lower = text.lower()
        found: Set[str] = set()
        
        # 1. Точные совпадения с алиасами (сортировка по длине для правильного порядка)
        sorted_aliases = sorted(
            ITEM_TYPE_ALIASES.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )
        
        for alias, normalized in sorted_aliases:
            # Используем границы слов для точного поиска
            if re.search(rf"(?<![а-яёa-z]){re.escape(alias)}(?![а-яёa-z])", text_lower):
                found.add(normalized)
        
        # 2. Поиск через союзы (для множественных типов)
        # Разбиваем текст по союзам "и", ",", "а также"
        parts = re.split(r'\s+(?:и|,|а также|\/)\s+', text_lower)
        if len(parts) > 1:
            for part in parts:
                for alias, normalized in sorted_aliases:
                    if re.search(rf"(?<![а-яёa-z]){re.escape(alias)}(?![а-яёa-z])", part):
                        found.add(normalized)
        
        # 3. Fuzzy-поиск (для опечаток и вариантов написания)
        found.update(self._fuzzy_search(text_lower))
        
        # 4. Специальные случаи (контекстные)
        found.update(self._context_search(text_lower))
        
        result = list(found)
        
        # 5. ✅ Обозначение детали имеет приоритет над словесным типом:
        #    "заглушка ОКШ90-219x10..." - это отвод (ОКШ = отвод крутоизогнутый сварной)
        designation_type = self._detect_designation_type(text)
        if designation_type:
            if designation_type in result:
                result.remove(designation_type)
            result.insert(0, designation_type)
        
        # Сохраняем в кеш
        self._cache[cache_key] = result.copy()
        return result

    def parse(self, text: str) -> Optional[str]:
        """
        Парсинг основного типа (первого найденного)
        """
        results = self.parse_all(text)
        return results[0] if results else None

    def parse_primary(self, text: str) -> Optional[str]:
        """
        Алиас для parse()
        """
        return self.parse(text)

    def parse_multiple(self, text: str) -> List[str]:
        """
        Алиас для parse_all()
        """
        return self.parse_all(text)

    def parse_subtype(self, text: str) -> Optional[str]:
        """
        Извлечение подтипа (subtype) из текста
        """
        if not text or not text.strip():
            return None
        
        # Проверка кеша
        cache_key = text.strip()
        if cache_key in self._subtype_cache:
            return self._subtype_cache[cache_key]
        
        text_lower = text.lower()
        subtype = None
        
        # Проверяем все паттерны
        for pattern, subtype_value in self.SUBTYPE_PATTERNS:
            if re.search(pattern, text_lower):
                subtype = subtype_value
                break
        
        # Сохраняем в кеш
        self._subtype_cache[cache_key] = subtype
        return subtype

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    # Префиксы обозначений деталей и соответствующие им типы
    DESIGNATION_PREFIXES = [
        (r'\b(?:ОКШ|ОГ)\d*[-\s]', "отвод"),   # ОКШ90-... / ОГ90 ...
        (r'\bЗКЛ\d*[-\s]', "задвижка"),       # ЗКЛ 150х16
        (r'\bКШ\d*[-\s]', "кран"),             # КШ DN50
    ]

    def _detect_designation_type(self, text: str) -> Optional[str]:
        """Определение типа по префиксу обозначения (ОКШ/ОГ/ЗКЛ/КШ)"""
        if not text:
            return None
        for pattern, item_type in self.DESIGNATION_PREFIXES:
            if re.search(pattern, text, re.IGNORECASE):
                return item_type
        return None

    def _fuzzy_search(self, text: str) -> Set[str]:
        """
        Поиск типов через fuzzy-сравнение
        """
        found: Set[str] = set()
        words = re.findall(r"[а-яёa-z]+", text)
        
        # Собираем все алиасы для fuzzy-поиска
        all_aliases = list(ITEM_TYPE_ALIASES.keys())
        
        for word in words:
            # Пропускаем слишком короткие слова и стоп-слова
            if len(word) < self.MIN_WORD_LENGTH:
                continue
            if word in self.STOP_WORDS:
                continue
            
            # Проверяем через FuzzyMatcher
            matches = self.fuzzy_matcher.match(word, all_aliases)
            for matched_alias, score in matches:
                if score >= self.FUZZY_THRESHOLD:
                    found.add(ITEM_TYPE_ALIASES[matched_alias])
                    break
        
        return found

    def _context_search(self, text: str) -> Set[str]:
        """
        Поиск типов по контекстным признакам
        """
        found: Set[str] = set()
        
        # Контекстные паттерны для каждого типа
        context_patterns = {
            "отвод": [
                r'меняет направление',
                r'изменяет направление',
                r'поворот',
                r'угол',
            ],
            "заглушка": [
                r'закрывает',
                r'заглуш',
                r'поворотная',
            ],
            "переход": [
                r'переход',
                r'изменение диаметра',
            ],
        }
        
        for item_type, patterns in context_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    found.add(item_type)
                    break
        
        return found

    # =========================================================
    # МЕТОДЫ ДЛЯ ОТЛАДКИ
    # =========================================================

    def get_all_item_types(self) -> List[str]:
        """
        Получить список всех поддерживаемых типов
        """
        return list(set(ITEM_TYPE_ALIASES.values()))

    def get_aliases_for_type(self, item_type: str) -> List[str]:
        """
        Получить все алиасы для типа
        """
        return [alias for alias, type_ in ITEM_TYPE_ALIASES.items() if type_ == item_type]

    def is_valid_type(self, item_type: str) -> bool:
        """
        Проверка, является ли строка валидным типом
        """
        return item_type in self.get_all_item_types()

    # =========================================================
    # ОЧИСТКА КЕША
    # =========================================================

    def clear_cache(self):
        """
        Очистка кеша
        """
        self._cache.clear()
        self._subtype_cache.clear()

    def clear_subtype_cache(self):
        """
        Очистка кеша подтипов
        """
        self._subtype_cache.clear()
