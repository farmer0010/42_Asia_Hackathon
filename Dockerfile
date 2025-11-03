# D:\42_asia-hackathon\42_Asia_Hackathon-backend\Dockerfile

# 1. 기본 이미지
FROM python:3.11-slim-bookworm AS base
ENV PYTHONUNBUFFERED=1

# 🔴 [유지] PyMuPDF/make/swig/pkg-config 오류 해결
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing \
    curl \
    # PyMuPDF (paddleocr 의존성) 컴파일에 필요한 C/C++ 빌드 도구 전체 추가
    build-essential \
    swig \
    pkg-config \
    # 🔴 [유지] NVIDIA GPU 라이브러리 및 PaddleOCR 의존성
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgl1 \
    libnss3 \
    libxss1 \
    libasound2 \
    libxrandr2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# 2. Python 의존성 설치 (개발 스테이지)
FROM base AS development
WORKDIR /usr/src
COPY requirements.txt .

# 🔴 [!!! 핵심 수정 !!!] Numpy/Scipy/Sklearn/Paddle 충돌 해결
RUN pip install --no-cache-dir -r requirements.txt && \
    # 🔴 1. 충돌 가능성이 있는 모든 라이브러리를 강제 삭제
    pip uninstall -y paddlepaddle paddlepaddle-gpu paddleocr paddlex numpy opencv-python opencv-python-headless scipy scikit-learn && \

    # 🔴 2. "황금 버전" 1: Paddle + Numpy
    pip install paddlepaddle-gpu==2.5.2 && \
    pip install paddleocr==2.7.0.3 && \
    pip install numpy==1.24.4 && \
    pip install opencv-python-headless==4.8.1.78 && \

    # 🔴 3. "황금 버전" 2: numpy 1.24.4와 호환되는 Sklearn + Scipy
    pip install scipy==1.11.4 && \
    pip install scikit-learn==1.3.2

# 3. 최종 애플리케이션 이미지 (개발 스테이지 사용)
FROM development AS final
WORKDIR /usr/src

# 🔴 [유지] '유령 캐시' 해결
COPY ./app /usr/src/app

# FastAPI 서버 실행 (기본 포트 8000)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]