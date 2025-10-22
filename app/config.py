import os
from functools import lru_cache

class Settings:
    """
    애플리케이션 설정을 관리하는 클래스입니다.
    환경변수에서 값을 읽어오며, 기본값을 제공합니다.
    """
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
    lru_cache를 사용하여 한번 생성된 객체를 재사용합니다.
    """
    return Settings()