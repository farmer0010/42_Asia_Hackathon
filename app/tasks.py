import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from app.worker import celery_app
from app.config import settings

# 1. 업그레이드된 OCR 모듈 임포트
from app.pipeline.ocr_module import PaddleOCRModule

# 2. 신규 규칙 기반(Heuristic) 파서 임포트
from app.pipeline.smart_extractor import (
    find_likely_mrz_lines,
    parse_mrz_data
)

# 3. 업그레이드된 LLM 태스크 임포트
from app.pipeline.llm_tasks import get_llm_extraction_task

# 4. 분류 모듈 임포트 (기존 ver2 로직)
from app.pipeline.classification_module import DocumentClassifier

# 로거 설정
logger = logging.getLogger(__name__)

# --- 모듈 싱글턴 관리 (Spring의 @Singleton Bean과 유사) ---
_ocr_module_gpu = None
_classifier = None


def get_ocr_module(use_gpu=True):
    global _ocr_module_gpu
    if use_gpu:
        if _ocr_module_gpu is None:
            logger.info("Initializing PaddleOCRModule (GPU)...")
            _ocr_module_gpu = PaddleOCRModule(use_gpu=True, enable_handwriting=True)
            logger.info("PaddleOCRModule (GPU) initialized.")
        return _ocr_module_gpu
    return None


def get_classifier():
    global _classifier
    if _classifier is None:
        logger.info("Initializing DocumentClassifier...")
        # .env의 MODEL_PATH와 로컬 모델 제약사항 준수
        # docker-compose.yml에서 celery-worker의 MODEL_PATH는
        # "/usr/src/models/classifier"로 설정됨.
        classifier_path = os.path.join(settings.MODEL_PATH, "document_classifier_model.joblib")

        if not os.path.exists(classifier_path):
            logger.error(f"Classifier model not found at primary path: {classifier_path}")
            # 대체 경로 시도: /usr/src/models/document_classifier_model.joblib
            # (MODEL_PATH가 /usr/src/models/classifier 일 경우)
            alt_path = os.path.join(
                os.path.dirname(settings.MODEL_PATH.rstrip('/')),
                "document_classifier_model.joblib"
            )
            logger.info(f"Attempting to load classifier from alternate path: {alt_path}")
            if os.path.exists(alt_path):
                classifier_path = alt_path
            else:
                logger.error(f"CRITICAL: Classifier model NOT FOUND at {classifier_path} or {alt_path}")
                _classifier = None  # 로드 실패
                return None

        _classifier = DocumentClassifier(model_path=classifier_path)
        logger.info(f"DocumentClassifier initialized from {classifier_path}.")
    return _classifier


# --- 🔴 [!!! 핵심 파이프라인 태스크 !!!] ---

@celery_app.task(name="process_document_task")
def process_document_task(file_path: str, classification_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    단일 문서를 처리하는 전체 하이브리드 파이프라인 (Celery Task)
    1. OCR (PDF/이미지/다국어/레이아웃)
    2. 분류 (Classifier)
    3. 규칙 기반(Heuristic) 1차 추출 (예: MRZ)
    4. LLM 기반 2차 추출 (OCR + Heuristic 결과 참조)
    """
    logger.info(f"🚀 [Task Started] Processing file: {file_path}")

    # --- 0. 파일 존재 여부 확인 ---
    # (FileNotFoundError는 Celery에서 @Async 작업 시 공유 볼륨 문제로 자주 발생)
    if not os.path.exists(file_path):
        logger.error(f"❌ [Task Failed] File not found at path: {file_path}. Check 'uploads_data' shared volume.")
        raise FileNotFoundError(f"File not found at {file_path}. Check shared volume mount.")

    try:
        # --- 1. OCR (Advanced) ---
        ocr_module = get_ocr_module(use_gpu=True)  # Celery 워커는 GPU 사용
        if not ocr_module:
            raise Exception("GPU OCR Module not available or failed to initialize.")

        is_pdf = file_path.lower().endswith('.pdf')

        if is_pdf:
            ocr_result = ocr_module.process_pdf_multipage(file_path, lang='auto')
        else:
            ocr_result = ocr_module.process_document(file_path, lang='auto')

        if ocr_result.get("error"):
            raise Exception(f"OCR failed: {ocr_result['error']}")

        logger.info(
            f"✅ [Step 1/4] OCR Succeeded. Lang: {ocr_result.get('detected_language')}, Confidence: {ocr_result.get('confidence'):.2%}")

        # --- 2. 분류 (Classifier) ---
        classifier = get_classifier()
        if not classifier:
            logger.warning("Classifier model not loaded. Skipping classification.")
            doc_type = "unknown"  # 분류기 없이 진행
            doc_type_result = {"doc_type": "unknown", "confidence": 0.0}
        else:
            doc_type_result = classifier.classify(ocr_result['full_text'])
            doc_type = doc_type_result.get("doc_type", "unknown")
            logger.info(
                f"✅ [Step 2/4] Classification Succeeded. Type: {doc_type} (Confidence: {doc_type_result.get('confidence'):.2%})")

        # --- 3. 규칙 기반(Heuristic) 1차 추출 ---
        heuristic_data = {}
        if doc_type == "passport":
            mrz_lines = find_likely_mrz_lines(ocr_result)
            if mrz_lines:
                heuristic_data = parse_mrz_data(mrz_lines)
                logger.info("✅ [Step 3/4] Heuristic Parser: MRZ data extracted.")
            else:
                logger.info("ℹ️ [Step 3/4] Heuristic Parser: No MRZ lines found.")
        else:
            logger.info(f"ℹ️ [Step 3/4] Heuristic Parser: No rules for doc_type '{doc_type}'.")

        # --- 4. LLM 기반 2차 추출 (하이브리드) ---
        llm_task = get_llm_extraction_task(doc_type)

        if not llm_task:
            logger.warning(f"No LLM extraction task found for doc_type: {doc_type}. Skipping LLM.")
            llm_result = {"warning": "No LLM task configured for this document type."}
        else:
            # [핵심] OCR 결과(all_boxes)와 Heuristic 결과를 모두 LLM에 전달
            pipeline_input = {
                "ocr": ocr_result,
                "heuristic": heuristic_data
            }
            llm_result = llm_task(pipeline_input)

            if llm_result.get("error"):
                raise Exception(f"LLM extraction failed: {llm_result['error']}")
            logger.info("✅ [Step 4/4] LLM Extraction Succeeded.")

        # --- 최종 결과 조합 ---
        final_result = {
            "filename": Path(file_path).name,
            "doc_type": doc_type,
            "classification_confidence": doc_type_result.get('confidence'),
            "ocr_confidence": ocr_result.get('confidence'),
            "detected_language": ocr_result.get('detected_language'),
            "extracted_data": llm_result,
            "heuristic_data": heuristic_data,  # (디버깅/검증용)
            "full_text": ocr_result.get("full_text")  # (검색 엔진 인덱싱용)
        }

        logger.info(f"🎉 [Task Finished] Successfully processed: {file_path}")

        # (TODO: 이 결과를 MeiliSearch/Qdrant에 인덱싱)

        return final_result

    except Exception as e:
        logger.error(f"❌ [Task Failed] Error processing {file_path}: {e}", exc_info=True)
        raise  # Celery가 재시도할 수 있도록 예외를 다시 발생시킴