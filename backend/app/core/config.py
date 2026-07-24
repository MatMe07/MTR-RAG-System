
from dotenv import load_dotenv
import os

load_dotenv()



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


settings = Settings()
