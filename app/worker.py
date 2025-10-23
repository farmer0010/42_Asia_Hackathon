import uuid
import meilisearch
from celery import Celery
import logging
from qdrant_client import QdrantClient, models

from .config import get_settings
from .pipeline import steps
from .logger_config import setup_logging

setup_logging()
log = logging.getLogger(__name__)

settings = get_settings()
celery_app = Celery("tasks", broker=settings.REDIS_BROKER_URL, backend=settings.REDIS_BROKER_URL)
meili_client = meilisearch.Client(url=settings.MEILI_HOST_URL)
qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)

QDRANT_COLLECTION_NAME = "documents_collection"


@celery_app.task(
    bind=True,  # self 인자를 사용하기 위함
    autoretry_for=(Exception,),  # 모든 예외에 대해 자동 재시도
    retry_kwargs={'max_retries': 3},  # 최대 3번 재시도
    retry_backoff=True,  # 재시도 간격이 점차 증가
    retry_backoff_max=60  # 최대 재시도 간격 60초
)
def process_document(self, filename: str, file_content: bytes):
    """문서 처리 전체 파이프라인을 비동기로 실행하는 Celery 작업."""
    log.info(f"'{filename}' 문서 처리 시작... (시도: {self.request.retries + 1})")

    try:
        # 1. OCR 단계
        extracted_text = steps.ocr_step(file_content)

        # 2. PII 탐지 단계
        if extracted_text:
            steps.pii_detection_step(extracted_text)
        else:
            log.warning(f"'{filename}' 텍스트 추출 실패. PII 탐지를 건너뜁니다.")

        # 문서 고유 ID를 생성하여 MeiliSearch와 Qdrant에서 동일하게 사용
        doc_id = str(uuid.uuid4())

        # 3. MeiliSearch 인덱싱 (키워드 검색용)
        log.info("--- MeiliSearch Indexing Step Start ---")
        meili_client.index("documents").add_documents([
            {"id": doc_id, "filename": filename, "content": extracted_text}
        ])
        log.info(f"'{filename}' MeiliSearch 인덱싱 완료.")

        # 4. 임베딩 생성 단계 (현재는 Mock 함수 사용)
        embedding_vector = steps.mock_embedding_step(extracted_text)

        # 5. Qdrant 인덱싱 (의미 기반 검색용)
        if embedding_vector:
            log.info("--- Qdrant Indexing Step Start ---")
            qdrant_client.upsert(
                collection_name=QDRANT_COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=doc_id,
                        vector=embedding_vector,
                        payload={"filename": filename, "content_preview": extracted_text[:200]}
                    )
                ],
                wait=True  # 개발 및 데모 환경에서는 즉시 적용
            )
            log.info(f"'{filename}' Qdrant 인덱싱 완료.")
        else:
            log.warning(f"'{filename}' 임베딩 벡터가 없어 Qdrant 인덱싱을 건너뜁니다.")

        result = f"'{filename}' 문서 처리가 성공적으로 완료되었습니다."
        log.info(result)
        return result

    except Exception as e:
        log.error(f"'{filename}' 처리 중 예외 발생 (시도: {self.request.retries + 1}): {e}")
        # autoretry_for 옵션에 의해 이 예외가 발생하면 Celery가 자동으로 재시도
        raise