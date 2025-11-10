# 🚀 완전체 가이드북

**42 Asia Hackathon - 다국어 문서 처리 시스템 완전 가이드**

> 이 문서는 프로젝트의 모든 기능, 설정, 사용법을 포함하는 종합 가이드입니다.

---

## 📋 목차

1. [프로젝트 개요](#-프로젝트-개요)
2. [빠른 시작](#-빠른-시작)
3. [시스템 아키텍처](#-시스템-아키텍처)
4. [설치 및 설정](#-설치-및-설정)
5. [핵심 기능](#-핵심-기능)
6. [사용 방법](#-사용-방법)
7. [API 레퍼런스](#-api-레퍼런스)
8. [다국어 지원](#-다국어-지원)
9. [성능 벤치마크](#-성능-벤치마크)
10. [문제 해결](#-문제-해결)
11. [프로덕션 배포](#-프로덕션-배포)
12. [FAQ](#-faq)

---

## 🎯 프로젝트 개요

### 핵심 목표

다양한 언어의 문서 이미지를 자동으로 처리하는 엔드-투-엔드 AI 파이프라인

### 주요 기능

✅ **다국어 OCR** - 영어, 태국어, 한국어, 일본어 및 80+ 언어 지원  
✅ **문서 분류** - Invoice, Receipt, Resume, Report, Contract 자동 분류  
✅ **구조화된 데이터 추출** - 문서에서 핵심 정보 자동 추출  
✅ **요약 생성** - 복잡한 문서(보고서, 계약서) 자동 요약  
✅ **PII 탐지 및 마스킹** - 개인정보 자동 탐지 및 보호  
✅ **GDPR/PDPA 준수** - 데이터 보호 규정 준수

### 기술 스택

- **OCR**: PaddleOCR (80+ 언어 지원)
- **분류기**: XLM-RoBERTa (100+ 언어 지원)
- **LLM**: Ollama (Qwen2.5)
- **프레임워크**: PyTorch, Transformers, OpenCV
- **언어**: Python 3.11+

---

## ⚡ 빠른 시작

### 1분 만에 시작하기

```bash
# 1. 저장소 클론
git clone <repository-url>
cd 42_Asia_Hackathon

# 2. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 빠른 테스트
python tests/test_final_integration.py
```

### 첫 번째 문서 처리

```python
from src.ocr.ocr_vl_module import OCRVLModule
from src.classification.classifier import DocumentClassifier

# OCR 초기화
ocr = OCRVLModule(
    use_gpu=False,
    enable_handwriting=True,
    supported_langs=['en', 'korean', 'japan', 'thai']
)

# 문서 처리
result = ocr.process_document('sample.jpg', lang='auto')
print(f"언어: {result['detected_language']}")
print(f"텍스트: {result['full_text'][:100]}...")
```

---

## 🏗️ 시스템 아키텍처

### 전체 파이프라인

```
이미지 입력
    │
    ├─> [1단계] OCR 다국어 처리
    │   ├─ 언어 자동 감지
    │   ├─ 손글씨 전처리 (옵션)
    │   └─ 텍스트 추출 (PaddleOCR)
    │
    ├─> [2단계] 문서 분류
    │   └─ XLM-RoBERTa 다국어 분류기
    │
    ├─> [3단계] 데이터 추출
    │   ├─ Invoice/Receipt → 구조화된 데이터
    │   ├─ Resume → 이력서 정보
    │   └─ Report/Contract → 요약 생성
    │
    └─> [4단계] PII 처리
        ├─ 개인정보 탐지 (Regex + LLM)
        ├─ 자동 마스킹
        └─ Compliance 레벨 계산
```

### 디렉토리 구조

```
42_Asia_Hackathon/
├── src/
│   ├── ocr/                    # OCR 모듈
│   │   ├── ocr_vl_module.py   # 다국어 OCR (PaddleOCR)
│   │   └── batch_ocr_vl.py    # 배치 처리
│   ├── classification/         # 문서 분류
│   │   ├── classifier.py      # XLM-RoBERTa 분류기
│   │   └── trainer.py         # 학습 스크립트
│   ├── llm/                   # LLM 기반 처리
│   │   ├── converter.py       # 출력 포맷 변환
│   │   └── extractors/
│   │       ├── smart_extractor.py  # 데이터 추출
│   │       ├── summarizer.py       # 요약 생성
│   │       └── pii_detector.py     # PII 탐지/마스킹
│   └── pipeline/
│       └── predict.py         # 통합 파이프라인
├── tests/                     # 테스트 스크립트
│   ├── test_final_integration.py  # 종합 테스트
│   ├── test_multilingual_ocr.py   # OCR 테스트
│   └── test_classifier_performance.py  # 분류기 벤치마크
├── docs/                      # 문서
│   ├── COMPLETE_GUIDE.md      # 이 문서
│   ├── MULTILINGUAL_GUIDE.md  # 다국어 가이드
│   └── 3.0가이드.md           # 프로젝트 가이드
├── config/                    # 설정 파일
│   └── test_labels.csv        # 학습 레이블
├── data/                      # 데이터 디렉토리
│   ├── input/                 # 입력 이미지
│   ├── output/                # 처리 결과
│   └── models/                # 학습된 모델
└── requirements.txt           # Python 의존성
```

---

## 🔧 설치 및 설정

### 시스템 요구사항

**최소 사양:**
- Python 3.11+
- 8GB RAM
- 10GB 저장공간

**권장 사양:**
- Python 3.11+
- 16GB+ RAM
- NVIDIA GPU (CUDA 지원)
- 20GB+ 저장공간

### 상세 설치 가이드

#### 1. Python 가상환경 설정

```bash
# Python 버전 확인
python3 --version  # 3.11 이상 필요

# 가상환경 생성
python3 -m venv venv

# 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows
```

#### 2. 의존성 설치

```bash
# 기본 의존성
pip install -r requirements.txt

# GPU 지원 (옵션)
pip install paddlepaddle-gpu

# Apple Silicon (M1/M2) 최적화
pip install paddlepaddle==2.5.1
```

#### 3. Ollama LLM 설정 (옵션)

```bash
# Ollama 설치 (https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# Qwen2.5 모델 다운로드
ollama pull qwen2.5:latest

# 서버 실행 확인
curl http://localhost:11434/api/tags
```

**참고**: LLM 없이도 OCR과 분류 기능은 정상 작동합니다.

#### 4. 설정 검증

```bash
# 종합 테스트 실행
python tests/test_final_integration.py

# 예상 출력:
# ✅ 성공 다국어 OCR
# ✅ 성공 XLM-RoBERTa 분류기
# ✅ 성공 전체 파이프라인
```

---

## 🌟 핵심 기능

### 1. 다국어 OCR

**지원 언어**: 영어, 태국어, 한국어, 일본어 + 80개 언어

**특징:**
- ✅ 자동 언어 감지 (Unicode 범위 분석)
- ✅ 손글씨 지원 (이미지 전처리 강화)
- ✅ Lazy Loading (필요 시에만 모델 로드)
- ✅ GPU 가속 지원

**사용 예제:**

```python
from src.ocr.ocr_vl_module import OCRVLModule

# 초기화
ocr = OCRVLModule(
    use_gpu=False,                          # GPU 사용 여부
    enable_handwriting=True,                # 손글씨 전처리
    supported_langs=['en', 'korean', 'japan', 'thai']
)

# 자동 언어 감지
result = ocr.process_document('document.jpg', lang='auto')
print(result['detected_language'])  # 'en', 'ko', 'ja', 'th' 등

# 특정 언어 지정
result = ocr.process_document('thai_doc.jpg', lang='thai')

# 결과
{
    'full_text': '추출된 전체 텍스트',
    'layout': [{'text': '...', 'bbox': [...], 'confidence': 0.95}],
    'confidence': 85.5,
    'detected_language': 'th',
    'processing_time': 3.2
}
```

### 2. 문서 분류 (XLM-RoBERTa)

**문서 유형**: Invoice, Receipt, Resume, Report, Contract

**특징:**
- ✅ 100+ 언어 지원 (단일 모델)
- ✅ 높은 정확도 (90%+)
- ✅ 빠른 추론 (~0.1초/문서)
- ✅ Fine-tuning 가능

**학습 방법:**

```bash
# 1. 레이블 데이터 준비 (config/test_labels.csv)
filename,label
invoice1.jpg,invoice
receipt1.jpg,receipt
resume1.jpg,resume

# 2. OCR 결과 생성
python src/ocr/batch_ocr_vl.py \
  --input data/input/ \
  --output data/output/predictions_ocr_only.json

# 3. 분류기 학습
python src/classification/trainer.py \
  --labels config/test_labels.csv \
  --ocr-results data/output/predictions_ocr_only.json \
  --output data/models/xlm_roberta_classifier \
  --epochs 5 \
  --batch-size 8
```

**추론 방법:**

```python
from src.classification.classifier import DocumentClassifier

# 초기화 및 모델 로드
classifier = DocumentClassifier(model_name='xlm-roberta-base')
classifier.load_model('data/models/xlm_roberta_classifier')

# 분류
text = "INVOICE #12345\nDate: 2024-01-15\n..."
result = classifier.classify(text)

print(result)
# {
#     'label': 'invoice',
#     'confidence': 0.95,
#     'processing_time': 0.08
# }
```

### 3. 구조화된 데이터 추출

**지원 문서:**
- **Invoice**: 번호, 날짜, 금액, 공급자/고객 정보
- **Receipt**: 상점명, 날짜, 항목, 총액
- **Resume**: 이름, 연락처, 경력, 학력, 기술

**사용 예제:**

```python
from src.llm.extractors.smart_extractor import SmartExtractor

extractor = SmartExtractor(ollama_url='http://localhost:11434')

# 예측 결과 (OCR + 분류)
prediction = {
    'filename': 'invoice.jpg',
    'classification': {'doc_type': 'invoice', 'confidence': 0.95},
    'full_text_ocr': 'INVOICE #INV-2024-001\nDate: 2024-01-15\n...'
}

# 추출
extracted = extractor.extract(prediction)
print(extracted)
# {
#     'invoice_number': 'INV-2024-001',
#     'date': '2024-01-15',
#     'total_amount': '1500.00',
#     'currency': 'USD',
#     'vendor_name': 'ABC Company',
#     'customer_name': 'XYZ Corp'
# }
```

### 4. 문서 요약

**지원 문서**: Report, Contract

**특징:**
- ✅ 다국어 입력 지원
- ✅ 영어 출력 (핵심 용어 원어 보존)
- ✅ 3-5문장 간결 요약

**사용 예제:**

```python
from src.llm.extractors.summarizer import DocumentSummarizer

summarizer = DocumentSummarizer(ollama_url='http://localhost:11434')

text = """
【業務報告書】
2024年第1四半期の業績について...
（長い일본어 보고서）
"""

summary = summarizer.summarize(text, doc_type='report')
print(summary)
# "This quarterly report covers Q1 2024 performance.
#  Key highlights include 15% revenue growth and successful
#  product launch in the Asian market..."
```

### 5. PII 탐지 및 마스킹

**지원 PII 유형:**
- 📧 이메일
- 💳 신용카드 번호
- 📱 전화번호 (EN, TH, KR, JP)
- 🆔 주민번호 (KR), 마이넘버 (JP), ID (TH)

**사용 예제:**

```python
from src.llm.extractors.pii_detector import PIIDetector

detector = PIIDetector(ollama_url='http://localhost:11434')

text = """
Name: 홍길동
Phone: 010-1234-5678
Email: hong@example.com
ID: 950101-1234567
"""

# PII 탐지
pii_list = detector.detect(text, use_llm=True)

for pii in pii_list:
    print(f"{pii['type']}: {pii['text']} → {detector.mask_text(pii['text'], pii['type'])}")

# 출력:
# KOREAN_PHONE: 010-1234-5678 → 010-****-5678
# EMAIL: hong@example.com → h***@example.com
# KOREAN_ID: 950101-1234567 → 950101-*******

# 전체 텍스트 마스킹
masked_text = detector.mask_full_text(text, pii_list)
print(masked_text)
```

---

## 📖 사용 방법

### 시나리오 1: 단일 문서 처리

```python
from pathlib import Path
from src.pipeline.predict import process_single_document
from src.ocr.ocr_vl_module import OCRVLModule
from src.classification.classifier import DocumentClassifier

# 모듈 초기화
ocr = OCRVLModule(use_gpu=False, enable_handwriting=True)
classifier = DocumentClassifier()
classifier.load_model('data/models/xlm_roberta_classifier')

# 문서 처리
result = process_single_document(
    image_path='data/input/invoice.jpg',
    ocr_vl=ocr,
    classifier=classifier
)

print(f"파일: {result['filename']}")
print(f"분류: {result['classification']}")
print(f"언어: {result['detected_language']}")
print(f"텍스트: {result['full_text_ocr'][:200]}...")
```

### 시나리오 2: 배치 처리

```bash
# 전체 파이프라인 실행
python src/pipeline/predict.py \
  --input data/input/ \
  --output data/output/results.json \
  --model-path data/models/xlm_roberta_classifier \
  --use-gpu
```

### 시나리오 3: CLI 사용

```bash
# OCR만 실행
python src/ocr/batch_ocr_vl.py \
  --input data/input/ \
  --output data/output/ocr_results.json \
  --lang auto \
  --handwriting

# 분류 + LLM 처리
python src/llm/converter.py \
  --input data/output/ocr_results.json \
  --output data/output/final_results.json \
  --ollama-url http://localhost:11434
```

### 시나리오 4: 커스텀 파이프라인

```python
import json
from pathlib import Path
from src.ocr.ocr_vl_module import OCRVLModule
from src.classification.classifier import DocumentClassifier
from src.llm.converter import convert_prediction_to_hackathon
from src.llm.extractors.smart_extractor import SmartExtractor
from src.llm.extractors.pii_detector import PIIDetector
from src.llm.extractors.summarizer import DocumentSummarizer

# 1. OCR
ocr = OCRVLModule(use_gpu=True)
ocr_result = ocr.process_document('invoice.jpg', lang='auto')

# 2. 분류
classifier = DocumentClassifier()
classifier.load_model('data/models/xlm_roberta_classifier')
classification = classifier.classify(ocr_result['full_text'])

# 3. LLM 처리
extractor = SmartExtractor()
pii_detector = PIIDetector()
summarizer = DocumentSummarizer()

prediction = {
    'filename': 'invoice.jpg',
    'classification': {
        'doc_type': classification['label'],
        'confidence': classification['confidence']
    },
    'full_text_ocr': ocr_result['full_text']
}

# 4. 최종 변환
final_result = convert_prediction_to_hackathon(
    prediction, extractor, pii_detector, summarizer
)

# 5. 저장
with open('result.json', 'w', encoding='utf-8') as f:
    json.dump(final_result, f, indent=2, ensure_ascii=False)
```

---

## 🔌 API 레퍼런스

### OCRVLModule

```python
class OCRVLModule:
    def __init__(
        self,
        use_gpu: bool = False,
        enable_handwriting: bool = True,
        supported_langs: List[str] = None
    ):
        """
        다국어 OCR 모듈 초기화
        
        Args:
            use_gpu: GPU 사용 여부
            enable_handwriting: 손글씨 전처리 활성화
            supported_langs: 지원 언어 리스트 (기본값: ['en'])
        """
    
    def process_document(
        self,
        image_path: str,
        lang: str = 'auto'
    ) -> Dict[str, Any]:
        """
        문서 이미지 처리
        
        Args:
            image_path: 이미지 파일 경로
            lang: 'auto' 또는 특정 언어 ('en', 'korean', 'japan', 'thai')
        
        Returns:
            {
                'full_text': str,           # 추출된 전체 텍스트
                'layout': List[Dict],       # 레이아웃 정보
                'confidence': float,        # 평균 신뢰도 (0-100)
                'detected_language': str,   # 감지된 언어
                'processing_time': float    # 처리 시간 (초)
            }
        """
```

### DocumentClassifier

```python
class DocumentClassifier:
    def __init__(self, model_name: str = 'xlm-roberta-base'):
        """
        XLM-RoBERTa 기반 다국어 문서 분류기
        
        Args:
            model_name: Hugging Face 모델 이름
        """
    
    def train(
        self,
        labels_csv_path: str,
        ocr_results_path: str,
        output_dir: str,
        epochs: int = 3,
        batch_size: int = 8
    ):
        """
        분류기 학습
        
        Args:
            labels_csv_path: 레이블 CSV 파일 경로
            ocr_results_path: OCR 결과 JSON 파일 경로
            output_dir: 모델 저장 경로
            epochs: 학습 에폭 수
            batch_size: 배치 크기
        """
    
    def classify(self, text: str) -> Dict[str, Any]:
        """
        텍스트 분류
        
        Args:
            text: 입력 텍스트
        
        Returns:
            {
                'label': str,               # 문서 유형
                'confidence': float,        # 신뢰도 (0-1)
                'processing_time': float    # 처리 시간 (초)
            }
        """
    
    def load_model(self, path: str):
        """저장된 모델 로드"""
    
    def save_model(self, path: str):
        """모델 저장"""
```

### SmartExtractor

```python
class SmartExtractor:
    def __init__(self, ollama_url: str = 'http://localhost:11434'):
        """
        LLM 기반 데이터 추출기
        
        Args:
            ollama_url: Ollama 서버 URL
        """
    
    def extract(self, prediction: Dict) -> Dict[str, Any]:
        """
        문서에서 구조화된 데이터 추출
        
        Args:
            prediction: {
                'classification': {'doc_type': str},
                'full_text_ocr': str
            }
        
        Returns:
            문서 유형별 구조화된 데이터
        """
```

### PIIDetector

```python
class PIIDetector:
    def __init__(self, ollama_url: str = 'http://localhost:11434'):
        """PII 탐지 및 마스킹 모듈"""
    
    def detect(
        self,
        text: str,
        use_llm: bool = True
    ) -> List[Dict]:
        """
        PII 탐지
        
        Returns:
            [
                {
                    'text': str,      # 원본 PII 텍스트
                    'type': str,      # PII 유형
                    'start': int,     # 시작 위치
                    'end': int        # 끝 위치
                },
                ...
            ]
        """
    
    def mask_text(self, text: str, pii_type: str) -> str:
        """개별 PII 마스킹"""
    
    def mask_full_text(self, text: str, pii_list: List[Dict]) -> str:
        """전체 텍스트에서 모든 PII 마스킹"""
```

### DocumentSummarizer

```python
class DocumentSummarizer:
    def __init__(self, ollama_url: str = 'http://localhost:11434'):
        """문서 요약 생성기"""
    
    def summarize(self, text: str, doc_type: str) -> str:
        """
        문서 요약
        
        Args:
            text: 전체 텍스트
            doc_type: 'report' 또는 'contract'
        
        Returns:
            3-5문장 요약 (영어)
        """
```

---

## 🌍 다국어 지원

### 지원 언어

| 언어 | OCR 코드 | 분류기 지원 | PII 탐지 |
|------|----------|-------------|----------|
| 영어 | `en` | ✅ | ✅ (이메일, 신용카드, 전화번호) |
| 태국어 | `thai` | ✅ | ✅ (전화번호, ID) |
| 한국어 | `korean` | ✅ | ✅ (전화번호, 주민번호) |
| 일본어 | `japan` | ✅ | ✅ (전화번호, 마이넘버) |
| 중국어 | `ch` | ✅ | ⚠️ (부분) |
| 기타 | 80+ 언어 | ✅ | ⚠️ (제한적) |

### 언어별 최적화 팁

**영어 (EN)**
- 기본 설정으로 최적 성능
- 손글씨 인식 우수

**태국어 (TH)**
- `lang='thai'` 명시적 지정 권장
- 복잡한 스크립트로 인해 신뢰도가 다소 낮을 수 있음

**한국어 (KR)**
- 한글과 한자 모두 지원
- PII 패턴(주민번호) 정확도 높음

**일본어 (JP)**
- 히라가나, 가타카나, 한자 모두 지원
- 혼합 스크립트 문서 처리 우수

### 다국어 사용 예제

```python
# 자동 언어 감지
ocr = OCRVLModule(supported_langs=['en', 'korean', 'japan', 'thai'])
result = ocr.process_document('mixed_language.jpg', lang='auto')
print(result['detected_language'])  # 자동 감지됨

# 언어별 처리
languages = ['en', 'korean', 'japan', 'thai']
results = {}

for lang in languages:
    result = ocr.process_document(f'{lang}_doc.jpg', lang=lang)
    results[lang] = result

# 분류기는 언어 자동 처리
classifier = DocumentClassifier()  # XLM-RoBERTa는 모든 언어 지원
classification = classifier.classify(result['full_text'])  # 언어 무관
```

---

## 📊 성능 벤치마크

### OCR 성능

| 언어 | 평균 처리 시간 | 평균 신뢰도 | GPU 가속 시 |
|------|----------------|-------------|-------------|
| 영어 | 3-5초 | 85-90% | 1-2초 |
| 태국어 | 4-6초 | 75-85% | 1.5-2.5초 |
| 한국어 | 3-5초 | 80-90% | 1-2초 |
| 일본어 | 4-6초 | 80-88% | 1.5-2.5초 |

**테스트 환경**: MacBook Pro M1, 16GB RAM

### 분류기 성능 (XLM-RoBERTa)

| 메트릭 | 값 |
|--------|-----|
| 정확도 | 90-95% |
| 추론 시간 (CPU) | 0.08-0.12초 |
| 추론 시간 (GPU) | 0.03-0.05초 |
| 모델 크기 | ~1.1GB |
| 메모리 사용량 | ~2-3GB |

### 전체 파이프라인

**단일 문서 처리 (CPU):**
- OCR: 3-5초
- 분류: 0.1초
- 추출/요약/PII (LLM): 2-5초
- **전체: 5-10초**

**단일 문서 처리 (GPU):**
- OCR: 1-2초
- 분류: 0.03초
- 추출/요약/PII (LLM): 2-5초
- **전체: 3-7초**

### 메모리 사용량

| 구성 요소 | 메모리 |
|-----------|--------|
| OCR (영어) | ~500MB |
| OCR (4개 언어) | ~2GB |
| XLM-RoBERTa | ~2-3GB |
| Ollama (Qwen2.5) | ~4-8GB |
| **전체 (최대)** | **~12-15GB** |

**최적화 팁:**
- Lazy Loading 활용 (필요 언어만 로드)
- GPU 사용 시 메모리 효율 증가
- 배치 처리로 처리량 향상

---

## 🛠️ 문제 해결

### 일반적인 문제

#### 1. "Model not loaded" 오류

**원인**: 분류기 모델이 학습되지 않았거나 로드되지 않음

**해결책**:

```bash
# 모델 학습
python src/classification/trainer.py \
  --labels config/test_labels.csv \
  --ocr-results data/output/predictions_ocr_only.json \
  --output data/models/xlm_roberta_classifier

# 또는 모델 로드
classifier.load_model('data/models/xlm_roberta_classifier')
```

#### 2. "Cannot connect to Ollama" 경고

**원인**: Ollama 서버가 실행되지 않음

**해결책**:

```bash
# Ollama 설치 및 실행
ollama serve

# 또는 LLM 기능 비활성화 (OCR/분류만 사용)
# 경고는 무시 가능 - 기본 기능은 작동함
```

#### 3. OCR 신뢰도가 낮음 (< 70%)

**원인**: 이미지 품질 문제 또는 복잡한 레이아웃

**해결책**:

```python
# 1. 손글씨 전처리 활성화
ocr = OCRVLModule(enable_handwriting=True)

# 2. 이미지 전처리
from PIL import Image
import cv2

img = cv2.imread('low_quality.jpg')
# 그레이스케일 변환
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
# 대비 향상
enhanced = cv2.equalizeHist(gray)
cv2.imwrite('enhanced.jpg', enhanced)

# 3. 언어 명시
result = ocr.process_document('enhanced.jpg', lang='en')
```

#### 4. 메모리 부족 오류

**원인**: 모든 언어 모델이 동시에 로드됨

**해결책**:

```python
# 필요한 언어만 지정
ocr = OCRVLModule(supported_langs=['en'])  # 1개 언어만

# 또는 배치 크기 감소
classifier.train(..., batch_size=4)  # 기본값 8에서 감소
```

#### 5. GPU 사용 안 됨

**확인**:

```python
import paddle
print(paddle.is_compiled_with_cuda())  # True여야 함
```

**해결책**:

```bash
# GPU 버전 재설치
pip uninstall paddlepaddle
pip install paddlepaddle-gpu
```

### 디버깅 모드

```python
import logging

# 로깅 활성화
logging.basicConfig(level=logging.DEBUG)

# OCR 로그 확인
ocr = OCRVLModule(use_gpu=False)
result = ocr.process_document('test.jpg', lang='auto')
# 상세한 처리 로그 출력됨
```

### 성능 프로파일링

```python
import time

def profile_pipeline(image_path):
    times = {}
    
    # OCR
    start = time.time()
    ocr_result = ocr.process_document(image_path)
    times['ocr'] = time.time() - start
    
    # 분류
    start = time.time()
    classification = classifier.classify(ocr_result['full_text'])
    times['classify'] = time.time() - start
    
    # LLM
    start = time.time()
    # ... LLM 처리
    times['llm'] = time.time() - start
    
    print("⏱️ 성능 분석:")
    for step, duration in times.items():
        print(f"  {step}: {duration:.2f}초")
    
    return times

profile_pipeline('data/input/sample.jpg')
```

---

## 🚀 프로덕션 배포

### Docker 배포

```bash
# Docker 이미지 빌드
docker build -t doc-processing-system -f docker/Dockerfile .

# 실행 (CPU)
docker-compose -f docker/docker-compose.cpu.yml up

# 실행 (GPU)
docker-compose -f docker/docker-compose.yml up
```

### API 서버 (예제)

```python
# app.py
from fastapi import FastAPI, File, UploadFile
from src.pipeline.predict import process_single_document
from src.ocr.ocr_vl_module import OCRVLModule
from src.classification.classifier import DocumentClassifier

app = FastAPI()

# 전역 초기화
ocr = OCRVLModule(use_gpu=True)
classifier = DocumentClassifier()
classifier.load_model('data/models/xlm_roberta_classifier')

@app.post("/process")
async def process_document(file: UploadFile = File(...)):
    # 임시 저장
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    # 처리
    result = process_single_document(temp_path, ocr, classifier)
    
    return result

# 실행: uvicorn app:app --host 0.0.0.0 --port 8000
```

### 배치 처리 최적화

```python
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def process_batch(image_paths, num_workers=4):
    """멀티스레드 배치 처리"""
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(process_single_document, img, ocr, classifier)
            for img in image_paths
        ]
        
        results = [f.result() for f in futures]
    
    return results

# 사용
images = list(Path("data/input").glob("*.jpg"))
results = process_batch(images, num_workers=4)
```

### 환경 변수 설정

```bash
# .env 파일
OLLAMA_URL=http://localhost:11434
MODEL_PATH=data/models/xlm_roberta_classifier
USE_GPU=true
OCR_LANGUAGES=en,korean,japan,thai
ENABLE_HANDWRITING=true
```

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    MODEL_PATH = os.getenv('MODEL_PATH', 'data/models/xlm_roberta_classifier')
    USE_GPU = os.getenv('USE_GPU', 'false').lower() == 'true'
    OCR_LANGUAGES = os.getenv('OCR_LANGUAGES', 'en').split(',')
    ENABLE_HANDWRITING = os.getenv('ENABLE_HANDWRITING', 'true').lower() == 'true'
```

---

## ❓ FAQ

### Q1. LLM 없이 사용할 수 있나요?

**A**: 네! OCR과 분류 기능은 LLM 없이 완벽하게 작동합니다. 다만 다음 기능은 사용할 수 없습니다:
- 구조화된 데이터 추출
- 문서 요약
- LLM 기반 PII 탐지 (Regex 탐지는 가능)

### Q2. GPU가 필수인가요?

**A**: 아니요. CPU만으로도 작동하지만, GPU 사용 시 3-5배 빠른 처리가 가능합니다.

### Q3. 새로운 문서 유형을 추가하려면?

**A**: 
1. `labels.csv`에 새 유형 추가
2. 분류기 재학습
3. `smart_extractor.py`에 추출 로직 추가

```python
# smart_extractor.py에 추가
def _get_fields_for_type(self, doc_type):
    if doc_type == "new_type":
        return {
            "field1": "Description 1",
            "field2": "Description 2"
        }
```

### Q4. 지원하지 않는 언어를 추가하려면?

**A**: PaddleOCR이 지원하는 80+ 언어는 모두 추가 가능합니다:

```python
ocr = OCRVLModule(supported_langs=['en', 'arabic', 'hindi'])
result = ocr.process_document('arabic_doc.jpg', lang='arabic')
```

PaddleOCR 지원 언어 목록: https://github.com/PaddlePaddle/PaddleOCR#language

### Q5. 배치 처리 시 속도는?

**A**: 
- **CPU**: ~10-15 문서/분
- **GPU**: ~30-50 문서/분
- **멀티 GPU**: ~100+ 문서/분

### Q6. 정확도를 높이려면?

**A**:
1. 더 많은 학습 데이터로 분류기 재학습
2. 이미지 품질 향상 (해상도, 대비)
3. 언어를 명시적으로 지정 (`lang='auto'` 대신)
4. GPU 사용으로 더 큰 모델 활용

### Q7. 상업적으로 사용 가능한가요?

**A**: 라이선스를 확인하세요:
- PaddleOCR: Apache 2.0 (상업 사용 가능)
- XLM-RoBERTa: MIT (상업 사용 가능)
- Qwen2.5: Apache 2.0 (상업 사용 가능)

---

## 📚 추가 리소스

### 공식 문서
- [PaddleOCR 문서](https://github.com/PaddlePaddle/PaddleOCR)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [Ollama 가이드](https://ollama.ai/docs)

### 프로젝트 문서
- [다국어 가이드](./MULTILINGUAL_GUIDE.md)
- [프로젝트 가이드](./3.0가이드.md)
- [아키텍처 문서](./archive/backup_old_architecture/ARCHITECTURE.md)

### 유용한 링크
- [XLM-RoBERTa 모델 카드](https://huggingface.co/xlm-roberta-base)
- [PaddleOCR 언어 목록](https://github.com/PaddlePaddle/PaddleOCR#language)
- [Qwen2.5 모델](https://ollama.ai/library/qwen2.5)

---

## 🎓 튜토리얼

### 튜토리얼 1: 첫 번째 문서 처리 (5분)

```python
# 1. 의존성 설치
# pip install -r requirements.txt

# 2. 기본 OCR
from src.ocr.ocr_vl_module import OCRVLModule

ocr = OCRVLModule()
result = ocr.process_document('data/input/sample1.jpg')
print(result['full_text'])

# 완료! 첫 번째 OCR 완료 🎉
```

### 튜토리얼 2: 분류기 학습 (10분)

```bash
# 1. 레이블 데이터 준비
echo "filename,label" > labels.csv
echo "invoice1.jpg,invoice" >> labels.csv
echo "receipt1.jpg,receipt" >> labels.csv

# 2. OCR 실행
python src/ocr/batch_ocr_vl.py --input data/input/ --output ocr.json

# 3. 학습
python src/classification/trainer.py \
  --labels labels.csv \
  --ocr-results ocr.json \
  --output my_model \
  --epochs 3

# 완료! 분류 모델 생성 완료 🎉
```

### 튜토리얼 3: 전체 파이프라인 (15분)

```python
# 전체 통합 예제
from pathlib import Path
import json
from src.ocr.ocr_vl_module import OCRVLModule
from src.classification.classifier import DocumentClassifier
from src.llm.converter import convert_prediction_to_hackathon
from src.llm.extractors.smart_extractor import SmartExtractor
from src.llm.extractors.pii_detector import PIIDetector
from src.llm.extractors.summarizer import DocumentSummarizer

# 초기화
ocr = OCRVLModule(supported_langs=['en', 'korean'])
classifier = DocumentClassifier()
classifier.load_model('data/models/xlm_roberta_classifier')

extractor = SmartExtractor()
pii_detector = PIIDetector()
summarizer = DocumentSummarizer()

# 처리
images = list(Path("data/input").glob("*.jpg"))
results = []

for img in images:
    # OCR
    ocr_result = ocr.process_document(str(img), lang='auto')
    
    # 분류
    classification = classifier.classify(ocr_result['full_text'])
    
    # 통합
    prediction = {
        'filename': img.name,
        'classification': {
            'doc_type': classification['label'],
            'confidence': classification['confidence']
        },
        'full_text_ocr': ocr_result['full_text']
    }
    
    # LLM 처리
    final_result = convert_prediction_to_hackathon(
        prediction, extractor, pii_detector, summarizer
    )
    
    results.append(final_result)

# 저장
with open('final_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"✅ {len(results)}개 문서 처리 완료!")

# 완료! 전체 파이프라인 실행 완료 🎉
```

---

## 🏆 모범 사례

### 1. 이미지 전처리

```python
import cv2
import numpy as np

def preprocess_image(image_path):
    """OCR 정확도 향상을 위한 전처리"""
    img = cv2.imread(image_path)
    
    # 그레이스케일
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 노이즈 제거
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # 대비 향상
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    # 저장
    output_path = image_path.replace('.jpg', '_preprocessed.jpg')
    cv2.imwrite(output_path, enhanced)
    
    return output_path

# 사용
preprocessed = preprocess_image('low_quality.jpg')
result = ocr.process_document(preprocessed)
```

### 2. 에러 핸들링

```python
import logging
from typing import Optional

def safe_process_document(image_path: str) -> Optional[dict]:
    """안전한 문서 처리 (에러 핸들링 포함)"""
    try:
        # OCR
        ocr_result = ocr.process_document(image_path, lang='auto')
        
        # 신뢰도 체크
        if ocr_result['confidence'] < 50:
            logging.warning(f"Low confidence: {ocr_result['confidence']}")
            # 재시도 로직 또는 수동 검토 플래그
        
        # 분류
        classification = classifier.classify(ocr_result['full_text'])
        
        return {
            'success': True,
            'ocr': ocr_result,
            'classification': classification
        }
        
    except Exception as e:
        logging.error(f"Error processing {image_path}: {e}")
        return {
            'success': False,
            'error': str(e),
            'filename': image_path
        }

# 사용
result = safe_process_document('data/input/sample.jpg')
if result['success']:
    print("처리 성공!")
else:
    print(f"처리 실패: {result['error']}")
```

### 3. 모니터링 및 로깅

```python
import time
from datetime import datetime

class PerformanceMonitor:
    def __init__(self):
        self.metrics = []
    
    def log_processing(self, filename, ocr_time, classify_time, total_time):
        self.metrics.append({
            'timestamp': datetime.now().isoformat(),
            'filename': filename,
            'ocr_time': ocr_time,
            'classify_time': classify_time,
            'total_time': total_time
        })
    
    def get_average_times(self):
        if not self.metrics:
            return None
        
        n = len(self.metrics)
        return {
            'avg_ocr_time': sum(m['ocr_time'] for m in self.metrics) / n,
            'avg_classify_time': sum(m['classify_time'] for m in self.metrics) / n,
            'avg_total_time': sum(m['total_time'] for m in self.metrics) / n,
            'documents_processed': n
        }
    
    def save_report(self, path='performance_report.json'):
        import json
        with open(path, 'w') as f:
            json.dump({
                'metrics': self.metrics,
                'summary': self.get_average_times()
            }, f, indent=2)

# 사용
monitor = PerformanceMonitor()

for img_path in image_paths:
    start = time.time()
    
    ocr_start = time.time()
    ocr_result = ocr.process_document(img_path)
    ocr_time = time.time() - ocr_start
    
    classify_start = time.time()
    classification = classifier.classify(ocr_result['full_text'])
    classify_time = time.time() - classify_start
    
    total_time = time.time() - start
    
    monitor.log_processing(img_path, ocr_time, classify_time, total_time)

# 리포트 저장
monitor.save_report()
print("Performance Report:")
print(json.dumps(monitor.get_average_times(), indent=2))
```

---

## 🎉 결론

이 가이드는 42 Asia Hackathon 다국어 문서 처리 시스템의 모든 기능과 사용법을 다룹니다.

### 핵심 요약

✅ **다국어 OCR**: 80+ 언어 지원, 자동 감지, 손글씨 인식  
✅ **문서 분류**: XLM-RoBERTa 기반, 90%+ 정확도  
✅ **데이터 추출**: LLM 기반 구조화, 다국어 지원  
✅ **PII 보호**: 자동 탐지 및 마스킹, GDPR/PDPA 준수  
✅ **프로덕션 준비**: Docker, API, 배치 처리 지원

### 다음 단계

1. **빠른 시작** 섹션으로 시스템 설치
2. **튜토리얼**로 기본 사용법 학습
3. **API 레퍼런스**로 고급 기능 탐색
4. **문제 해결** 섹션으로 이슈 해결

### 도움이 필요하신가요?

- 📖 [다국어 가이드](./MULTILINGUAL_GUIDE.md) 참고
- 🐛 이슈 발생 시: [문제 해결](#-문제-해결) 섹션
- 💬 질문: [FAQ](#-faq) 확인

---

**Happy Hacking! 🚀**

*Last Updated: 2024-11-06*  
*Version: 3.0 - Complete Edition*

