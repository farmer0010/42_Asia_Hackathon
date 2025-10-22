from fastapi import FastAPI, File, UploadFile, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
import meilisearch
import qdrant_client
from typing import List
import logging

# 내부 모듈 import
from .worker import process_document, celery_app
from .config import get_settings
from . import schemas
from .logger_config import setup_logging

# 로깅 시스템 초기화
setup_logging()
log = logging.getLogger(__name__)

# 설정 객체 로드
settings = get_settings()

# 클라이언트 객체 생성
meili_client = meilisearch.Client(url=settings.MEILI_HOST_URL)
qdrant_client = qdrant_client.QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


def setup_meilisearch(client: meilisearch.Client):
    """MeiliSearch의 인덱스 설정을 초기화합니다."""
    try:
        log.info("MeiliSearch 설정을 시작합니다...")
        client.index("documents").update_ranking_rules([
            "words", "typo", "proximity", "attribute", "sort", "exactness"
        ])
        log.info("MeiliSearch 설정이 성공적으로 업데이트되었습니다.")
    except Exception as e:
        log.error(f"MeiliSearch 설정 중 에러 발생: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션의 시작과 종료 시 수행될 작업을 관리합니다."""
    log.info("애플리케이션 시작...")
    setup_meilisearch(meili_client)
    yield
    log.info("애플리케이션 종료...")


app = FastAPI(
    title="42 Asia Hackathon - AI Document Engine",
    description="문서의 의미를 이해하는 지능형 AI 엔진 API",
    version="1.0.0",
    lifespan=lifespan
)

Instrumentator().instrument(app).expose(app)


@app.get("/", tags=["Root"])
def read_root():
    return {"Hello": "42_Asia_Hackathon_v2"}


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
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": str(task_result.result) if task_result.result else None
    }


@app.get("/search", response_model=schemas.SearchResult, tags=["Search"])
def search_documents(q: str):
    log.info(f"문서 검색 요청: q='{q}'")
    try:
        index = meili_client.index("documents")
        search_result = index.search(q)
        return search_result
    except Exception as e:
        log.error(f"문서 검색 중 에러 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))