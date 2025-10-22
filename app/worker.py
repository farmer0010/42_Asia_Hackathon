import time
from celery import Celery
import meilisearch
import uuid

# Celery 애플리케이션을 생성합니다.
celery_app = Celery(
    "tasks",
    broker="redis://redis-broker:6379/0",
    backend="redis://redis-broker:6379/0"
)

# MeiliSearch 클라이언트 생성
client = meilisearch.Client(url="http://meilisearch:7700")


@celery_app.task
def process_document(filename: str):
    print(f"'{filename}' 문서에 대한 처리를 시작합니다...")
    time.sleep(10)

    try:
        print(f"'{filename}'의 메타데이터를 MeiliSearch에 인덱싱합니다...")
        index = client.index("documents")

        # --- 안전한 고유 ID 생성 로직 추가 ---
        doc_id = str(uuid.uuid4())

        response = index.add_documents([
            # "id" 필드에 파일 이름 대신 생성된 고유 ID를 사용합니다.
            {"id": doc_id, "filename": filename}
        ])
        # ------------------------------------

        print(f"MeiliSearch 인덱싱 작업이 제출되었습니다: {response}")
    except Exception as e:
        print(f"MeiliSearch 인덱싱 중 에러 발생: {e}")

    result = f"'{filename}' 문서가 성공적으로 처리되었습니다."
    print(result)
    return result