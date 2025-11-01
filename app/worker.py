import os
import time
import logging
from celery import Celery
from celery.signals import worker_process_init
from kombu.utils.encoding import bytes_to_str
from kombu.serialization import register
from app.config import get_settings
from app.pipeline.ocr_module import OCRModule
from app.pipeline.classification_module import DocumentClassifier
from app.pipeline.llm_tasks import (
    classify_document_type,
    extract_invoice_data,
    extract_receipt_data,
    summarize_document,
    detect_pii
)
from app.pipeline.client import LLMClient
from app.schemas import DocumentData, DocumentResult

log = logging.getLogger(__name__)
settings = get_settings()

# --- [수정] MODEL_PATH 기본값을 학습된 모델 경로로 변경 ---
MODEL_PATH = os.getenv("MODEL_PATH", "/models/classifier")

# 전역 변수로 모델 인스턴스 저장 (워커 초기화 시 로드)
ocr_model_instance = None
classifier_model_instance = None


@worker_process_init.connect
def init_worker(**kwargs):
    global ocr_model_instance, classifier_model_instance
    log.info("--- 🚀 Celery 워커 초기화: AI 모델 로드 시작 ---")

    # 1. OCR 모듈 로드
    ocr_model_instance = OCRModule()

    # 2. 분류 모듈 로드
    classifier_model_instance = DocumentClassifier()
    try:
        # --- [수정] 핫픽스 제거: 모델 로드 주석 해제 ---
        classifier_model_instance.load_model(MODEL_PATH)
        log.info(f"✅ 분류 모델 로드 성공: {MODEL_PATH}")
    except Exception as e:
        log.error(f"🚨 분류 모델 로드 실패: {e}", exc_info=True)
        # 모델 로드 실패 시에도 워커는 계속 실행되도록 함 (대신 분류 기능은 비활성화)
        classifier_model_instance = None

    log.info("--- ✅ AI 모델 로드 완료 ---")


# Celery 앱 설정
celery_app = Celery(
    "worker",
    broker=settings.REDIS_BROKER_URL,
    backend=settings.REDIS_BROKER_URL
)
celery_app.conf.task_track_started = True


@celery_app.task(name="process_document_task")
def process_document_task(doc_data: dict) -> dict:
    global ocr_model_instance, classifier_model_instance

    start_time = time.time()
    doc = DocumentData(**doc_data)
    log.info(f"--- 📄 작업 시작 (ID: {doc.id}) ---")

    try:
        # --- 1. OCR Step ---
        if not ocr_model_instance:
            raise Exception("OCR 모델이 로드되지 않았습니다.")

        extracted_text = ocr_model_instance.extract_text(doc.content_b64)
        if not extracted_text:
            log.warning(f"OCR 결과 없음 (ID: {doc.id})")
            extracted_text = ""  # 텍스트가 없어도 다음 단계 진행

        # --- 2. Classification Step ---
        doc_type = "unknown"
        if not classifier_model_instance:
            log.error(f"🚨 분류 모델이 로드되지 않아 'unknown'으로 처리 (ID: {doc.id})")
            classification_result = {"doc_type": "unknown", "confidence": 0.0}
        else:
            # --- [수정] 핫픽스 제거: 실제 분류기 호출 ---
            classification_result = classifier_model_instance.classify(extracted_text)
            doc_type = classification_result.get("doc_type", "unknown")
            log.info(f"분류 결과: {doc_type} (신뢰도: {classification_result.get('confidence', 0):.2%})")

        # --- 3. LLM Tasks (정보 추출, 요약, PII) ---
        llm_client = LLMClient(model=settings.LLM_MODEL_NAME, base=settings.LLM_BASE_URL)

        extracted_data = {}
        if doc_type == "invoice":
            log.info("LLM 호출: Invoice 정보 추출")
            extracted_data = extract_invoice_data(extracted_text, llm_client)
        elif doc_type == "receipt":
            log.info("LLM 호출: Receipt 정보 추출")
            extracted_data = extract_receipt_data(extracted_text, llm_client)

        log.info("LLM 호출: 요약")
        summary = summarize_document(extracted_text, llm_client)

        log.info("LLM 호출: PII 탐지")
        pii_results = detect_pii(extracted_text, llm_client)

        end_time = time.time()
        result = DocumentResult(
            id=doc.id,
            filename=doc.filename,
            status="SUCCESS",
            full_text_ocr=extracted_text,
            classification=classification_result,
            extracted_data=extracted_data,
            summary=summary,
            pii_detected=pii_results,
            processing_time=end_time - start_time
        )

        log.info(f"--- ✅ 작업 성공 (ID: {doc.id}, 소요 시간: {end_time - start_time:.2f}s) ---")
        return result.model_dump()

    except Exception as e:
        end_time = time.time()
        log.error(f"--- 🚨 작업 실패 (ID: {doc.id}): {e} ---", exc_info=True)
        result = DocumentResult(
            id=doc.id,
            filename=doc.filename,
            status="FAILURE",
            error_message=str(e),
            processing_time=end_time - start_time
        )
        return result.model_dump()