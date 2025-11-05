import os
import logging
from paddleocr import PaddleOCR
from app.config import settings

# 로거 설정
logger = logging.getLogger(__name__)


# --- 🔴 [수정] 클래스 이름을 worker.py와 일치 ---
class PaddleOCRModule:

    def __init__(self, lang='en', use_gpu=False, **kwargs):
        """
        PaddleOCR 인스턴스를 초기화합니다.
        Mac 테스트 및 안정적인 Docker 배포를 위해 use_gpu=False를 기본값으로 합니다.
        """
        logger.info(f"PaddleOCR 초기화 시작. Language: {lang}, Use GPU: {use_gpu}")
        try:
            # 🔴 [수정] Mac/CPU 환경을 위해 use_gpu=False 강제
            # (True로 설정 시 Mac에서 Docker가 CUDA 드라이버를 찾지 못해 충돌)
            self.ocr = PaddleOCR(lang=lang, use_gpu=False, **kwargs)
            logger.info("PaddleOCR 초기화 성공.")
        except Exception as e:
            logger.error(f"PaddleOCR 초기화 실패: {e}", exc_info=True)
            logger.error("DOCKERFILE의 paddlepaddle/numpy 버전이 호환되는지 확인하세요.")
            raise

    def perform_ocr(self, image_path: str) -> str:
        """
        주어진 이미지 경로에서 OCR을 수행하고 전체 텍스트를 반환합니다.

        [참고] worker.py의 101번째 줄에서 이 함수를 호출합니다.
        """
        if not os.path.exists(image_path):
            logger.error(f"OCR 실패: 파일을 찾을 수 없습니다. 경로: {image_path}")
            return ""

        try:
            # 1. OCR 실행
            # (cls=True는 텍스트 방향 분류를 활성화합니다)
            result = self.ocr.ocr(image_path, cls=True)

            if not result or not result[0]:
                logger.warning(f"OCR 결과가 비어있습니다. (이미지에 텍스트가 없음) 파일: {image_path}")
                return ""

            # 2. 결과에서 텍스트만 추출
            lines = [line[1][0] for line in result[0]]

            # 3. 모든 텍스트 라인을 하나의 문자열로 결합
            full_text = "\n".join(lines)
            return full_text

        except Exception as e:
            logger.error(f"OCR 처리 중 예외 발생. 파일: {image_path}, 오류: {e}", exc_info=True)
            return f"OCR_FAILED: {str(e)}"

# 모듈 수준에서 단일 인스턴스 생성 (싱글톤 패턴)
# try:
#     ocr_instance = PaddleOCRModule(lang='en', use_gpu=False)
# except Exception as e:
#     logger.critical(f"OCR 모듈 인스턴스 생성 실패. 시스템이 작동하지 않을 수 있습니다. {e}")
#     ocr_instance = None