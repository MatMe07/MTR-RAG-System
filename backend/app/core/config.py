
from dotenv import load_dotenv
import os
from pathlib import Path

# Грузим .env из корня репозитория (не из CWD), чтобы запуск из backend/
# и из корня проекта работал одинаково.
# config.py -> app/core -> app -> backend -> корень репозитория (parents[3])
_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    QDRANT_URL = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "")
    COLLECTION_NAME = "tplink_DOCS"

    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    EMBEDDING_DEVICE = "cpu"
    VECTOR_SIZE = 1024

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://mtr:password@localhost:5432/mtr")

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_TOKEN")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL")
    LLM_MODEL = os.getenv("LLM_MODEL")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))

    # Локальный фолбэк (Ollama) используется, когда OpenRouter недоступен
    # или USE_LOCAL_LLM=true.
    USE_LOCAL_LLM = _env_bool("USE_LOCAL_LLM", False)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    # Режим LLM-усиления агентного конвейера: auto | on | off.
    # auto — всегда пытаться с офлайн-фолбэком, off — только офлайн.
    AGENT_LLM_MODE = os.getenv("AGENT_LLM_MODE", "on")

    # Источник данных агентского слоя: json | db | auto.
    # json — демо-JSON, db — PostgreSQL + Qdrant, auto — пробуем db, при
    # недоступности БД падаем на json (см. app/services/agents/repository.py).
    AGENT_STORAGE = os.getenv("AGENT_STORAGE", "db")


settings = Settings()
