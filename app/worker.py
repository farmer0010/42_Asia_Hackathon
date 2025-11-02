# D:\42_asia-hackathon\app\worker.py

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
from .pipeline.classification_module import DocumentClassifier
from .pipeline.ocr_module import OCRModule
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
    broker=settings.CELERY_BROKER_URL,  # 🚨 [수정 7]: config.py와 .env에 맞게 수정
    backend=settings.CELERY_RESULT_BACKEND,  # 🚨 [수정 7]: config.py와 .env에 맞게 수정
    include=["app.tasks"],
)
celery_app.conf.task_track_started = True
celery_app.conf.task_serializer = 'json'
celery_app.conf.result_serializer = 'json'
celery_app.conf.accept_content = ['json']

# --- AI 모델 및 클라이언트 로드 ---
MODEL_PATH = os.getenv("MODEL_PATH", "/usr/src/models/classifier")
log.info(f"Attempting to load DocumentClassifier model from: {MODEL_PATH}")

classifier_model = DocumentClassifier(model_path=MODEL_PATH)

try:
    USE_GPU = torch.cuda.is_available()
    log.info(f"GPU Available: {USE_GPU}")
    ocr_module = OCRModule(lang='en', use_gpu=USE_GPU)
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
        classification_result = classifier_model.classify(
            text=context.extracted_text,
            file_name=context.file_name
        )
        context.classification_result = classification_result
        context.classification_time = time.time() - t_start
        log.info(
            f"[{context.job_id}] (2/6) Classification finished ({context.classification_time:.2f}s). Result: {classification_result}")
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
            "id": context.job_id,  # 🚨 [수정 8]: MeiliSearch의 PK는 'id'로 설정 (client.py와 일치)
            "document_id": context.job_id,  # document_id도 유지
            "file_name": context.file_name,
            "doc_type": context.classification_result.get("doc_type", "unknown"),
            "content": context.extracted_text,
            "summary": context.summary,
            "created_at": int(context.start_time),
            **context.structured_data
        }
        # 🚨 [수정 9]: client.py에 정의된 add_document 함수 사용
        search_client.add_document(meili_doc)
        log.info(f"[{context.job_id}] (6/6) MeiliSearch indexing finished.")

        # 2. Qdrant (Vector Search)
        # 🚨 [수정 10]: client.py의 add_vectors에 맞게 데이터 포맷팅
        # Qdrant는 텍스트를 직접 받지 않고, 벡터와 payload를 받습니다.
        # [주의] 실제로는 여기서 텍스트를 임베딩 벡터로 변환하는 단계가 필요합니다.
        # 지금은 임베딩 단계가 없으므로, 임시로 Qdrant 저장을 건너뜁니다.

        # vector_client.index_document( ... ) # <- 이 함수는 client.py에 존재하지 않음

        # [임시 조치] Qdrant 인덱싱은 임베딩 파이프라인이 추가될 때까지 비활성화
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