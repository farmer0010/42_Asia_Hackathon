import uuid
import meilisearch
from celery import Celery
import logging

from .config import get_settings
from .pipeline import steps
from .logger_config import setup_logging

# 로깅 시스템 초기화
setup_logging()
log = logging.getLogger(__name__)

settings = get_settings()
celery_app = Celery("tasks", broker=settings.REDIS_BROKER_URL, backend=settings.REDIS_BROKER_URL)
meili_client = meilisearch.Client(url=settings.MEILI_HOST_URL)

@celery_app.task
def process_document(filename: str, file_content: bytes):
    log.info(f"'{filename}' 문서에 대한 처리를 시작합니다...")

    # 1. OCR 단계 실행
    extracted_text = steps.ocr_step(file_content)

    # 2. PII 탐지 단계 실행
    if extracted_text:
        steps.pii_detection_step(extracted_text)
    else:
        log.warning(f"'{filename}'에서 텍스트를 추출하지 못해 PII 탐지를 건너뜁니다.")

    # 3. MeiliSearch 인덱싱 단계
    try:
        log.info("--- MeiliSearch Indexing Step Start ---")
        index = meili_client.index("documents")
        doc_id = str(uuid.uuid4())
        index.add_documents([
            {"id": doc_id, "filename": filename, "content": extracted_text}
        ])
        log.info(f"'{filename}' MeiliSearch 인덱싱 작업이 성공적으로 제출되었습니다.")
    except Exception as e:
        log.error(f"'{filename}' MeiliSearch 인덱싱 중 에러 발생: {e}")

    result = f"'{filename}' 문서 처리가 완료되었습니다."
    log.info(result)
    return result