# 시스템 아키텍처 📐

## 📋 목차

1. [전체 데이터 흐름](#전체-데이터-흐름)
2. [모듈별 상세 설명](#모듈별-상세-설명)
3. [함수별 설명](#함수별-설명)
4. [테스트 가이드](#테스트-가이드)
5. [성능 및 최적화](#성능-및-최적화)

---

## 🌊 전체 데이터 흐름

### 시각적 흐름도

```
┌─────────────────┐
│  문서 이미지     │ (invoice.jpg, receipt.png, ...)
│  (JPG/PNG/PDF)  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  1단계: OCR (ocr_module.py)                         │
│  ─────────────────────────────────────────────      │
│  • PaddleOCR 사용                                   │
│  • 이미지 전처리 (회색조, 노이즈 제거, CLAHE)         │
│  • PDF → 이미지 변환                                 │
│  • 텍스트 추출                                       │
└────────┬─────────────────────────────────────────────┘
         │ {"text": "Invoice\nCompany: ABC...", 
         │  "confidence": 0.97}
         ▼
┌─────────────────────────────────────────────────────┐
│  2단계: 분류 (classification_module.py)             │
│  ─────────────────────────────────────────────      │
│  • DistilBERT 사용                                  │
│  • 텍스트 → 토큰화 → 벡터                            │
│  • 5가지 문서 타입 중 하나로 분류                     │
│    (invoice, receipt, resume, report, contract)     │
└────────┬─────────────────────────────────────────────┘
         │ {"doc_type": "invoice", 
         │  "confidence": 0.96}
         ▼
┌─────────────────────────────────────────────────────┐
│  3단계: 추출 (extraction_module.py)                 │
│  ─────────────────────────────────────────────      │
│  • BERT-NER 사용                                    │
│  • 문서 타입에 따라 다른 정보 추출                    │
│  • invoice/receipt만 구조화 추출                     │
│  • 나머지는 빈 객체 {}                               │
└────────┬─────────────────────────────────────────────┘
         │ {"vendor": "ABC Exports", 
         │  "amount": 13000.0, 
         │  "date": "2030-09-30"}
         ▼
┌─────────────────────────────────────────────────────┐
│  최종 JSON 출력                                      │
│  ─────────────────────────────────────────────      │
│  {                                                  │
│    "filename": "invoice.jpg",                       │
│    "full_text_ocr": "...",                          │
│    "classification": {...},                         │
│    "extracted_data": {...}                          │
│  }                                                  │
└─────────────────────────────────────────────────────┘
```

---

## 📦 모듈별 상세 설명

### 1. `ocr_module.py` - OCR 텍스트 추출

**역할**: 이미지/PDF에서 텍스트를 읽어냅니다

**사용 기술**: PaddleOCR (중국 Baidu에서 만든 오픈소스 OCR)

**핵심 클래스**: `OCRModule`

#### 왜 PaddleOCR?
- ✅ CPU에서도 빠름
- ✅ 영어 + 한글 + 중국어 지원
- ✅ 손글씨 어느정도 인식
- ✅ 설치 간단

#### 처리 과정

```python
입력 이미지 
  → 회색조 변환 (색상 제거, 텍스트 강조)
  → 노이즈 제거 (얼룩 제거)
  → CLAHE (명암 대비 향상)
  → PaddleOCR 실행
  → 텍스트 + 신뢰도 반환
```

#### 주요 함수

**`__init__()`**
```python
def __init__(self):
    self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
```
- PaddleOCR 모델 초기화
- `use_angle_cls=True`: 회전된 텍스트도 인식
- `lang='en'`: 영어 모델 사용

**`preprocess_image(image_path)`**
```python
def preprocess_image(self, image_path):
    # 1. 이미지 로드
    img = cv2.imread(image_path)
    
    # 2. 회색조 변환 (BGR → Gray)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 3. 노이즈 제거 (얼룩 제거)
    denoised = cv2.fastNlMeansDenoising(gray)
    
    # 4. CLAHE (명암 대비 향상)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    return enhanced
```
- **왜 회색조?** OCR은 색상이 필요없고, 흑백이 더 정확
- **왜 노이즈 제거?** 스캔 문서의 얼룩이 글자로 오인될 수 있음
- **CLAHE가 뭐지?** Contrast Limited Adaptive Histogram Equalization - 어두운 부분을 밝게, 밝은 부분을 어둡게 해서 텍스트 명확하게

**`extract_text(file_path)`** (핵심!)
```python
def extract_text(self, file_path):
    # PDF면 이미지로 변환
    if file_path.endswith('.pdf'):
        img = self.pdf_to_image(file_path)
    else:
        img = self.preprocess_image(file_path)
    
    # OCR 실행
    result = self.ocr.ocr(img, cls=False)
    
    # 결과 파싱
    lines = []
    confidences = []
    for line in result[0]:
        bbox, (text, conf) = line
        lines.append(text)
        confidences.append(conf)
    
    return {
        'text': '\n'.join(lines),
        'confidence': avg(confidences),
        'processing_time': elapsed_time
    }
```

**반환 예시**:
```json
{
  "text": "Commercial Invoice\nCompany: ABC...",
  "confidence": 0.97,
  "processing_time": 2.3
}
```

---

### 2. `classification_module.py` - 문서 분류

**역할**: OCR로 추출한 텍스트를 보고 문서 종류를 판단합니다

**사용 기술**: DistilBERT (BERT의 경량화 버전)

**핵심 클래스**: `DocumentClassifier`

#### 왜 DistilBERT?
- ✅ BERT보다 40% 빠름
- ✅ 메모리 60% 절약
- ✅ 정확도는 BERT의 97% 유지
- ✅ CPU에서도 실용적

#### AI 학습 원리 (초보자용 설명)

**비유**: 강아지 vs 고양이 구분 학습

```
학습 전:
사진 보여주면 → "모르겠어요..." 😵

학습 데이터:
[사진1, "강아지"] ← 정답 알려줌
[사진2, "고양이"]
[사진3, "강아지"]
... 1000번 반복 ...

학습 후:
새로운 사진 보여주면 → "이건 강아지! (95% 확신)" 🎯
```

**우리 프로젝트**:
```
학습 데이터:
["Invoice text...", "invoice"] ← labels.csv의 정답
["Receipt text...", "receipt"]
... 500-1000개 ...

학습 후:
새 문서 텍스트 보여주면 → "invoice입니다! (96% 확신)"
```

#### 주요 함수

**`__init__()`**
```python
def __init__(self):
    self.model_name = 'distilbert-base-uncased'
    self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
    self.labels = ['invoice', 'receipt', 'resume', 'report', 'contract']
    self.model = None  # 학습 or 로드 전까지 None
```

**`train(labels_csv_path, ocr_results_path, output_dir)`** (중요!)

이 함수가 AI를 학습시킵니다!

```python
def train(self, labels_csv, ocr_results, output_dir):
    # Step 1: 데이터 로드
    df = pd.read_csv(labels_csv)  # 정답 레이블
    ocr = json.load(ocr_results)  # OCR 텍스트
    
    # Step 2: 학습 데이터 준비
    texts = []
    labels = []
    for _, row in df.iterrows():
        filename = row['filename']
        doc_type = row['doc_type']
        text = ocr[filename]['text']
        
        texts.append(text)
        labels.append(self.label_to_id[doc_type])
    
    # Step 3: Dataset 생성 (AI가 읽을 수 있는 형식)
    dataset = Dataset.from_dict({
        'text': texts,
        'label': labels
    })
    
    # Step 4: Tokenization (단어 → 숫자)
    def tokenize_function(examples):
        return self.tokenizer(
            examples['text'],
            padding='max_length',
            truncation=True,
            max_length=512
        )
    tokenized_dataset = dataset.map(tokenize_function, batched=True)
    
    # Step 5: 모델 초기화
    self.model = DistilBertForSequenceClassification.from_pretrained(
        self.model_name,
        num_labels=5  # 5가지 문서 타입
    )
    
    # Step 6: 학습 설정
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,      # 전체 데이터 3번 반복
        per_device_train_batch_size=8,  # 한번에 8개씩
        learning_rate=2e-5,      # 학습 속도
    )
    
    # Step 7: 학습 실행! (30-60분)
    trainer = Trainer(
        model=self.model,
        args=training_args,
        train_dataset=tokenized_dataset,
    )
    trainer.train()  # 실제 학습 시작
    
    # Step 8: 모델 저장
    self.save_model(output_dir)
```

**학습 과정 설명**:

1. **Epoch 1 (1번째 반복)**
   - 모델: "Invoice는 아마 'invoice' 일까?" (60% 확신)
   - 정답: "맞아!" → 모델 조금 개선

2. **Epoch 2 (2번째 반복)**
   - 모델: "Invoice는 'invoice'!" (85% 확신)
   - 정답: "맞아!" → 모델 더 개선

3. **Epoch 3 (3번째 반복)**
   - 모델: "Invoice는 'invoice'!" (96% 확신)
   - 정답: "맞아!" → 학습 완료!

**`classify(text)`** (예측!)

학습된 모델로 새 문서 분류:

```python
def classify(self, text):
    # 1. 텍스트 → 숫자 (토큰화)
    inputs = self.tokenizer(text, return_tensors='pt', 
                            truncation=True, max_length=512)
    
    # 2. 모델 실행
    with torch.no_grad():
        outputs = self.model(**inputs)
    
    # 3. 결과 해석
    logits = outputs.logits[0]
    probabilities = torch.nn.functional.softmax(logits, dim=0)
    
    # 4. 가장 높은 확률의 클래스 선택
    predicted_id = torch.argmax(probabilities).item()
    confidence = probabilities[predicted_id].item()
    
    return {
        'doc_type': self.id_to_label[predicted_id],
        'confidence': confidence
    }
```

**예시**:
```python
text = "Commercial Invoice\nCompany: ABC..."
result = classifier.classify(text)
# {"doc_type": "invoice", "confidence": 0.96}
```

---

### 3. `extraction_module.py` - 구조화된 정보 추출

**역할**: 텍스트에서 특정 정보(금액, 날짜, 회사명 등)를 찾아냅니다

**사용 기술**: BERT-NER (Named Entity Recognition)

**핵심 클래스**: `DataExtractor`

#### NER이 뭔가요?

**비유**: 형광펜으로 중요 부분 표시하기

```
텍스트: "John Smith works at Apple in New York."

사람이 보면:
- "John Smith" → 사람 이름
- "Apple" → 회사
- "New York" → 장소

NER 모델:
- "John Smith" → [PER] (Person)
- "Apple" → [ORG] (Organization)
- "New York" → [LOC] (Location)
```

#### 주요 함수

**`configure_from_labels(labels_csv)`** (핵심!)

labels.csv를 보고 무엇을 추출할지 자동으로 파악:

```python
def configure_from_labels(self, labels_csv):
    df = pd.read_csv(labels_csv)
    
    # labels.csv 예시:
    # filename, doc_type, vendor, amount, date
    # inv1.pdf, invoice, ABC, 1500, 2025-01-01
    
    for doc_type in df['doc_type'].unique():
        # 'filename', 'doc_type' 제외한 나머지가 추출할 필드
        fields = [col for col in df.columns 
                  if col not in ['filename', 'doc_type']]
        
        self.extraction_config[doc_type] = fields
    
    # 결과:
    # self.extraction_config = {
    #     'invoice': ['vendor', 'amount', 'date'],
    #     'receipt': ['store', 'total', 'date']
    # }
```

**왜 동적으로?**
- 해커톤 당일 labels.csv가 어떻게 나올지 모름
- invoice가 아니라 resume일 수도 있음
- 필드가 'vendor'가 아니라 'company'일 수도 있음
- → 자동으로 적응!

**`_run_ner(text)`** (NER 실행)

```python
def _run_ner(self, text):
    # 1. BERT 모델에 텍스트 입력
    tokens = self.tokenizer(text, return_tensors='pt')
    outputs = self.model(**tokens)
    
    # 2. 각 단어에 레이블 예측
    predictions = torch.argmax(outputs.logits, dim=2)
    
    # 3. 엔티티 분류
    entities = {'PER': [], 'ORG': [], 'LOC': [], 'MISC': []}
    
    for token, label in zip(tokens, predictions):
        if label == 'B-PER':  # Person 시작
            entities['PER'].append(token)
        elif label == 'B-ORG':  # Organization 시작
            entities['ORG'].append(token)
        # ...
    
    return entities
    # {'PER': ['John Smith'], 'ORG': ['ABC Exports'], ...}
```

**`extract(text, doc_type)`** (최종 추출)

```python
def extract(self, text, doc_type):
    # 이 문서 타입은 추출 안 함 (resume, report 등)
    if doc_type not in self.extraction_config:
        return {}
    
    # NER로 엔티티 찾기
    entities = self._run_ner(text)
    # {'PER': [], 'ORG': ['ABC Exports'], ...}
    
    # 정규식으로 날짜/금액 패턴 찾기
    patterns = self._extract_patterns(text)
    # {'dates': ['2030-09-30'], 'amounts': ['$13,000'], ...}
    
    # 필드별로 적절한 값 매칭
    result = {}
    for field in self.extraction_config[doc_type]:
        # 'vendor' 필드 → ORG 엔티티 사용
        # 'amount' 필드 → 패턴에서 가장 큰 금액
        # 'date' 필드 → 패턴에서 첫 날짜
        result[field] = self._match_field(field, entities, patterns)
    
    return result
    # {'vendor': 'ABC Exports', 'amount': 13000, 'date': '2030-09-30'}
```

---

### 4. `batch_ocr.py` - 일괄 OCR 처리

**역할**: 폴더 안의 모든 문서를 한번에 OCR 처리

**언제 사용?**: 해커톤 당일 training_set/testing_set 받았을 때

```python
python src/batch_ocr.py \
  --input training_set/documents \
  --output outputs/training_ocr.json
```

**동작**:
```python
# 1. 폴더 스캔
files = ['doc1.jpg', 'doc2.png', 'doc3.pdf', ...]

# 2. 각 파일 OCR (진행바 표시)
for file in tqdm(files):
    result = ocr.extract_text(file)
    results[file.name] = result

# 3. JSON 저장
# {
#   "doc1.jpg": {"text": "...", "confidence": 0.97},
#   "doc2.png": {"text": "...", "confidence": 0.95},
#   ...
# }
```

---

### 5. `train_classifier.py` - 분류 모델 학습

**역할**: DocumentClassifier.train()을 명령줄에서 실행

```python
python src/train_classifier.py \
  --labels training_set/labels.csv \
  --ocr outputs/training_ocr.json \
  --output models/classifier
```

**내부 동작**:
```python
classifier = DocumentClassifier()
classifier.train(
    labels_csv_path=args.labels,
    ocr_results_path=args.ocr,
    output_dir=args.output
)
```

---

### 6. `main.py` - 통합 파이프라인 (단일 문서)

**역할**: OCR + 분류 + 추출을 한번에 실행

```python
python src/main.py \
  --input invoice.jpg \
  --classifier models/classifier \
  --output result.json
```

**핵심 함수**: `process_document()`

```python
def process_document(image_path, ocr, classifier, extractor):
    # Step 1: OCR
    ocr_result = ocr.extract_text(image_path)
    
    # Step 2: 분류
    classification = classifier.classify(ocr_result['text'])
    
    # Step 3: 추출
    extracted_data = {}
    if extractor:
        extracted_data = extractor.extract(
            ocr_result['text'],
            classification['doc_type']
        )
    
    # Step 4: 결과 조합
    return {
        'filename': filename,
        'full_text_ocr': ocr_result['text'],
        'classification': classification,
        'extracted_data': extracted_data
    }
```

---

### 7. `predict.py` - 일괄 예측 (제출용)

**역할**: testing_set 전체를 처리해서 predictions.json 생성

```python
python src/predict.py \
  --input testing_set/documents \
  --classifier models/classifier \
  --labels training_set/labels.csv \
  --output predictions.json
```

**동작**:
```python
# 1. 모듈 초기화
ocr = OCRModule()
classifier = DocumentClassifier()
classifier.load_model(args.classifier)
extractor = DataExtractor()
extractor.configure_from_labels(args.labels)

# 2. 모든 문서 처리
results = []
for file in files:
    result = process_document(file, ocr, classifier, extractor)
    results.append(result)

# 3. JSON 저장
json.dump(results, open(args.output, 'w'))
```

---

## 🧪 테스트 가이드

### 테스트 1: OCR만 테스트

```bash
python -c "
from src.ocr_module import OCRModule
ocr = OCRModule()
result = ocr.extract_text('test_samples/sample1.jpg')
print(result)
"
```

**예상 출력**:
```json
{
  "text": "Commercial Invoice\nCompany: ABC Exports...",
  "confidence": 0.97,
  "processing_time": 2.3
}
```

**해석**:
- `confidence: 0.97` → 97% 신뢰도, 매우 좋음!
- `processing_time: 2.3` → 2.3초 걸림

---

### 테스트 2: 추출 모듈 테스트

```bash
python quick_test.py
```

**예상 출력**:
```
============================================================
Testing Extraction Module
============================================================

[Step 1] Initializing...
Loading NER model...
✓ Success!

[Step 2] Testing NER...
Entities found:
  ORG: ['ABC Exports Ltd']

[Step 3] Testing patterns...
  Dates: []
  Amounts: ['$13,000.00']
  Currency: USD

============================================================
✓ All tests passed!
============================================================
```

**해석**:
- `ORG: ['ABC Exports Ltd']` → 회사명 찾음!
- `Amounts: ['$13,000.00']` → 금액 찾음!
- `Currency: USD` → 통화 감지!

---

### 테스트 3: 실제 OCR 데이터로 테스트

```bash
python test_with_ocr.py
```

**예상 출력**:
```
📄 sample1.jpg
   Text length: 1022 chars
   Confidence: 97.04%

   Entities found:
   → Organizations: ['ABC Exports Ltd', 'XYZ Importers Inc']
   → Persons: []
   → Locations: ['Export City', 'Import City']

   Patterns found:
   → Dates: ['2030-09-30']
   → Amounts: ['$5,000.00', '$4,500.00', '$13,000.00']
   → Currency: USD
```

**해석**:
- **Text length**: OCR로 추출한 글자 수
- **Confidence**: OCR 신뢰도 (90% 이상 좋음)
- **Organizations**: NER이 찾은 회사명
- **Amounts**: 정규식으로 찾은 모든 금액
- **가장 큰 금액** ($13,000)이 최종 'total_amount'가 됨

---

## 📊 성능 및 최적화

### 현재 성능 (M1 Mac 기준)

| 작업 | 시간 | 메모리 |
|------|------|--------|
| OCR (단일 문서) | 2-5초 | 200MB |
| 분류 (예측) | 0.3초 | 643MB |
| 추출 (예측) | 0.2초 | 433MB |
| **전체 파이프라인** | **3-6초** | **~1GB** |

### 대량 처리 (1000개 문서)

| 작업 | 예상 시간 |
|------|-----------|
| OCR (1000개) | 40-80분 |
| 분류 학습 (500-1000개) | 30-60분 |
| 예측 (100개) | 10-15분 |
| **전체 (OCR+학습+예측)** | **80-155분 (1.3-2.6시간)** |

### 최적화 팁

1. **OCR 병렬 처리**: 4개 코어 사용시 4배 빠름
2. **배치 크기 조정**: GPU 있으면 batch_size 16으로 증가
3. **Epoch 줄이기**: 시간 부족시 3 → 2로 감소 (정확도 약간 하락)

---

## 🐛 자주 발생하는 이슈

### 1. OCR 신뢰도 낮음 (< 80%)

**원인**: 이미지 품질 문제
- 흐릿함
- 회전됨
- 너무 작음

**해결**: 
```python
# ocr_module.py에서 전처리 강화
# CLAHE 파라미터 조정
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16,16))
```

### 2. 분류 정확도 낮음 (< 85%)

**원인**: 학습 데이터 부족 또는 품질 문제

**해결**:
- Epoch 증가: 3 → 5
- learning_rate 감소: 2e-5 → 5e-6
- 데이터 확인: labels.csv에 오류 없는지 체크

### 3. 추출 결과가 None

**원인**: NER이 엔티티를 못 찾음

**해결**:
- 정규식 패턴 추가
- _match_field()에 휴리스틱 추가

---

## 📚 추가 학습 자료

### AI 초보자
- [DistilBERT 논문 쉬운 설명](https://medium.com/@...)
- [NER이란 무엇인가](https://en.wikipedia.org/wiki/Named-entity_recognition)

### 코드 개선하고 싶다면
- Hugging Face Transformers 문서
- PaddleOCR GitHub

---

**다음 단계**: [HACKATHON_WORKFLOW.md](./HACKATHON_WORKFLOW.md)에서 해커톤 당일 실행 가이드 확인 →

