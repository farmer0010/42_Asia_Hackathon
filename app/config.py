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

    # [수정] LLM 설정 (Shimmy)
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://shimmy-server:8001/v1")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "google_gemma-3-4b-it-Q4_K_M.gguf")

    # [수정] 시맨틱 검색 설정 (Shimmy)
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "mxbai-embed-large.safetensors")
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", 1024))


@lru_cache()
def get_settings():
    return Settings()