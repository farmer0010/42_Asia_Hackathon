# Stage 1: 빌드 환경 및 OS 의존성 추출 (Builder Stage)
FROM python:3.11 as builder
# ★★★ 수정됨: WORKDIR을 애플리케이션의 '상위' 경로로 변경합니다. ★★★
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

# 2. Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: 최종 '실행 환경' 설정 (Security/Minimal Final Stage)
FROM python:3.11-slim
# ★★★ 수정됨: WORKDIR을 애플리케이션의 '상위' 경로로 변경합니다. ★★★
WORKDIR /usr/src

# 1. Tesseract 런타임 의존성 복사 (Stage 1에서 가져옴)
COPY --from=builder /usr/bin/tesseract /usr/bin/tesseract
COPY --from=builder /usr/share/tesseract-ocr/5/tessdata /usr/share/tessdata
COPY --from=builder /usr/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/
COPY --from=builder /lib/x86_64-linux-gnu/ /lib/x86_64-linux-gnu/

# 2. Python 패키지와 애플리케이션 코드 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# ★★★ 수정됨: 'app' 폴더를 WORKDIR 안의 'app'이라는 폴더로 복사합니다. ★★★
COPY ./app /usr/src/app

# 3. 비 root 사용자 실행 및 권한 설정 (보안 강화)
RUN groupadd -r nonroot && useradd --no-log-init -r -g nonroot nonroot
# 권한 설정도 변경된 경로에 맞춥니다.
RUN chown -R nonroot:nonroot /usr/src

USER nonroot:nonroot

EXPOSE 8000
# ★★★ 최종 수정: 'app.main:app' 모듈 경로로 실행합니다. (WORKDIR이 /usr/src) ★★★
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]