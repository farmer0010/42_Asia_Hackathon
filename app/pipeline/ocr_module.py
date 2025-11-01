# D:\42_asia_hackathon\app\pipeline\ocr_module.py (전체 코드)

import os
from paddleocr import PaddleOCR
from PIL import Image
from typing import Any, Dict

from ..logger_config import setup_logging
from ..config import settings

log = setup_logging()


class OCRModule:
    # 🚨 [수정]: use_gpu, show_log 인자를 PaddleOCR 생성자에서 삭제 (Value Error 해결)
    def __init__(self, lang: str = 'en', use_gpu: bool = False):
        log.info(f"Initializing OCR module (PaddleOCR, language: {lang}, GPU: {use_gpu})...")

        try:
            # 🚨 [수정]: 오류 유발 인자 삭제. 현재 버전의 PaddleOCR은 lang만 받도록 합니다.
            self.ocr = PaddleOCR(lang=lang)
            log.info("PaddleOCR initialization successful (using default models).")
        except Exception as e:
            log.error(f"Failed to initialize PaddleOCR: {e}")
            raise

    def perform_ocr(self, file_path: str) -> str:
        """
        주어진 파일 경로의 이미지/PDF에서 OCR을 수행하고 전체 텍스트를 반환합니다.
        """
        # ... (나머지 perform_ocr 로직 유지)
        try:
            result = self.ocr.ocr(file_path, cls=True)

            full_text = ""
            for line in result:
                if line and line[0] is not None:
                    for item in line:
                        if isinstance(item, list) and len(item) > 1 and isinstance(item[1], tuple):
                            full_text += item[1][0] + " "

            return full_text.strip()

        except Exception as e:
            log.error(f"OCR execution failed for {file_path}: {e}")
            return ""