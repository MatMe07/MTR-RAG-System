# agent/llm/cache.py
"""In-memory LRU-кэш для LLM-вызовов.

Особенности:
- TTL фиксируется в момент set (get его не продлевает).
- Потокобезопасен (RLock).
- При переполнении вытесняется самый давно неиспользуемый ключ.
- Singleton + reset для тестов.
"""

import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple


class LLMCache:
    """Потокобезопасный LRU-кэш с TTL."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = int(max_size)
        self.default_ttl = int(default_ttl)
        self._cache: "OrderedDict[str, Tuple[Any, float, int]]" = OrderedDict()
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ get
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, timestamp, ttl = entry
            if (time.time() - timestamp) > ttl:
                self._cache.pop(key, None)
                return None
            self._cache.move_to_end(key)
            return value

    # ------------------------------------------------------------------ set
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ttl = int(ttl) if ttl is not None else self.default_ttl
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            self._cache[key] = (value, time.time(), ttl)

    # -------------------------------------------------------------- прочее
    def remove(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def remove_prefix(self, prefix: str) -> int:
        """Удаляет все ключи с данным префиксом. Возвращает число удалённых."""
        with self._lock:
            to_delete = [k for k in self._cache if k.startswith(prefix)]
            for k in to_delete:
                del self._cache[k]
            return len(to_delete)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def keys(self, include_expired: bool = False) -> List[str]:
        with self._lock:
            if include_expired:
                return list(self._cache.keys())
            now = time.time()
            alive = []
            expired = []
            for k, (_, ts, ttl) in self._cache.items():
                if (now - ts) > ttl:
                    expired.append(k)
                else:
                    alive.append(k)
            for k in expired:
                self._cache.pop(k, None)
            return alive

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {"size": len(self._cache), "max_size": self.max_size}


# ------------------------------------------------------------------ singleton
_llm_cache: Optional[LLMCache] = None
_llm_cache_lock = threading.Lock()


def get_llm_cache() -> LLMCache:
    global _llm_cache
    if _llm_cache is None:
        with _llm_cache_lock:
            if _llm_cache is None:
                _llm_cache = LLMCache()
    return _llm_cache


def reset_llm_cache() -> None:
    """Сброс синглтона — для тестов и reload."""
    global _llm_cache
    with _llm_cache_lock:
        if _llm_cache is not None:
            _llm_cache.clear()
        _llm_cache = None
