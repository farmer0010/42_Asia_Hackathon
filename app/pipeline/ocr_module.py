# D:\42_asia-hackathon\42_Asia_Hackathon-backend\app\pipeline\ocr_module.py
# (기반: ocr_ver.2/srcs/ocr_vl_module.py)

import os
from paddleocr import PaddleOCR
from PIL import Image
from typing import Any, Dict

from ..logger_config import setup_logging
from ..config import settings

log = setup_logging()


class OCRModule:
    # 🔴 [핵심 수정] NVIDIA GPU 환경에 맞게 use_gpu 플래그를 생성자에서 받도록 수정
    def __init__(self, lang: str = 'en', use_gpu: bool = False):
        log.info(f"Initializing OCR module (PaddleOCR, language: {lang}, GPU: {use_gpu})...")

        try:
            # 🔴 [핵심] use_gpu 플래그를 PaddleOCR 생성자에 "전달"
            self.ocr = PaddleOCR(lang=lang, use_gpu=use_gpu)
            log.info("PaddleOCR initialization successful.")
        except Exception as e:
            log.error(f"Failed to initialize PaddleOCR: {e}. OCR tasks will fail.", exc_info=True)
            self.ocr = None

    def perform_ocr(self, file_path: str) -> str:
        if self.ocr is None:
            log.error(f"OCR execution skipped for {file_path}: Module failed to initialize.")
            return ""

        try:
            # 🔴 [유지] cls 인자 제거 (라이브러리 호환성 문제 해결)
            result = self.ocr.ocr(file_path)

            full_text = ""

            if not result or result[0] is None:
                log.warning(f"OCR result is empty for {file_path}.")
                return ""

            # ocr_ver.2의 파싱 로직과 동일
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