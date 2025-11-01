import os
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
from typing import List, Optional
import logging
import meilisearch
import qdrant_client
from qdrant_client import models
from pathlib import Path
import requests

# 'app' 모듈 내의 다른 파일을 임포트합니다.
from .config import settings
from .logger_config import setup_logging
from .worker import process_document_pipeline, celery_app
from . import schemas
from .pipeline import llm_tasks

# --- 로거 및 설정 초기화 ---
setup_logging()
log = logging.getLogger("uvicorn")

# --- 서비스 클라이언트 초기화 ---
try:
    log.info(f"MeiliSearch 연결 시도: {settings.MEILI_HOST_URL}")

    # 🚨 [최종 수정]: MeiliSearch Master Key 설정 (API Key 오류 해결)
    # setup_databases에서 인덱스 설정을 변경하려면 Master Key가 필요합니다.
    # settings 객체에서 MEILI_MASTER_KEY를 가져오되, 정의되어 있지 않으면 None을 사용합니다.
    meili_api_key = getattr(settings, 'MEILI_MASTER_KEY', None)
    if meili_api_key is None:
        log.warning("⚠️ MEILI_MASTER_KEY가 설정되지 않았습니다. 인덱스 설정이 실패할 수 있습니다.")

    meili_client = meilisearch.Client(url=settings.MEILI_HOST_URL, api_key=meili_api_key)

    if not meili_client.is_healthy():
        raise Exception("MeiliSearch is not healthy")
    log.info("MeiliSearch 연결 성공.")
except Exception as e:
    log.error(f"MeiliSearch 연결 실패: {e}. Master Key가 필요할 수 있습니다.")
    meili_client = None  # 연결 실패 시 None으로 설정

try:
    log.info(f"Qdrant 연결 시도: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    qdrant_cli = qdrant_client.QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT
    )
    # Qdrant 연결 확인
    qdrant_cli.get_collections()
    log.info("Qdrant 연결 성공.")
except Exception as e:
    log.error(f"Qdrant 연결 실패: {e}")
    qdrant_cli = None  # 연결 실패 시 None으로 설정

QDRANT_COLLECTION_NAME = "documents_collection"
VECTOR_DIMENSION = settings.VECTOR_DIMENSION


def setup_databases():
    """
    애플리케이션 시작 시 MeiliSearch 인덱스와 Qdrant 컬렉션을 설정합니다.
    """
    # 1. MeiliSearch 설정
    if meili_client:
        try:
            log.info("MeiliSearch 인덱스('documents') 설정을 시작합니다...")
            index = meili_client.index("documents")

            # 🚨 Master Key가 없으면 이 부분이 403 Forbidden 오류를 발생시킵니다.
            index.update_filterable_attributes([
                'doc_type',
                'created_at'
            ])
            index.update_sortable_attributes([
                'created_at'
            ])
            index.update_ranking_rules([
                "words", "typo", "proximity", "attribute", "sort", "exactness"
            ])
            log.info("MeiliSearch 인덱스 설정 완료.")
        except Exception as e:
            # 이 오류가 발생했다면 .env에 MEILI_MASTER_KEY가 누락된 것입니다.
            log.error(f"MeiliSearch 인덱스 설정 중 에러 발생: {e}", exc_info=True)
            log.warning("MeiliSearch 인덱스 설정 실패. MEILI_MASTER_KEY를 확인하세요.")
    else:
        log.warning("MeiliSearch 클라이언트가 초기화되지 않아 설정을 건너뜁니다.")

    # 2. Qdrant 설정
    if qdrant_cli:
        try:
            log.info(f"Qdrant 컬렉션('{QDRANT_COLLECTION_NAME}') 확인 및 생성을 시작합니다...")
            try:
                collection_info = qdrant_cli.get_collection(collection_name=QDRANT_COLLECTION_NAME)
                log.info(f"Qdrant 컬렉션 '{QDRANT_COLLECTION_NAME}'이(가) 이미 존재합니다.")

                # 벡터 차원 확인 및 재생성 (필요시)
                current_dim = collection_info.config.params.vectors.size
                if current_dim != VECTOR_DIMENSION:
                    log.warning(f"벡터 차원이 다릅니다! (현재: {current_dim}, 필요: {VECTOR_DIMENSION}). 컬렉션을 재생성합니다.")
                    qdrant_cli.delete_collection(collection_name=QDRANT_COLLECTION_NAME)
                    raise Exception("컬렉션 차원이 달라 재생성 필요")

            except Exception as e:
                # 컬렉션이 존재하지 않거나 재생성이 필요한 경우
                log.info(f"컬렉션이 존재하지 않아 새로 생성합니다. (차원: {VECTOR_DIMENSION})")
                qdrant_cli.recreate_collection(
                    collection_name=QDRANT_COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=VECTOR_DIMENSION,
                        distance=models.Distance.COSINE
                    )
                )
                log.info(f"Qdrant 컬렉션 '{QDRANT_COLLECTION_NAME}' 생성 완료.")
        except Exception as e:
            log.error(f"Qdrant 컬렉션 설정 중 심각한 에러 발생: {e}", exc_info=True)
    else:
        log.warning("Qdrant 클라이언트가 초기화되지 않아 설정을 건너뜁니다.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("애플리케이션 시작...")
    setup_databases()
    yield
    log.info("애플리케이션 종료...")


app = FastAPI(
    title="42 Asia Hackathon - AI Document Engine",
    description="문서의 의미를 이해하는 지능형 AI 엔진 API (키워드 + 시맨틱 검색 지원)",
    version="1.0.0",
    lifespan=lifespan
)

# --- 미들웨어 설정 ---
origins = ["*"]  # 데모를 위해 모든 오리진 허용

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)


# --- 라우트 정의 ---

@app.get("/", tags=["Root"])
def read_root():
    return {"Hello": "42_Asia_Hackathon_AI_Engine"}


@app.get("/health", tags=["Monitoring"])
def health_check():
    """서비스 상태 확인"""
    health_results = {
        "api": "ok",
        "redis": "checking",
        "qdrant": "checking",
        "meilisearch": "checking",
        "llm_server": "checking"
    }

    # Redis (Celery Broker)
    try:
        celery_app.control.ping()
        health_results["redis"] = "ok"
    except Exception as e:
        health_results["redis"] = str(e)

    # Qdrant
    if qdrant_cli:
        try:
            # 🚨 [수정]: Qdrant 헬스 체크 함수 안정화
            qdrant_cli.get_collections()
            health_results["qdrant"] = "ok"
        except Exception as e:
            health_results["qdrant"] = str(e)
    else:
        health_results["qdrant"] = "client not initialized"

    # MeiliSearch
    if meili_client:
        try:
            if meili_client.is_healthy():
                health_results["meilisearch"] = "ok"
            else:
                health_results["meilisearch"] = "unhealthy"
        except Exception as e:
            health_results["meilisearch"] = str(e)
    else:
        health_results["meilisearch"] = "client not initialized"

    # LLM Server (Shimmy)
    try:
        response = requests.get(f"{settings.LLM_API_BASE_URL}/health", timeout=1)
        if response.status_code == 200:
            health_results["llm_server"] = "ok"
        else:
            health_results["llm_server"] = f"status_code: {response.status_code}"
    except Exception as e:
        health_results["llm_server"] = "connection_failed"

    # 모든 서비스가 ok가 아니면 503 반환
    if any(status != "ok" for status in health_results.values()):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_results)

    return {"status": "ok", "services": health_results}


# ◀◀◀ [주석 처리 유지] /search 엔드포인트는 SyntaxError 방지를 위해 주석 처리합니다. ◀◀◀
# @app.get("/search", status_code=status.HTTP_200_OK)
# async def search_documents(
#     query: str,
#     doc_type: Optional[str] = None
# ):
#     try:
#         raise HTTPException(st  # <--- 이 줄이 SyntaxError의 원인입니다.
#     except Exception as e:
#         log.error(f"Search failed: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail="Search operation failed")
# ◀◀◀ [수정 완료] ◀◀◀


@app.get("/job/{job_id}", status_code=status.HTTP_200_OK, response_model=schemas.JobStatusResponse)
async def get_job_status(job_id: str):
    """Celery 작업 ID를 사용하여 문서 처리 상태를 조회합니다."""
    log.info(f"작업 상태 조회 요청: {job_id}")
    try:
        task_result = celery_app.AsyncResult(job_id)

        status = task_result.status
        result = task_result.result

        if status == "PENDING":
            # 작업이 존재하지 않거나 아직 시작되지 않음
            log.warning(f"'{job_id}'에 대한 작업을 찾을 수 없습니다 (PENDING).")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job ID {job_id} not found.")

        if status == "FAILURE":
            log.warning(f"작업 실패: {job_id}, Error: {str(result)}")
            return schemas.JobStatusResponse(
                job_id=job_id,
                status=status,
                message=str(result)
            )

        # PENDING도 아니고 FAILURE도 아니면 (PROCESSING 또는 SUCCESS)
        return schemas.JobStatusResponse(
            job_id=job_id,
            status=status,
            result=result
        )

    except Exception as e:
        log.error(f"작업 상태 조회 중 예외 발생: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving job status")


@app.post("/upload", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.UploadResponse)
async def upload_document(
        file: UploadFile = File(...)
):
    """단일 문서를 업로드하여 처리 파이프라인을 시작합니다."""

    job_id = str(uuid.uuid4())
    temp_dir = Path("/tmp/doc_uploads")
    temp_dir.mkdir(exist_ok=True)

    # 파일 확장자 유지
    file_ext = Path(file.filename).suffix
    temp_file_path = temp_dir / f"{job_id}{file_ext}"

    try:
        log.info(f"[{job_id}] 파일 수신: {file.filename}, 임시 저장 위치: {temp_file_path}")

        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Celery 작업 생성
        process_document_pipeline.delay(
            job_id=job_id,
            file_path=str(temp_file_path),
            file_name=file.filename,
            file_mime_type=file.content_type
        )
        log.info(f"[{job_id}] Celery 작업 생성 완료.")

        return schemas.UploadResponse(
            job_id=job_id,
            filename=file.filename,
            message="File received and processing started."
        )

    except Exception as e:
        log.error(f"파일 업로드 처리 중 심각한 에러 발생: {e}", exc_info=True)
        # 임시 파일이 생성되었다면 삭제 시도
        if temp_file_path.exists():
            os.remove(temp_file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"File processing error: {e}")