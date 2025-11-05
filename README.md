# 🧠 42 Asia Hackathon - 지능형 문서 처리 AI 엔진 (Backend)

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95-green?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-20.10-blue?logo=docker&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.3-yellow?logo=celery&logoColor=black)
![MeiliSearch](https://img.shields.io/badge/MeiliSearch-1.2-orange)
![Qdrant](https://img.shields.io/badge/Qdrant-0.11-red)

---

## 🎯 프로젝트 개요

2025 아시아 해커톤 출품작으로, 업로드된 문서 이미지(PDF/JPG/PNG)에 대해 **OCR, 문서 분류, 정보 추출, 검색**까지 지원하는 지능형 문서 처리 AI 엔진 백엔드입니다.

### 핵심 기능

- 📝 OCR (텍스트 추출) - PaddleOCR
- 📂 문서 분류 - DistilBERT 기반 자동 분류 (invoice, receipt 등)
- 🔍 정보 추출 (Extraction) - BERT-NER 기반 핵심 정보 구조화 (금액, 날짜, 회사명)
- 🤖 의미 기반 검색 / 요약 - LLM(vLLM / Ollama) 활용 벡터 임베딩 및 요약 (Phase 2)
- 💾 결과 저장 및 검색 - 키워드 검색: MeiliSearch, 벡터 검색: Qdrant

---

## 🏗️ 시스템 아키텍처

📁 FastAPI (Main API Server)
┣ 📦 Celery (비동기 작업 큐)
┃ ┣ 🧠 AI Processor (OCR, 분류, 추출)
┃ ┣ 🗂️ LLM Engine (요약 / 임베딩)
┃ ┗ 💬 Message Queue (Redis)
┣ 💾 DB Layer
┃ ┣ 🔍 MeiliSearch (키워드 검색)
┃ ┗ 🧩 Qdrant (벡터 검색)
┗ 🌐 Client / Frontend (문서 업로드 및 결과 조회)

---

## ⚙️ 기술 스택

| 구분 | 기술 |
|------|------|
| Backend Framework | FastAPI |
| Task Queue | Celery + Redis |
| OCR Engine | PaddleOCR |
| NLP Models | DistilBERT, BERT-NER |
| Vector DB | Qdrant |
| Search Engine | MeiliSearch |
| Containerization | Docker Compose |
| Language | Python 3.11 |

---

## 🚀 실행 방법

### 1. 환경 변수 설정
`.env` 파일을 생성하고 아래 항목을 채워주세요.

REDIS_URL=redis://redis:6379/0
MEILI_HOST=http://meilisearch:7700

QDRANT_HOST=http://qdrant:6333

### 2. Docker Compose 실행
```bash
docker-compose up --build

. API 문서 확인

FastAPI 서버 실행 후 Swagger 문서를 열어보세요:
👉 http://localhost:8000/docs

📂 주요 디렉토리 구조
backend/
 ┣ 📁 app/
 ┃ ┣ 📄 main.py
 ┃ ┣ 📁 api/
 ┃ ┣ 📁 core/
 ┃ ┣ 📁 services/
 ┃ ┗ 📁 models/
 ┣ 📁 worker/
 ┃ ┣ 📄 celery_app.py
 ┃ ┗ 📄 tasks.py
 ┣ 📁 docker/
 ┣ 📄 docker-compose.yml
 ┣ 📄 requirements.txt
 ┗ 📄 README.md
