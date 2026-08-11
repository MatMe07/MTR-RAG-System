# query_parser/parsers/operation_parser.py

import re
from typing import List, Optional, Dict, Tuple, Set
from dataclasses import dataclass, field
from functools import lru_cache

from rapidfuzz import fuzz

from ..dictionaries import OPERATION_ALIASES
from ..utils.fuzzy_utils import FuzzyMatcher


@dataclass
class OperationRule:
    """Правило для определения операции"""
    operation: str
    keywords: List[str]
    priority: int = 0
    context_words: List[str] = field(default_factory=list)
    negative_context: List[str] = field(default_factory=list)


class OperationParser:
    """
    Парсер для определения операций (действий) из запроса.
    Поддерживает:
    - Точные совпадения ключевых слов
    - Алиасы из словаря
    - Fuzzy-поиск для опечаток
    - Контекстные признаки
    - Приоритеты операций
    """
    
    # Приоритеты операций (чем выше, тем важнее)
    OPERATION_PRIORITY = {
        "repair": 100,
        "replace": 95,
        "inventory": 90,
        "check": 85,
        "impact": 80,
        "plan": 75,
        "explain": 70,
        "search": 50,
        "assemble": 40,
        "document": 35,
        "calculate": 30,
    }
    
    # Основные ключевые слова для каждой операции
    KEYWORDS = {
        "repair": [
            "сломался", "сломалась", "сломалось", "сломаны", "сломанный",
            "поврежден", "повреждена", "повреждено", "повреждены",
            "утечка", "ремонт", "починить", "отказал",
        ],
        "replace": [
            "замена", "заменить", "замену", "замены",
            "аналог", "аналога", "аналогом",
            "вместо", "подбери замену", "подобрать замену",
            "подбери", "подобрать",
        ],
        "plan": [
            "план", "плановой", "плановое",
            "обслуживание", "комплект",
            "список деталей", "порядок работ",
            "составь", "составить",
        ],
        "check": [
            "проверить", "проверь", "проверка",
            "хватает", "достаточно",
            "подходит", "подойдут",
            "что проверить", "проверяем",
        ],
        "explain": [
            "объясни", "объяснить",
            "расскажи", "рассказать",
            "что значит", "означает",
            "чем отличается",
        ],
        "inventory": [
            "сколько", "наличие", "остаток", "остатки",
            "на складе", "складе",
            "пополнение", "закупки", "закупку",
            "есть ли", "хватает ли", "достаточно ли",
            "запас",
        ],
        "search": [
            "найди", "найти",
            "покажи", "показать",
            "выбери", "выбрать",
        ],
        "impact": [
            "что изменится", "последствия",
            "влияние", "риск",
            "придётся заменить",
            "придется заменить",
            "что проверить",
            "какие соседние",
            "затронет",
        ],
        "document": [
            "паспорта", "паспорт",
            "документы", "документацию",
            "госты", "гост",
            "лнд",
        ],
        "assemble": [
            "собери", "собрать",
            "комплект", "сборка",
            "полный комплект",
        ],
        "calculate": [
            "посчитай", "подсчитай",
            "рассчитай", "расчет",
            "калькуляция",
        ],
    }
    
    # Фразы (точные совпадения) с приоритетом выше ключевых слов
    PHRASES = [
        ("план замены", "plan"),
        ("план обслуживания", "plan"),
        ("комплект замены", "plan"),
        ("комплект ремонта", "plan"),
        ("полный комплект", "plan"),
        ("порядок ремонта", "repair"),
        ("что проверить", "check"),
        ("что изменится", "impact"),
        ("откуда взяты госты", "document"),
        ("паспорта и ту", "document"),
        ("найди замену", "replace"),
        ("подбери замену", "replace"),
        ("подобрать замену", "replace"),
        ("найди аналог", "replace"),
        ("подбери аналог", "replace"),
        ("собери комплект", "assemble"),
        ("собрать комплект", "assemble"),
        ("какие соседние детали", "impact"),  
        ("придётся заменить", "impact"),      
        ("запас деталей", "inventory"),       
    ]
    
    # Контекстные признаки (для уточнения операций)
    CONTEXT_PATTERNS = {
        "inventory": [
            (r'складе', 10),
            (r'остат', 8),
            (r'налич', 8),
            (r'пополн', 7),
            (r'закуп', 7),
            (r'запас', 7),  
            (r'(?:есть ли|сколько|хватает ли|достаточно ли)', 10),
        ],
        "repair": [
            (r'сломал', 10),
            (r'поврежд', 10),
            (r'утечк', 10),
            (r'отказал', 10),
        ],
        "plan": [
            (r'план', 8),
            (r'обслужив', 8),
            (r'комплект', 7),
            (r'перечисл', 5),
        ],
        "check": [
            (r'провер', 10),
            (r'хвата', 8),
            (r'достаточ', 8),
            (r'подход', 8),
        ],
        "explain": [
            (r'объясн', 10),
            (r'расскаж', 8),
            (r'что значит', 10),
            (r'означа', 8),
        ],
        "document": [
            (r'паспорт', 10),
            (r'документ', 10),
            (r'лнд', 10),
            (r'(?:гост|ту)\s+[\d\-]+', 10),
        ],
        "impact": [
            (r'изменится', 10),
            (r'последств', 10),
            (r'влияние', 8),
            (r'заменят', 7),      
            (r'затрон', 7),       
            (r'соседн', 7),       
            (r'прид[её]тся', 7),  
        ],
        "assemble": [
            (r'собер', 10),
            (r'комплект', 8),
        ],
        "calculate": [
            (r'посчита', 10),
            (r'подсчита', 10),
            (r'рассчита', 10),
        ],
    }
    
    # Негативный контекст (исключения)
    NEGATIVE_CONTEXT = [
        r'установлены?\s+ни\s+на\s+одном',
        r'без\s+ремонта',
    ]
    
    # Пороги для fuzzy-поиска
    FUZZY_THRESHOLD = 75
    FUZZY_STRONG_THRESHOLD = 85
    
    def __init__(self):
        self.fuzzy_matcher = FuzzyMatcher(threshold=self.FUZZY_THRESHOLD)
        self._cache: Dict[str, List[str]] = {}

    def parse_all(self, text: str) -> List[str]:
        """
        Парсинг всех операций из текста
        Возвращает список операций, отсортированный по приоритету
        """
        if not text or not text.strip():
            return ["unknown"]
        
        # Проверка кеша
        cache_key = text.strip()
        if cache_key in self._cache:
            return self._cache[cache_key].copy()
        
        found: Set[str] = set()
        text_lower = text.lower()
        
        # 1. Проверка фраз (высший приоритет)
        for phrase, operation in self.PHRASES:
            if phrase in text_lower:
                found.add(operation)
        
        # 2. Точные ключевые слова
        for operation, keywords in self.KEYWORDS.items():
            for keyword in keywords:
                if self._contains_keyword(text_lower, keyword):
                    found.add(operation)
                    break
        
        # 3. Алиасы из словаря
        for alias, operation in OPERATION_ALIASES.items():
            if self._contains_keyword(text_lower, alias):
                found.add(operation)
        
        # 4. Fuzzy-поиск (для опечаток)
        found.update(self._fuzzy_search(text))
        
        # 5. Контекстные признаки
        found.update(self._context_search(text_lower))
        
        # 6. Удаляем ложные срабатывания
        found = self._filter_false_positives(found, text_lower)
        
        # Если ничего не найдено - unknown
        if not found:
            result = ["unknown"]
        else:
            # Сортировка по приоритету
            result = sorted(
                found,
                key=lambda op: self.OPERATION_PRIORITY.get(op, 0),
                reverse=True
            )
        
        # Сохраняем в кеш
        self._cache[cache_key] = result.copy()
        return result

    def parse(self, text: str) -> Optional[str]:
        """
        Парсинг основной операции (первой по приоритету)
        """
        operations = self.parse_all(text)
        if not operations or operations == ["unknown"]:
            return "unknown"
        return operations[0]

    def parse_primary(self, text: str) -> str:
        """
        Алиас для parse()
        """
        return self.parse(text)

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================================================

    def _contains_keyword(self, text: str, keyword: str) -> bool:
        """
        Проверка наличия ключевого слова в тексте (с учётом границ слов)
        """
        pattern = rf"(?<![а-яёА-ЯЁa-zA-Z]){re.escape(keyword.lower())}(?![а-яёА-ЯЁa-zA-Z])"
        return bool(re.search(pattern, text))

    def _fuzzy_search(self, text: str) -> Set[str]:
        """
        Поиск операций через fuzzy-сравнение
        """
        found: Set[str] = set()
        words = re.findall(r"[а-яёa-z]+", text.lower())
        
        # Собираем все ключевые слова для fuzzy-поиска
        all_keywords = {}
        for operation, keywords in self.KEYWORDS.items():
            for keyword in keywords:
                if len(keyword) >= 4:
                    all_keywords[keyword] = operation
        
        for word in words:
            if len(word) < 4:
                continue
            
            matches = self.fuzzy_matcher.match(word, list(all_keywords.keys()))
            for matched_keyword, score in matches:
                if score >= self.FUZZY_STRONG_THRESHOLD:
                    found.add(all_keywords[matched_keyword])
                    break
                elif score >= self.FUZZY_THRESHOLD:
                    found.add(all_keywords[matched_keyword])
        
        return found

    def _context_search(self, text: str) -> Set[str]:
        """
        Поиск операций по контекстным признакам
        """
        found: Set[str] = set()
        
        # Проверяем негативный контекст
        for neg_pattern in self.NEGATIVE_CONTEXT:
            if re.search(neg_pattern, text):
                pass
        
        for operation, patterns in self.CONTEXT_PATTERNS.items():
            for pattern, _ in patterns:
                if re.search(pattern, text):
                    found.add(operation)
                    break
        
        return found

    def _filter_false_positives(self, operations: Set[str], text: str) -> Set[str]:
        """
        Фильтрация ложных срабатываний
        """
        result = operations.copy()
        
        if "inventory" in result:
            if re.search(r'установлены?\s+ни\s+на\s+одном', text):
                result.discard("inventory")
            if re.search(r'не\s+установлены', text):
                result.discard("inventory")
        
        if "repair" in result:
            if re.search(r'без\s+ремонта', text):
                result.discard("repair")
        
        if "document" in result:
            has_document_words = any(
                word in text for word in ["паспорт", "документ", "лнд"]
            )
            has_gost = bool(re.search(r'(?:гост|ту)\s+[\d\-]+', text))
            if not has_document_words and not has_gost:
                result.discard("document")
        
        return result

    # =========================================================
    # ОЧИСТКА КЕША
    # =========================================================

    def clear_cache(self):
        """
        Очистка кеша результатов
        """
        self._cache.clear()

    # =========================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ДЛЯ ОТЛАДКИ
    # =========================================================

    def get_operation_priority(self, operation: str) -> int:
        """
        Получить приоритет операции
        """
        return self.OPERATION_PRIORITY.get(operation, 0)

    def get_all_operations(self) -> List[str]:
        """
        Получить список всех поддерживаемых операций
        """
        return list(self.OPERATION_PRIORITY.keys())

    def get_keywords_for_operation(self, operation: str) -> List[str]:
        """
        Получить ключевые слова для операции
        """
        return self.KEYWORDS.get(operation, [])
