import uuid
import meilisearch
from celery import Celery
import logging
import os

from .config import get_settings
# steps.py 대신 새로운 AI 모듈을 가져옵니다.
from .pipeline.ocr_module import OCRModule
from .pipeline.classification_module import DocumentClassifier
from .logger_config import setup_logging

setup_logging()
log = logging.getLogger(__name__)

settings = get_settings()
celery_app = Celery("tasks", broker=settings.REDIS_BROKER_URL, backend=settings.REDIS_BROKER_URL)
meili_client = meilisearch.Client(url=settings.MEILI_HOST_URL)

# --- Qdrant는 Phase 2에서 다시 사용할 것이므로 일단 비활성화 ---
# from qdrant_client import QdrantClient, models
# qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
# QDRANT_COLLECTION_NAME = "documents_collection"


# === 핵심: AI 모델을 워커 시작 시 1회만 로드 ===
log.info("AI 모델을 메모리에 로드합니다...")
try:
    ocr_model = OCRModule(lang='en')
    classifier_model = DocumentClassifier()

    # !! 중요: "models/classifier"는 해커톤 당일 학습 후 생성되는 경로입니다.
    # !! 지금은 테스트를 위해 기본 'distilbert-base-uncased' 모델을 로드합니다.
    # !! 이 모델은 5종 분류 학습이 안된 상태라 정확한 분류는 못하지만, 파이프라인 테스트는 가능합니다.
    MODEL_PATH = os.getenv("MODEL_PATH", "distilbert-base-uncased")
    classifier_model.load_model(MODEL_PATH)

    # (추후 extraction_module.py도 여기에 추가 로드)
    # extractor_model = DataExtractor()
    # extractor_model.load_model("models/extractor")

    log.info(f"AI 모델 ({MODEL_PATH}) 로드 완료.")
except Exception as e:
    log.error(f"AI 모델 로드 실패: {e}", exc_info=True)
    # 실제 환경에서는 워커가 비정상 종료되도록 하는 것이 좋습니다.
    raise e


@celery_app.task(
    bind=True,  # self 인자를 사용하기 위함
    autoretry_for=(Exception,),  # 모든 예외에 대해 자동 재시도
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=60
)
def process_document(self, filename: str, file_content: bytes):
    """[수정됨] AI 파이프라인을 비동기로 실행하는 Celery 작업."""
    log.info(f"'{filename}' AI 파이프라인 처리 시작... (시도: {self.request.retries + 1})")

    # ocr_module.py는 파일 경로를 인자로 받으므로, bytes를 임시 파일로 저장합니다.
    temp_dir = "/tmp/hackathon_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    # 파일 이름에 UUID를 추가하여 동시성 문제 방지
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{filename}")

    try:
        with open(temp_file_path, "wb") as f:
            f.write(file_content)

        # 1. OCR 단계 (PaddleOCR로 변경)
        log.info("--- (신규) PaddleOCR Step Start ---")
        ocr_result = ocr_model.extract_text(temp_file_path)
        extracted_text = ocr_result.get('text', '')

        if not extracted_text:
            log.warning(f"'{filename}' 텍스트 추출 실패. 파이프라인을 중단합니다.")
            return f"'{filename}'에서 텍스트를 추출할 수 없습니다."

        # 2. PII 탐지 단계 (Presidio - 일단 비활성화, 추후 보너스 기능으로 추가)
        # log.info("--- PII Detection Step Start (SKIPPED) ---")
        # pii_results = pii_analyzer.analyze(text=extracted_text, language='en')

        # 3. 문서 분류 단계 (신규 - DistilBERT)
        log.info("--- (신규) Classification Step Start ---")
        classification_result = classifier_model.classify(extracted_text)
        doc_type = classification_result.get('doc_type', 'unknown')
        doc_confidence = classification_result.get('confidence', 0.0)
        log.info(f"'{filename}' 분류 결과: {doc_type} (신뢰도: {doc_confidence:.2%})")

        # 4. 데이터 추출 단계 (신규 - BERT-NER, Phase 1.5에서 추가)
        extracted_data = {
            # "vendor": None, # (추후 extractor_model로 채움)
        }
        # if doc_type in ['invoice', 'receipt']:
        #    extracted_data = extractor_model.extract(extracted_text)

        doc_id = str(uuid.uuid4())

        # 5. MeiliSearch 인덱싱 (핵심: Qdrant -> MeiliSearch로 집중)
        log.info("--- MeiliSearch Indexing Step Start ---")

        document_payload = {
            "id": doc_id,
            "filename": filename,
            "content": extracted_text,
            "doc_type": doc_type,  # <-- AI가 분류한 타입
            "doc_confidence": doc_confidence,
            **extracted_data  # vendor, total_amount 등이 여기에 추가됨
        }

        meili_client.index("documents").add_documents([document_payload])
        log.info(f"'{filename}' MeiliSearch 인덱싱 완료. (doc_type: {doc_type})")

        # 6. Qdrant 인덱싱 (Phase 1에서는 실행 안 함)
        # log.info("--- Qdrant Indexing Step Start (SKIPPED) ---")

        result = f"'{filename}' 문서 처리(분류: {doc_type})가 성공적으로 완료되었습니다."
        log.info(result)
        return result

    except Exception as e:
        log.error(f"'{filename}' 처리 중 예외 발생 (시도: {self.request.retries + 1}): {e}", exc_info=True)
        raise
    finally:
        # 작업 성공/실패와 관계없이 임시 파일 삭제
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            log.info(f"임시 파일 삭제: {temp_file_path}")