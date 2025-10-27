from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, UploadFile, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
import meilisearch
# import qdrant_client # (Phase 1에서는 비활성화)
# from qdrant_client import models # (Phase 1에서는 비활성화)
from typing import List, Optional  # Optional 임포트 확인
import logging

from .worker import process_document, celery_app
from .config import get_settings
from . import schemas
from .logger_config import setup_logging

# from .pipeline import steps # (더 이상 사용 안 함)

setup_logging()
log = logging.getLogger(__name__)

settings = get_settings()

meili_client = meilisearch.Client(url=settings.MEILI_HOST_URL)


# qdrant_cli = qdrant_client.QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT) # (비활성화)

# QDRANT_COLLECTION_NAME = "documents_collection" # (비활성화)
# VECTOR_SIZE = 1024 # (비활성화)

def setup_database():
    """MeiliSearch 설정 및 Qdrant 컬렉션 생성을 처리합니다."""
    try:
        log.info("MeiliSearch 설정을 시작합니다...")
        index = meili_client.index("documents")

        # 'doc_type'을 필터링 및 패싯 검색이 가능하도록 설정 (중요!)
        index.update_filterable_attributes([
            'doc_type',
            'vendor',  # (추후 추출 필드들 추가)
        ])

        index.update_ranking_rules([
            "words", "typo", "proximity", "attribute", "sort", "exactness"
        ])
        log.info("MeiliSearch 설정 업데이트 완료.")
    except Exception as e:
        log.error(f"MeiliSearch 설정 중 에러 발생: {e}")

    # (Qdrant 컬렉션 생성 로직은 비활성화)
    # try:
    #     log.info(f"Qdrant 컬렉션 '{QDRANT_COLLECTION_NAME}' 확인 및 생성을 시작합니다...")
    # ...
    # except Exception as e:
    #     log.info(f"Qdrant 컬렉션 생성 실패 (이미 존재할 수 있음): {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 시 DB 설정 등을 수행합니다."""
    log.info("애플리케이션 시작...")
    setup_database()
    yield
    log.info("애플리케이션 종료...")


app = FastAPI(
    title="42 Asia Hackathon - AI Document Engine",
    description="문서의 의미를 이해하는 지능형 AI 엔진 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 설정
origins = [
    "*",  # 개발 중에는 모든 출처를 허용합니다.
]

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
    return {"Hello": "42_Asia_Hackathon_v2_AI_Integrated"}  # 버전 메시지 변경


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
    task_result_value = str(task_result.result) if task_result.result else None

    if task_result.failed():
        task_status = "FAILED"
        task_result_value = str(task_result.traceback)

    return {
        "task_id": task_id,
        "status": task_status,
        "result": task_result_value
    }


@app.get("/search", response_model=schemas.SearchResult, tags=["Search"])
def search_documents(q: str, doc_type: Optional[str] = None):
    """
    [수정됨] 키워드로 문서를 검색합니다.
    doc_type으로 필터링할 수 있습니다. (예: 'invoice', 'receipt')
    """
    log.info(f"필터 검색 요청: q='{q}', doc_type='{doc_type}'")
    try:
        index = meili_client.index("documents")

        search_options = {
            "limit": 10
        }

        if doc_type:
            # 이것이 바로 '필터 검색'입니다.
            search_options['filter'] = f'doc_type = "{doc_type}"'

        search_result = index.search(q, search_options)
        return search_result
    except Exception as e:
        log.error(f"문서 검색 중 에러 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- /hybrid_search 엔드포인트는 Phase 2에서 재작업할 것이므로 일단 주석 처리 ---
# @app.get("/hybrid_search", tags=["Search"])
# def hybrid_search_documents(q: str):
#     """키워드 검색과 의미 기반 벡터 검색을 모두 수행합니다."""
#     log.info(f"하이브리드 검색 요청: q='{q}'")
#     try:
#         query_vector = steps.mock_embedding_step(q) # (이 함수는 이제 없음)
#         semantic_hits = []
#         if query_vector:
#             semantic_hits = qdrant_cli.search(
#                 collection_name=QDRANT_COLLECTION_NAME,
#                 query_vector=query_vector,
#                 limit=5
#             )
#         keyword_hits = meili_client.index("documents").search(q, {"limit": 5})
#         return {
#             "semantic_search_results": semantic_hits,
#             "keyword_search_results": keyword_hits
#         }
#     except Exception as e:
#         log.error(f"하이브리드 검색 중 에러 발생: {e}")
#         raise HTTPException(status_code=500, detail=str(e))