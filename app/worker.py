import time
from celery import Celery
import meilisearch
import uuid
from presidio_analyzer import AnalyzerEngine

# Celery 애플리케이션 생성
celery_app = Celery(
    "tasks",
    broker="redis://redis-broker:6379/0",
    backend="redis://redis-broker:6379/0"
)

# MeiliSearch 클라이언트 생성
client = meilisearch.Client(url="http://meilisearch:7700")

# --- Presidio Analyzer 엔진 초기화 (가장 안정적인 방식) ---
# Presidio가 내부적으로 필요한 Spacy 모델을 스스로 불러오도록 합니다.
analyzer = AnalyzerEngine()
# ----------------------------------------------------

@celery_app.task
def process_document(filename: str):
    print(f"'{filename}' 문서에 대한 처리를 시작합니다...")
    sample_text = f"The user's name is John Doe, and his phone number is (555) 555-1234. You can email him at john.doe@email.com. This document is {filename}."
    try:
        print(f"'{filename}' 내용에서 PII를 탐지합니다...")
        pii_results = analyzer.analyze(text=sample_text, language='en')
        if pii_results:
            print("개인정보가 탐지되었습니다:")
            for result in pii_results:
                print(f"- Type: {result.entity_type}, Text: {sample_text[result.start:result.end]}")
        else:
            print("개인정보가 탐지되지 않았습니다.")
    except Exception as e:
        print(f"PII 탐지 중 에러 발생: {e}")

    # MeiliSearch 인덱싱
    try:
        print(f"'{filename}'의 메타데이터를 MeiliSearch에 인덱싱합니다...")
        index = client.index("documents")
        doc_id = str(uuid.uuid4())
        response = index.add_documents([
            {"id": doc_id, "filename": filename}
        ])
        # 구버전 라이브러리에 맞는 반환값 처리
        task_uid = response.get('uid') if isinstance(response, dict) else response
        print(f"MeiliSearch 인덱싱 작업이 제출되었습니다: {task_uid}")
    except Exception as e:
        print(f"MeiliSearch 인덱싱 중 에러 발생: {e}")

    result = f"'{filename}' 문서가 성공적으로 처리되었습니다."
    print(result)
    return result