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


@lru_cache()
def get_settings():
    """
    설정 객체를 반환하는 함수입니다.
    lru_cache를 사용하여 한번 생성된 객체를 재사용.
    """
    return Settings()