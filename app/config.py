import os
from functools import lru_cache

class Settings:
    # Celery & Redis 설정
    REDIS_BROKER_URL: str = os.getenv("REDIS_BROKER_URL", "redis://redis-broker:6379/0")

    # MeiliSearch 설정
    MEILI_HOST_URL: str = os.getenv("MEILI_HOST_URL", "http://meilisearch:7700")

    # Qdrant 설정
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "qdrant")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", 6333))

    # LLM 설정
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemma3:4b")


@lru_cache()
def get_settings():
    return Settings()