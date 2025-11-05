# D:\42_asia-hackathon\app\worker.py
# (오류 3개가 모두 수정된 버전)

import os
import json
import time
from celery import Celery
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from .config import settings
import requests
import torch
import uuid  # 🚨 Qdrant 포인트 ID 생성을 위해 추가

from .config import settings
from .logger_config import setup_logging

# --- 🔴 [수정 1] ---
# (버그) ClassificationModule -> (수정) DocumentClassifier
from .pipeline.classification_module import DocumentClassifier
# (버그) OCRModule -> (수정) PaddleOCRModule
from .pipeline.ocr_module import PaddleOCRModule
# --- (수정 끝) ---

from .pipeline.llm_tasks import (
    get_llm_extraction_task,
    perform_pii_masking,
    perform_summarization
)
from .pipeline.client import SearchClient, VectorClient
# 🚨 Qdrant 포인트 생성을 위해 models 임포트
from qdrant_client.http import models as qdrant_models

log = setup_logging()

# --- Celery 설정 ---
celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)
celery_app.conf.task_track_started = True
celery_app.conf.task_serializer = 'json'
celery_app.conf.result_serializer = 'json'
celery_app.conf.accept_content = ['json']

# --- AI 모델 및 클라이언트 로드 ---
MODEL_PATH = os.getenv("MODEL_PATH", "/usr/src/models/classifier")
log.info(f"Attempting to load DocumentClassifier model from: {MODEL_PATH}")

# --- 🔴 [수정 2] ---
# (버그) ClassificationModule() -> (수정) DocumentClassifier()
classifier_model = DocumentClassifier()
# --- (수정 끝) ---

try:
    USE_GPU = torch.cuda.is_available()
    log.info(f"GPU Available: {USE_GPU}")

    # --- 🔴 [수정 3] ---
    # (버그) OCRModule(...) -> (수정) PaddleOCRModule(...)
    ocr_module = PaddleOCRModule(lang='en', use_gpu=USE_GPU)
    # --- (수정 끝) ---

except Exception as e:
    log.error(f"Failed to load OCRModule: {e}. OCR tasks will fail.", exc_info=True)
    ocr_module = None

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
    log.info(f"[{context.job_id}] (1/6) Starting OCR...")
    t_start = time.time()
    if ocr_module is None:
        log.error(f"[{context.job_id}] OCRModule is not loaded. Skipping OCR.")
        context.extracted_text = ""
        return
    try:
        # (참고) ocr_module.py의 실제 함수명은 'perform_ocr'이 아닌 'process_document' 입니다.
        # 이 부분은 ocr_module.py 파일 자체를 수정해야 하지만, 일단은 코드를 유지합니다.
        # (만약 'perform_ocr'이 없다고 오류가 나면 'process_document'로 변경해야 합니다.)
        context.extracted_text = ocr_module.perform_ocr(context.file_path)
        context.ocr_time = time.time() - t_start
        log.info(
            f"[{context.job_id}] (1/6) OCR finished ({context.ocr_time:.2f}s). Extracted {len(context.extracted_text)} chars.")
    except Exception as e:
        log.error(f"[{context.job_id}] OCR task failed: {e}", exc_info=True)
        context.extracted_text = ""


def perform_classification(context: DocumentContext):
    log.info(f"[{context.job_id}] (2/6) Starting Classification...")
    t_start = time.time()
    if not context.extracted_text:
        log.warning(f"[{context.job_id}] No text extracted from OCR. Skipping classification.")
        context.classification_result = {"doc_type": "ocr_failed", "confidence": 0.0}
        return
    try:
        # --- 🔴 [수정 4] ---
        # (버그) predict()는 1개 값이 아닌 2개(label, score)를 반환합니다.
        # (버그) 인자 이름이 'ocr_text'가 아닌 'text' 입니다.
        predicted_label, confidence_score = classifier_model.predict(text=context.extracted_text)

        # (수정) 반환된 실제 값으로 결과를 구성합니다.
        context.classification_result = {
            "doc_type": predicted_label,
            "confidence": confidence_score
        }
        # --- (수정 끝) ---

        context.classification_time = time.time() - t_start
        log.info(
            f"[{context.job_id}] (2/6) Classification finished ({context.classification_time:.2f}s). Result: {context.classification_result}")
    except Exception as e:
        log.error(f"[{context.job_id}] Classification task failed: {e}", exc_info=True)
        context.classification_result = {"doc_type": "classification_failed", "confidence": 0.0}


def perform_llm_extraction(context: DocumentContext):
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


def perform_pii_and_summary(context: DocumentContext):
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
            "document_id": context.job_id,
            "file_name": context.file_name,
            "doc_type": context.classification_result.get("doc_type", "unknown"),
            "content": context.extracted_text,
            "summary": context.summary,
            "created_at": int(context.start_time),
            **context.structured_data
        }
        search_client.add_document(meili_doc)
        log.info(f"[{context.job_id}] (6/6) MeiliSearch indexing finished.")

        # 2. Qdrant (Vector Search)
        log.warning(f"[{context.job_id}] Qdrant indexing skipped: Embedding pipeline not implemented yet.")

        # [참고] 실제 구현 시:
        # points = [
        #     qdrant_models.PointStruct(
        #         id=str(uuid.uuid4()),
        #         vector=embedding_function(context.extracted_text), # [필수] 임베딩 함수 필요
        #         payload=meili_doc
        #     )
        # ]
        # vector_client.add_vectors(points)
        # log.info(f"[{context.job_id}] (6/6) Qdrant indexing finished.")

    except Exception as e:
        log.error(f"[{context.job_id}] Indexing task failed: {e}", exc_info=True)


def cleanup_file(file_path: str):
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
    log.info(f"[{job_id}] Celery task started for file: {file_name}")
    context = DocumentContext(
        job_id=job_id,
        file_path=file_path,
        file_name=file_name,
        file_mime_type=file_mime_type
    )
    try:
        perform_ocr(context)
        perform_classification(context)
        perform_llm_extraction(context)
        perform_pii_and_summary(context)
        perform_indexing(context)

        context.total_time = time.time() - context.start_time
        log.info(f"[{job_id}] Pipeline COMPLETED ({context.total_time:.2f}s).")
        cleanup_file(file_path)
        return json.loads(context.model_dump_json())

    except Exception as e:
        log.critical(f"[{job_id}] Unhandled error in pipeline: {e}", exc_info=True)
        cleanup_file(file_path)
        error_result = context.model_dump()
        error_result["pipeline_status"] = "FAILED"
        error_result["error"] = str(e)
        return error_result