from fastapi import FastAPI, File, UploadFile
from prometheus_fastapi_instrumentator import Instrumentator
from worker import process_document, celery_app
import meilisearch
import qdrant_client
from typing import List

app = FastAPI()

# 클라이언트 객체 생성
meili_client = meilisearch.Client(url="http://meilisearch:7700")
qdrant_client = qdrant_client.QdrantClient(host="qdrant", port=6333)

# Prometheus 미들웨어 연결
Instrumentator().instrument(app).expose(app)

@app.get("/")
def read_root():
    return {"Hello": "42_Asia_Hackathon"}


@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile):
    # file.read()를 통해 파일의 실제 내용을 바이트(bytes) 형태로 읽어옵니다.
    file_content = await file.read()

    # 파일 내용과 함께 파일 이름도 전달합니다.
    task = process_document.delay(file.filename, file_content)
    return {"task_id": task.id}
@app.post("/uploadfiles/")
async def create_upload_files(files: List[UploadFile] = File(...)):
    task_ids = []
    for file in files:
        task = process_document.delay(file.filename)
        task_ids.append(task.id)
    return {"task_ids": task_ids}

@app.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    task_result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result
    }

@app.get("/search")
def search_documents(q: str):
    try:
        index = meili_client.index("documents")
        search_result = index.search(q)
        return search_result
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/meili-health")
def get_meili_health():
    # 구버전 라이브러리에 맞는 건강 상태 확인 방식
    return meili_client.health()

@app.get("/qdrant-health")
def get_qdrant_health():
    try:
        collections = qdrant_client.get_collections()
        return {"status": "ok", "collections": collections}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# MeiliSearch 한글 설정을 위한 임시 엔드포인트
@app.post("/setup-meilisearch", tags=["Setup"])
def setup_meilisearch_tokenizer():
    try:
        # 구버전 라이브러리에 맞는 설정 업데이트 방식
        meili_client.index("documents").update_ranking_rules([
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness"
        ])
        return {"status": "ok", "message": "MeiliSearch settings updated."}
    except Exception as e:
        return {"status": "error", "detail": str(e)}