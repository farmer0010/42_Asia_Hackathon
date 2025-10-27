# 42 Asia Hackathon - 지능형 문서 처리 AI 엔진 (Backend)

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95-green?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-20.10-blue?logo=docker&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.3-yellow?logo=celery&logoColor=black)
![MeiliSearch](https://img.shields.io/badge/MeiliSearch-1.2-orange)
![Qdrant](https://img.shields.io/badge/Qdrant-0.11-red)

---

## 프로젝트 개요

2025 아시아 해커톤 출품작으로, 업로드된 문서 이미지(PDF/JPG/PNG)에 대해 **OCR, 문서 분류, 정보 추출, 검색**까지 지원하는 지능형 문서 처리 AI 엔진 백엔드입니다.

### 핵심 기능

- 📝 OCR (텍스트 추출) - PaddleOCR
- 📂 문서 분류 - DistilBERT 기반 자동 분류 (invoice, receipt 등)
- 🔍 정보 추출 (Extraction) - BERT-NER 기반 핵심 정보 구조화 (금액, 날짜, 회사명)
- 🤖 의미 기반 검색 / 요약 - LLM(vLLM / Ollama) 활용 벡터 임베딩 및 요약 (Phase 2)
- 💾 결과 저장 및 검색 - 키워드 검색: MeiliSearch, 벡터 검색: Qdrant

구성 요소
컴포넌트	역할
FastAPI (app/main.py)	사용자 요청 처리, 작업 큐잉, 검색 인터페이스
Celery (app/worker.py)	Redis 작업 수신, 비동기 문서 처리
AI 모듈 (app/pipeline/)	OCR, 분류, 추출 등 AI 로직 수행
Redis	Celery 브로커
MeiliSearch	키워드 검색 및 필터링
Qdrant	의미 기반 벡터 검색 (Phase 2)
Flower	Celery 작업 모니터링 UI
vLLM / Ollama	LLM 서빙 엔진 (Phase 2)
프로젝트 구조
42_Asia_Hackathon-backend/
├── app/
│   ├── pipeline/
│   │   ├── ocr_module.py
│   │   ├── classification_module.py
│   │   └── extraction_module.py
│   ├── config.py
│   ├── logger_config.py
│   ├── main.py
│   ├── schemas.py
│   └── worker.py
├── Dockerfile
├── docker-compose.yml
├── docker-compose.monitoring.yml
├── prometheus.yml
└── requirements.txt


---

## 🏗️ 시스템 아키텍처

```mermaid
graph LR
    Client --> FastAPI_Server
    FastAPI_Server --> Redis_Broker
    FastAPI_Server --> MeiliSearch
    FastAPI_Server --> Qdrant
    Celery_Worker --> Redis_Broker
    Celery_Worker --> AI_Module
    Celery_Worker --> LLM_Server
    Celery_Worker --> MeiliSearch
    Celery_Worker --> Qdrant
