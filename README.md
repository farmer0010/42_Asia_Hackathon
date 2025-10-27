# 🧠 42 Asia Hackathon - 지능형 문서 처리 AI 엔진 (Backend)

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95-green?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-20.10-blue?logo=docker&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.3-yellow?logo=celery&logoColor=black)
![MeiliSearch](https://img.shields.io/badge/MeiliSearch-1.2-orange)
![Qdrant](https://img.shields.io/badge/Qdrant-0.11-red)

---

## 🎯 프로젝트 개요

**2025 아시아 해커톤 출품작**으로, 업로드된 문서 이미지(PDF/JPG/PNG)에 대해 **OCR, 문서 분류, 정보 추출, 검색**까지 지원하는 지능형 문서 처리 AI 엔진 백엔드입니다.  

### 핵심 기능

- 📝 **OCR (텍스트 추출)** - `PaddleOCR`  
- 📂 **문서 분류** - `DistilBERT` 기반 자동 분류 (invoice, receipt 등)  
- 🔍 **정보 추출 (Extraction)** - `BERT-NER` 기반 핵심 정보 구조화 (금액, 날짜, 회사명)  
- 🤖 **의미 기반 검색 / 요약** - LLM(`vLLM` / `Ollama`) 활용 벡터 임베딩 및 요약 (Phase 2)  
- 💾 **결과 저장 및 검색** - 키워드 검색: `MeiliSearch`, 벡터 검색: `Qdrant`  

---

## 🏗️ 시스템 아키텍처

```mermaid
graph LR
    A[사용자/클라이언트] -- HTTP Request --> B(FastAPI 서버)
    B -- 작업 요청 --> C{Redis (Celery Broker)}
    B -- 검색 요청 --> D(MeiliSearch)
    B -- 시맨틱 검색 --> E(Qdrant)
    F(Celery 워커) -- 작업 수신 --> C
    F -- 문서 처리 --> G[AI 모듈 (OCR/분류/추출)]
    F -- LLM 호출 --> H(vLLM/Ollama 서버)
    F -- 결과 저장 --> D
    F -- 벡터 저장 --> E

    style F fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#ccf,stroke:#333,stroke-width:2px
    style H fill:#ccf,stroke:#333,stroke-width:2px
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

📂 프로젝트 구조
arduino
코드 복사
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
🚀 빠른 시작
1️⃣ 사전 준비
Docker & Docker Compose 설치 (Docker Desktop 권장)

2️⃣ 프로젝트 클론
bash
코드 복사
git clone <repository_url>
cd 42_Asia_Hackathon-backend
3️⃣ Docker Compose 실행
bash
코드 복사
docker-compose up --build -d
4️⃣ 서비스 확인
API (Swagger UI): http://localhost:8000/docs

MeiliSearch: http://localhost:7700 (/health)

Qdrant: http://localhost:6333/dashboard

Flower: http://localhost:5555

Redis: 포트 6379

5️⃣ 모니터링 (선택)
bash
코드 복사
docker-compose -f docker-compose.monitoring.yml up -d
Prometheus: http://localhost:9090

Grafana: http://localhost:3000 (admin/admin)

cAdvisor: http://localhost:8080

6️⃣ 종료
bash
코드 복사
docker-compose down
docker-compose -f docker-compose.monitoring.yml down
⚙️ API 엔드포인트
Method	Endpoint	설명
GET	/	루트, 환영 메시지
POST	/uploadfile/	단일 파일 업로드, Celery 작업 ID 반환
POST	/uploadfiles/	다중 파일 업로드, 작업 ID 리스트 반환
GET	/tasks/{task_id}	작업 상태/결과 조회
GET	/search?q={query}&doc_type={type}	MeiliSearch 키워드 검색 및 필터링
GET	/hybrid_search?q={query}	(Phase 2) 키워드 + 시맨틱 검색 통합 (비활성화)

🧪 테스트 방법
Swagger UI: http://localhost:8000/docs

Postman / Insomnia: API 테스트

Celery 작업 모니터링: http://localhost:5555

🛠️ 기술 스택
영역	기술
웹 프레임워크	FastAPI
비동기 큐	Celery, Redis
OCR	PaddleOCR
문서 분류	Transformers (DistilBERT)
검색	MeiliSearch
벡터 검색	Qdrant
컨테이너화	Docker, Docker Compose
모니터링	Prometheus, Grafana, cAdvisor
LLM 서빙	vLLM / Ollama (Phase 2)
