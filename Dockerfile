# 1. Builder Stage
FROM python:3.11-slim as builder

# 시스템 의존성 설치
# (pdf2image용 poppler-utils, opencv-python용 libgl1)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src

# requirements.txt만 먼저 복사하여 Docker 캐시 활용
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 소스 코드 복사
COPY . .

# 2. Final Stage
FROM python:3.11-slim

# 시스템 의존성 설치 (런타임에도 필요)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Builder 스테이지에서 설치한 라이브러리와 소스 코드 복사
COPY --from=builder /usr/src/app ./app
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# 로컬의 shimmy-source를 이미지 내부로 복사
COPY ./shimmy-source /usr/src/shimmy-source

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]