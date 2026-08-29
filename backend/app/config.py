from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Дефолты — локальный docker-стек (docker-compose.yml). Продакшен/облако
    # задаётся через переменные окружения или .env (в gitignore).
    DATABASE_URL: str = "postgresql://syn:syn_password@localhost:5432/syn"

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "changeme"

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "mtr_descriptions"
    QDRANT_API_KEY: Optional[str] = None

    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "change-this-to-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    LLM_MODEL: str = "llama3:70b"
    LLM_TEMPERATURE: float = 0.0
    LLM_TIMEOUT: int = 120
    OPENROUTER_BASE_URL: str = ""
    OPENROUTER_TOKEN: str = ""

    OCR_ENGINE: str = "tesseract"

    CORS_ORIGINS: str = "http://localhost:3000"

    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    HF_TOKEN: str = ""

    LOG_LEVEL: str = "INFO"
    AGENT_LLM_MODE: str = "on"
    AGENT_STORAGE: str = "db"

    USE_LOCAL_LLM: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "qwen2.5:3b"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
