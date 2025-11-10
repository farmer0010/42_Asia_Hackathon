# D:\42_asia-hackathon\app\main.py
# [수정 완료된 파일]

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

from .config import settings
from .logger_config import setup_logging
from .worker import process_document_pipeline, celery_app
from . import schemas
from .pipeline import llm_tasks

setup_logging()
log = logging.getLogger("uvicorn")

# --- 서비스 클라이언트 초기화 ---
meili_client = None
qdrant_cli = None

# 🔴 [수정 1] MEILI_HOST_URL -> MEILI_URL
try:
    log.info(f"MeiliSearch 연결 시도: {settings.MEILI_URL}")
    meili_client = meilisearch.Client(url=settings.MEILI_URL, api_key=settings.MEILI_MASTER_KEY)
    if not meili_client.is_healthy():
        raise Exception("MeiliSearch is not healthy")
    log.info("MeiliSearch 연결 성공.")
except Exception as e:
    log.error(f"MeiliSearch 연결 실패: {e}")

# 🔴 [수정 2] QDRANT_HOST/PORT -> QDRANT_URL
try:
    log.info(f"Qdrant 연결 시도: {settings.QDRANT_URL}")
    qdrant_cli = qdrant_client.QdrantClient(
        url=settings.QDRANT_URL  # host/port 대신 URL 사용
    )
    qdrant_cli.get_collections()  # 헬스 체크 대용
    log.info("Qdrant 연결 성공.")
except Exception as e:
    log.error(f"Qdrant 연결 실패: {e}")

QDRANT_COLLECTION_NAME = "documents_collection"
VECTOR_DIMENSION = settings.VECTOR_DIMENSION


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
            qdrant_cli.get_collections()
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
        response = requests.get(f"{settings.LLM_API_BASE_URL}/health", timeout=1)
        if response.status_code == 200:
            health_results["llm_server"] = "ok"
        else:
            health_results["llm_server"] = f"status_code: {response.status_code}"
    except Exception as e:
        health_results["llm_server"] = "connection_failed"

    if any(status != "ok" for status in health_results.values()):
        return schemas.HealthCheck(status="error", services=health_results)
    return schemas.HealthCheck(status="ok", services=health_results)


@app.get("/search", tags=["Search"], response_model=schemas.SearchResponse)
async def search_documents(query: str, limit: int = 10):
    """
    MeiliSearch와 Qdrant를 사용한 하이브리드 검색.
    frontend/script.js 가 이 API를 호출합니다.
    """
    if not meili_client or not qdrant_cli or not llm_tasks.embed_model:
        log.error("Search, Vector, or Embedding client is not initialized.")
        raise HTTPException(status_code=503, detail="Search service is not available")

    try:
        # 1. MeiliSearch (Keyword Search)
        log.info(f"MeiliSearch (Keyword) 쿼리: '{query}'")
        meili_index = meili_client.index("documents")
        # 🔴 [수정] script.js의 스키마 불일치 해결 (doc_type, snippet 반환)
        search_results = meili_index.search(
            query,
            {'limit': limit, 'attributesToRetrieve': ['document_id', 'filename', 'doc_type', 'snippet']}
        )
        exact_hits = search_results.get('hits', [])

        # 2. Qdrant (Semantic Search)
        log.info(f"Qdrant (Semantic) 쿼리: '{query}'")
        query_vector = llm_tasks.embed_model.encode(query).tolist()

        semantic_hits_response = qdrant_cli.search(
            collection_name="document_chunks",
            query_vector=query_vector,
            limit=limit,
            with_payload=True  # payload(메타데이터) 포함
        )

        # 3. 결과 포맷팅 (script.js가 기대하는 형식으로)
        semantic_hits = []
        for hit in semantic_hits_response:
            payload = hit.payload
            semantic_hits.append({
                "document_id": payload.get("document_id"),
                "filename": payload.get("filename", "Unknown"),
                "doc_type": payload.get("doc_type", "Unknown"),
                "snippet": payload.get("text", "No snippet available.")  # text 필드를 snippet으로 사용
            })

        # 4. SearchResponse 스키마에 맞춰 반환
        return schemas.SearchResponse(
            exact_matches=exact_hits,
            semantic_matches=semantic_hits
        )

    except Exception as e:
        log.error(f"Search query '{query}' 처리 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# 🔴 [수정 3] 엔드포인트 이름을 /upload -> /uploadfile/ 로 변경 (끝에 / 포함)
@app.post("/uploadfile/", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())

    # 🚨 [경로 수정] 공유 볼륨 /uploads_data/input/ 사용
    temp_dir = Path("/uploads_data/input/")
    temp_dir.mkdir(parents=True, exist_ok=True)  # parents=True 추가

    file_ext = Path(file.filename).suffix
    temp_file_path = temp_dir / f"{job_id}{file_ext}"
    try:
        log.info(f"[{job_id}] 파일 수신: {file.filename}, 공유 볼륨 저장 위치: {temp_file_path}")
        with open(temp_file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Celery 작업 호출
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


# 🚨 [수정] JobStatusResponse -> TaskStatusResponse
@app.get("/tasks/{task_id}", status_code=status.HTTP_200_OK, response_model=schemas.TaskStatusResponse)
async def get_task_status(task_id: str):
    log.info(f"작업 상태 조회 요청: {task_id}")
    try:
        task_result = celery_app.AsyncResult(task_id)
        status = task_result.status
        result = task_result.result

        if status == "PENDING":
            log.warning(f"'{task_id}'에 대한 작업을 찾을 수 없습니다 (PENDING).")
            # 404 대신 PENDING 상태를 반환 (프론트엔드가 폴링)
            return schemas.TaskStatusResponse(task_id=task_id, status="PENDING")

        if status == "FAILURE":
            log.warning(f"작업 실패: {task_id}, Error: {str(result)}")
            return schemas.TaskStatusResponse(task_id=task_id, status=status, result={"error": str(result)})

        # 🚨 [수정] 성공 시, result가 PipelineResult 객체여야 함
        return schemas.TaskStatusResponse(task_id=task_id, status=status, result=result)

    except Exception as e:
        log.error(f"작업 상태 조회 중 예외 발생: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving task status")