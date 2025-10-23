import pytesseract
from PIL import Image
import io
from presidio_analyzer import AnalyzerEngine
import logging
import numpy as np

log = logging.getLogger(__name__)

analyzer = AnalyzerEngine()


def ocr_step(file_content: bytes) -> str:
    """OCR 처리 단계: 파일 내용(bytes)을 받아 텍스트를 추출."""
    try:
        log.info("--- OCR Step Start ---")
        image = Image.open(io.BytesIO(file_content))

        # ⭐️ [핵심 수정] pytesseract에게 'tessdata' 디렉토리의 정확한 위치를 직접 알려줍니다.
        # Dockerfile에 설정된 TESSDATA_PREFIX 경로와 동일합니다.
        tessdata_dir_config = r'--tessdata-dir "/usr/share/tesseract-ocr/5/tessdata"'

        extracted_text = pytesseract.image_to_string(image, lang='eng', config=tessdata_dir_config)

        log.info(f"OCR 텍스트 추출 완료. (길이: {len(extracted_text)})")
        return extracted_text
    except Exception as e:
        log.error(f"OCR 처리 중 에러 발생: {e}")
        return ""


def pii_detection_step(text: str):
    """PII 탐지 단계: 텍스트를 받아 개인정보를 탐지하고 로그 제공."""
    try:
        log.info("--- PII Detection Step Start ---")
        pii_results = analyzer.analyze(text=text, language='en')
        if pii_results:
            log.info(f"{len(pii_results)}개의 개인정보가 탐지되었습니다.")
        else:
            log.info("개인정보가 탐지되지 않았습니다.")
    except Exception as e:
        log.error(f"PII 탐지 중 에러 발생: {e}")


def mock_embedding_step(text: str) -> list[float]:
    """[임시 목업 함수] LLM 모델 대신 가짜 벡터(숫자 배열)를 생성합니다."""
    if not text:
        log.warning("입력 텍스트가 없어 가짜 임베딩 생성을 건너뜁니다.")
        return []

    log.info("--- Mock Embedding Step Start ---")
    mock_vector = np.random.rand(1024).tolist()
    log.info(f"가짜 임베딩 벡터 생성 완료. (차원: {len(mock_vector)})")
    return mock_vector