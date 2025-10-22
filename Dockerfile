# 빌드 환경 및 OS 의존성 추출 (Builder Stage)
FROM python:3.11 as builder
WORKDIR /usr/src

# 1. Tesseract OCR 엔진과 개발 도구 설치
RUN apt-get update \
    && apt-get install -y \
        tesseract-ocr \
        libtesseract-dev \
        libleptonica-dev \
        locales \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
)
FROM python:3.11-slim
WORKDIR /usr/src

# 1. Tesseract 런타임 의존성 복사 (Stage 1에서 가져옴)
COPY --from=builder /usr/bin/tesseract /usr/bin/tesseract
COPY --from=builder /usr/share/tesseract-ocr/5/tessdata /usr/share/tessdata
COPY --from=builder /usr/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/
COPY --from=builder /lib/x86_64-linux-gnu/ /lib/x86_64-linux-gnu/

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY ./app /usr/src/app

# 비 root 사용자 실행 및 권한 설정 (보안 강화)
RUN groupadd -r nonroot && useradd --no-log-init -r -g nonroot nonroot
# 권한 설정도 변경된 경로에 맞춥니다.
RUN chown -R nonroot:nonroot /usr/src

USER nonroot:nonroot

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]