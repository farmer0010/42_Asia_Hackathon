# 42 Asia Hackathon - 지능형 문서 처리 AI 엔진 (백엔드) 🧠

## 🎯 프로젝트 개요

이 프로젝트는 **2025 아시아 해커톤** 출품을 위한 **지능형 문서 처리 AI 엔진의 백엔드 서버**입니다. FastAPI를 기반으로 구축되었으며, 업로드된 문서 이미지(PDF/JPG/PNG)에 대해 다음과 같은 기능을 비동기적으로 처리하고 결과를 저장/검색하는 API를 제공합니다:

1.  **OCR (텍스트 추출)** - `PaddleOCR`을 사용하여 문서 내 텍스트 추출
2.  **문서 분류 (Classification)** - `DistilBERT` 모델을 사용하여 문서 종류 자동 판단 (예: invoice, receipt)
3.  **(향후) 정보 추출 (Extraction)** - `BERT-NER` 등을 활용하여 문서 내 핵심 정보 구조화 (예: 금액, 날짜, 회사명)
4.  **(향후) 의미 기반 검색 및 요약** - LLM(`vLLM` 또는 `Ollama`)을 활용한 벡터 임베딩 생성 및 문서 요약
5.  **결과 저장 및 검색** - 처리된 텍스트와 메타데이터는 `MeiliSearch`에, 벡터 임베딩은 `Qdrant`에 저장하여 키워드 및 시맨틱 검색 지원

### 💡 아키텍처 철학

Python의 방대한 AI 생태계와 FastAPI의 빠른 개발 속도를 활용하는 동시에, Celery, MeiliSearch, Qdrant 등 각 분야 최고의 오픈소스 도구를 조합하여 '개발 속도'와 '운영 성능'의 최적 균형을 맞추는 것을 목표로 합니다.

---

## 🏗️ 시스템 구조 (한눈에)

```mermaid
graph LR
    A[사용자/클라이언트] -- HTTP Request --> B(FastAPI API 서버);
    B -- 작업 요청 --> C{Redis (Celery Broker)};
    B -- 검색 요청 --> D(MeiliSearch);
    B -- (시맨틱 검색) --> E(Qdrant);
    F(Celery 워커) -- 작업 수신 --> C;
    F -- 문서 처리 --> G[AI 모듈 (OCR/분류/추출)];
    F -- (LLM 호출) --> H(vLLM/Ollama 서버);
    F -- 결과 저장 --> D;
    F -- (벡터 저장) --> E;

    style F fill:#f9f,stroke:#333,stroke-width:2px;
    style G fill:#ccf,stroke:#333,stroke-width:2px;
    style H fill:#ccf,stroke:#333,stroke-width:2px;
FastAPI 서버 (app/main.py): 사용자 요청 처리, 작업 큐잉, 검색 인터페이스 제공

Celery 워커 (app/worker.py): Redis로부터 작업(문서 처리)을 받아 비동기적으로 실행

AI 모듈 (app/pipeline/): OCR, 분류, 추출 등 실제 AI 로직 수행

Redis: Celery의 메시지 브로커 및 백엔드로 사용

MeiliSearch: 키워드 검색 및 필터링을 위한 검색 엔진

Qdrant: (Phase 2) 의미 기반 검색을 위한 벡터 데이터베이스

Flower: Celery 작업 모니터링 UI

(향후) vLLM/Ollama: LLM 서빙 엔진

📂 프로젝트 파일 구조
42_Asia_Hackathon-backend/
├── app/                      # FastAPI 애플리케이션 코드
│   ├── pipeline/             # AI 처리 파이프라인 모듈
│   │   ├── ocr_module.py
│   │   └── classification_module.py
│   │   └── (extraction_module.py)
│   ├── config.py             # 환경변수 및 설정 관리
│   ├── logger_config.py      # 로깅 설정
│   ├── main.py               # FastAPI 앱 정의 및 API 엔드포인트
│   ├── schemas.py            # Pydantic 모델 (데이터 유효성 검사)
│   └── worker.py             # Celery 작업 정의
│
├── .idea/                    # (IDE 설정 파일 - Git 무시됨)
├── Dockerfile                # Docker 이미지 빌드 설정 (멀티스테이지 최적화)
├── docker-compose.yml        # 서비스 실행 환경 정의 (API, Worker, DB 등)
├── docker-compose.monitoring.yml # 모니터링 스택 (Prometheus, Grafana)
├── prometheus.yml            # Prometheus 설정
└── requirements.txt          # Python 라이브러리 의존성 목록
🚀 빠른 시작 가이드
이 프로젝트는 Docker Compose를 사용하여 모든 서비스(API 서버, Celery 워커, Redis, MeiliSearch, Qdrant, Flower)를 한 번에 실행합니다.

0단계: 사전 준비
Docker & Docker Compose 설치: 시스템에 Docker와 Docker Compose가 설치되어 있어야 합니다. (Docker Desktop 권장)

1단계: 프로젝트 클론 및 이동
Bash

# (아직 클론하지 않았다면)
# git clone <repository_url>
cd 42_Asia_Hackathon-backend
2단계: Docker Compose 실행 (빌드 포함)
Bash

# 모든 서비스 빌드 및 백그라운드 실행 (-d 옵션)
docker-compose up --build -d
--build: Dockerfile이나 코드가 변경되었을 때 이미지를 새로 빌드합니다.

-d: 컨테이너를 백그라운드에서 실행합니다. (로그를 보려면 -d 옵션 제거)

3단계: 서비스 확인
API 서버 (Swagger UI): 웹 브라우저에서 http://localhost:8000/docs 접속

MeiliSearch: http://localhost:7700 (상태 확인: /health)

Qdrant: http://localhost:6333/dashboard

Flower (Celery Monitor): http://localhost:5555

Redis: (보통 직접 접속 필요 없음, 포트: 6379)

4단계: 모니터링 스택 실행 (선택 사항)
Bash

# 별도의 터미널에서 실행
docker-compose -f docker-compose.monitoring.yml up -d
Prometheus: http://localhost:9090

Grafana: http://localhost:3000 (초기 로그인: admin/admin)

cAdvisor: http://localhost:8080

5단계: 종료
Bash

# 모든 서비스 중지 및 컨테이너/네트워크 제거
docker-compose down

# 모니터링 스택 종료
docker-compose -f docker-compose.monitoring.yml down
⚙️ 주요 API 엔드포인트 (app/main.py)
GET /: 루트 경로, 간단한 환영 메시지 반환.

POST /uploadfile/: 단일 파일 업로드 받아 Celery 작업 생성 후 작업 ID 반환.

POST /uploadfiles/: 여러 파일 업로드 받아 각각 Celery 작업 생성 후 작업 ID 리스트 반환.

GET /tasks/{task_id}: 주어진 작업 ID의 상태(PENDING, SUCCESS, FAILURE 등)와 결과 조회.

GET /search?q={query}&doc_type={type}: MeiliSearch를 이용한 키워드 검색 및 doc_type 필터링 수행.

(비활성화) GET /hybrid_search?q={query}: (Phase 2) 키워드 검색(MeiliSearch)과 시맨틱 검색(Qdrant) 결과 통합 반환.

자세한 사용법은 http://localhost:8000/docs의 Swagger UI를 참고하세요.

🧪 테스트 방법
Swagger UI 사용: http://localhost:8000/docs에서 직접 파일을 업로드하고 검색 API를 테스트할 수 있습니다.

API 테스트 도구: Postman, Insomnia 등을 사용하여 각 엔드포인트에 요청을 보내고 응답을 확인할 수 있습니다.

Celery 작업 확인: http://localhost:5555 (Flower)에서 작업 상태(성공/실패) 및 로그를 모니터링할 수 있습니다.

🛠️ 주요 기술 스택
웹 프레임워크: FastAPI

비동기 작업 큐: Celery, Redis

OCR: PaddleOCR

AI 모델 (분류): Transformers (DistilBERT)

키워드 검색: MeiliSearch

벡터 검색: Qdrant

컨테이너화: Docker, Docker Compose

모니터링: Prometheus, Grafana, cAdvisor

(향후) LLM 서빙: vLLM 또는 Ollama
