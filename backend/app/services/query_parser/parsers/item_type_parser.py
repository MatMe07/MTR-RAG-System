# query_parser/item_type_parser.py

import re
from typing import List, Optional, Set
from rapidfuzz import fuzz
from .dictionaries import ITEM_TYPE_ALIASES


class ItemTypeParser:
    FUZZY_THRESHOLD = 85  # было 80

    def parse_all(self, text: str) -> List[str]:
        text_lower = text.lower()
        found: Set[str] = set()
        
        # 1. Точные совпадения и алиасы (уже есть)
        for alias, normalized in sorted(ITEM_TYPE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(rf"(?<![а-яёa-z]){re.escape(alias)}(?![а-яёa-z])", text_lower):
                found.add(normalized)

        # 1.1. Дополнительно: поиск через союз "и" (труба и задвижка)
        # Разбиваем текст по союзам "и", ",", "а также"
        parts = re.split(r'\s+(?:и|,|а также)\s+', text_lower)
        if len(parts) > 1:
            for part in parts:
                # Для каждой части пробуем найти тип
                for alias, normalized in ITEM_TYPE_ALIASES.items():
                    if re.search(rf"(?<![а-яёa-z]){re.escape(alias)}(?![а-яёa-z])", part):
                        found.add(normalized)

        # 2. Fuzzy поиск (без изменений)
        words = re.findall(r"[а-яёa-z]+", text_lower)
        for word in words:
            if len(word) < 4:
                continue
            if word in ['перед', 'после', 'около', 'возле', 'между']:
                continue
            for alias, normalized in ITEM_TYPE_ALIASES.items():
                if fuzz.ratio(word, alias) >= self.FUZZY_THRESHOLD:
                    found.add(normalized)

        return list(found)
    def parse_subtype(self, text: str) -> Optional[str]:
        """Извлечение подтипа из текста"""
        text_lower = text.lower()
        
        subtype_patterns = [
            (r'клинов(?:ая|ой|ую)', "клиновая"),
            (r'параллельн(?:ая|ой|ую)', "параллельная"),
            (r'шиберн(?:ая|ой|ую)', "шиберная"),
            # Краны
            (r'шаров(?:ой|ая|ую)', "шаровой"),
            (r'пробков(?:ый|ая|ую)', "пробковый"),
            # Переходы
            (r'концентрическ(?:ий|ая|ое)', "концентрический"),
            (r'эксцентрическ(?:ий|ая|ое)', "эксцентрический"),
            # Отводы
            (r'крутоизогнут(?:ый|ая|ое)', "крутоизогнутый"),
            (r'гнут(?:ый|ая|ое)', "гнутый"),
            (r'штампованн(?:ый|ая|ое)', "штампованный"),
            # Трубы (НОВОЕ)
            (r'сварн(?:ой|ая|ое|ую|ой)', "сварная"),
            (r'бесшовн(?:ый|ая|ое|ую|ой)', "бесшовная"),
            (r'электросварн(?:ой|ая|ое|ую|ой)', "электросварная"),
            # Тройники
            (r'равнопроходн(?:ый|ая|ое)', "равнопроходный"),
            (r'переходн(?:ой|ая|ое)', "переходной"),
            (r'сварк(?:а|ой|у|е)', "сварная"),  # <-- добавить
            (r'бесшовн(?:ый|ая|ое|ую|ой)', "бесшовная"),
        ]
        
        for pattern, subtype in subtype_patterns:
            if re.search(pattern, text_lower):
                return subtype
        
        return None
    
    def parse(self, text: str) -> Optional[str]:
        res = self.parse_all(text)
        return res[0] if res else None
    
    def parse_primary(self, text: str) -> Optional[str]:
        res = self.parse_all(text)
        return res[0] if res else None
    
    def parse_multiple(self, text: str) -> List[str]:
        return self.parse_all(text)
