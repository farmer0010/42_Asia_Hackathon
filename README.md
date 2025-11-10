# 🏆 42 Asia Hackathon - 문서 처리 시스템

> **AI 기반 문서 자동 처리 시스템**  
> OCR + 분류 + LLM 추출 + PII 탐지

---

## ⚡ Quick Start

### 🧪 빠른 테스트 (훈련 없이)

**분류 모델 학습 없이 바로 전체 파이프라인 테스트!**

```bash
# 1. 설치
source venv/bin/activate
pip install -r requirements.txt
brew install ollama
ollama pull qwen2.5:7b

# 2. Ollama 실행
ollama serve &

# 3. 테스트 실행 (자동으로 OCR → 타입 할당 → LLM 처리)
scripts/test_pipeline_notrain.sh
```

**결과:** `data/output/test_final_results.json` (2-4분)

---

### 🔥 전체 실행 (분류 모델 포함)

**분류 모델을 학습한 후 실행:**

```bash
# 1. Groundtruth 파일 병합
python3 scripts/merge_groundtruth.py

# 2. 분류 모델 학습 (해커톤 당일)
python src/classification/trainer.py \
  --groundtruth config/groundtruth_merged.json \
  --ocr data/output/training_ocr.json \
  --output data/models/classifier

# 3. 전체 파이프라인 실행
scripts/run_local.sh
```

**결과:** `data/output/final_results.json`

---

### 🐳 Docker 실행 (GPU 서버)

```bash
# 입력 준비
mkdir -p data/input && cp documents/* data/input/

# 실행 (docker/ 폴더에서)
cd docker && docker compose up
```

**결과:** `data/output/final_results.json` (1-2분, NVIDIA GPU)

---

## 📚 문서

- **📘 [완전 가이드](docs/가이드.md)** - 모든 정보 (필독!)
  - Quick Start
  - 실행 방법 (로컬/Docker)
  - 환경 설정
  - 모듈 설명
  - 해커톤 워크플로우
  - FAQ

- **📖 [기술 문서](docs/MY_PART_ARCHITECTURE.md)** - 상세 아키텍처

- **🎤 [발표 자료](docs/TEAM_PRESENTATION.md)** - 팀 프레젠테이션

---

## 🎯 시스템 구조

```
이미지/PDF
    ↓
OCR-VL (PaddleOCR) - 텍스트 + 레이아웃
    ↓
분류 (DistilBERT) - 5가지 문서 타입
    ↓
LLM (Qwen2.5) - 추출 + 요약 + PII
    ↓
JSON 출력
```

**지원 문서:**
- invoice, receipt, resume, report, contract

**주요 기능:**
- 텍스트 추출 (OCR 91%+ 신뢰도)
- 자동 분류 (DistilBERT 학습)
- 구조화 데이터 추출 (LLM)
- PII 탐지 (Regex + LLM)
- 문서 요약 (report/contract)

---

## 🚀 성능

| 환경 | 속도 | GPU |
|------|------|-----|
| 로컬 (M1) | 20-40초/문서 | Metal ✅ |
| Docker (NVIDIA) | 10-20초/문서 | CUDA ✅ |

---

## 🛠️ 기술 스택

- **OCR**: PaddleOCR 2.8.1
- **분류**: DistilBERT (fine-tuned)
- **LLM**: Qwen2.5:7b (Ollama)
- **Framework**: PyTorch, Transformers

---

## 📂 프로젝트 구조

```
42_Asia_Hackathon/
├── srcs/                    # OCR & 분류
├── llm_service/             # LLM 처리
├── input/                   # 입력
├── output/                  # 출력
├── models/                  # 학습 모델
├── run_local.sh             # 로컬 실행
├── docker-compose.yml       # Docker 설정
└── docs/가이드.md           # 완전 가이드
```

---

## 📖 자세한 내용

**[docs/가이드.md](docs/가이드.md)** 참고!

---

**🚀 Happy Hacking!**
