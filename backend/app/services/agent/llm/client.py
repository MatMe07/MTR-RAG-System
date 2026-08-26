# agent/llm/client.py

from typing import Optional, Any, Type, Dict
import time
import json

from .cache import get_llm_cache
from ..core.config import DEFAULT_CONFIG, AgentConfig
from ..core.exceptions import LLMError, LLMTimeoutError


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
        }
    
    @property
    def client(self):
        """Ленивая инициализация LLM-клиента"""
        if self._client is None:
            try:
                from langchain_openai import ChatOpenAI
                
                # Пробуем OpenRouter
                import os
                api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("LLM_API_KEY")
                base_url = os.getenv("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
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
    
    def invoke(self, prompt: str, use_cache: bool = True) -> str:
        """Вызов LLM с кешированием"""
        cache_key = f"llm:{hash(prompt[:500])}"
        
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._metrics["cache_hits"] += 1
                return cached
        
        self._metrics["cache_misses"] += 1
        self._metrics["total_calls"] += 1
        
        start = time.time()
        try:
            response = self.client.invoke(prompt)
            content = getattr(response, "content", str(response))
            
            duration = (time.time() - start) * 1000
            self._metrics["total_duration_ms"] += duration
            
            if use_cache and content:
                self.cache.set(cache_key, content)
            
            return content
            
        except TimeoutError as e:
            duration = (time.time() - start) * 1000
            self._metrics["errors"] += 1
            raise LLMTimeoutError(self.config.llm_timeout) from e
        except Exception as e:
            duration = (time.time() - start) * 1000
            self._metrics["errors"] += 1
            raise LLMError(f"LLM ошибка: {e}") from e
    
    def structured_invoke(self, prompt: str, schema: Type, use_cache: bool = True) -> Any:
        """Вызов LLM со структурированным выводом"""
        cache_key = f"llm_structured:{hash(prompt[:500])}:{schema.__name__}"
        
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._metrics["cache_hits"] += 1
                return cached
        
        self._metrics["cache_misses"] += 1
        self._metrics["total_calls"] += 1
        
        start = time.time()
        try:
            # Пробуем structured output
            if hasattr(self.client, "with_structured_output"):
                result = self.client.with_structured_output(schema).invoke(prompt)
            else:
                # Fallback: парсим JSON вручную
                response = self.client.invoke(prompt)
                content = getattr(response, "content", str(response))
                # Ищем JSON в ответе
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    result = schema(**data)
                else:
                    result = schema()
            
            duration = (time.time() - start) * 1000
            self._metrics["total_duration_ms"] += duration
            
            if use_cache and result:
                self.cache.set(cache_key, result)
            
            return result
            
        except TimeoutError as e:
            duration = (time.time() - start) * 1000
            self._metrics["errors"] += 1
            raise LLMTimeoutError(self.config.llm_timeout) from e
        except Exception as e:
            duration = (time.time() - start) * 1000
            self._metrics["errors"] += 1
            raise LLMError(f"LLM ошибка: {e}") from e
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик"""
        total = self._metrics["cache_hits"] + self._metrics["cache_misses"]
        return {
            "total_calls": self._metrics["total_calls"],
            "cache_hits": self._metrics["cache_hits"],
            "cache_misses": self._metrics["cache_misses"],
            "cache_hit_rate": self._metrics["cache_hits"] / total if total > 0 else 0,
            "avg_duration_ms": self._metrics["total_duration_ms"] / self._metrics["total_calls"] if self._metrics["total_calls"] > 0 else 0,
            "errors": self._metrics["errors"],
        }
    
    def clear_cache(self) -> None:
        self.cache.clear()
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
