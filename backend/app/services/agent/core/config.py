# agent/core/config.py
"""Конфигурация агента.

Единый источник значений (env / .env) — app.config.Settings. Поля LLM,
хранилища и уровня логирования берут дефолты оттуда; остальное —
рантайм-настройки оркестратора (литералы).
"""

from dataclasses import dataclass, field

from app.config import settings


@dataclass
class AgentConfig:
    """Конфигурация агента"""

    # LLM (единый источник: settings / .env)
    use_llm: bool = field(default_factory=lambda: settings.AGENT_LLM_MODE == "on")
    llm_model: str = field(default_factory=lambda: settings.LLM_MODEL)
    llm_temperature: float = field(default_factory=lambda: settings.LLM_TEMPERATURE)
    llm_timeout: float = field(default_factory=lambda: settings.LLM_TIMEOUT)
    llm_base_url: str = field(default_factory=lambda: settings.OPENROUTER_BASE_URL)
    llm_api_key: str = field(default_factory=lambda: settings.OPENROUTER_TOKEN)

    # Тулы
    tool_timeout: float = 30.0
    tool_retries: int = 2
    max_candidates: int = 40

    # Репозиторий (единый источник: settings.AGENT_STORAGE)
    storage: str = field(default_factory=lambda: settings.AGENT_STORAGE)

    # LangGraph
    checkpoint_thread_id: str = "default"
    checkpoint_type: str = "memory"  # memory | sqlite
    recursion_limit: int = 50

    # Логирование (единый источник: settings.LOG_LEVEL)
    debug: bool = False
    log_level: str = field(default_factory=lambda: settings.LOG_LEVEL)

    # Пороги
    min_confidence: float = 0.5
    review_threshold: float = 0.7


DEFAULT_CONFIG = AgentConfig()
