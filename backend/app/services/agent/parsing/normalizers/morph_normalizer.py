# agent/parsing/normalizers/morph_normalizer.py

"""Морфологическая нормализация (pymorphy2) — возрождённый модуль (Этап 1, §1E).

Используется нормализаторами параметров и LLM-доизвлечением: приводит формы
слов к лемме («стали» → «сталь»), что повышает точность словарных матчей.
"""

from functools import lru_cache
from typing import Dict, List, Optional

try:
    import mawo_pymorphy3 as pymorphy2

    _MORPH = pymorphy2.MorphAnalyzer()
except Exception:  # noqa: BLE001  (офлайн-окружение без словарей)
    _MORPH = None


class MorphNormalizer:
    """Лемматизация слов и текста с LRU-кешем."""

    def __init__(self):
        self._cache: Dict[str, str] = {}

    @lru_cache(maxsize=10000)
    def normalize(self, word: str) -> str:
        """Нормальная форма слова (лемма)."""
        if word in self._cache:
            return self._cache[word]
        if _MORPH is None:
            return word.lower()
        try:
            parsed = _MORPH.parse(word.strip().lower())[0]
            normalized = parsed.normal_form or word.lower()
        except Exception:  # noqa: BLE001
            normalized = word.lower()
        self._cache[word] = normalized
        return normalized

    def normalize_text(self, text: str) -> str:
        """Лемматизация всего текста (порядок слов сохраняется)."""
        return " ".join(self.normalize(w) for w in (text or "").split())

    def lemmatize_words(self, text: str) -> List[str]:
        """Лемматизация слов в список."""
        return [self.normalize(w) for w in (text or "").split()]

    def clear_cache(self):
        self._cache.clear()
        self.normalize.cache_clear()  # type: ignore[attr-defined]


class ParamNormalizer:
    """Нормализация параметров (статический класс) — обёртка над normalizers."""

    @staticmethod
    def normalize_diameter(value: str) -> float:
        from .normalizers import normalize_decimal

        return normalize_decimal(value)

    @staticmethod
    def normalize_pressure(value: str) -> float:
        """PN40 → 4.0 (доизвлечённое давление трактуем как МПа по §1E.2)."""
        from .normalizers import normalize_pressure

        out = normalize_pressure(value, None)
        return out if out is not None else 0.0

    @staticmethod
    def normalize_steel_grade(value: str) -> str:
        from .normalizers import normalize_steel

        return normalize_steel(value)

    @staticmethod
    def normalize_medium(value: str) -> str:
        from .normalizers import normalize_medium

        return normalize_medium(value) or value