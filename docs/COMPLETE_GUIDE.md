# 📘 OCR & 문서 분류 시스템 - 완전 가이드

> **작성일:** 2025-11-01  
> **담당:** OCR & 분류 파트  
> **버전:** 2.0 (PaddleOCR-VL 기반)

---

## 📑 목차

1. [환경 설정](#1-환경-설정)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [데이터 플로우](#3-데이터-플로우)
4. [각 모듈 상세 설명](#4-각-모듈-상세-설명)
5. [테스트 방법](#5-테스트-방법)
6. [해커톤 당일 워크플로우](#6-해커톤-당일-워크플로우)
7. [LLM 팀 인수인계](#7-llm-팀-인수인계)
8. [기술적 배경](#8-기술적-배경)
9. [FAQ](#9-faq)

---

## 1. 환경 설정

### 1.1 Python 가상환경 생성

```bash
# 프로젝트 디렉토리로 이동
cd /Users/ahnhyunjun/Desktop/42_Asia_Hackathon

# Python 3.11로 가상환경 생성
python3.11 -m venv venv

# 가상환경 활성화 (Mac/Linux)
source venv/bin/activate

# 활성화 확인
which python
# 출력: /Users/ahnhyunjun/Desktop/42_Asia_Hackathon/venv/bin/python
```

### 1.2 패키지 설치

```bash
# pip 업그레이드
pip install --upgrade pip

# requirements.txt로 일괄 설치
pip install -r requirements.txt

# 설치 시간: 약 5-10분
```

**주요 패키지:**
- `paddleocr` - OCR 엔진
- `torch`, `transformers` - 딥러닝 프레임워크
- `opencv-python` - 이미지 처리
- `pandas`, `numpy` - 데이터 처리

### 1.3 설치 확인

```bash
# PaddleOCR 확인
python -c "from paddleocr import PaddleOCR; print('✓ PaddleOCR OK')"

# PyTorch 확인
python -c "import torch; print('✓ PyTorch OK')"

# Transformers 확인
python -c "from transformers import DistilBertTokenizer; print('✓ Transformers OK')"

# 모든 모듈 확인
python -c "
import sys
sys.path.append('srcs')
from ocr_vl_module import OCRVLModule
from classification_module import DocumentClassifier
print('✓ All modules OK!')
"
```

---

## 2. 프로젝트 구조

### 2.1 디렉토리 구조

```
42_Asia_Hackathon/
├── srcs/                           # 메인 소스 코드
│   ├── ocr_vl_module.py           # OCR-VL 모듈
│   ├── batch_ocr_vl.py            # 배치 OCR 처리
│   ├── classification_module.py   # 분류 모듈
│   ├── train_classifier.py        # 학습 스크립트
│   └── predict_ocr_classify.py    # 최종 파이프라인
│
├── outputs/                        # 결과 파일
│   ├── test_batch.json            # 테스트 OCR 결과
│   ├── training_ocr_vl.json       # Training set OCR (해커톤 당일)
│   └── predictions_final.json     # 최종 예측 결과 (LLM에게 전달)
│
├── models/                         # 학습된 모델
│   └── classifier/                # 분류 모델 (해커톤 당일 생성)
│
├── test_samples/                   # 테스트용 샘플
│   ├── invoice1.jpg
│   ├── sample1.jpg
│   └── ...
│
├── venv/                          # 가상환경
├── requirements.txt               # 패키지 목록
└── docs/
    ├── COMPLETE_GUIDE.md          # 이 파일
    └── MY_PART_ARCHITECTURE.md    # 기술 문서
```

### 2.2 핵심 파일 설명

| 파일 | 역할 | 입력 | 출력 |
|------|------|------|------|
| `ocr_vl_module.py` | OCR + 레이아웃 분석 | 이미지 | 텍스트 + 레이아웃 JSON |
| `batch_ocr_vl.py` | 여러 파일 OCR 처리 | 디렉토리 | JSON 파일 |
| `classification_module.py` | 문서 분류 모델 | 텍스트 | 문서 타입 |
| `train_classifier.py` | 모델 학습 | OCR JSON + labels.csv | 학습된 모델 |
| `predict_ocr_classify.py` | OCR + 분류 통합 | 디렉토리 + 모델 | 최종 JSON |

---

## 3. 데이터 플로우

### 3.1 전체 파이프라인

```
┌─────────────────────────────────────────────────────────────┐
│                    Input: 이미지/PDF                         │
│          (invoice, receipt, resume, report, contract)       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 1: OCR-VL (PaddleOCR)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  • 텍스트 추출 (OCR)                                  │  │
│  │  • 레이아웃 분석:                                     │  │
│  │    - 제목 위치 (Y좌표 < 100)                        │  │
│  │    - 키-값 쌍 개수 ("Date:", "Total:" 등)           │  │
│  │    - 테이블 존재 여부                               │  │
│  │    - 텍스트 밀도 (줄 수 / 100)                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Output:                                                     │
│  {                                                           │
│    "full_text": "INVOICE\nABC Corp\nTotal: $1500...",      │
│    "layout": {                                              │
│      "title": "INVOICE",                                   │
│      "features": {                                         │
│        "has_table": true,                                  │
│        "num_key_value_pairs": 15,                         │
│        "text_density": 0.56                               │
│      }                                                     │
│    },                                                      │
│    "confidence": 0.97                                      │
│  }                                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           Step 2: Enhanced Text 생성                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  텍스트 + 레이아웃 정보 결합:                         │  │
│  │                                                        │  │
│  │  enhanced_text = full_text + layout_description       │  │
│  │                                                        │  │
│  │  "INVOICE                                             │  │
│  │   ABC Corp                                            │  │
│  │   Total: $1500                                        │  │
│  │   ...                                                 │  │
│  │                                                        │  │
│  │   [LAYOUT_INFO]                                       │  │
│  │   Title: INVOICE                                      │  │
│  │   Has_Table: True                                     │  │
│  │   Key_Value_Pairs: 15                                │  │
│  │   Text_Density: 0.56                                 │  │
│  │   [END_LAYOUT_INFO]"                                 │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│       Step 3: DistilBERT 문서 분류                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Tokenization (문자 → 숫자)                        │  │
│  │     enhanced_text → [101, 2024, 15641, ...]          │  │
│  │                                                        │  │
│  │  2. Model Inference (학습된 모델 사용)                │  │
│  │     Training set으로 학습된 가중치 적용               │  │
│  │                                                        │  │
│  │  3. Classification (5개 클래스 중 선택)               │  │
│  │     logits: [0.1, 9.8, 0.3, 0.2, 0.1]                │  │
│  │              ↓                                         │  │
│  │     softmax: [0.01, 0.96, 0.01, 0.01, 0.01]          │  │
│  │              ↓                                         │  │
│  │     argmax: 1 → "invoice" (96% 신뢰도)               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Output:                                                     │
│  {                                                           │
│    "doc_type": "invoice",                                   │
│    "confidence": 0.96                                       │
│  }                                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Step 4: 최종 JSON 생성                         │
│              (LLM 팀에게 전달)                              │
│                                                              │
│  {                                                           │
│    "filename": "invoice_001.jpg",                           │
│    "full_text_ocr": "INVOICE\nABC Corp\n...",              │
│    "ocr_confidence": 0.97,                                  │
│    "layout": {                                              │
│      "title": "INVOICE",                                   │
│      "features": {...}                                     │
│    },                                                       │
│    "classification": {                                      │
│      "doc_type": "invoice",                                │
│      "confidence": 0.96                                    │
│    }                                                        │
│  }                                                          │
│                                                              │
│  → LLM이 이 정보로:                                         │
│    • 구조화 데이터 추출 (vendor, amount, date)            │
│    • 요약 생성 (report/contract)                          │
│    • PII 탐지 (개인정보)                                   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 왜 레이아웃 정보가 중요한가?

**문제:** 텍스트만으로는 구분이 어려운 경우

```
Receipt:
  텍스트: "Total: 89.50 THB\nDate: 2025-01-01"
  레이아웃: Key_Value_Pairs=3, Text_Density=0.3
  → 간단하고 키-값 적음 = Receipt!

Invoice:
  텍스트: "Total: 8,480.00 USD\nDate: 2025-01-01"
  레이아웃: Key_Value_Pairs=26, Text_Density=0.67, Has_Table=True
  → 복잡하고 키-값 많음, 테이블 있음 = Invoice!
```

**효과:**
- 텍스트만 사용: 정확도 ~85%
- 텍스트 + 레이아웃: 정확도 ~95% (예상)

---

## 4. 각 모듈 상세 설명

### 4.1 OCR-VL Module (`ocr_vl_module.py`)

**역할:** 이미지에서 텍스트와 레이아웃 정보 추출

**핵심 기능:**

```python
class OCRVLModule:
    def __init__(self, use_gpu=False):
        """PaddleOCR 초기화"""
        self.ocr = PaddleOCR(
            use_angle_cls=True,  # 이미지 회전 보정
            lang='en',           # 영어
            use_gpu=use_gpu,     # GPU 사용 여부
            show_log=False
        )
    
    def process_document(self, image_path):
        """
        메인 처리 함수
        
        Returns:
            {
                "full_text": str,        # 전체 텍스트
                "layout": dict,          # 레이아웃 정보
                "confidence": float,     # OCR 신뢰도
                "processing_time": float # 처리 시간
            }
        """
```

**레이아웃 파싱 로직:**

```python
def _parse_layout(self, result):
    """
    좌표 기반 레이아웃 분석
    
    1. 제목 감지:
       - Y좌표 < 100 (상단)
       - 너비 > 150 (큰 텍스트)
       - 높이 > 15 (큰 폰트)
    
    2. 키-값 쌍 감지:
       - ':' 포함 (예: "Date: 2025-01-01")
       - 특정 키워드 포함 ('Date', 'Total', 'Invoice' 등)
    
    3. 테이블 감지:
       - 숫자가 많은 줄 비율 > 30%
    
    4. 텍스트 밀도:
       - 전체 줄 수 / 100
    """
```

### 4.2 Classification Module (`classification_module.py`)

**역할:** 문서 타입 분류 (5개 클래스)

**클래스 정의:**
```python
labels = ['invoice', 'receipt', 'resume', 'report', 'contract']
```

**학습 프로세스:**

```python
def train(self, labels_csv_path, ocr_results_path):
    """
    1. 데이터 로드:
       - labels.csv: filename, doc_type
       - ocr_results.json: OCR 결과
    
    2. 데이터 매칭:
       - CSV의 filename과 JSON의 키 매칭
       - OCR 텍스트 + 정답 레이블 조합
    
    3. Tokenization:
       - 텍스트 → 숫자 토큰 변환
       - 최대 512 토큰으로 제한
    
    4. 모델 학습:
       - DistilBERT 기반
       - 3 epochs (약 60분)
       - Batch size: 8
       - Learning rate: 2e-5
    
    5. 모델 저장:
       - models/classifier/ 에 저장
    """
```

**분류 과정:**

```python
def classify(self, text):
    """
    1. Tokenization:
       text → [101, 2024, 15641, ...]
    
    2. Model Forward Pass:
       tokens → logits [0.1, 9.8, 0.3, 0.2, 0.1]
    
    3. Softmax:
       logits → probabilities [0.01, 0.96, 0.01, 0.01, 0.01]
    
    4. Argmax:
       probabilities → class_id (1) → "invoice"
    
    5. Return:
       {
         "doc_type": "invoice",
         "confidence": 0.96
       }
    """
```

**왜 DistilBERT인가?**

| 특징 | 설명 |
|------|------|
| **경량** | BERT의 40% 크기 |
| **빠름** | 추론 속도 60% 향상 |
| **정확** | BERT 성능의 97% 유지 |
| **학습 가능** | Fine-tuning 쉬움 |

### 4.3 Batch Processing (`batch_ocr_vl.py`)

**역할:** 여러 파일을 한 번에 OCR 처리

**사용법:**
```bash
python srcs/batch_ocr_vl.py \
  --input training_set/documents \
  --output outputs/training_ocr_vl.json \
  --gpu
```

**처리 과정:**
1. 디렉토리 스캔 (jpg, png, pdf)
2. 각 파일 OCR 처리 (진행률 표시)
3. JSON 파일로 저장
4. 에러 파일 별도 저장

**출력 형식:**
```json
{
  "file1.jpg": {
    "full_text": "...",
    "layout": {...},
    "confidence": 0.97
  },
  "file2.jpg": {
    "full_text": "...",
    "layout": {...},
    "confidence": 0.95
  }
}
```

### 4.4 Prediction Pipeline (`predict_ocr_classify.py`)

**역할:** OCR + 분류를 통합한 최종 파이프라인

**사용법:**
```bash
python srcs/predict_ocr_classify.py \
  --input testing_set/documents \
  --classifier models/classifier \
  --output predictions_final.json \
  --gpu
```

**처리 단계:**
1. OCR-VL로 텍스트 + 레이아웃 추출
2. Enhanced text 생성 (텍스트 + 레이아웃 설명)
3. 분류 모델로 문서 타입 예측
4. 최종 JSON 생성 (LLM 팀에게 전달)

---

## 5. 테스트 방법

### 5.1 개별 모듈 테스트

#### **OCR-VL 모듈 테스트**

```bash
# 단일 파일 테스트
python srcs/ocr_vl_module.py

# 예상 출력:
# Quick test...
# ✓ Confidence: 99.15%
# ✓ Title: Receipt
# ✓ Text preview: Receipt...
```

**확인 사항:**
- ✅ 에러 없이 완료
- ✅ Confidence > 85%
- ✅ Title 제대로 감지
- ✅ 텍스트 추출 정상

#### **분류 모듈 테스트**

```bash
# 모듈 테스트
python srcs/classification_module.py

# 예상 출력:
# Test 1: Initializing classifier... ✓
# Test 2: Loading pretrained model... ✓
# Test 3: Testing classify() function... ✓
# Test 4: Memory usage... 645.97 MB
# All tests passed!
```

**확인 사항:**
- ✅ 초기화 성공
- ✅ 모델 로드 성공
- ✅ classify() 함수 작동
- ✅ 메모리 사용량 < 1GB

### 5.2 배치 처리 테스트

```bash
# test_samples로 OCR 배치 테스트
python srcs/batch_ocr_vl.py \
  --input test_samples \
  --output outputs/test_batch.json

# 예상 출력:
# Found 6 files
# Processing: 100%|████████| 6/6 [00:26<00:00]
# Total files: 6
# Successful: 6
# Average confidence: 91.61%
```

**출력 파일:** `outputs/test_batch.json`

**확인 사항:**
- ✅ 모든 파일 처리 성공
- ✅ 평균 신뢰도 > 85%
- ✅ JSON 파일 생성

### 5.3 통합 파이프라인 테스트

```bash
# OCR + 분류 통합 테스트 (분류 모델 없이)
python srcs/predict_ocr_classify.py \
  --input test_samples \
  --output outputs/test_predictions.json

# 예상 출력:
# ⚠️  No classifier specified. Will skip classification.
# Found 6 files
# Processing: 100%|████████| 6/6
# Successful: 6
# Average OCR confidence: 91.61%
```

**출력 파일:** `outputs/test_predictions.json`

**확인 사항:**
- ✅ OCR 처리 성공
- ✅ JSON 형식 올바름
- ✅ 모든 필드 존재

### 5.4 출력 파일 확인

```bash
# JSON 파일 미리보기
cat outputs/test_batch.json | head -50

# 또는 Python으로
python -c "
import json
with open('outputs/test_batch.json') as f:
    data = json.load(f)
    print(f'Total documents: {len(data)}')
    print(f'First file: {list(data.keys())[0]}')
    print(f'Keys: {list(data[list(data.keys())[0]].keys())}')
"
```

---

## 6. 해커톤 당일 워크플로우

### 6.1 사전 준비 체크리스트

```bash
# ✅ 가상환경 활성화
source venv/bin/activate

# ✅ 패키지 확인
python -c "from paddleocr import PaddleOCR; print('OK')"

# ✅ GPU 확인 (있으면)
python -c "import torch; print(f'GPU available: {torch.cuda.is_available()}')"

# ✅ 디렉토리 준비
mkdir -p outputs models
```

### 6.2 Phase 1: 데이터 수신 및 확인 (10분)

**데이터 구조:**
```
received_data/
├── training_set/
│   ├── documents/     # 500-1000개 문서
│   │   ├── doc001.jpg
│   │   ├── doc002.pdf
│   │   └── ...
│   └── labels.csv     # 정답 레이블
│
└── testing_set/
    └── documents/     # 100개 문서 (레이블 없음)
        ├── test001.jpg
        └── ...
```

**확인 명령어:**
```bash
# 1. 파일 개수 확인
ls training_set/documents | wc -l
ls testing_set/documents | wc -l

# 2. labels.csv 구조 확인
head training_set/labels.csv

# 예상 출력:
# filename,doc_type
# doc001.jpg,invoice
# doc002.pdf,receipt
# doc003.png,resume

# 3. 문서 타입 분포 확인
cut -d',' -f2 training_set/labels.csv | sort | uniq -c
```

### 6.3 Phase 2: Training Set OCR-VL (40-50분)

**명령어:**
```bash
python srcs/batch_ocr_vl.py \
  --input training_set/documents \
  --output outputs/training_ocr_vl.json \
  --gpu
```

**진행 과정:**
```
Initializing OCR-VL...
OCR ready!
Found 500 files

Processing: 100%|████████████| 500/500 [45:23<00:00, 5.45s/it]

============================================================
Processing Complete!
============================================================
Total files: 500
Successful: 497
Errors: 3

Average confidence: 93.2%
Average processing time: 5.4s

✓ Results saved to: outputs/training_ocr_vl.json
```

**이 동안 할 일:**
- ☕ 커피 마시기
- 📝 labels.csv 재확인
- 🤝 LLM 팀과 JSON 형식 최종 확인

**출력 파일:** `outputs/training_ocr_vl.json`
- **크기:** 약 10-50MB
- **형식:** `{filename: {full_text, layout, confidence}}`
- **용도:** 분류 모델 학습

### 6.4 Phase 3: 분류 모델 학습 (60분)

**명령어:**
```bash
python srcs/train_classifier.py \
  --labels training_set/labels.csv \
  --ocr outputs/training_ocr_vl.json \
  --output models/classifier
```

**진행 과정:**
```
Train Classification Model

Input files:
  Labels CSV: training_set/labels.csv
  OCR Results: outputs/training_ocr_vl.json
  Output dir: models/classifier

All input files found!

Training Classification Model

Step 1: Loading data...
Loaded 500 labels from CSV
Loaded 500 OCR results

Step 2: Preparing training data...
Prepared 497 training samples
Skipped 3 samples due to errors

Step 3: Creating dataset...
Dataset created with 497 samples

Step 4: Tokenizing text...
Tokenization complete!

Step 5: Initializing model...
Model initialized for 5 classes

Step 6: Configuring training...
Training configuration set

Step 7: Starting training...
This may take 30-60 minutes...

Epoch 1/3:
  Step 10: loss=0.892
  Step 20: loss=0.745
  ...
  Epoch 1 complete: avg_loss=0.623

Epoch 2/3:
  Step 10: loss=0.234
  ...
  Epoch 2 complete: avg_loss=0.189

Epoch 3/3:
  Step 10: loss=0.089
  ...
  Epoch 3 complete: avg_loss=0.067

Training complete!

Step 8: Saving model...
Model saved to models/classifier

============================================================
Training Complete!
============================================================
```

**좋은 신호:**
- ✅ Loss 감소: 0.8 → 0.2 → 0.08
- ✅ 에러 없이 완료
- ✅ 모델 저장 성공

**나쁜 신호:**
- ❌ Loss 증가하거나 변동 심함
- ❌ NaN 에러 발생
- → Learning rate 조정 필요

**출력 파일:** `models/classifier/`
- `config.json` - 모델 설정
- `pytorch_model.bin` - 학습된 가중치
- `tokenizer_config.json` - 토크나이저 설정

### 6.5 Phase 4: Testing Set 처리 (20-30분)

**명령어:**
```bash
python srcs/predict_ocr_classify.py \
  --input testing_set/documents \
  --classifier models/classifier \
  --output predictions_final.json \
  --gpu
```

**진행 과정:**
```
Initializing OCR-VL...
Loading classifier from models/classifier...
Modules ready!

Found 100 files

Processing: 100%|████████████| 100/100 [28:45<00:00, 17.3s/it]

============================================================
Processing Complete!
============================================================
Total files: 100
Successful: 98
Errors: 2

Average OCR confidence: 94.3%
Average processing time: 17.2s

Document types:
  invoice: 45
  receipt: 32
  resume: 15
  report: 6

Average classification confidence: 94.8%

✓ Results saved to: predictions_final.json

💡 Next step:
  → 이 파일을 LLM 팀에게 전달하세요!
============================================================
```

**출력 파일:** `predictions_final.json`

**형식:**
```json
[
  {
    "filename": "test001.jpg",
    "full_text_ocr": "COMMERCIAL INVOICE\nABC Exports...",
    "ocr_confidence": 0.97,
    "layout": {
      "title": "COMMERCIAL INVOICE",
      "features": {
        "has_table": true,
        "num_key_value_pairs": 26,
        "text_density": 0.56
      }
    },
    "classification": {
      "doc_type": "invoice",
      "confidence": 0.96
    },
    "processing_time": 17.3
  },
  ...
]
```

### 6.6 Phase 5: 검증 및 제출 (10분)

```bash
# 1. 파일 개수 확인
python -c "
import json
with open('predictions_final.json') as f:
    data = json.load(f)
    print(f'Total predictions: {len(data)}')
"

# 2. 샘플 확인
python -c "
import json
with open('predictions_final.json') as f:
    data = json.load(f)
    print(json.dumps(data[0], indent=2)[:500])
"

# 3. JSON 검증
python -m json.tool predictions_final.json > /dev/null && echo "✓ Valid JSON"

# 4. 문서 타입 분포
python -c "
import json
from collections import Counter
with open('predictions_final.json') as f:
    data = json.load(f)
    types = [d['classification']['doc_type'] for d in data]
    for dtype, count in Counter(types).items():
        print(f'{dtype}: {count}')
"

# 5. 백업
cp predictions_final.json predictions_backup_$(date +%H%M).json

# 6. LLM 팀에게 전달!
```

---

## 7. LLM 팀 인수인계

### 7.1 전달 파일

**파일명:** `predictions_final.json`

**위치:** 프로젝트 루트 디렉토리

**형식:** JSON Array (리스트)

### 7.2 JSON 구조 설명

```json
[
  {
    // 기본 정보
    "filename": "test001.jpg",           // 원본 파일명
    
    // OCR 결과
    "full_text_ocr": "전체 텍스트...",   // 추출된 모든 텍스트
    "ocr_confidence": 0.97,              // OCR 신뢰도 (0-1)
    
    // 레이아웃 정보
    "layout": {
      "title": "COMMERCIAL INVOICE",   // 감지된 제목
      "sections": [                     // 섹션 정보 (선택)
        {
          "type": "key_value",
          "text": "Date: 2025-01-01"
        }
      ],
      "features": {
        "has_table": true,               // 테이블 존재 여부
        "num_key_value_pairs": 26,       // 키-값 쌍 개수
        "text_density": 0.56,            // 텍스트 밀도 (0-1)
        "total_lines": 56                // 총 줄 수
      }
    },
    
    // 분류 결과
    "classification": {
      "doc_type": "invoice",            // 문서 타입 (5개 중 1개)
      "confidence": 0.96                // 분류 신뢰도 (0-1)
    },
    
    // 메타데이터
    "processing_time": 17.3             // 처리 시간 (초)
  }
]
```

### 7.3 필드별 설명

| 필드 | 타입 | 설명 | 용도 |
|------|------|------|------|
| `filename` | string | 원본 파일명 | 결과 매칭 |
| `full_text_ocr` | string | OCR 텍스트 | LLM 입력 (메인) |
| `ocr_confidence` | float | OCR 신뢰도 | 품질 판단 |
| `layout.title` | string | 제목 | 컨텍스트 |
| `layout.features` | object | 레이아웃 특징 | 구조 이해 |
| `classification.doc_type` | string | 문서 타입 | 추출 전략 결정 |
| `classification.confidence` | float | 분류 신뢰도 | 신뢰성 판단 |

### 7.4 LLM 팀이 해야 할 일

#### **입력:** `predictions_final.json`

#### **작업:**

**1. 구조화 데이터 추출**

```python
# 문서 타입별 추출 필드

invoice:
  - vendor (회사명)
  - invoice_number (인보이스 번호)
  - invoice_date (날짜)
  - total_amount (총액)
  - currency (통화)

receipt:
  - store (상점명)
  - date (날짜)
  - total (총액)
  - currency (통화)

resume:
  - name (이름)
  - experience (경력)
  - education (학력)
  - skills (기술)

report:
  - title (제목)
  - date (날짜)
  - key_findings (핵심 내용)

contract:
  - parties (계약 당사자)
  - effective_date (시작일)
  - key_terms (주요 조항)
```

**2. 보너스 기능**

- **요약 생성:** report, contract의 경우 2-3문장 요약
- **PII 탐지:** 이름, 주소, 전화번호, ID 번호 등

#### **출력:** `final_results.json`

```json
[
  {
    "filename": "test001.jpg",
    "doc_type": "invoice",
    
    // OCR 파트에서 제공한 정보
    "full_text_ocr": "...",
    "classification": {...},
    
    // LLM 파트에서 추가한 정보
    "extracted_data": {
      "vendor": "ABC Exports Ltd.",
      "invoice_date": "2025-01-01",
      "total_amount": 1500.00,
      "currency": "USD"
    },
    "summary": null,  // invoice는 요약 불필요
    "pii_detected": [
      {
        "type": "ADDRESS",
        "text": "123 Business Street",
        "context": "Vendor address"
      }
    ]
  }
]
```

### 7.5 주의사항

**1. OCR 오류 처리**

```python
# full_text_ocr에 오타가 있을 수 있음
"Ihe Bill" → "The Bill"  # LLM이 문맥으로 수정

# ocr_confidence가 낮으면 더 조심스럽게
if ocr_confidence < 0.85:
    # 추출 결과를 더 신중하게 검증
```

**2. 분류 신뢰도 활용**

```python
# classification.confidence가 낮으면
if classification_confidence < 0.80:
    # 문서 타입이 불확실함
    # 텍스트를 더 자세히 분석
    # 또는 여러 타입의 필드를 모두 시도
```

**3. 레이아웃 정보 활용**

```python
# layout.features 활용 예시
if layout["features"]["has_table"]:
    # 테이블이 있으면 구조화된 데이터 추출 유리
    
if layout["features"]["num_key_value_pairs"] > 15:
    # 키-값 쌍이 많으면 invoice 가능성 높음
    # "Total:", "Date:" 같은 키워드 주변 탐색
```

### 7.6 테스트 방법 (LLM 팀용)

```python
# 샘플 1개로 테스트
import json

with open('predictions_final.json') as f:
    data = json.load(f)
    sample = data[0]
    
    print(f"Filename: {sample['filename']}")
    print(f"Doc type: {sample['classification']['doc_type']}")
    print(f"Text preview: {sample['full_text_ocr'][:200]}")
    
    # LLM 처리
    result = your_llm_function(sample)
    print(f"Extracted: {result}")
```

---

## 8. 기술적 배경

### 8.1 왜 PaddleOCR-VL인가?

#### **기존 방식의 문제점:**

```
기존: PaddleOCR (텍스트만)
  - 텍스트: "Total: 1500 USD"
  - 위치 정보: 없음
  - 구조 정보: 없음
  → 분류 정확도: ~85%
```

#### **PaddleOCR-VL의 장점:**

```
개선: PaddleOCR-VL (텍스트 + 레이아웃)
  - 텍스트: "Total: 1500 USD"
  - 위치: (100, 450) - 하단
  - 구조: Key-value 쌍, 테이블 근처
  → 분류 정확도: ~95% (예상)
```

**구체적 이점:**

1. **레이아웃 분석**
   - 제목 위치 (상단/중앙)
   - 테이블 존재 여부
   - 텍스트 밀도

2. **구조 이해**
   - 키-값 쌍 개수
   - 섹션 구분
   - 복잡도 파악

3. **분류 개선**
   - Receipt vs Invoice 구분
   - Form vs Resume 구분
   - 복잡한 문서 처리

### 8.2 DistilBERT 학습 원리

#### **Step 1: 데이터 준비**

```
Training Set:
  doc001.jpg → OCR → "INVOICE ABC Corp Total 1500" → Label: invoice
  doc002.jpg → OCR → "Receipt Store Date Total 89" → Label: receipt
  doc003.pdf → OCR → "Resume John Smith MIT 5 yrs" → Label: resume
  ...
  (500-1000개)
```

#### **Step 2: 학습 과정**

```python
# Epoch 1: 모델이 패턴 학습 시작
"INVOICE ... Total" → 80% invoice (아직 불확실)
"Receipt ... Date"  → 60% receipt

# Epoch 2: 패턴 강화
"INVOICE ... Total" → 92% invoice (더 확신)
"Receipt ... Date"  → 85% receipt

# Epoch 3: 패턴 정교화
"INVOICE ... Total" → 96% invoice (확실)
"Receipt ... Date"  → 93% receipt
```

#### **Step 3: 가중치 업데이트**

```
초기 가중치 (랜덤):
  "INVOICE" → [0.2, 0.2, 0.2, 0.2, 0.2] (균등)

학습 후 가중치:
  "INVOICE" → [9.5, 0.3, 0.1, 0.1, 0.0]
               invoice^^ 가 높음!
  
  "Receipt" → [0.2, 8.7, 0.4, 0.2, 0.5]
               receipt^^ 가 높음!
```

### 8.3 Enhanced Text의 역할

#### **일반 텍스트:**
```
"Commercial Invoice
ABC Exports
Total: $13,000"
```

#### **Enhanced Text (텍스트 + 레이아웃):**
```
"Commercial Invoice
ABC Exports
Total: $13,000

[LAYOUT_INFO]
Title: Commercial Invoice
Has_Table: True
Key_Value_Pairs: 26
Text_Density: 0.56
[END_LAYOUT_INFO]"
```

**효과:**
- 모델이 "많은 키-값 쌍 = Invoice" 패턴 학습
- 모델이 "테이블 있음 = Invoice/Receipt" 패턴 학습
- 텍스트만으로 애매한 경우 레이아웃으로 결정

### 8.4 분류 정확도가 어떻게 90%+가 되는가?

#### **학습 과정:**

```
Training Set: 500개 문서

Invoice 150개:
  - 공통점: "Invoice", "Total", "Payment", 키-값 많음, 테이블
  - 모델이 이 패턴 학습

Receipt 150개:
  - 공통점: "Receipt", "Total", 간단, 키-값 적음
  - 모델이 이 패턴 학습

Resume 100개:
  - 공통점: "Experience", "Education", 이름, 날짜
  - 모델이 이 패턴 학습
  
Report 50개:
Contract 50개:
  - 각각의 패턴 학습
```

#### **테스트 시:**

```
새 문서: "INVOICE ABC Corp Total 5000"

모델 추론:
  1. "INVOICE" 발견 → invoice 점수 +3
  2. "Total" 발견 → invoice 점수 +2
  3. 키-값 25개 → invoice 점수 +2
  4. 테이블 있음 → invoice 점수 +1
  
  최종 점수:
    invoice: 8
    receipt: 2
    resume: 0
    report: 1
    contract: 0
  
  → Softmax → 96% invoice
```

#### **일반화:**

```
학습에 없던 새 Invoice:
  - "COMMERCIAL INVOICE" (학습 시 못 본 단어)
  - 하지만 "Total", "Payment", 키-값 많음
  → 여전히 invoice로 분류 (패턴이 유사)
```

---

## 9. FAQ

### 9.1 개발/환경

**Q: GPU 없으면 어떻게 하나요?**

A: `--gpu` 옵션만 제거하면 됩니다. CPU로도 작동하지만 2-3배 느립니다.
```bash
# GPU 있으면
python srcs/batch_ocr_vl.py --input ... --output ... --gpu

# GPU 없으면
python srcs/batch_ocr_vl.py --input ... --output ...
```

**Q: 가상환경이 안 활성화되는데요?**

A: 경로 확인 후 재생성:
```bash
# 기존 venv 삭제
rm -rf venv

# 새로 생성
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Q: import 에러가 나요.**

A: sys.path 추가:
```python
import sys
sys.path.append('srcs')
from ocr_vl_module import OCRVLModule
```

### 9.2 OCR 관련

**Q: OCR 신뢰도가 낮으면?**

A: 
1. 이미지 품질 확인
2. 회전된 이미지는 회전 보정 (`use_angle_cls=True`)
3. 신뢰도 < 70%인 파일은 수동 확인
4. LLM이 오류 수정할 것이므로 너무 걱정 안 해도 됨

**Q: PDF가 처리 안 되는데요?**

A: `pdf2image` 패키지 확인:
```bash
pip install pdf2image
```

Mac에서 추가 설치 필요:
```bash
brew install poppler
```

**Q: 처리 속도가 너무 느린데요?**

A: 
1. GPU 사용 (`--gpu`)
2. 이미지 크기가 너무 크면 리사이징 고려
3. 배치 처리 중 다른 작업 하지 않기

### 9.3 분류 관련

**Q: 학습 시간이 60분보다 오래 걸려요.**

A: 정상입니다. 데이터 개수에 따라 30-90분 소요 가능.
- 500개: ~40분
- 1000개: ~70분

빠르게 하려면 epochs 감소:
```python
# srcs/classification_module.py Line 101
num_train_epochs=3  →  num_train_epochs=2
```

**Q: 분류 정확도가 낮으면?**

A: 
1. Epochs 증가 (3 → 5)
2. Learning rate 감소 (2e-5 → 5e-6)
3. Training set OCR 결과 재확인
4. labels.csv 확인

**Q: 학습 중 NaN 에러가 나요.**

A: Learning rate가 너무 높음:
```python
# srcs/classification_module.py Line 103
learning_rate=2e-5  →  learning_rate=5e-6
```

### 9.4 파일/데이터

**Q: JSON 파일이 너무 큰데요?**

A: 정상입니다. 500개 문서면 10-50MB 가능. 압축 고려:
```bash
gzip predictions_final.json
# → predictions_final.json.gz
```

**Q: 파일명에 한글이 있으면?**

A: UTF-8 인코딩이므로 문제없습니다. 다만 출력 시 주의:
```python
with open(..., encoding='utf-8') as f:
    ...
```

**Q: labels.csv 형식이 다르면?**

A: 필수 컬럼: `filename`, `doc_type`
추가 컬럼은 무시됩니다.

### 9.5 해커톤 당일

**Q: Training set이 1000개인데 시간이 부족해요.**

A: 
1. Epochs 감소 (3 → 2)
2. GPU 사용
3. 팀원과 역할 분담 (OCR 중에 다른 작업)

**Q: 에러 파일이 몇 개 있는데 괜찮나요?**

A: 2-3%는 정상입니다 (이미지 품질 문제). 대부분 처리되면 OK.

**Q: LLM 팀이 JSON 형식을 바꿔달라고 해요.**

A: `srcs/predict_ocr_classify.py` 수정:
```python
# Line 34-48 부근
result = {
    # 필드 추가/제거/변경
}
```

---

## 10. 마무리

### 10.1 체크리스트

**개발 완료:**
- ✅ ocr_vl_module.py
- ✅ batch_ocr_vl.py
- ✅ classification_module.py
- ✅ train_classifier.py
- ✅ predict_ocr_classify.py

**테스트 완료:**
- ✅ 단일 파일 OCR
- ✅ 배치 처리
- ✅ 분류 모듈
- ✅ 통합 파이프라인

**문서 완료:**
- ✅ 환경 설정 가이드
- ✅ 사용법 설명
- ✅ LLM 인수인계
- ✅ 기술 배경 설명

### 10.2 해커톤 당일 요약

```
Phase 1: 데이터 확인 (10분)
Phase 2: Training OCR (40-50분) 
Phase 3: 모델 학습 (60분)
Phase 4: Testing 처리 (20-30분)
Phase 5: 제출 (10분)
─────────────────────────────────
Total: 2시간 30분 ~ 3시간
```

### 10.3 연락처

**문의사항:**
- OCR 관련: OCR 파트 담당자
- 분류 관련: OCR 파트 담당자
- LLM 연동: LLM 파트 담당자

---

**화이팅! 🚀 성공을 기원합니다!**

*마지막 업데이트: 2025-11-01*

