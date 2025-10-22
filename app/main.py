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
    task = process_document.delay(file.filename)
    return {"task_id": task.id}

# 여러 파일 업로드를 위한 엔드포인트 (기억해두기로 했던 코드)
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
        index = meili_client.index("documents")
        # 'tokenization' 객체로 감싸서 전달합니다.
        index.update_settings({
            'tokenization': {
                'tokenizer': 'charabia'
            }
        })
        return {"status": "ok", "message": "MeiliSearch tokenizer updated for CJK support."}
    except Exception as e:
        return {"status": "error", "detail": str(e)}