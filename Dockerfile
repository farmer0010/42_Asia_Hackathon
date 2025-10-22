# 1단계: '작업실' 환경 설정
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
# 이제 pip이 requirements.txt에 명시된 모든 것을 설치합니다 (spacy 모델 포함).
RUN pip install --no-cache-dir -r requirements.txt

# 2단계: 최종 '배송 상자' 환경 설정
FROM python:3.11-slim
WORKDIR /app
# 작업실에서 조립한 모든 부품들을 복사합니다.
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY ./app /app

# nonroot 사용자 및 그룹 생성
RUN groupadd -r nonroot && useradd --no-log-init -r -g nonroot nonroot

USER nonroot:nonroot

EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]