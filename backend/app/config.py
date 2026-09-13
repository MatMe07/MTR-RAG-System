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
    # Legacy-имя единой коллекции (нормы раньше жили в mtr_descriptions).
    # Актуальные коллекции — ниже: нормы/norm_documents, каталог/mtr_descriptions,
    # паспорта/documents.
    QDRANT_COLLECTION: str = "mtr_descriptions"
    QDRANT_NORMS_COLLECTION: str = "norm_documents"
    QDRANT_CATALOG_COLLECTION: str = "mtr_descriptions"
    QDRANT_DOCUMENTS_COLLECTION: str = "documents"
    QDRANT_API_KEY: Optional[str] = None

    REDIS_URL: str = "redis://localhost:6379/0"

    # OCR-движок паспортов (Фаза 3): tesseract | easyocr | doctr | none.
    # Docling поставляется как optional-dependency (см. pyproject [ocr]);
    # при его отсутствии pipeline переходит в статус error с сообщением.
    OCR_ENGINE: str = "tesseract"
    # Каталог сохранения загруженных паспортов (пусто → <repo>/data/uploads).
    DOCUMENT_UPLOAD_DIR: str = ""

    SECRET_KEY: str = "change-this-to-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # Окружение: development | production. В production запрещены дефолтные
    # значения SECRET_KEY и учётные записи (должны задаваться через env).
    ENV: str = "development"

    # Параметры агента (единый источник — подхватываются AgentConfig)
    LLM_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"
    LLM_TEMPERATURE: float = 0.0
    LLM_TIMEOUT: int = 120
    OPENROUTER_BASE_URL: str = ""
    OPENROUTER_TOKEN: str = ""
    OPENROUTER_API_KEY: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    AGENT_LLM_MODE: str = "on"
    AGENT_STORAGE: str = "db"

    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
