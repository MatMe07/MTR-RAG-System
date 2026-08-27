# agent/core/config.py

from dataclasses import dataclass, field
from typing import Optional
from app.core.config import settings


@dataclass
class AgentConfig:
    """Конфигурация агента"""
    
    # LLM
    use_llm: bool = True
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_timeout: float = 30.0
    
    # Тулы
    tool_timeout: float = 30.0
    tool_retries: int = 2
    max_candidates: int = 40
    
    # Репозиторий
    storage: str = "auto"  # json | db | auto
    
    # LangGraph
    checkpoint_thread_id: str = "default"
    checkpoint_type: str = "memory"  # memory | sqlite
    
    # Логирование
    debug: bool = False
    log_level: str = "INFO"
    
    # Пороги
    min_confidence: float = 0.5
    review_threshold: float = 0.7


DEFAULT_CONFIG = AgentConfig()
