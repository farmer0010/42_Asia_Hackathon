# 1. Builder Stage
FROM python:3.11-slim as builder

# 🚨 [수정 3]: Scipy 빌드에 필요한 모든 시스템 도구 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    gfortran \
    libblas-dev \
    liblapack-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 소스 코드 복사
COPY . .

# -----------------------------------------------------------
# 2. Final Stage (빌드 도구 없이 런타임 환경 구성)
# -----------------------------------------------------------
FROM python:3.11-slim

# 런타임에 필요한 시스템 의존성만 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src
ENV PYTHONPATH="/usr/src"

# Builder 스테이지에서 설치된 결과물 (소스 코드, 라이브러리) 복사
COPY --from=builder /usr/src/app ./app
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# 로컬의 shimmy-source 복사
COPY ./shimmy-source /usr/src/shimmy-source

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]