# repository/providers/redis_cache.py
"""Redis-кеш (read-through) для каталога, остатков и словарей.

При недоступности Redis кеш работает как no-op: чтение/запись проваливаются
молча, каталог строится из PostgreSQL (или JSON-fallback).

Словари (Этап 1, секция 1J.2): снимок dynamic-правил/справочников живёт в
Redis ровно 1 час, версия-счётчик позволяет обнаружить обновление из
админ-эндпоинтов без перезапуска.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import redis

log = logging.getLogger("mtr.repository.redis_cache")

DEFAULT_URL = "redis://localhost:6379/0"
DEFAULT_TTL = 300
# 1J.2: словари кешируются на 1 час.
DICTIONARIES_TTL = 3600
_PREFIX_SNAPSHOT = "dictionaries:snapshot"
_PREFIX_VERSION = "dictionaries:version"


class RedisCache:
    def __init__(self, url: Optional[str] = None, prefix: str = "mtr:", ttl: int = DEFAULT_TTL):
        self._prefix = prefix
        self._ttl = int(ttl)
        self._url = url or None
        self._client: Optional[redis.Redis] = None
        self._available: Optional[bool] = None

    # ------------------------------------------------------------------ conn
    def _conn(self) -> Optional[redis.Redis]:
        if self._available is False:
            return None
        if self._client is None:
            try:
                url = self._url
                if not url:
                    from app.config import settings

                    url = settings.REDIS_URL
                self._client = redis.Redis.from_url(
                    url,
                    socket_connect_timeout=1,
                    socket_timeout=1,
                    decode_responses=False,
                )
                self._client.ping()
            except Exception as e:
                self._client = None
                self._available = False
                log.warning("RedisCache: Redis недоступен, кеш отключён: %s", e)
                return None
        return self._client

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    # ---------------------------------------------------------------- API
    def get(self, key: str) -> Optional[Any]:
        c = self._conn()
        if c is None:
            return None
        try:
            raw = c.get(self._key(key))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        c = self._conn()
        if c is None:
            return
        try:
            c.setex(
                self._key(key),
                int(ttl) if ttl is not None else self._ttl,
                json.dumps(value, ensure_ascii=False, default=str),
            )
        except Exception:
            pass

    def delete(self, *keys: str) -> None:
        c = self._conn()
        if c is None:
            return
        try:
            if keys:
                c.delete(*[self._key(k) for k in keys])
        except Exception:
            pass

    def flush_prefix(self) -> None:
        c = self._conn()
        if c is None:
            return
        try:
            for key in c.scan_iter(match=self._prefix + "*"):
                c.delete(key)
        except Exception:
            pass

    @property
    def available(self) -> bool:
        return self._conn() is not None

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None


_cache_singleton: Optional[RedisCache] = None


def get_redis_cache(**overrides: Any) -> RedisCache:
    """Синглтон-обёртка поверх RedisCache (для инвалидации при reload)."""
    global _cache_singleton
    if _cache_singleton is None:
        _cache_singleton = RedisCache(**overrides)
    return _cache_singleton


def flush_redis_cache() -> None:
    """Полная инвалидация Redis-кеша (вызывается при admin/reload)."""
    if _cache_singleton is not None:
        _cache_singleton.flush_prefix()


def reset_redis_cache() -> None:
    global _cache_singleton
    if _cache_singleton is not None:
        _cache_singleton.close()
        _cache_singleton = None


# ===========================================================================
# Словари (1J.2): снимок dynamic-правил в Redis с версией-счётчиком.
# ===========================================================================

def set_dictionary_snapshot(data: Dict[str, Any]) -> None:
    """Пишет снимок словарей в Redis (TTL 1 час) и инкрементит версию."""
    cache = get_redis_cache()
    if not cache.available:
        return
    try:
        version = cache.get(_PREFIX_VERSION) or 0
        version = int(version) + 1
        cache.set(_PREFIX_VERSION, version, ttl=DICTIONARIES_TTL)
        cache.set(_PREFIX_SNAPSHOT, data, ttl=DICTIONARIES_TTL)
    except Exception as e:  # noqa: BLE001
        log.warning("set_dictionary_snapshot failed: %s", e)


def get_dictionary_snapshot() -> Optional[Dict[str, Any]]:
    """Снимок словарей из Redis, если он свежее локального version (или первый)."""
    cache = get_redis_cache()
    if not cache.available:
        return None
    try:
        return cache.get(_PREFIX_SNAPSHOT)
    except Exception:
        return None


def dictionary_version() -> Optional[int]:
    cache = get_redis_cache()
    if not cache.available:
        return None
    try:
        v = cache.get(_PREFIX_VERSION)
        return int(v) if v is not None else None
    except Exception:
        return None


def invalidate_dictionary_snapshot() -> None:
    """Инвалидация словарного снимка после изменений в админ-эндпоинтах."""
    cache = get_redis_cache()
    if cache.available:
        cache.delete(_PREFIX_SNAPSHOT, _PREFIX_VERSION)