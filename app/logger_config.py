import logging
import sys

def setup_logging():
    """
    애플리케이션의 로깅 시스템을 설정합니다.
    모든 로그는 표준 출력(stdout)으로 전송되며, Docker 환경에서 쉽게 확인할 수 있습니다.
    """
    # 전역 로거를 가져옵니다.
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # 로그 레벨 설정

    # 로그 메시지 포맷을 정의합니다.
    # 예: 2025-10-21 15:30:00,123 - app.main - INFO - 애플리케이션 시작...
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 핸들러를 설정합니다. 여기서는 콘솔로 출력합니다.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # 로거에 핸들러가 이미 추가되어 있는지 확인하여 중복을 방지합니다.
    if not logger.handlers:
        logger.addHandler(handler)