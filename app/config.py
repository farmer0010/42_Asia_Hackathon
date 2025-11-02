# D:\42_asia_hackathon\app\config.py (전체 코드)

import os
from functools import lru_cache
from typing import Optional


class Settings:
    # 1. LLM 설정
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "Qwen2-1.5B-Instruct.Q4_K_M.gguf")
    LLM_API_BASE_URL: str = os.getenv("LLM_API_BASE_URL", "http://llm-server:11434")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", 300))

    # 2. Celery & Redis 설정
    REDIS_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0") # .env 변수명 사용
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

    # 3. MeiliSearch 설정
    MEILI_HOST_URL: str = os.getenv("MEILI_URL", "http://meilisearch:7700")
    # 🚨 [해결]: MEILI_MASTER_KEY 추가 (API Key 오류 해결)
    MEILI_MASTER_KEY: Optional[str] = os.getenv("MEILI_MASTER_KEY", None)

    # 4. Qdrant 설정
    # 🚨 [해결]: QDRANT_URL 대신 호스트 이름만 사용하도록 수정 (Qdrant 연결 오류 해결)
    QDRANT_HOST: str = os.getenv("QDRANT_URL", "qdrant").replace("http://", "").replace("https://", "").split(':')[0]
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", 6333))

    # 5. 시맨틱 검색 설정
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "mxbai-embed-large.safetensors")
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", 1024))


@lru_cache()
def get_settings():
    return Settings()

# --- settings 객체 생성 ---
settings = get_settings()