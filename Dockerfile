FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2단계: 최종 '배송 상자' 환경 설정
FROM python:3.11-slim
WORKDIR /app
# 작업실에서 조립한 부품들만 복사해오기
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY ./app /app

# nonroot 사용자 그룹 생성
RUN groupadd -r nonroot && useradd --no-log-init -r -g nonroot nonroot

# 보안을 위해 일반 사용자 권한으로 실행
USER nonroot:nonroot

EXPOSE 8000
# 컨테이너가 시작될 때 uvicorn 서버를 실행하라는 기본 명령어
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]