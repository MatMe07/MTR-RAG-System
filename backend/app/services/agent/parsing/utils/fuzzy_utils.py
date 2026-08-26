# query_parser/utils/fuzzy_utils.py

from typing import List, Tuple, Dict
from rapidfuzz import fuzz
from functools import lru_cache


class FuzzyMatcher:
    """Оптимизированный fuzzy-поиск с кешированием"""
    
    def __init__(self, threshold: int = 75):
        self.threshold = threshold
        self._cache: Dict[str, Dict[str, int]] = {}
    
    @lru_cache(maxsize=5000)
    def _cached_ratio(self, word: str, target: str) -> int:
        """Кеширование сравнения"""
        return fuzz.ratio(word, target)
    
    def match(self, word: str, targets: List[str]) -> List[Tuple[str, int]]:
        """
        Поиск совпадений слова среди целей
        Возвращает список (target, score)
        """
        results = []
        word_lower = word.lower()
        
        for target in targets:
            target_lower = target.lower()
            
            # Быстрая проверка на точное совпадение
            if word_lower == target_lower:
                results.append((target, 100))
                continue
            
            # Используем кешированное сравнение
            score = self._cached_ratio(word_lower, target_lower)
            if score >= self.threshold:
                results.append((target, score))
        
        # Сортировка по убыванию score
        return sorted(results, key=lambda x: x[1], reverse=True)
    
    def match_batch(self, words: List[str], targets: List[str], 
                    min_score: int = 75) -> Dict[str, List[str]]:
        """
        Массовый поиск совпадений
        Возвращает {word: [matched_targets]}
        """
        result = {}
        for word in words:
            matches = self.match(word, targets)
            result[word] = [m[0] for m in matches if m[1] >= min_score]
        return result
    
    def clear_cache(self):
        """Очистка кеша"""
        self._cache.clear()
        self._cached_ratio.cache_clear()
