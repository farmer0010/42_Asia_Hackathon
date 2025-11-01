from paddleocr import PaddleOCR
import cv2
import numpy as np
from pathlib import Path
import time
import logging
from pdf2image import convert_from_path
import torch

# Loguru 로거 설정 (worker.py와 동일한 로거 사용)
log = logging.getLogger("uvicorn")


class OCRModule:
    """
    [최신 모듈] PaddleOCR을 사용하여 텍스트를 추출합니다.
    (당신이 제공한 코드를 기반으로 작성됨)
    """

    def __init__(self, lang='en', use_gpu=False):
        log.info(f"Initializing OCR module (PaddleOCR, language: {lang}, GPU: {use_gpu})...")
        try:
            self.ocr = PaddleOCR(
                use_angle_cls=False,
                lang=lang,
                use_gpu=use_gpu,
                show_log=False
            )
            log.info("OCR module (PaddleOCR) ready.")
        except Exception as e:
            log.error(f"Failed to initialize PaddleOCR: {e}", exc_info=True)
            self.ocr = None

    def _preprocess_image(self, image_path: str):
        img = cv2.imread(str(image_path))

        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        return enhanced

    def _pdf_to_image(self, pdf_path: str) -> str:
        """(first page only)"""
        images = convert_from_path(pdf_path, first_page=1, last_page=1)
        temp_dir = Path("/tmp/ocr_cache")
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / f"{Path(pdf_path).stem}.png"
        images[0].save(str(temp_path), 'PNG')
        return str(temp_path)

    def perform_ocr(self, file_path: str) -> str:
        """
        [수정] Celery worker.py와 연동하기 위한 메인 함수.
        성공 시 텍스트 문자열(str)을, 실패 시 빈 문자열("")을 반환합니다.
        """
        if self.ocr is None:
            log.error("PaddleOCR is not initialized. OCR failed.")
            return ""

        try:
            image_to_process = file_path

            # PDF 파일인 경우 이미지로 변환
            if Path(file_path).suffix.lower() == '.pdf':
                log.debug(f"Converting PDF to image: {file_path}")
                image_to_process = self._pdf_to_image(file_path)

            # 이미지 전처리
            log.debug(f"Preprocessing image: {image_to_process}")
            img = self._preprocess_image(image_to_process)

            # OCR 수행
            log.debug("Performing PaddleOCR...")
            result = self.ocr.ocr(img, cls=False)

            if not result or not result[0]:
                log.warning(f"No text detected in {file_path}")
                return ""

            lines = []
            for line in result[0]:
                bbox, (text, conf) = line
                lines.append(text)

            return '\n'.join(lines)

        except Exception as e:
            log.error(f"Error during PaddleOCR processing for {file_path}: {e}", exc_info=True)
            return ""  # 실패 시 빈 문자열 반환