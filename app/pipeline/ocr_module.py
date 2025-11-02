# D:\42_asia_hackathon\app\pipeline\ocr_module.py (전체 코드)

import os
from paddleocr import PaddleOCR
from PIL import Image
from typing import Any, Dict

from ..logger_config import setup_logging
from ..config import settings

log = setup_logging()


class OCRModule:
    # use_gpu는 worker.py에서 받지만, 내부에서 직접 사용하지 않습니다.
    def __init__(self, lang: str = 'en', use_gpu: bool = False):
        log.info(f"Initializing OCR module (PaddleOCR, language: {lang}, GPU: {use_gpu})...")

        try:
            # 최종 안전 코드: 오류 유발 인자를 모두 제거합니다. (lang만 남김)
            self.ocr = PaddleOCR(lang=lang)
            log.info("PaddleOCR initialization successful (using default models).")
        except Exception as e:
            # 🚨 [최종 수정]: 초기화 실패 시 시스템 크래시를 방지하는 'raise' 문을 제거합니다.
            log.error(f"Failed to initialize PaddleOCR: {e}. OCR tasks will fail.", exc_info=True)
            self.ocr = None # ⬅️ self.ocr을 None으로 설정
            # raise가 제거되었으므로, worker.py는 이 오류를 무시하고 다음 초기화로 넘어갑니다.

    def perform_ocr(self, file_path: str) -> str:
        """
        OCR을 수행하고 전체 텍스트를 반환합니다.
        """
        if self.ocr is None:
            # 🚨 self.ocr이 None이면 OCR 실행을 건너뛰고 빈 문자열 반환
            log.error(f"OCR execution skipped for {file_path}: Module failed to initialize.")
            return ""

        try:
            result = self.ocr.ocr(file_path, cls=False)

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