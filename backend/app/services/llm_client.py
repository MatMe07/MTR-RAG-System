"""Транспорт LLM-клиента: OpenRouter (основной) -> Ollama (фолбэк).

Вынесен из llm_service.py без изменения поведения. lazy-импорт langchain
сохранён, чтобы LLMClient можно было загружать без установленных
langchain-зависимостей (например, в офлайн-тестах).
"""

from typing import Optional, Type

from app.core.config import settings


class LLMClient:
    """LLM-клиент с фолбэком OpenRouter -> локальная Ollama.

    Основной провайдер: OpenRouter (ключ из .env). Если запрос к нему падает
    или таймаутит, автоматически переключаемся на Ollama. Если ключа OpenRouter
    нет или USE_LOCAL_LLM=true — сразу работаем через Ollama.
    """

    def __init__(self):
        self.use_local = getattr(settings, "USE_LOCAL_LLM", False)

        # Если явно не включён локальный режим, но ключа нет — всё равно уходим
        # в Ollama, чтобы сервис не падал из-за конфигурации.
        self.api_key = None if self.use_local else settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE

        self._llm = None
        self._fallback = None

    def _make_client(self, base_url, api_key, model, json_mode=False):
        """Создаёт ChatOpenAI-совместимый клиент (ленивый импорт)."""
        from langchain_openai import ChatOpenAI

        extra_kwargs = {}
        if json_mode:
            extra_kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=self.temperature,
            timeout=settings.LLM_TIMEOUT,
            max_retries=settings.LLM_MAX_RETRIES,
            **extra_kwargs
        )

    @property
    def llm(self):
        """Основной клиент: OpenRouter (если настроен), иначе Ollama."""
        if self._llm is None:
            if not self.use_local and self.api_key and self.base_url:
                self._llm = self._make_client(
                    self.base_url, self.api_key, self.model, json_mode=False
                )
            else:
                self._llm = self._make_client(
                    settings.OLLAMA_BASE_URL, "ollama", settings.OLLAMA_MODEL,
                    json_mode=settings.LLM_JSON_MODE,
                )
        return self._llm

    @property
    def fallback_llm(self):
        """Локальный фолбэк (Ollama). Есть только когда основной — OpenRouter."""
        if self.use_local:
            return None
        if self.api_key and self.base_url:
            if self._fallback is None:
                self._fallback = self._make_client(
                    settings.OLLAMA_BASE_URL, "ollama", settings.OLLAMA_MODEL,
                    json_mode=settings.LLM_JSON_MODE,
                )
            return self._fallback
        return None

    def invoke(self, prompt: str):
        """Вызывает основную модель, при сбое — фолбэк Ollama."""
        try:
            return self.llm.invoke(prompt)
        except Exception:
            fb = self.fallback_llm
            if fb is None:
                raise
            return fb.invoke(prompt)

    def structured_invoke(self, prompt: str, schema: Type):
        """Вызывает модель со structured output, при сбое — фолбэк Ollama."""
        try:
            return self.llm.with_structured_output(schema).invoke(prompt)
        except Exception:
            fb = self.fallback_llm
            if fb is None:
                raise
            return fb.with_structured_output(schema).invoke(prompt)


# Совместимый псевдоним для импортёров старого имени.
LLMServiceBase = LLMClient


def make_llm_client(**overrides) -> LLMClient:
    """Фабрика: просто конструирует LLMClient (для инжекции в сервисы)."""
    return LLMClient()