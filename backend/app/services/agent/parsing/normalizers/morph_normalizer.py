# # query_parser/normalizers/morph_normalizer.py

# import mawo_pymorphy3
# from typing import List, Optional, Dict
# from functools import lru_cache


# class MorphNormalizer:
#     def __init__(self):
#         self.morph = mawo_pymorphy3.MorphAnalyzer()
#         # Кеш с ограничением размера (LRU)
#         self._cache: Dict[str, str] = {}
#         self._max_cache_size = 10000
    
#     @lru_cache(maxsize=10000)
#     def normalize(self, word: str) -> str:
#         """Нормализация слова с кешированием"""
#         if word in self._cache:
#             return self._cache[word]
        
#         try:
#             parsed = self.morph.parse(word)[0]
#             normalized = parsed.normal_form
#             self._cache[word] = normalized
#             return normalized
#         except Exception:
#             return word.lower()
    
#     def normalize_text(self, text: str) -> str:
#         """Нормализация всего текста"""
#         words = text.split()
#         return " ".join(self.normalize(w) for w in words)
    
#     def lemmatize_words(self, text: str) -> List[str]:
#         """Лемматизация слов"""
#         words = text.split()
#         return [self.normalize(w) for w in words]
    
#     def clear_cache(self):
#         """Очистка кеша"""
#         self._cache.clear()
#         self.normalize.cache_clear()  # Очищаем LRU кеш


# class ParamNormalizer:
#     """Нормализация параметров (статический класс)"""
    
#     @staticmethod
#     def normalize_diameter(value: str) -> float:
#         """Нормализация диаметра"""
#         return float(value.replace(',', '.'))
    
#     @staticmethod
#     def normalize_pressure(value: str) -> float:
#         """PN40 -> 4.0, PN160 -> 16.0"""
#         num = float(value)
#         if num >= 10:
#             return num / 10.0
#         return num
    
#     @staticmethod
#     def normalize_steel_grade(value: str) -> str:
#         """09г2с -> 09Г2С"""
#         return value.upper()
    
#     @staticmethod
#     def normalize_medium(value: str) -> str:
#         """Нормализация среды"""
#         mapping = {
#             "сероводород": "H2S",
#             "сероводородная среда": "H2S",
#             "h2s": "H2S",
#             "углекислый газ": "CO2",
#             "co2": "CO2",
#             "природный газ": "природный газ",
#             "газ": "газ",
#             "нефть": "нефть",
#             "вода": "вода",
#         }
#         return mapping.get(value.lower(), value)
