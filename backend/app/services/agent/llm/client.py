# agent/llm/client.py

import contextvars
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Union

import httpx
from langchain_core.messages import HumanMessage

from ..core.config import DEFAULT_CONFIG, AgentConfig
from ..core.exceptions import LLMError, LLMTimeoutError
from .cache import get_llm_cache

# ---------------------------------------------------------------- контекст запроса
# Позволяют привязывать вызовы LLM к конкретному request_id (для диагностики в
# AgentAnswer.llm.calls), даже когда LLMClient вызывается из разных модулей
# (llm_extractor, refine_loop, LLMAgent) — все они попадают в один request.
_llm_request_id: contextvars.ContextVar = contextvars.ContextVar("llm_request_id", default="")
_llm_request_mode: contextvars.ContextVar = contextvars.ContextVar("llm_request_mode", default="")


def current_request_id() -> str:
    return _llm_request_id.get()


def set_llm_request_context(request_id: Optional[str], mode: Optional[str] = None) -> None:
    _llm_request_id.set(request_id or "")
    _llm_request_mode.set(mode or "")


def reset_llm_request_context() -> None:
    _llm_request_id.set("")
    _llm_request_mode.set("")


def _message_to_dict(m: Any) -> dict:
    """Нормализует BaseMessage или dict в плоский вид."""
    if isinstance(m, dict):
        role = m.get("role") or m.get("type") or "user"
        content = m.get("content", "")
    else:
        role = getattr(m, "type", None) or getattr(m, "role", "user")
        content = getattr(m, "content", "")
    # content может быть list (мультимодальный) — приводим к каноническому виду
    if isinstance(content, list):
        content = [
            {"type": p.get("type"), "text": p.get("text")}
            if isinstance(p, dict) else str(p)
            for p in content
        ]
    return {"role": role, "content": content}


def make_cache_key(
    prompt: List[Any],
    model: str,
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    system_version: str = "v1",
    extra: dict | None = None,
) -> str:
    normalized = [_message_to_dict(m) for m in prompt]
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "system_version": system_version,
        "messages": normalized,
        "extra": extra or {},
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"llm:{digest}"

def _snapshot_response(response: Any) -> dict:
    return {
        "content": getattr(response, "content", "") or "",
        "usage_metadata": getattr(response, "usage_metadata", None),
        "response_metadata": getattr(response, "response_metadata", None),
        "tool_calls": getattr(response, "tool_calls", None),
    }

class LLMClient:
    """LLM-клиент с кешем и метриками"""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.cache = get_llm_cache()
        self._client = None
        self._metrics = {
            "total_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_duration_ms": 0.0,
            "errors": 0,
            "extractor_calls": 0,
            "extractor_hits": 0,
            "extractor_errors": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }
        # Помесячно-по-запросу: request_id -> список вызовов LLM (для диагностики)
        self._request_calls: Dict[str, List[Dict[str, Any]]] = {}
    CACHE_TTL_DEFAULT = 300      # 5 минут
    CACHE_TTL_EXPLAIN = 600      # 10 минут
    SYSTEM_PROMPT_VERSION = "v1" # бампай при правках SYSTEM_PROMPT

    @property
    def client(self):
        """Ленивая инициализация LLM-клиента"""
        if self._client is None:
            try:
                import os

                from langchain_openai import ChatOpenAI
                api_key = (
                    self.config.llm_api_key
                    or os.getenv("OPENROUTER_API_KEY")
                    or os.getenv("LLM_API_KEY")
                )
                base_url = self.config.llm_base_url or "https://openrouter.ai/api/v1"
                model = os.getenv("LLM_MODEL") or self.config.llm_model
                self._client = ChatOpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    temperature=self.config.llm_temperature,
                    timeout=self.config.llm_timeout,
                )
            except ImportError:
                # Если langchain-openai не установлен — заглушка
                class DummyLLM:
                    def invoke(self, prompt):
                        return type('Response', (), {'content': '{"response": "LLM недоступен"}'})()
                    def with_structured_output(self, schema):
                        return self
                self._client = DummyLLM()
        return self._client

    def _make_cache_key(self, prompt: List[Any], extra: Optional[dict] = None) -> str:
        return make_cache_key(
            prompt,
            model=self.config.llm_model,           # или MODEL_NAME, как у тебя
            temperature=self.config.llm_temperature,
            max_tokens=getattr(self.config, "max_tokens", None),
            system_version=self.SYSTEM_PROMPT_VERSION,
            extra=extra,
        )

    def invoke(
        self,
        prompt: Union[str, Sequence[Any]],
        use_cache: bool = True,
        *,
        cache_ttl: Optional[int] = None,
        stage: str = "",
    ) -> str:
        if isinstance(prompt, str):
            prompt = [HumanMessage(content=prompt)]
        cache_key = self._make_cache_key(prompt)

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._metrics["cache_hits"] += 1
                self._metrics["total_calls"] += 1
                # usage из кэша, чтобы статистика по токенам не «проседала»
                usage_meta = cached.get("usage_metadata") if isinstance(cached, dict) else None
                usage = self._consume_usage_snapshot(usage_meta) if usage_meta else {}
                if usage:
                    self._metrics.update(usage)
                self._record_call(stage=stage, usage=usage, cache_hit=True)
                return cached["content"] if isinstance(cached, dict) else cached

        # --- вызов LLM ---
        self._metrics["total_calls"] += 1
        start = time.time()
        try:
            response = self.client.invoke(prompt)
        except (httpx.TimeoutException, TimeoutError) as e:
            self._metrics["errors"] += 1
            self._record_call(
                stage=stage,
                duration_ms=(time.time() - start) * 1000,
                error=f"timeout {self.config.llm_timeout}s",
            )
            raise LLMTimeoutError(self.config.llm_timeout) from e
        except Exception as e:
            self._metrics["errors"] += 1
            self._record_call(
                stage=stage,
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
            )
            raise LLMError(f"LLM ошибка: {e}") from e

        duration = (time.time() - start) * 1000
        self._metrics["total_duration_ms"] += duration
        usage = self._consume_usage(response)
        self._metrics.update(usage)
        self._record_call(stage=stage, duration_ms=duration, usage=usage)

        content = getattr(response, "content", None) or str(response)

        if use_cache and content:
            snapshot = _snapshot_response(response)
            ttl = cache_ttl if cache_ttl is not None else self.CACHE_TTL_DEFAULT
            self.cache.set(cache_key, snapshot, ttl=ttl)
            self._metrics["cache_misses"] += 1

        return content

    # ------------------------------------------------------- диагностика запроса
    def _record_call(
        self,
        *,
        stage: str,
        duration_ms: float = 0.0,
        usage: Optional[Dict[str, int]] = None,
        cache_hit: bool = False,
        error: Optional[str] = None,
    ) -> None:
        """Записывает вызов LLM в бакет текущего request_id (если он задан)."""
        rid = _llm_request_id.get()
        if not rid:
            return
        usage = usage or {}
        self._request_calls.setdefault(rid, []).append({
            "stage": stage,
            "mode": _llm_request_mode.get() or None,
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
            "duration_ms": round(float(duration_ms), 1),
            "cache_hit": bool(cache_hit),
            "error": error,
            "ts": datetime.now(timezone.utc).isoformat(),
        })

    def request_calls(self, request_id: Optional[str]) -> List[Dict[str, Any]]:
        """Вызовы LLM, привязанные к конкретному запросу (для диагностики)."""
        if not request_id:
            return []
        return list(self._request_calls.get(request_id) or [])

    def reset_request(self, request_id: Optional[str]) -> None:
        if not request_id:
            return
        self._request_calls.pop(request_id, None)


    def clear_cache(self) -> None:
        self.cache.clear()

    def get_metrics(self) -> Dict[str, Any]:
        """Копия метрик (включая extractor_calls/hits/errors §1F и токены)."""
        return dict(self._metrics)

    @staticmethod
    def _consume_usage(response: Any) -> Dict[str, int]:
        """Извлекает статистику токенов (token_usage/usage) из ответа LLM."""
        try:
            meta = getattr(response, "response_metadata", None) or {}
        except Exception:  # noqa: BLE001  (некоторые провайдеры кидают в геттерах)
            meta = {}
        usage = meta.get("token_usage") or meta.get("usage") or {}
        if not isinstance(usage, dict):
            return {}
        return {
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
        }

    @staticmethod
    def _consume_usage_snapshot(usage: Any) -> Dict[str, int]:
        """Нормализует usage_metadata из кэша (LangChain) в {prompt,completion,total}_tokens.

        Поддерживает оба распространённых представления:
          {'prompt_tokens', 'completion_tokens', 'total_tokens'}
          {'input_tokens', 'output_tokens', 'total_tokens'}
        """
        if not isinstance(usage, dict):
            return {}
        total = (
            usage.get("total_tokens")
            or (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0)
        )
        return {
            "total_tokens": int(total or 0),
            "prompt_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            "completion_tokens": int(
                usage.get("completion_tokens") or usage.get("output_tokens") or 0
            ),
        }
# ============================================================
# ГЛОБАЛЬНАЯ ФАБРИКА
# ============================================================

_llm_client: Optional[LLMClient] = None


def get_llm_client(config: Optional[AgentConfig] = None) -> Optional[LLMClient]:
    """Глобальный доступ к LLM-клиенту (не сериализуется)"""
    global _llm_client
    if _llm_client is None:
        config = config or DEFAULT_CONFIG
        if config.use_llm:
            _llm_client = LLMClient(config)
    return _llm_client


def reset_llm_client() -> None:
    global _llm_client
    if _llm_client:
        _llm_client.clear_cache()
        _llm_client = None
