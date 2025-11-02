# D:\42_asia-hackathon\app\config.py

import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


# 🚨 [수정 4]: .env의 모든 변수를 로드하도록 BaseSettings 사용
class Settings(BaseSettings):
    LLM_MODEL_NAME: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    QDRANT_URL: str
    MEILI_URL: str
    MEILI_MASTER_KEY: Optional[str] = None
    LLM_API_BASE_URL: str
    LLM_TIMEOUT: int = 300

    # 기존 코드에서 가져온 값들 (이 값들은 .env에 없을 수 있으므로 기본값 유지)
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    MEILI_HOST_URL: str = "http://meilisearch:7700"
    LLM_BASE_URL: str = "http://shimmy-server:8001/v1"
    EMBEDDING_MODEL_NAME: str = "mxbai-embed-large.safetensors"
    VECTOR_DIMENSION: int = 1024

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()