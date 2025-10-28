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
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemma3:4b") # 생성(추출,요약)용 모델

    # 시맨틱 검색 설정 추가
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "mxbai-embed-large") # 임베딩(검색)용 모델
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", 1024)) # mxbai-embed-large의 차원


@lru_cache()
def get_settings():
    return Settings()