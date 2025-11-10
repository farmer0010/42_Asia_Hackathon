# [수정 후: app/pipeline/ocr_module.py]
import os
import logging
from paddleocr import PaddleOCR
from app.config import settings

# 로거 설정
logger = logging.getLogger(__name__)


# --- 🔴 [수정] 클래스 이름을 worker.py와 일치 ---
class PaddleOCRModule:

    # 🟢 [GPU 수정] use_gpu=False 기본값을 받도록 하되,
    def __init__(self, lang='en', use_gpu=False, **kwargs):
        """
        PaddleOCR 인스턴스를 초기화합니다.
        A100 서버에서는 worker.py가 use_gpu=True를 전달할 것입니다.
        """
        logger.info(f"PaddleOCR 초기화 시작. Language: {lang}, Use GPU: {use_gpu}")
        try:
            # 🟢 [GPU 수정] Mac에서 하드코딩했던 'False' 대신, 전달받은 'use_gpu' 변수를 사용합니다.
            self.ocr = PaddleOCR(lang=lang, use_gpu=use_gpu, **kwargs)
            logger.info("PaddleOCR 초기화 성공.")
        except Exception as e:
            logger.error(f"PaddleOCR 초기화 실패: {e}", exc_info=True)
            logger.error("DOCKERFILE의 paddlepaddle/numpy 버전이 호환되는지 확인하세요.")
            raise

    def perform_ocr(self, image_path: str) -> str:
        """
        주어진 이미지 경로에서 OCR을 수행하고 전체 텍스트를 반환합니다.
        """
        if not os.path.exists(image_path):
            logger.error(f"OCR 실패: 파일을 찾을 수 없습니다. 경로: {image_path}")
            return ""

        try:
            # 1. OCR 실행
            # 🔴 [수정] cls=False (Mac 브랜치는 True였으나, 원본 GPU 브랜치는 False였음. 안정성을 위해 False 유지)
            # (cls=True는 텍스트 방향 분류이며, 우리 모델은 영어 수평 텍스트가 기본임)
            result = self.ocr.ocr(image_path, cls=False)

            if not result or not result[0]:
                logger.warning(f"OCR 결과가 비어있습니다. (이미지에 텍스트가 없음) 파일: {image_path}")
                return ""

            # 2. 텍스트 추출 방식 수정 (원본 GPU 브랜치 방식)
            # (신뢰도(confidence)는 무시하고 텍스트(text)만 가져와서 공백으로 연결)
            lines = [line[1][0] for line in result[0]]
            full_text = " ".join(lines)  # \n 대신 공백으로 연결

            return full_text.strip()

        except Exception as e:
            logger.error(f"OCR 처리 중 예외 발생. 파일: {image_path}, 오류: {e}", exc_info=True)
            return f"OCR_FAILED: {str(e)}"