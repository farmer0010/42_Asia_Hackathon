# 해커톤 당일 실행 가이드 🏃‍♂️

## ⏰ 타임라인 (총 2시간 기준)

```
┌─────────────────────────────────────────────────────────┐
│  00:00 ~ 00:10 (10분)  │  데이터 확인 및 환경 준비      │
├─────────────────────────────────────────────────────────┤
│  00:10 ~ 00:50 (40분)  │  Training set OCR 처리         │
├─────────────────────────────────────────────────────────┤
│  00:50 ~ 01:50 (60분)  │  분류 모델 학습                │
├─────────────────────────────────────────────────────────┤
│  01:50 ~ 02:10 (20분)  │  Testing set 예측 및 검증      │
├─────────────────────────────────────────────────────────┤
│  02:10 ~ 02:20 (10분)  │  결과 제출 및 여유 시간        │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 사전 준비 (해커톤 시작 전)

### ⚠️ 처음 환경 설정하는 경우

**venv가 없거나 새 컴퓨터라면:**

```bash
# Python 3.11 설치 확인
python3.11 --version

# 없으면 설치
brew install python@3.11

# 가상환경 생성 + 패키지 설치
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5-10분 대기...
```

**자세한 설명은 → [README.md](./README.md)의 "0단계" 참고**

---

### ✅ 체크리스트

```bash
# 1. 가상환경 테스트
source venv/bin/activate
python --version  # Python 3.11.x 확인

# 2. 패키지 확인
python -c "from src.ocr_module import OCRModule; print('✓ OCR OK')"
python -c "from src.classification_module import DocumentClassifier; print('✓ Classifier OK')"
python -c "from src.extraction_module import DataExtractor; print('✓ Extractor OK')"

# 3. 테스트 샘플 실행
python src/batch_ocr.py --input test_samples --output test_ocr.json
# → 에러 없이 완료되면 OK!

# 4. 디렉토리 생성
mkdir -p outputs
mkdir -p models
```

### 📋 준비물

- [ ] 노트북 충전 완료
- [ ] 인터넷 연결 확인
- [ ] 이 가이드 출력 또는 북마크
- [ ] 명령어 템플릿 복사 (아래에 있음)
- [ ] 팀원과 역할 분담 완료

---

## 🎬 해커톤 시작! (Step by Step)

### Step 0: 데이터 수신 및 확인 (10분)

#### 받는 데이터

```
provided_data/
├── training_set/
│   ├── documents/        # 500-1000개 문서
│   │   ├── doc001.jpg
│   │   ├── doc002.pdf
│   │   └── ...
│   └── labels.csv       # 정답 레이블
│
└── testing_set/
    └── documents/        # 100개 문서 (레이블 없음!)
        ├── test001.jpg
        └── ...
```

#### labels.csv 구조 확인

```bash
# labels.csv 열기
head -n 5 training_set/labels.csv
```

**예상 출력 1 (Invoice/Receipt)**:
```csv
filename,doc_type,vendor,amount,date
doc001.jpg,invoice,ABC Company,1500.75,2025-01-01
doc002.png,receipt,SuperMart,89.90,2025-01-02
```

**예상 출력 2 (Resume)** ⚠️:
```csv
filename,doc_type,name,experience,education
doc001.pdf,resume,John Smith,5 years,MIT
```

**중요**: 컬럼을 확인하세요!
- `vendor, amount, date` → Invoice/Receipt (예상대로)
- `name, experience, education` → Resume (예상 밖!)
- 다른 필드면 → 긴급 수정 필요 (나중에 설명)

#### 샘플 확인

```bash
# 문서 개수 확인
ls training_set/documents | wc -l   # 500-1000개?
ls testing_set/documents | wc -l    # 100개?

# 샘플 1-2개 눈으로 확인
open training_set/documents/doc001.jpg  # Mac
# 또는
xdg-open training_set/documents/doc001.jpg  # Linux
```

**확인사항**:
- [ ] 이미지가 흐릿하지 않은가?
- [ ] 회전되어 있지 않은가?
- [ ] PDF가 스캔본인가 텍스트 PDF인가?

---

### Step 1: Training Set OCR (40분)

**목표**: training_set의 모든 문서를 OCR 처리

#### 명령어 (복사 후 실행)

```bash
# 가상환경 활성화 (터미널 새로 열었으면)
source venv/bin/activate

# OCR 실행 (500개 기준 30-40분 소요)
python src/batch_ocr.py \
  --input training_set/documents \
  --output outputs/training_ocr.json

# 완료되면 파일 크기 확인
ls -lh outputs/training_ocr.json
# → 1-5MB 정도면 정상
```

#### 진행 중 출력

```
Scanning files...
Found 500 documents

OCR Progress: 100%|████████████| 500/500 [35:23<00:00,  4.23s/doc]

✓ Processed: 497 documents
✗ Errors: 3 documents

Statistics:
  Total files: 500
  Successful: 497
  Failed: 3
  Average confidence: 94.2%
  Total time: 35m 23s

Saved to: outputs/training_ocr.json
```

#### 에러 발생 시

**에러: "Out of memory"**
```bash
# 파일을 2개로 나눠서 처리
mkdir training_set/documents_part1
mkdir training_set/documents_part2
# ... 파일 절반씩 옮기기 ...

# 각각 OCR
python src/batch_ocr.py --input training_set/documents_part1 --output outputs/ocr1.json
python src/batch_ocr.py --input training_set/documents_part2 --output outputs/ocr2.json

# JSON 합치기
python -c "
import json
with open('outputs/ocr1.json') as f1, open('outputs/ocr2.json') as f2:
    data1 = json.load(f1)
    data2 = json.load(f2)
    combined = data1 + data2
    with open('outputs/training_ocr.json', 'w') as out:
        json.dump(combined, out)
"
```

#### OCR 중 할 일

OCR은 시간이 오래 걸립니다. 기다리는 동안:

1. **Testing set 샘플 확인**: 어떤 문서들인지 미리 보기
2. **LLM 팀과 소통**: JSON 형식 최종 확인
3. **labels.csv 재확인**: 컬럼 이름이 이상하면 대응 준비
4. **휴식**: 커피 한잔 ☕

---

### Step 2: 분류 모델 학습 (60분)

**목표**: DistilBERT 모델을 training_set으로 학습

#### 명령어

```bash
# 학습 시작 (500-1000개 기준 30-60분)
python src/train_classifier.py \
  --labels training_set/labels.csv \
  --ocr outputs/training_ocr.json \
  --output models/classifier
```

#### 진행 중 출력

```
============================================================
Training Classification Model
============================================================

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
  Loss: 0.892 | Accuracy: 72.3%
Epoch 2/3:
  Loss: 0.234 | Accuracy: 91.5%
Epoch 3/3:
  Loss: 0.089 | Accuracy: 96.8%

Training complete!

Step 8: Saving model...
Model saved to models/classifier

============================================================
Training Complete!
============================================================
```

#### 학습 중 모니터링

**좋은 신호** ✅:
- Loss가 점점 감소 (0.8 → 0.2 → 0.08)
- Accuracy가 점점 증가 (70% → 90% → 96%)
- Epoch 3에서 Accuracy > 90%

**나쁜 신호** ⚠️:
- Loss가 증가하거나 변동 심함
- Accuracy가 70% 미만에서 멈춤
- "NaN" 에러 발생

**나쁜 신호 발생 시**:
```bash
# 학습 중단 (Ctrl+C)
# learning_rate 낮추기
# train_classifier.py 열어서 수정:
# learning_rate=2e-5 → learning_rate=5e-6
# 다시 실행
```

#### 학습 중 할 일

1. **Testing set OCR (선택)**: 미리 해두면 시간 절약
   ```bash
   # 새 터미널 열어서
   python src/batch_ocr.py \
     --input testing_set/documents \
     --output outputs/testing_ocr.json
   ```

2. **모델 검증 준비**: 샘플 1-2개로 테스트할 준비

---

### Step 3: Testing Set 예측 (20분)

**목표**: 학습된 모델로 testing_set 예측 → predictions.json 생성

#### 명령어

```bash
# 예측 실행 (100개 기준 10-20분)
python src/predict.py \
  --input testing_set/documents \
  --classifier models/classifier \
  --labels training_set/labels.csv \
  --output predictions.json
```

#### 진행 중 출력

```
============================================================
Batch Prediction for Testing Set
============================================================

Initializing modules...
Loading NER model...
Configuring extractor from training_set/labels.csv...
  invoice: ['vendor', 'amount', 'date']
  receipt: ['store', 'total', 'date']
Extraction configured for 2 document types
Modules ready!

Scanning files...
Found 100 documents

Processing documents...
Progress: 100%|████████████| 100/100 [12:34<00:00,  7.54s/doc]

Processed: 98 documents
Errors: 2 documents

Saved to: predictions.json
Errors saved to: predictions_errors.json
```

---

### Step 4: 결과 검증 (10분)

#### predictions.json 샘플 확인

```bash
# 처음 2개 문서 확인
python -c "
import json
with open('predictions.json') as f:
    data = json.load(f)
    for item in data[:2]:
        print(json.dumps(item, indent=2))
"
```

**예상 출력**:
```json
{
  "filename": "test001.jpg",
  "full_text_ocr": "Commercial Invoice\nCompany: ABC...",
  "ocr_confidence": 0.97,
  "classification": {
    "doc_type": "invoice",
    "confidence": 0.96
  },
  "extracted_data": {
    "vendor": "ABC Exports Ltd",
    "date": "2030-09-30",
    "total_amount": 13000.0,
    "currency": "USD"
  }
}
```

#### 체크리스트

- [ ] `filename`이 올바른가?
- [ ] `full_text_ocr`에 텍스트가 있는가?
- [ ] `classification.doc_type`이 합리적인가?
- [ ] `classification.confidence`가 80% 이상인가?
- [ ] `extracted_data`에 값이 있는가? (invoice/receipt인 경우)

#### 통계 확인

```bash
python -c "
import json
with open('predictions.json') as f:
    data = json.load(f)
    
print(f'Total predictions: {len(data)}')

# 문서 타입 분포
from collections import Counter
types = [d['classification']['doc_type'] for d in data]
print('\nDocument types:')
for dtype, count in Counter(types).items():
    print(f'  {dtype}: {count}')

# 평균 신뢰도
confidences = [d['classification']['confidence'] for d in data]
avg_conf = sum(confidences) / len(confidences)
print(f'\nAverage confidence: {avg_conf:.2%}')
"
```

**예상 출력**:
```
Total predictions: 98

Document types:
  invoice: 45
  receipt: 32
  resume: 15
  report: 6

Average confidence: 93.4%
```

---

### Step 5: 제출 준비 (10분)

#### 최종 파일 확인

```bash
# 파일 존재 및 크기 확인
ls -lh predictions.json
# → 100KB ~ 5MB 사이면 정상

# JSON 형식 검증
python -m json.tool predictions.json > /dev/null && echo "✓ Valid JSON"
```

#### 제출 전 최종 체크

```bash
# 예측 개수 = testing_set 개수?
python -c "import json; print(len(json.load(open('predictions.json'))))"
# vs
ls testing_set/documents | wc -l

# 두 숫자가 비슷해야 함 (에러 2-3개는 OK)
```

#### 백업 생성

```bash
# 만약을 위해 백업
cp predictions.json predictions_backup_$(date +%H%M).json
```

---

## 🚨 긴급 상황 대응

### 상황 1: labels.csv의 컬럼이 예상과 다름

**예**: `vendor, amount, date` 대신 `name, salary, position`

#### 해결책

**자동 대응** (추출 모듈이 자동으로 처리):
```bash
# 그냥 실행하면 자동으로 필드를 인식!
python src/predict.py \
  --input testing_set/documents \
  --classifier models/classifier \
  --labels training_set/labels.csv \
  --output predictions.json
```

extraction_module.py의 `configure_from_labels()`가:
1. labels.csv 열기
2. 컬럼 확인
3. 자동으로 추출 설정 조정

**수동 확인**:
```bash
# 추출 설정 확인
python -c "
from src.extraction_module import DataExtractor
extractor = DataExtractor()
extractor.configure_from_labels('training_set/labels.csv')
print(extractor.extraction_config)
"
# → {'resume': ['name', 'salary', 'position']} 출력되면 OK
```

---

### 상황 2: OCR 신뢰도가 너무 낮음 (< 70%)

#### 원인

- 이미지 품질 문제
- PDF가 스캔본이 아니라 텍스트 PDF

#### 해결책

```bash
# 신뢰도 낮은 파일 찾기
python -c "
import json
with open('outputs/training_ocr.json') as f:
    data = json.load(f)
    low_conf = [(item['filename'], item['confidence']) 
                for item in data if item['confidence'] < 0.7]
    for fname, conf in low_conf[:10]:
        print(f'{fname}: {conf:.2%}')
"

# 해당 파일들 수동 확인
# → 정말 흐릿하면 어쩔 수 없음
# → 회전되어 있으면 이미지 회전 후 재실행
```

---

### 상황 3: 분류 정확도가 낮음 (< 85%)

#### 해결책 1: Epoch 증가

```python
# src/train_classifier.py 수정
# 59번 줄:
num_train_epochs=3  → num_train_epochs=5
```

#### 해결책 2: Learning rate 감소

```python
# 61번 줄:
learning_rate=2e-5  → learning_rate=5e-6
```

---

### 상황 4: 추출 결과가 대부분 None

#### 원인

- NER 모델이 엔티티를 못 찾음
- 정규식 패턴이 맞지 않음

#### 해결책

```bash
# 샘플 1개로 디버깅
python -c "
from src.extraction_module import DataExtractor
extractor = DataExtractor()

text = '''
Invoice
Company: ABC Ltd
Total: 1500 USD
Date: 2025-01-01
'''

entities = extractor._run_ner(text)
print('Entities:', entities)

patterns = extractor._extract_patterns(text)
print('Patterns:', patterns)
"

# 엔티티와 패턴이 제대로 추출되는지 확인
# 안 되면 extraction_module.py 수정 필요
```

---

## 🎯 성공을 위한 팁

### 시간 관리

```
우선순위:
1. OCR (필수!) → 40분
2. 학습 (필수!) → 60분
3. 예측 (필수!) → 20분
───────────────────────────
총 120분 (2시간)

여유 시간: 20분
```

**만약 시간이 부족하면**:
- Epoch 감소: 3 → 2 (10-20분 절약)
- Testing set OCR 병렬 실행 (10분 절약)

### 팀 역할 분담

**담당자 1 (AI 담당)**:
- OCR 실행 및 모니터링
- 모델 학습 및 검증
- 에러 발생 시 디버깅

**담당자 2 (데이터 담당)**:
- labels.csv 분석
- 샘플 문서 확인
- 결과 검증 및 통계

**담당자 3 (협업 담당)**:
- LLM 팀과 소통
- JSON 형식 확인
- 백업 및 제출 준비

### 커뮤니케이션

**LLM 팀에게 미리 알려주기**:
```json
{
  "filename": "문서 파일명",
  "full_text_ocr": "전체 OCR 텍스트 (요약/PII 검출에 사용)",
  "classification": {
    "doc_type": "문서 타입 (invoice/receipt/...)",
    "confidence": "분류 신뢰도"
  },
  "extracted_data": {
    "vendor": "구조화된 추출 결과 (invoice/receipt만)",
    "amount": 1500.75,
    "date": "2025-01-01"
  }
}
```

**질문 예상**:
- Q: "full_text_ocr이 왜 이렇게 길어요?"
  - A: "원본 텍스트 그대로입니다. 요약은 LLM이 해주세요."
  
- Q: "extracted_data가 비어있는 문서가 있어요"
  - A: "resume, report, contract는 추출 안 합니다. full_text_ocr 사용해주세요."

---

## 🎊 완료!

### 제출 전 최종 체크리스트

- [ ] predictions.json 파일 존재
- [ ] JSON 형식 검증 완료
- [ ] 예측 개수 = testing_set 개수 (±5개 이내)
- [ ] 샘플 2-3개 육안 확인
- [ ] 평균 신뢰도 > 85%
- [ ] 백업 파일 생성 완료
- [ ] LLM 팀에게 형식 전달 완료

### 제출 후

1. **로그 저장**: 모든 터미널 출력 복사해서 저장
2. **통계 기록**: 정확도, 처리 시간 등 기록
3. **팀 피드백**: 어떤 부분이 어려웠는지 공유

---

## 📞 추가 도움이 필요하면

- **ARCHITECTURE.md**: 함수별 상세 설명
- **README.md**: 프로젝트 전체 개요
- **긴급_수정_가이드.md**: 코드 수정이 필요한 경우

---

**화이팅! 🚀 성공을 기원합니다!**

