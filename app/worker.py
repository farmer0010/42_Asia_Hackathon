# [경로: app/worker.py]
# (이 내용으로 덮어쓰세요)

import logging
from celery import Celery
from app.config import settings

# 로거 설정 (유지)
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

logger.info("Initializing Celery app...")

# --- 🔴 [!!! 수정 !!!] ---
#
# (app/tasks.py의 get_ocr_module, get_classifier가
# 모델 로딩을 처리하므로, 이 파일의 모든 전역 모델 로딩 로직을 제거합니다.)
#
# (기존 DocumentClassifier 및 PaddleOCRModule 초기화 코드 블록 전체 삭제)
#
# --- [수정 완료] ---


# MeiliSearch 및 Qdrant 클라이언트 초기화 (이것은 유지해도 좋습니다.
# 또는 app/tasks.py의 get_client 함수로 옮겨도 됩니다.)
try:
    from app.pipeline.client import SearchClient, VectorClient
    search_client = SearchClient()
    vector_client = VectorClient()
    logger.info(f"[SearchClient] MeiliSearch 연결 성공 (호스트: {settings.MEILI_URL})")
    logger.info(f"[VectorClient] Qdrant 연결 성공 (URL: {settings.QDRANT_URL})")
except Exception as e:
    logger.error(f"Search/Vector client 초기화 실패: {e}", exc_info=True)


# Celery 앱 정의 (유지)
celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# 🔴 [핵심] app.tasks를 임포트하도록 설정 (유지)
# 이 설정 덕분에 app/tasks.py 내부의 코드가 실행됩니다.
celery_app.conf.imports = ("app.tasks",)
celery_app.conf.task_track_started = True

logger.info("Celery app configured. Worker a_waiting tasks...")