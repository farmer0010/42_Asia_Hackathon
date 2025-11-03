FROM python:3.11-slim

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY srcs/ ./srcs/
COPY llm_service/ ./llm_service/
COPY run_pipeline.sh .
RUN chmod +x run_pipeline.sh

# 디렉토리 생성
RUN mkdir -p input output models

# 기본 명령
CMD ["bash", "run_pipeline.sh"]