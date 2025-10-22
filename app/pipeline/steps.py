import pytesseract
from PIL import Image
import io
from presidio_analyzer import AnalyzerEngine
import logging

log = logging.getLogger(__name__)

# AnalyzerEngine처럼 초기화 비용이 큰 객체는 재사용하도록 전역으로 선언합니다.
analyzer = AnalyzerEngine()

def ocr_step(file_content: bytes) -> str:
    """OCR 처리 단계: 파일 내용(bytes)을 받아 텍스트를 추출."""
    try:
        log.info("--- OCR Step Start ---")
        image = Image.open(io.BytesIO(file_content))
        extracted_text = pytesseract.image_to_string(image, lang='eng')
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
            for result in pii_results:
                log.debug(f"- Type: {result.entity_type}, Text: {text[result.start:result.end]}")
        else:
            log.info("개인정보가 탐지되지 않았습니다.")
    except Exception as e:
        log.error(f"PII 탐지 중 에러 발생: {e}")