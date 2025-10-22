import logging
import sys

def setup_logging():
    """
    모든 로그는 표준 출력(stdout)으로 전송되며, Docker 환경에서 쉽게 확인 가능.
    """
    # 전역 로거를 가져옵니다.
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # 로그 레벨 설정

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # 로거에 핸들러가 이미 추가되어 있는지 확인하여 중복을 방지.
    if not logger.handlers:
        logger.addHandler(handler)