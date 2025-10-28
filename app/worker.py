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
from qdrant_client import QdrantClient, models

setup_logging()
log = logging.getLogger(__name__)

settings = get_settings()
celery_app = Celery("tasks", broker=settings.REDIS_BROKER_URL, backend=settings.REDIS_BROKER_URL)
meili_client = meilisearch.Client(url=settings.MEILI_HOST_URL)
qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
QDRANT_COLLECTION_NAME = "documents_collection"

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
    doc_id = str(uuid.uuid4())
    log.info(f"'{filename}' (ID: {doc_id}) AI 파이프라인(Phase 2) 처리 시작... (시도: {self.request.retries + 1})")

    temp_dir = "/tmp/hackathon_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"{doc_id}_{filename}")

    try:
        with open(temp_file_path, "wb") as f:
            f.write(file_content)

        log.info(f"--- 1. PaddleOCR Step Start (ID: {doc_id}) ---")
        ocr_result = ocr_model.extract_text(temp_file_path)
        extracted_text = ocr_result.get('text', '')

        if not extracted_text:
            log.warning(f"'{filename}' (ID: {doc_id}) 텍스트 추출 실패.")
            return {
                "id": doc_id, "filename": filename, "error": "Failed to extract text (OCR)",
                "classification": {}, "extracted_data": {}, "summary": "", "pii_detected": [],
                "vector_indexed": False
            }

        log.info(f"--- 2. Classification Step Start (ID: {doc_id}) ---")
        classification_result = classifier_model.classify(extracted_text)
        doc_type = classification_result.get('doc_type', 'unknown')
        doc_confidence = classification_result.get('confidence', 0.0)
        log.info(f"'{filename}' (ID: {doc_id}) 분류 결과: {doc_type} (신뢰도: {doc_confidence:.2%})")

        log.info(f"--- 3a. LLM Extraction Step Start (ID: {doc_id}, Type: {doc_type}) ---")
        extracted_data = {}
        if doc_type == "invoice":
            extracted_data = await llm_tasks.extract_invoice(extracted_text, llm_client, invoice_schema) or {}
        elif doc_type == "receipt":
            extracted_data = await llm_tasks.extract_receipt(extracted_text, llm_client, receipt_schema) or {}
        log.info(f"LLM (ID: {doc_id}) 추출 완료: {extracted_data}")

        log.info(f"--- 3b. LLM Summarization Step Start (ID: {doc_id}) ---")
        summary = await llm_tasks.summarize(extracted_text, llm_client)
        log.info(f"LLM (ID: {doc_id}) 요약 완료: {summary[:50]}...")

        log.info(f"--- 3c. LLM PII Detection Step Start (ID: {doc_id}) ---")
        pii_results = await llm_tasks.detect_pii(extracted_text, llm_client)
        log.info(f"LLM (ID: {doc_id}) PII 탐지 완료: {len(pii_results)}개")

        log.info(f"--- 4. MeiliSearch Indexing Step Start (ID: {doc_id}) ---")
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
        log.info(f"'{filename}' (ID: {doc_id}) MeiliSearch 인덱싱 완료.")

        log.info(f"--- 5. Qdrant Indexing Step Start (ID: {doc_id}) ---")
        vector_indexed = False

        vector = await llm_tasks.get_embedding(
            extracted_text,
            llm_client,
            settings.EMBEDDING_MODEL_NAME
        )

        if not vector:
            log.warning(f"'{filename}' (ID: {doc_id})의 임베딩 벡터 생성 실패. Qdrant 인덱싱을 건너뜁니다.")
        else:
            qdrant_payload = {
                "filename": filename,
                "doc_type": doc_type,
                "summary": summary,
                "meili_id": doc_id
            }

            qdrant_client.upsert(
                collection_name=QDRANT_COLLECTION_NAME,
                points=[
                    models.PointStruct(
                        id=doc_id,
                        vector=vector,
                        payload=qdrant_payload
                    )
                ]
            )
            vector_indexed = True
            log.info(f"'{filename}' (ID: {doc_id}) Qdrant 인덱싱 완료.")

        result_summary = f"'{filename}' (Phase 2) 처리 완료 (ID: {doc_id}, Type: {doc_type}, Vector: {vector_indexed})"
        log.info(result_summary)

        return {
            "id": doc_id,
            "filename": filename,
            "classification": classification_result,
            "extracted_data": extracted_data,
            "summary": summary,
            "pii_detected": pii_results,
            "vector_indexed": vector_indexed
        }

    except Exception as e:
        log.error(f"'{filename}' (ID: {doc_id}) 처리 중 예외 발생 (시도: {self.request.retries + 1}): {e}", exc_info=True)
        raise
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            log.info(f"임시 파일 삭제: {temp_file_path}")
