# query_parser/base_parser.py

import re
from typing import Any, Dict, Optional, TypeVar, Generic
from abc import ABC, abstractmethod

T = TypeVar('T')


class BaseParser(ABC):
    """Базовый класс для всех парсеров с общей логикой"""
    
    def __init__(self):
        self._cache = {}
    
    @abstractmethod
    def parse(self, text: str) -> Any:
        """Основной метод парсинга"""
        pass
    
    def _safe_parse(self, text: str) -> Optional[Any]:
        """Безопасный парсинг с обработкой ошибок"""
        try:
            return self.parse(text)
        except Exception:
            return None
    
    def _normalize_text(self, text: str) -> str:
        """Нормализация текста (приведение к нижнему регистру)"""
        return text.lower().strip()
    
    def _extract_number(self, text: str, pattern: str) -> Optional[float]:
        """Универсальное извлечение чисел с поддержкой запятых"""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).replace(',', '.')
            try:
                return float(value)
            except ValueError:
                return None
        return None
    
    def _cached_parse(self, text: str) -> Any:
        """Кеширование результатов парсинга"""
        cache_key = f"{self.__class__.__name__}:{text}"
        if cache_key not in self._cache:
            self._cache[cache_key] = self.parse(text)
        return self._cache[cache_key]
