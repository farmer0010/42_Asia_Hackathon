# 1단계: 빌드 스테이지 (Builder Stage)
# 모든 개발 도구와 라이브러리를 설치하는 '공장'
FROM python:3.11 as builder
WORKDIR /usr/src/app

# Tesseract OCR 엔진 및 관련 라이브러리 설치
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# 2단계: 최종 실행 스테이지 (Final Stage)
# 실제 서비스가 실행될 최소한의 '제품' 환경
FROM python:3.11-slim
WORKDIR /usr/src/app

# ⭐️ [핵심 수정] Tesseract에게 '영어사전'의 위치를 알려주는 환경변수 설정
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5

# Tesseract 실행에 필요한 라이브러리 및 데이터 파일들을 '공장'에서 복사
# ⭐️ [경로 수정] 환경변수에 설정된 경로와 일치하도록 복사 경로를 명확히 함
COPY --from=builder /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu
COPY --from=builder /lib/x86_64-linux-gnu /lib/x86_64-linux-gnu
COPY --from=builder /usr/share/tesseract-ocr/5/tessdata ${TESSDATA_PREFIX}/tessdata
COPY --from=builder /usr/bin/tesseract /usr/bin/tesseract

# uvicorn 등 실행 파일 복사
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# 파이썬 라이브러리 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/

# 애플리케이션 소스 코드 복사
COPY ./app ./app

# 보안 강화를 위해 non-root 사용자로 실행
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["/usr/local/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]