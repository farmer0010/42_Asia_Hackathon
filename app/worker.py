import uuid
import meilisearch
from celery import Celery
import logging
import os
import json
import asyncio

from .config import get_settings
from .pipeline.ocr_module import OCRModule
from .pipeline.classification_module import DocumentClassifier
from .logger_config import setup_logging
from .pipeline.client import LLMClient
from .pipeline import llm_tasks, guards

setup_logging()
log = logging.getLogger(__name__)

settings = get_settings()
celery_app = Celery("tasks", broker=settings.REDIS_BROKER_URL, backend=settings.REDIS_BROKER_URL)
meili_client = meilisearch.Client(url=settings.MEILI_HOST_URL)

log.info("AI 모델(OCR/Classifier)을 메모리에 로드합니다...")
try:
    ocr_model = OCRModule(lang='en')
    classifier_model = DocumentClassifier()
    MODEL_PATH = os.getenv("MODEL_PATH", "distilbert-base-uncased")
    classifier_model.load_model(MODEL_PATH)
    log.info(f"AI 모델 ({MODEL_PATH}) 로드 완료.")
    log.info("LLM 클라이언트 및 스키마를 로드합니다...")
    llm_client = LLMClient(model=settings.LLM_MODEL_NAME, base=settings.OLLAMA_BASE_URL)
    invoice_schema = json.loads(llm_tasks.read("app/pipeline/schemas/invoice_v1.json"))
    receipt_schema = json.loads(llm_tasks.read("app/pipeline/schemas/receipt_v1.json"))
    log.info("LLM 클라이언트 및 스키마 로드 완료.")
except Exception as e:
    log.error(f"AI 모델 로드 실패: {e}", exc_info=True)
    raise e


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=60
)
async def process_document(self, filename: str, file_content: bytes):
    log.info(f"'{filename}' AI 파이프라인 처리 시작... (시도: {self.request.retries + 1})")
    temp_dir = "/tmp/hackathon_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{filename}")

    try:
        with open(temp_file_path, "wb") as f:
            f.write(file_content)

        log.info("--- 1. PaddleOCR Step Start ---")
        ocr_result = ocr_model.extract_text(temp_file_path)
        extracted_text = ocr_result.get('text', '')

        if not extracted_text:
            log.warning(f"'{filename}' 텍스트 추출 실패.")
            return {
                "filename": filename,
                "error": "Failed to extract text (OCR)",
                "classification": {}, "extracted_data": {}, "summary": "", "pii_detected": []
            }

        log.info("--- 2. Classification Step Start (DistilBert) ---")
        classification_result = classifier_model.classify(extracted_text)
        doc_type = classification_result.get('doc_type', 'unknown')
        doc_confidence = classification_result.get('confidence', 0.0)
        log.info(f"'{filename}' 분류 결과: {doc_type} (신뢰도: {doc_confidence:.2%})")

        log.info(f"--- 3a. LLM Extraction Step Start (Type: {doc_type}) ---")
        extracted_data = {}
        if doc_type == "invoice":
            extracted_data = await llm_tasks.extract_invoice(extracted_text, llm_client, invoice_schema) or {}
        elif doc_type == "receipt":
            extracted_data = await llm_tasks.extract_receipt(extracted_text, llm_client, receipt_schema) or {}
        log.info(f"LLM 추출 완료: {extracted_data}")

        log.info("--- 3b. LLM Summarization Step Start ---")
        summary = await llm_tasks.summarize(extracted_text, llm_client)
        log.info(f"LLM 요약 완료: {summary[:50]}...")

        log.info("--- 3c. LLM PII Detection Step Start ---")
        pii_results = await llm_tasks.detect_pii(extracted_text, llm_client)
        log.info(f"LLM PII 탐지 완료: {len(pii_results)}개")

        doc_id = str(uuid.uuid4())
        log.info("--- 4. MeiliSearch Indexing Step Start ---")
        document_payload = {
            "id": doc_id,
            "filename": filename,
            "content": extracted_text,
            "doc_type": doc_type,
            "doc_confidence": doc_confidence,
            "extracted_data": extracted_data,
            "summary": summary,
            "pii_count": len(pii_results),
        }
        meili_client.index("documents").add_documents([document_payload])
        log.info(f"'{filename}' MeiliSearch 인덱싱 완료. (doc_type: {doc_type})")

        result_summary = f"'{filename}' 처리 완료 (유형: {doc_type}, 추출 항목: {len(extracted_data)}개, PII: {len(pii_results)}개)"
        log.info(result_summary)
        return {
            "filename": filename,
            "classification": classification_result,
            "extracted_data": extracted_data,
            "summary": summary,
            "pii_detected": pii_results
        }

    except Exception as e:
        log.error(f"'{filename}' 처리 중 예외 발생 (시도: {self.request.retries + 1}): {e}", exc_info=True)
        raise
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            log.info(f"임시 파일 삭제: {temp_file_path}")
