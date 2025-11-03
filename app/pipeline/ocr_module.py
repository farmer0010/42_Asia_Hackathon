# D:\42_asia_hackathon\app\pipeline\ocr_module.py (최종 수정본)

import os
from paddleocr import PaddleOCR
from PIL import Image
from typing import Any, Dict

from ..logger_config import setup_logging
from ..config import settings

log = setup_logging()


class OCRModule:
    def __init__(self, lang: str = 'en', use_gpu: bool = False):
        log.info(f"Initializing OCR module (PaddleOCR, language: {lang}, GPU: {use_gpu})...")

        try:
            # 🔴 [수정] use_gpu 플래그를 PaddleOCR 생성자에 "전달"합니다.
            self.ocr = PaddleOCR(lang=lang, use_gpu=use_gpu)

            log.info("PaddleOCR initialization successful (using default models).")
        except Exception as e:
            log.error(f"Failed to initialize PaddleOCR: {e}. OCR tasks will fail.", exc_info=True)
            self.ocr = None

    def perform_ocr(self, file_path: str) -> str:
        """
        OCR을 수행하고 전체 텍스트를 반환합니다.
        """
        if self.ocr is None:
            log.error(f"OCR execution skipped for {file_path}: Module failed to initialize.")
            return ""

        try:
            # 🔴 [유지] cls 인자 제거 (라이브러리 호환성 문제 해결)
            result = self.ocr.ocr(file_path)

            full_text = ""

            # 🔴 [유지] 새로운 결과 형식(result[0])에 맞게 파싱
            if not result or result[0] is None:
                log.warning(f"OCR result is empty for {file_path}.")
                return ""

            for line_data in result[0]:
                if isinstance(line_data, list) and len(line_data) == 2:
                    text, confidence = line_data[1]
                    full_text += text + " "
                else:
                    log.warning(f"Unexpected OCR line format: {line_data}")

            return full_text.strip()

        except Exception as e:
            log.error(f"OCR execution failed for {file_path}: {e}", exc_info=True)
            return ""