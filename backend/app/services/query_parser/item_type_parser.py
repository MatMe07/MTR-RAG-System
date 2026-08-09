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

    def parse(self, text: str) -> Optional[str]:
        res = self.parse_all(text)
        return res[0] if res else None
    
    def parse_primary(self, text: str) -> Optional[str]:
        res = self.parse_all(text)
        return res[0] if res else None
    
    def parse_multiple(self, text: str) -> List[str]:
        return self.parse_all(text)
