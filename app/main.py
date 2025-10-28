from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, UploadFile, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
import meilisearch
import time
import qdrant_client
from qdrant_client import models
from typing import List, Optional
import logging
from .worker import process_document, celery_app, llm_client
from .pipeline import llm_tasks
from .config import get_settings
from . import schemas
from .logger_config import setup_logging

setup_logging()
log = logging.getLogger(__name__)
settings = get_settings()
meili_client = meilisearch.Client(url=settings.MEILI_HOST_URL)
qdrant_cli = qdrant_client.QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
QDRANT_COLLECTION_NAME = "documents_collection"
VECTOR_DIMENSION = settings.VECTOR_DIMENSION

def setup_database():
    try:
        log.info("MeiliSearch 설정을 시작합니다...")
        index = meili_client.index("documents")
        index.update_filterable_attributes([
            'doc_type',
            'pii_count',
        ])
        index.update_ranking_rules([
            "words", "typo", "proximity", "attribute", "sort", "exactness"
        ])
        log.info("MeiliSearch 설정 업데이트 완료.")
    except Exception as e:
        log.error(f"MeiliSearch 설정 중 에러 발생: {e}")

    try:
        log.info(f"Qdrant 컬렉션 '{QDRANT_COLLECTION_NAME}' 확인 및 생성을 시작합니다...")
        try:
            collection_info = qdrant_cli.get_collection(collection_name=QDRANT_COLLECTION_NAME)
            log.info(f"Qdrant 컬렉션 '{QDRANT_COLLECTION_NAME}'이(가) 이미 존재합니다.")
            current_dim = collection_info.config.params.vectors.size
            if current_dim != VECTOR_DIMENSION:
                log.warning(f"벡터 차원이 다릅니다! (현재: {current_dim}, 필요: {VECTOR_DIMENSION}). 컬렉션을 재생성합니다.")
                qdrant_cli.delete_collection(collection_name=QDRANT_COLLECTION_NAME)
                raise Exception("컬렉션 차원이 달라 재생성 필요")
        except Exception:
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
        log.error(f"Qdrant 컬렉션 설정 중 심각한 에러 발생: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("애플리케이션 시작...")
    setup_database()
    yield
    log.info("애플리케이션 종료...")

app = FastAPI(
    title="42 Asia Hackathon - AI Document Engine (Phase 2)",
    description="문서의 의미를 이해하는 지능형 AI 엔진 API (키워드 + 시맨틱 검색 지원)",
    version="2.0.0",
    lifespan=lifespan
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

@app.get("/", tags=["Root"])
def read_root():
    return {"Hello": "42_Asia_Hackathon_v2_AI_Integrated_Phase2"}

@app.post("/uploadfile/", response_model=schemas.TaskTicket, tags=["Document Processing"])
async def create_upload_file(file: UploadFile = File(...)):
    log.info(f"단일 파일 업로드 요청 수신: {file.filename}")
    file_content = await file.read()
    task = process_document.delay(file.filename, file_content)
    log.info(f"Celery 작업 생성 완료. Task ID: {task.id}")
    return {"task_id": task.id}

@app.post("/uploadfiles/", response_model=schemas.TasksTicket, tags=["Document Processing"])
async def create_upload_files(files: List[UploadFile] = File(...)):
    log.info(f"{len(files)}개의 파일에 대한 다중 업로드 요청 수신")
    task_ids = []
    for file in files:
        file_content = await file.read()
        task = process_document.delay(file.filename, file_content)
        task_ids.append(task.id)
    log.info(f"{len(task_ids)}개의 Celery 작업 생성 완료.")
    return {"task_ids": task_ids}

@app.get("/tasks/{task_id}", response_model=schemas.TaskStatus, tags=["Document Processing"])
def get_task_status(task_id: str):
    log.info(f"작업 상태 조회 요청: {task_id}")
    task_result = celery_app.AsyncResult(task_id)
    task_status = task_result.status
    task_result_value = task_result.result if task_result.result else None
    if task_result.failed():
        task_status = "FAILED"
        task_result_value = str(task_result.traceback)
    return {"task_id": task_id, "status": task_status, "result": task_result_value}

@app.get("/search", response_model=schemas.SearchResult, tags=["Search"])
def search_documents(q: str, doc_type: Optional[str] = None):
    log.info(f"키워드 검색 요청: q='{q}', doc_type='{doc_type}'")
    try:
        index = meili_client.index("documents")
        search_options = {
            "limit": 10,
            "attributesToRetrieve": [
                "id", "filename", "content", "doc_type", "doc_confidence",
                "summary", "pii_count", "extracted_data"
            ]
        }
        if doc_type:
            search_options['filter'] = f'doc_type = "{doc_type}"'
        search_result = index.search(q, search_options)
        return search_result
    except Exception as e:
        log.error(f"문서 검색 중 에러 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/semantic_search", response_model=schemas.SemanticSearchResult, tags=["Search"])
async def semantic_search_documents(q: str):
    log.info(f"시맨틱 검색 요청: q='{q}'")
    start_time = time.time()
    try:
        query_vector = await llm_tasks.get_embedding(
            q,
            llm_client,
            settings.EMBEDDING_MODEL_NAME
        )
        if not query_vector:
            log.warning("검색어의 임베딩 벡터 생성 실패.")
            return {"hits": [], "query": q, "processingTimeMs": (time.time() - start_time) * 1000}
        semantic_hits = qdrant_cli.search(
            collection_name=QDRANT_COLLECTION_NAME,
            query_vector=query_vector,
            limit=5,
            with_payload=True
        )
        response_hits = []
        for hit in semantic_hits:
            payload = hit.payload or {}
            response_hits.append(
                schemas.SemanticSearchHit(
                    id=hit.id,
                    score=hit.score,
                    filename=payload.get('filename', 'N/A'),
                    doc_type=payload.get('doc_type', 'unknown'),
                    summary=payload.get('summary', '')
                )
            )
        processing_time_ms = (time.time() - start_time) * 1000
        log.info(f"시맨틱 검색 완료: {len(response_hits)}개 (처리 시간: {processing_time_ms:.2f}ms)")
        return {"hits": response_hits, "query": q, "processingTimeMs": processing_time_ms}
    except Exception as e:
        log.error(f"시맨틱 검색 중 에러 발생: {e}", exc_info=True)
        raise HTTPException(st
