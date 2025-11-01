# 🎯 내 파트: OCR-VL + 문서 분류

## 📌 담당 범위

```
Input (이미지/PDF)
    ↓
PaddleOCR-VL (레이아웃 분석)
    ↓
DistilBERT (문서 분류 - 학습 필요)
    ↓
Output (JSON) → LLM 팀에게 전달
```

**내가 하는 일:**
- ✅ OCR-VL로 텍스트 + 레이아웃 추출
- ✅ DistilBERT로 문서 분류 (학습 포함)
- ✅ JSON 출력

**LLM 팀이 하는 일:**
- 🔵 구조화 데이터 추출 (vendor, amount, date 등)
- 🔵 요약 생성
- 🔵 PII 탐지

---

## 🏗️ 단순화된 아키텍처

```
┌─────────────────┐
│  invoice_001.jpg│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│    PaddleOCR-VL Module          │
│  • 텍스트 추출                   │
│  • 레이아웃 분석                 │
└────────┬────────────────────────┘
         │
         ▼
    {
      "full_text": "INVOICE\n...",
      "layout": {
        "title": "INVOICE",
        "sections": [...],
        "tables": [...],
        "features": {...}
      },
      "confidence": 0.97
    }
         │
         ▼
┌─────────────────────────────────┐
│   Enhanced Text Preparation     │
│  텍스트 + 레이아웃 → 하나의 문자열 │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   DistilBERT Classifier         │
│  • Training set으로 학습         │
│  • 5개 클래스 분류               │
└────────┬────────────────────────┘
         │
         ▼
    {
      "doc_type": "invoice",
      "confidence": 0.96
    }
         │
         ▼
┌─────────────────────────────────┐
│   Final Output (JSON)           │
│   → LLM 팀에게 전달              │
└─────────────────────────────────┘
```

---

## 📤 출력 형식 (LLM 팀에게 전달)

```json
{
  "filename": "invoice_001.jpg",
  
  "full_text_ocr": "COMMERCIAL INVOICE\nABC Exports Ltd.\nInvoice No: INV-2025-001\nDate: 2025-01-01\nTotal Amount: $1,500.00\nPayment Method: Wire Transfer",
  
  "ocr_confidence": 0.97,
  
  "layout": {
    "title": "COMMERCIAL INVOICE",
    "sections": [
      {
        "type": "header",
        "text": "ABC Exports Ltd.",
        "position": [10, 60, 180, 80]
      },
      {
        "type": "key_value",
        "key": "Invoice No",
        "value": "INV-2025-001",
        "position": [10, 90, 250, 110]
      }
    ],
    "tables": [],
    "features": {
      "has_table": false,
      "num_key_value_pairs": 2
    }
  },
  
  "classification": {
    "doc_type": "invoice",
    "confidence": 0.96
  },
  
  "processing_time": 2.3
}
```

**LLM 팀은 이 JSON을 받아서:**
- `full_text_ocr`: 텍스트 분석
- `layout`: 구조 이해
- `classification.doc_type`: 어떤 필드를 추출할지 결정
- → 구조화된 데이터 추출

---

## 📂 내가 만들 파일들

```
src/
├── ocr_vl_module.py          ⭐ 새로 작성
│   └── OCRVLModule 클래스
│
├── classification_module.py  ✏️ 약간 수정
│   └── DocumentClassifier (기존 유지)
│
├── train_classifier.py       ✅ 그대로 사용
│
├── batch_ocr_vl.py           ⭐ 새로 작성
│   └── Training set 배치 처리
│
└── predict_ocr_classify.py   ⭐ 새로 작성
    └── Testing set 처리 (분류까지만)
```

**삭제/무시:**
- ~~`llm_module.py`~~ (필요없음)
- ~~`main.py`~~ (LLM 통합 부분 있음)
- ~~`extraction_module.py`~~ (이미 백업됨)

---

## 🔄 상세 데이터 플로우

### Step 1: PaddleOCR-VL 처리

**코드:**
```python
from src.ocr_vl_module import OCRVLModule

ocr_vl = OCRVLModule(use_gpu=True)
result = ocr_vl.process_document('invoice_001.jpg')
```

**출력:**
```python
{
  "full_text": "COMMERCIAL INVOICE\nABC Exports Ltd.\n...",
  "layout": {
    "title": "COMMERCIAL INVOICE",
    "sections": [...],
    "tables": [...],
    "features": {...}
  },
  "confidence": 0.97,
  "processing_time": 2.3
}
```

### Step 2: Enhanced Text 준비

**코드:**
```python
def prepare_classification_input(ocr_result):
    """레이아웃 정보를 텍스트로 추가"""
    text = ocr_result['full_text']
    layout = ocr_result['layout']
    
    layout_info = f"""
[LAYOUT_INFO]
Title: {layout.get('title', 'None')}
Has_Table: {len(layout.get('tables', [])) > 0}
Key_Value_Pairs: {layout.get('features', {}).get('num_key_value_pairs', 0)}
[END_LAYOUT_INFO]
"""
    
    return text + "\n\n" + layout_info
```

**출력:**
```text
COMMERCIAL INVOICE
ABC Exports Ltd.
...

[LAYOUT_INFO]
Title: COMMERCIAL INVOICE
Has_Table: True
Key_Value_Pairs: 5
[END_LAYOUT_INFO]
```

### Step 3: DistilBERT 분류

**코드:**
```python
from src.classification_module import DocumentClassifier

classifier = DocumentClassifier()
classifier.load_model('models/classifier')

enhanced_text = prepare_classification_input(ocr_result)
classification = classifier.classify(enhanced_text)
```

**출력:**
```python
{
  "doc_type": "invoice",
  "confidence": 0.96
}
```

### Step 4: 최종 결과 조합

**코드:**
```python
def create_output(filename, ocr_result, classification_result):
    """LLM 팀에게 전달할 JSON 생성"""
    return {
        "filename": filename,
        "full_text_ocr": ocr_result['full_text'],
        "ocr_confidence": ocr_result['confidence'],
        "layout": ocr_result['layout'],
        "classification": classification_result,
        "processing_time": ocr_result['processing_time']
    }
```

---

## 📝 구현 체크리스트

### Phase 1: OCR-VL 모듈 (우선순위 🔥)
- [ ] `src/ocr_vl_module.py` 생성
- [ ] `OCRVLModule.__init__()` - PaddleOCR-VL 초기화
- [ ] `OCRVLModule.process_document()` - 텍스트 + 레이아웃 추출
- [ ] `OCRVLModule._parse_layout()` - 레이아웃 파싱
- [ ] test_samples로 테스트

### Phase 2: 분류 모듈 수정 (우선순위 🟡)
- [ ] `classification_module.py` 열기
- [ ] `classify()` 메서드 확인 (수정 필요 없을 수도)
- [ ] Enhanced text 입력 테스트

### Phase 3: 배치 스크립트 (우선순위 🟡)
- [ ] `src/batch_ocr_vl.py` 생성
- [ ] Training set 배치 OCR-VL 처리
- [ ] 진행률 표시 (tqdm)
- [ ] outputs/training_ocr_vl.json 저장

### Phase 4: 예측 스크립트 (우선순위 🟡)
- [ ] `src/predict_ocr_classify.py` 생성
- [ ] Testing set 처리 (OCR-VL + 분류)
- [ ] predictions.json 저장 (LLM 팀 전달용)

### Phase 5: 테스트 (우선순위 🔥)
- [ ] test_samples로 단일 문서 테스트
- [ ] 전체 파이프라인 테스트
- [ ] 출력 JSON 형식 검증

---

## 🚀 해커톤 당일 워크플로우

### Phase 1: 데이터 수신 (10분)
```bash
# training_set, testing_set 다운로드
# labels.csv 확인
```

### Phase 2: Training Set OCR-VL (40-50분)
```bash
python src/batch_ocr_vl.py \
  --input training_set/documents \
  --output outputs/training_ocr_vl.json

# 진행률: 500개 문서 → 약 40-50분
```

### Phase 3: 분류 모델 학습 (60분)
```bash
python src/train_classifier.py \
  --labels training_set/labels.csv \
  --ocr outputs/training_ocr_vl.json \
  --output models/classifier

# Epoch 1/3: Accuracy=72%
# Epoch 2/3: Accuracy=91%
# Epoch 3/3: Accuracy=96%
```

### Phase 4: Testing Set 처리 (20-30분)
```bash
python src/predict_ocr_classify.py \
  --input testing_set/documents \
  --classifier models/classifier \
  --output predictions_for_llm.json

# 100개 문서 → 약 20-30분
```

### Phase 5: LLM 팀에게 전달 (10분)
```bash
# predictions_for_llm.json 확인
python -c "
import json
with open('predictions_for_llm.json') as f:
    data = json.load(f)
    print(f'Total: {len(data)} documents')
    print(f'Sample: {json.dumps(data[0], indent=2)[:500]}')
"

# LLM 팀에게 파일 전달!
```

**총 시간: 140-160분 (2시간 20분 ~ 2시간 40분)**

---

## 💻 코드 스켈레톤

### 1. `src/ocr_vl_module.py`

```python
from paddleocr import PaddleOCR
import time
from pathlib import Path

class OCRVLModule:
    def __init__(self, use_gpu=True):
        """PaddleOCR-VL 초기화"""
        print("Initializing PaddleOCR-VL...")
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            use_gpu=use_gpu,
            show_log=False
        )
        print("OCR-VL ready!")
    
    def process_document(self, image_path):
        """
        이미지에서 텍스트 + 레이아웃 추출
        
        Returns:
        {
            "full_text": str,
            "layout": dict,
            "confidence": float,
            "processing_time": float
        }
        """
        start_time = time.time()
        
        # OCR 실행
        result = self.ocr.ocr(str(image_path), cls=True)
        
        if not result or not result[0]:
            return {
                "full_text": "",
                "layout": {},
                "confidence": 0.0,
                "processing_time": time.time() - start_time,
                "error": "No text detected"
            }
        
        # 텍스트 추출
        full_text = self._extract_text(result)
        
        # 레이아웃 파싱
        layout = self._parse_layout(result)
        
        # 평균 신뢰도 계산
        confidences = [line[1][1] for line in result[0]]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "full_text": full_text,
            "layout": layout,
            "confidence": avg_confidence,
            "processing_time": time.time() - start_time
        }
    
    def _extract_text(self, ocr_result):
        """전체 텍스트 추출"""
        lines = []
        for line in ocr_result[0]:
            bbox, (text, conf) = line
            lines.append(text)
        return '\n'.join(lines)
    
    def _parse_layout(self, ocr_result):
        """
        레이아웃 정보 파싱
        - 제목 식별
        - 섹션 구분
        - 테이블 감지
        - 키-값 쌍 식별
        """
        layout = {
            "title": None,
            "sections": [],
            "tables": [],
            "features": {}
        }
        
        lines = ocr_result[0]
        
        # 첫 줄을 제목으로 (큰 폰트, 상단)
        if lines:
            first_line = lines[0]
            bbox, (text, conf) = first_line
            if self._is_title(bbox, text):
                layout["title"] = text
        
        # 키-값 쌍 식별
        key_value_pairs = 0
        for line in lines:
            bbox, (text, conf) = line
            if ':' in text or 'No' in text:
                key_value_pairs += 1
                layout["sections"].append({
                    "type": "key_value",
                    "text": text,
                    "position": bbox[0]  # 좌상단 좌표
                })
        
        # Features
        layout["features"] = {
            "has_table": self._detect_table(lines),
            "num_key_value_pairs": key_value_pairs,
            "text_density": len(lines) / 100.0  # 간단한 밀도 계산
        }
        
        return layout
    
    def _is_title(self, bbox, text):
        """제목인지 판단 (상단 + 짧은 텍스트)"""
        y_position = bbox[0][1]  # 좌상단 y 좌표
        return y_position < 100 and len(text.split()) <= 5
    
    def _detect_table(self, lines):
        """테이블 존재 여부 감지 (간단한 휴리스틱)"""
        # 숫자가 많거나, 여러 열로 정렬된 경우
        numeric_lines = sum(1 for line in lines if any(c.isdigit() for c in line[1][0]))
        return numeric_lines > len(lines) * 0.3

# 테스트
if __name__ == "__main__":
    ocr_vl = OCRVLModule()
    result = ocr_vl.process_document("test_samples/invoice1.jpg")
    
    print(f"Text length: {len(result['full_text'])}")
    print(f"Title: {result['layout']['title']}")
    print(f"Confidence: {result['confidence']:.2%}")
```

### 2. `src/batch_ocr_vl.py`

```python
from ocr_vl_module import OCRVLModule
from pathlib import Path
import json
import argparse
from tqdm import tqdm

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input directory')
    parser.add_argument('--output', required=True, help='Output JSON file')
    args = parser.parse_args()
    
    # OCR-VL 초기화
    print("Initializing OCR-VL...")
    ocr_vl = OCRVLModule(use_gpu=True)
    
    # 파일 수집
    input_dir = Path(args.input)
    files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.pdf']:
        files.extend(input_dir.glob(ext))
    
    print(f"Found {len(files)} files")
    
    # 배치 처리
    results = {}
    errors = []
    
    for file_path in tqdm(files, desc="Processing"):
        try:
            result = ocr_vl.process_document(str(file_path))
            
            if 'error' not in result:
                results[file_path.name] = result
            else:
                errors.append(file_path.name)
        
        except Exception as e:
            print(f"\nError processing {file_path.name}: {e}")
            errors.append(file_path.name)
    
    # 결과 저장
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 통계
    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Total files: {len(files)}")
    print(f"Successful: {len(results)}")
    print(f"Errors: {len(errors)}")
    
    if results:
        avg_conf = sum(r['confidence'] for r in results.values()) / len(results)
        print(f"Average confidence: {avg_conf:.2%}")
    
    print(f"\nSaved to: {args.output}")

if __name__ == "__main__":
    main()
```

### 3. `src/predict_ocr_classify.py`

```python
from ocr_vl_module import OCRVLModule
from classification_module import DocumentClassifier
from pathlib import Path
import json
import argparse
from tqdm import tqdm

def prepare_classification_input(ocr_result):
    """레이아웃 정보를 텍스트에 추가"""
    text = ocr_result['full_text']
    layout = ocr_result['layout']
    
    layout_info = f"""
[LAYOUT_INFO]
Title: {layout.get('title', 'None')}
Has_Table: {layout.get('features', {}).get('has_table', False)}
Key_Value_Pairs: {layout.get('features', {}).get('num_key_value_pairs', 0)}
Text_Density: {layout.get('features', {}).get('text_density', 0):.2f}
[END_LAYOUT_INFO]
"""
    
    return text[:2000] + "\n\n" + layout_info

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input directory')
    parser.add_argument('--classifier', required=True, help='Classifier model path')
    parser.add_argument('--output', required=True, help='Output JSON file')
    args = parser.parse_args()
    
    # 모듈 초기화
    print("Initializing modules...")
    ocr_vl = OCRVLModule(use_gpu=True)
    classifier = DocumentClassifier()
    classifier.load_model(args.classifier)
    print("Modules ready!")
    
    # 파일 수집
    input_dir = Path(args.input)
    files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.pdf']:
        files.extend(input_dir.glob(ext))
    
    print(f"Found {len(files)} files\n")
    
    # 배치 처리
    results = []
    
    for file_path in tqdm(files, desc="Processing"):
        try:
            # Step 1: OCR-VL
            ocr_result = ocr_vl.process_document(str(file_path))
            
            if 'error' in ocr_result:
                print(f"\nOCR error: {file_path.name}")
                continue
            
            # Step 2: Classification
            enhanced_text = prepare_classification_input(ocr_result)
            classification = classifier.classify(enhanced_text)
            
            # Step 3: 결과 조합 (LLM 팀 전달용)
            output = {
                "filename": file_path.name,
                "full_text_ocr": ocr_result['full_text'],
                "ocr_confidence": ocr_result['confidence'],
                "layout": ocr_result['layout'],
                "classification": classification,
                "processing_time": ocr_result['processing_time']
            }
            
            results.append(output)
        
        except Exception as e:
            print(f"\nError processing {file_path.name}: {e}")
    
    # 결과 저장
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 통계
    print("\n" + "="*60)
    print("Processing Complete!")
    print("="*60)
    print(f"Total files: {len(files)}")
    print(f"Processed: {len(results)}")
    
    if results:
        from collections import Counter
        types = [r['classification']['doc_type'] for r in results]
        print(f"\nDocument types:")
        for dtype, count in Counter(types).items():
            print(f"  {dtype}: {count}")
        
        avg_conf = sum(r['classification']['confidence'] for r in results) / len(results)
        print(f"\nAverage classification confidence: {avg_conf:.2%}")
    
    print(f"\nSaved to: {args.output}")
    print("→ 이 파일을 LLM 팀에게 전달하세요!")

if __name__ == "__main__":
    main()
```

---

## ⏱️ 시간 추정

| 작업 | 예상 시간 |
|------|----------|
| OCR-VL 모듈 개발 | 3-4시간 |
| 분류 모듈 확인/수정 | 30분-1시간 |
| 배치 스크립트 작성 | 1-2시간 |
| 예측 스크립트 작성 | 1-2시간 |
| 테스트 및 디버깅 | 2-3시간 |
| **총 개발 시간** | **8-12시간** |

**추천 일정:**
- Day 1: OCR-VL 모듈 개발 (4시간)
- Day 2: 스크립트 작성 (3시간)
- Day 3: 통합 테스트 (2시간)

---

## ✅ 다음 단계

### 즉시:
```bash
# 1. PaddleOCR 테스트
python -c "from paddleocr import PaddleOCR; print('OK')"

# 2. test_samples 확인
ls test_samples/
```

### 오늘:
```bash
# src/ocr_vl_module.py 작성 시작
touch src/ocr_vl_module.py
```

### 내일:
```bash
# 스크립트 작성
touch src/batch_ocr_vl.py
touch src/predict_ocr_classify.py
```

---

**훨씬 간단해졌죠? LLM 부분은 신경 쓸 필요 없습니다! 🎉**

