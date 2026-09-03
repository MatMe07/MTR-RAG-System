# agent/llm/cache.py

import time
from typing import Any, Dict, Optional
from collections import OrderedDict


class LLMCache:
    """Кеш для LLM-вызовов с LRU-эвакцией"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, tuple] = OrderedDict()
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        
        value, timestamp, ttl = self._cache[key]
        if (time.time() - timestamp) > ttl:
            del self._cache[key]
            return None
        
        # Обновляем порядок (LRU)
        self._cache.move_to_end(key)
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = ttl or self.default_ttl
        
        if len(self._cache) >= self.max_size:
            # Удаляем самый старый элемент (LRU)
            self._cache.popitem(last=False)
        
        self._cache[key] = (value, time.time(), ttl)
    
    def clear(self) -> None:
        self._cache.clear()
    
    def remove(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

    def keys(self) -> list:
        return list(self._cache.keys())


# Глобальный кеш
_llm_cache: Optional[LLMCache] = None


def get_llm_cache() -> LLMCache:
    """Ленивая инициализация кеша"""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
    return _llm_cache
