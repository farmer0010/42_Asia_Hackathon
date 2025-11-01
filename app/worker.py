import os
import json
import time
from celery import Celery
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import requests
import torch  # ◀◀◀ [추가] GPU 사용 여부 확인용

from .config import settings
from .logger_config import setup_logging
from .pipeline.classification_module import DocumentClassifier  # ◀◀◀ 이제 '진짜' 모듈
from .pipeline.ocr_module import OCRModule  # ◀◀◀ 이제 '최신 PaddleOCR' 모듈
from .pipeline.llm_tasks import (
    get_llm_extraction_task,
    perform_pii_masking,
    perform_summarization
)
from .pipeline.client import SearchClient, VectorClient

# 로거 설정
log = setup_logging()

# --- Celery 설정 ---
celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)
celery_app.conf.task_track_started = True
celery_app.conf.task_serializer = 'json'
celery_app.conf.result_serializer = 'json'
celery_app.conf.accept_content = ['json']

# --- AI 모델 및 클라이언트 로드 ---
MODEL_PATH = os.getenv("MODEL_PATH", "/usr/src/models/classifier")
log.info(f"Attempting to load DocumentClassifier model from: {MODEL_PATH}")

# [수정] 모델 로드를 생성자에서 호출
classifier_model = DocumentClassifier(model_path=MODEL_PATH)

# [수정] PaddleOCR 모듈 인스턴스화
try:
    USE_GPU = torch.cuda.is_available()
    ocr_module = OCRModule(lang='en', use_gpu=USE_GPU)
except Exception as e:
    log.error(f"Failed to load OCRModule: {e}. OCR tasks will fail.", exc_info=True)
    ocr_module = None

# 데이터베이스 클라이언트
search_client = SearchClient()
vector_client = VectorClient()


# --- 문서 처리 컨텍스트 ---
class DocumentContext(BaseModel):
    job_id: str
    file_path: str
    file_name: str
    file_mime_type: str

    extracted_text: Optional[str] = None
    classification_result: Dict[str, Any] = Field(default_factory=dict)
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    summary: Optional[str] = None
    pii_results: Dict[str, Any] = Field(default_factory=dict)

    start_time: float = Field(default_factory=time.time)
    ocr_time: float = 0.0
    classification_time: float = 0.0
    extraction_time: float = 0.0
    total_time: float = 0.0


# --- 파이프라인 단계 (함수) ---

def perform_ocr(context: DocumentContext):
    """1. OCR 수행 (이제 '최신 PaddleOCR' 모듈 사용)"""
    log.info(f"[{context.job_id}] (1/6) Starting OCR...")
    t_start = time.time()

    if ocr_module is None:
        log.error(f"[{context.job_id}] OCRModule is not loaded. Skipping OCR.")
        context.extracted_text = ""
        return

    try:
        # [수정] '최신 PaddleOCR' 모듈의 perform_ocr 함수 실행
        context.extracted_text = ocr_module.perform_ocr(context.file_path)

        context.ocr_time = time.time() - t_start
        log.info(f"[{context.job_id}] (1/6) OCR finished ({context.ocr_time:.2f}s). "
                 f"Extracted {len(context.extracted_text)} chars.")
    except Exception as e:
        log.error(f"[{context.job_id}] OCR task failed: {e}", exc_info=True)
        context.extracted_text = ""


def perform_classification(context: DocumentContext):
    """2. 문서 분류 (이제 '진짜' 모듈 + '데모 모드' 사용)"""
    log.info(f"[{context.job_id}] (2/6) Starting Classification...")
    t_start = time.time()

    if not context.extracted_text:
        log.warning(f"[{context.job_id}] No text extracted from OCR. Skipping classification.")
        context.classification_result = {"doc_type": "ocr_failed", "confidence": 0.0}
        return

    try:
        # ◀◀◀ [수정] 'classify' 함수에 file_name 인자 전달 ◀◀◀
        classification_result = classifier_model.classify(
            text=context.extracted_text,
            file_name=context.file_name
        )
        # ◀◀◀ [수정 완료] ◀◀◀

        context.classification_result = classification_result
        context.classification_time = time.time() - t_start
        log.info(f"[{context.job_id}] (2/6) Classification finished ({context.classification_time:.2f}s). "
                 f"Result: {classification_result}")
    except Exception as e:
        log.error(f"[{context.job_id}] Classification task failed: {e}", exc_info=True)
        context.classification_result = {"doc_type": "classification_failed", "confidence": 0.0}


def perform_llm_extraction(context: DocumentContext):
    """3. LLM 기반 정보 추출 (분류 결과에 따라)"""
    doc_type = context.classification_result.get("doc_type", "unknown")
    extraction_task = get_llm_extraction_task(doc_type)

    if not extraction_task:
        log.info(f"[{context.job_id}] (3/6) No extraction task defined for doc_type '{doc_type}'. Skipping.")
        return

    log.info(f"[{context.job_id}] (3/6) Starting LLM Extraction for '{doc_type}'...")
    t_start = time.time()

    try:
        context.structured_data = extraction_task(context.extracted_text)
        context.extraction_time = time.time() - t_start
        log.info(f"[{context.job_id}] (3/6) LLM Extraction finished ({context.extraction_time:.2f}s).")
    except Exception as e:
        log.error(f"[{context.job_id}] LLM Extraction task failed: {e}", exc_info=True)
        context.structured_data = {"error": str(e)}


# ... (perform_pii_and_summary, perform_indexing, cleanup_file 함수는 변경 없음) ...
def perform_pii_and_summary(context: DocumentContext):
    """4. (병렬) PII 탐지 및 요약"""
    log.info(f"[{context.job_id}] (4/6) Starting PII Masking...")
    try:
        context.pii_results = perform_pii_masking(context.extracted_text)
        log.info(f"[{context.job_id}] (4/6) PII Masking finished.")
    except Exception as e:
        log.error(f"[{context.job_id}] PII Masking task failed: {e}", exc_info=True)

    log.info(f"[{context.job_id}] (5/6) Starting Summarization...")
    try:
        context.summary = perform_summarization(context.extracted_text)
        log.info(f"[{context.job_id}] (5/6) Summarization finished.")
    except Exception as e:
        log.error(f"[{context.job_id}] Summarization task failed: {e}", exc_info=True)


def perform_indexing(context: DocumentContext):
    """6. 검색 엔진에 인덱싱"""
    log.info(f"[{context.job_id}] (6/6) Starting Indexing...")

    try:
        # 1. MeiliSearch (Full-Text Search)
        meili_doc = {
            "id": context.job_id,
            "file_name": context.file_name,
            "doc_type": context.classification_result.get("doc_type", "unknown"),
            "content": context.extracted_text,
            "summary": context.summary,
            "created_at": int(context.start_time),
            **context.structured_data
        }
        search_client.index_document(meili_doc)
        log.info(f"[{context.job_id}] (6/6) MeiliSearch indexing finished.")

        # 2. Qdrant (Vector Search)
        vector_client.index_document(
            doc_id=context.job_id,
            text_content=context.extracted_text,
            metadata=meili_doc
        )
        log.info(f"[{context.job_id}] (6/6) Qdrant indexing finished.")

    except Exception as e:
        log.error(f"[{context.job_id}] Indexing task failed: {e}", exc_info=True)


def cleanup_file(file_path: str):
    """파이프라인 완료 후 임시 파일 삭제"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            log.info(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        log.error(f"Failed to cleanup file {file_path}: {e}")


# --- 메인 Celery 작업 ---

@celery_app.task(name="process_document_pipeline")
def process_document_pipeline(
        job_id: str,
        file_path: str,
        file_name: str,
        file_mime_type: str
):
    """
    파일 업로드 후 실행되는 메인 문서 처리 파이프라인
    (OCR -> 분류 -> 추출 -> PII/요약 -> 인덱싱)
    """
    log.info(f"[{job_id}] Celery task started for file: {file_name}")

    context = DocumentContext(
        job_id=job_id,
        file_path=file_path,
        file_name=file_name,
        file_mime_type=file_mime_type
    )

    try:
        # --- 파이프라인 실행 ---
        perform_ocr(context)
        perform_classification(context)
        perform_llm_extraction(context)
        perform_pii_and_summary(context)
        perform_indexing(context)
        # --- 파이프라인 종료 ---

        context.total_time = time.time() - context.start_time
        log.info(f"[{job_id}] Pipeline COMPLETED ({context.total_time:.2f}s).")

        # 임시 파일 삭제
        cleanup_file(file_path)

        # 최종 결과 반환 (Celery Result Backend에 저장됨)
        return json.loads(context.model_dump_json())

    except Exception as e:
        log.critical(f"[{job_id}] Unhandled error in pipeline: {e}", exc_info=True)
        cleanup_file(file_path)
        error_result = context.model_dump()
        error_result["pipeline_status"] = "FAILED"
        error_result["error"] = str(e)
        return error_result