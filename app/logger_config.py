import logging
import sys


def setup_logging(name="worker_log") -> logging.Logger:
    """
    Celery 워커를 위한 로깅을 설정하고 로거 인스턴스를 반환합니다.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 핸들러가 이미 존재하면 추가하지 않습니다. (Celery의 이중 로깅 방지)
    if not logger.handlers:
        # 콘솔 출력 핸들러 설정
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)

        # 포맷 설정
        formatter = logging.Formatter(
            '%(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)

        # 로거에 핸들러 추가
        logger.addHandler(ch)

    return logger  # ◀◀◀ 이 반환문이 누락된 오류를 해결합니다!