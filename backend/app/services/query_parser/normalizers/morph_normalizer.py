# query_parser/normalizers/morph_normalizer.py

import pymorphy2
from typing import List, Optional


class MorphNormalizer:
    def __init__(self):
        self.morph = pymorphy2.MorphAnalyzer()
        self.cache = {}

    def normalize(self, word: str) -> str:
        if word in self.cache:
            return self.cache[word]
        
        try:
            parsed = self.morph.parse(word)[0]
            normalized = parsed.normal_form
            self.cache[word] = normalized
            return normalized
        except Exception:
            return word.lower()

    def normalize_text(self, text: str) -> str:
        words = text.split()
        normalized_words = [self.normalize(w) for w in words]
        return " ".join(normalized_words)

    def lemmatize_words(self, text: str) -> List[str]:
        words = text.split()
        return [self.normalize(w) for w in words]


class ParamNormalizer:
    """Нормализация параметров"""
    
    @staticmethod
    def normalize_diameter(value: str) -> float:
        """Нормализация диаметра: 426 -> 426.0, 0.5 -> 0.5"""
        return float(value.replace(',', '.'))

    @staticmethod
    def normalize_pressure(value: str) -> float:
        """PN40 -> 4.0, PN160 -> 16.0"""
        num = float(value)
        if num >= 10:
            return num / 10.0
        return num

    @staticmethod
    def normalize_steel_grade(value: str) -> str:
        """Нормализация марки стали: 09г2с -> 09Г2С"""
        return value.upper()
