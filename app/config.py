import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

# 🔴 [핵심 1] .env 파일을 찾기 위해 dotenv 로드
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """
    애플리케이션 설정을 관리하는 Pydantic 모델.
    .env 파일 또는 환경 변수에서 값을 읽어옵니다.
    """

    # 1. LLM 설정
    # ----------------------------------------------------
    # .env 파일에서 LLM_MODEL_NAME을 읽어옵니다.
    LLM_MODEL_NAME: str = Field(..., env="LLM_MODEL_NAME")

    # LLM_API_BASE_URL (기본값: shimmy-source)
    LLM_API_BASE_URL: str = "http://llm-server:11434/v1"

    # LLM 요청 타임아웃
    LLM_TIMEOUT: int = 300

    # 2. Celery & Redis (브로커 및 백엔드)
    # ----------------------------------------------------
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # 3. Vector DB (Qdrant)
    # ----------------------------------------------------
    QDRANT_URL: str = "http://qdrant:6333"
    VECTOR_DIMENSION: int = 768  # (mxbai-embed-large-v1 기준)

    # 4. Search DB (MeiliSearch)
    # ----------------------------------------------------
    MEILI_URL: str = "http://meilisearch:7700"

    # .env 파일에서 MEILI_MASTER_KEY를 읽어옵니다.
    MEILI_MASTER_KEY: str = Field(..., env="MEILI_MASTER_KEY")

    # 5. AI 모듈 경로 (🔴 [!!! 핵심 수정 !!!] 🔴)
    # ----------------------------------------------------
    # docker-compose.yml에서 주입되는 MODEL_PATH를 Pydantic이 인식하도록 필드 추가
    # (기본값은 docker-compose.yml의 값과 동일하게 설정)
    MODEL_PATH: str = "/usr/src/models/classifier"

    class Config:
        # 🔴 [핵심 2] .env 파일 경로 명시
        # 이 설정이 .env 파일에서 LLM_MODEL_NAME, MEILI_MASTER_KEY 등을
        # 올바르게 읽어오도록 보장합니다.
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore'  # .env에 정의되지 않은 필드는 무시


# settings 객체를 생성하여 다른 모듈에서 import 할 수 있도록 함
settings = Settings()