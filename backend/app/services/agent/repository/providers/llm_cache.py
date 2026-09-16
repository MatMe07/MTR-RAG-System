# repository/providers/llm_cache.py
"""Кэш ответов LLM поверх RedisCache.

Ключ — нормализованный контекст запроса + модель + версия system-промта.
TTL наследуется из DEFAULT_TTLS по namespace 'llm:'.
При недоступности Redis работает как no-op (как и RedisCache).
"""

import hashlib
import json
import logging
from typing import Any, Dict, Optional

from repository.providers.redis_cache import get_redis_cache

log = logging.getLogger("mtr.repository.llm_cache")

NAMESPACE = "llm:"
# Версия system-промта: меняй при правках SYSTEM_PROMPT, чтобы старый кэш
# автоматически не использовался.
SYSTEM_PROMPT_VERSION = "v1"


def _normalize_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Оставляем только то, что реально влияет на ответ.

    Порядок кандидатов не должен влиять на ключ — сортируем по code.
    status/warnings/errors — не влияют на сам ответ, исключаем.
    """
    candidates = context.get("candidates") or []
    codes = sorted(
        str(c.get("code"))
        for c in candidates
        if isinstance(c, dict) and c.get("code") is not None
    )
    return {
        "query": (context.get("query") or "").strip().lower(),
        "critical_params": context.get("critical_params"),
        "candidate_codes": codes,
        "compatibility": context.get("compatibility"),
        "recommendations": context.get("recommendations"),
    }


def make_key(context: Dict[str, Any], model: str) -> str:
    payload = {
        "model": model,
        "system_version": SYSTEM_PROMPT_VERSION,
        "ctx": _normalize_context(context),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{NAMESPACE}explain:{digest}"


def _serialize_response(response: Any) -> Dict[str, Any]:
    """Сохраняем content + метаданные, чтобы downstream не терял usage/tool_calls."""
    return {
        "content": getattr(response, "content", None),
        "response_metadata": getattr(response, "response_metadata", None),
        "usage_metadata": getattr(response, "usage_metadata", None),
        "tool_calls": getattr(response, "tool_calls", None),
        "additional_kwargs": getattr(response, "additional_kwargs", None),
        "type": getattr(response, "type", "ai"),
    }


def _deserialize_response(payload: Dict[str, Any]) -> Any:
    """Восстанавливаем объект, совместимый с AIMessage."""
    from langchain_core.messages import AIMessage

    return AIMessage(
        content=payload.get("content") or "",
        additional_kwargs=payload.get("additional_kwargs") or {},
        response_metadata=payload.get("response_metadata") or {},
        usage_metadata=payload.get("usage_metadata"),
        tool_calls=payload.get("tool_calls") or [],
    )


def get_cached(context: Dict[str, Any], model: str) -> Optional[Any]:
    cache = get_redis_cache()
    if not cache.available:
        return None
    try:
        payload = cache.get(make_key(context, model))
        if not payload:
            return None
        return _deserialize_response(payload)
    except Exception as e:  # noqa: BLE001
        log.warning("llm_cache.get failed: %s", e)
        return None


def put_cached(context: Dict[str, Any], model: str, response: Any) -> None:
    cache = get_redis_cache()
    if not cache.available:
        return
    try:
        cache.set(make_key(context, model), _serialize_response(response))
    except Exception as e:  # noqa: BLE001
        log.warning("llm_cache.put failed: %s", e)


def invalidate_all() -> None:
    """Сброс всего LLM-кэша (вызывать при reload каталога/словарей)."""
    cache = get_redis_cache()
    if cache.available:
        cache.delete_prefix(NAMESPACE)
