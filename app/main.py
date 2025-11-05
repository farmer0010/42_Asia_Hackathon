# D:\42_asia-hackathon\app\main.py

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

# 🚨 [수정 6]: 모든 모듈이 config와 schemas의 새 이름을 사용하도록 함
from .config import settings
from .logger_config import setup_logging
from .worker import process_document_pipeline, celery_app
from . import schemas  # 수정된 schemas.py 임포트
from .pipeline import llm_tasks

setup_logging()
log = logging.getLogger("uvicorn")

# --- 서비스 클라이언트 초기화 ---
meili_client = None
qdrant_cli = None

try:
    log.info(f"MeiliSearch 연결 시도: {settings.MEILI_HOST_URL}")
    meili_client = meilisearch.Client(url=settings.MEILI_HOST_URL, api_key=settings.MEILI_MASTER_KEY)
    if not meili_client.is_healthy():
        raise Exception("MeiliSearch is not healthy")
    log.info("MeiliSearch 연결 성공.")
except Exception as e:
    log.error(f"MeiliSearch 연결 실패: {e}")

try:
    log.info(f"Qdrant 연결 시도: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    qdrant_cli = qdrant_client.QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT
    )
    qdrant_cli.get_collections()  # 헬스 체크 대용
    log.info("Qdrant 연결 성공.")
except Exception as e:
    log.error(f"Qdrant 연결 실패: {e}")

QDRANT_COLLECTION_NAME = "documents_collection"
VECTOR_DIMENSION = settings.VECTOR_DIMENSION  # config.py의 VECTOR_DIMENSION 사용


def setup_databases():
    if meili_client:
        try:
            log.info("MeiliSearch 인덱스('documents') 설정을 시작합니다...")
            index = meili_client.index("documents")
            index.update_filterable_attributes(['doc_type', 'created_at'])
            index.update_sortable_attributes(['created_at'])
            index.update_ranking_rules(["words", "typo", "proximity", "attribute", "sort", "exactness"])
            log.info("MeiliSearch 인덱스 설정 완료.")
        except Exception as e:
            log.error(f"MeiliSearch 인덱스 설정 중 에러 발생: {e}", exc_info=True)
    else:
        log.warning("MeiliSearch 클라이언트가 초기화되지 않아 설정을 건너뜁니다.")

    if qdrant_cli:
        try:
            log.info(f"Qdrant 컬렉션('{QDRANT_COLLECTION_NAME}') 확인 및 생성을 시작합니다...")
            try:
                collection_info = qdrant_cli.get_collection(collection_name=QDRANT_COLLECTION_NAME)
                log.info(f"Qdrant 컬렉션 '{QDRANT_COLLECTION_NAME}'이(가) 이미 존재합니다.")
                current_dim = collection_info.config.params.vectors.size
                if current_dim != VECTOR_DIMENSION:
                    log.warning(f"벡터 차원이 다릅니다! (현재: {current_dim}, 필요: {VECTOR_DIMENSION}). 컬렉션을 재생성합니다.")
                    qdrant_cli.delete_collection(collection_name=QDRANT_COLLECTION_NAME)
                    raise Exception("컬렉션 차원이 달라 재생성 필요")
            except Exception as e:
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


app = FastAPI(title="42 Asia Hackathon - AI Document Engine", lifespan=lifespan)
origins = ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])
Instrumentator().instrument(app).expose(app)


@app.get("/", tags=["Root"])
def read_root():
    return {"Hello": "42_Asia_Hackathon_AI_Engine"}


@app.get("/health", tags=["Monitoring"], response_model=schemas.HealthCheck)
def health_check():
    health_results = {"api": "ok", "redis": "checking", "qdrant": "checking", "meilisearch": "checking",
                      "llm_server": "checking"}
    try:
        celery_app.control.ping()
        health_results["redis"] = "ok"
    except Exception as e:
        health_results["redis"] = str(e)
    if qdrant_cli:
        try:
            qdrant_cli.get_collections()  # health_check() 대신
            health_results["qdrant"] = "ok"
        except Exception as e:
            health_results["qdrant"] = str(e)
    else:
        health_results["qdrant"] = "client not initialized"
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
    try:
        response = requests.get(f"{settings.LLM_API_BASE_URL}/health", timeout=1)  # settings.LLM_API_BASE_URL 사용
        if response.status_code == 200:
            health_results["llm_server"] = "ok"
        else:
            health_results["llm_server"] = f"status_code: {response.status_code}"
    except Exception as e:
        health_results["llm_server"] = "connection_failed"

    if any(status != "ok" for status in health_results.values()):
        return schemas.HealthCheck(status="error", services=health_results)
    return schemas.HealthCheck(status="ok", services=health_results)


# ... (주석 처리된 /search 엔드포인트) ...

@app.get("/job/{job_id}", status_code=status.HTTP_200_OK, response_model=schemas.JobStatusResponse)  # 🚨 [수정] 스키마 이름 변경
async def get_job_status(job_id: str):
    log.info(f"작업 상태 조회 요청: {job_id}")
    try:
        task_result = celery_app.AsyncResult(job_id)
        status = task_result.status
        result = task_result.result
        if status == "PENDING":
            log.warning(f"'{job_id}'에 대한 작업을 찾을 수 없습니다 (PENDING).")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job ID {job_id} not found.")
        if status == "FAILURE":
            log.warning(f"작업 실패: {job_id}, Error: {str(result)}")
            return schemas.JobStatusResponse(job_id=job_id, status=status, message=str(result))
        return schemas.JobStatusResponse(job_id=job_id, status=status, result=result)
    except Exception as e:
        log.error(f"작업 상태 조회 중 예외 발생: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving job status")


@app.post("/upload", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.UploadResponse)  # 🚨 [수정] 스키마 이름 변경
async def upload_document(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    temp_dir = Path("/tmp/doc_uploads")
    temp_dir.mkdir(exist_ok=True)
    file_ext = Path(file.filename).suffix
    temp_file_path = temp_dir / f"{job_id}{file_ext}"
    try:
        log.info(f"[{job_id}] 파일 수신: {file.filename}, 임시 저장 위치: {temp_file_path}")
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())
        process_document_pipeline.delay(
            job_id=job_id,
            file_path=str(temp_file_path),
            file_name=file.filename,
            file_mime_type=file.content_type
        )
        log.info(f"[{job_id}] Celery 작업 생성 완료.")
        return schemas.UploadResponse(job_id=job_id, filename=file.filename)
    except Exception as e:
        log.error(f"파일 업로드 처리 중 심각한 에러 발생: {e}", exc_info=True)
        if temp_file_path.exists():
            os.remove(temp_file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"File processing error: {e}")