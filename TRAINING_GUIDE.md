# 🎓 학습 가이드 - JSON Groundtruth 사용법

## 📋 개요

이 프로젝트는 JSON 형식의 groundtruth 파일을 사용하여 문서 분류 모델을 학습합니다.

## 📁 Groundtruth 파일 구조

### 개별 파일

`config/` 폴더에는 5개의 groundtruth JSON 파일이 있습니다:

1. **groundtruth.json** - Invoice 데이터 (2000개)
2. **groundtruth2.json** - Passport 데이터 (2000개)  
3. **groundtruth3.json** - Resume 데이터 (2000개)
4. **groundtruth4.json** - Purchase Order 데이터 (2000개)
5. **groundtruth5.json** - Custom Form 데이터 (2000개)

각 파일의 구조:

```json
{
  "invoice_INV-2025-0001.pdf": {
    "invoice_id": "INV-2025-0001",
    "issue_date": "2025-11-01",
    "customer_name": "StellarWorks Inc.",
    ...
  },
  "passport_857952365.png": {
    "passport_number": "857952365",
    "surname": "YORK",
    ...
  },
  ...
}
```

### 파일명 규칙

문서 타입은 파일명 prefix로 자동 추론됩니다:

- `invoice_*.pdf` → `invoice`
- `passport_*.png` → `passport`
- `resume_*.pdf` → `resume`
- `PO_*.pdf` → `purchase_order`
- `Customs_Form_*.pdf` → `custom_form`

## 🔧 사용 방법

### 1단계: Groundtruth 파일 병합

여러 개의 groundtruth 파일을 하나로 병합합니다:

```bash
python3 scripts/merge_groundtruth.py
```

**출력:**
- `config/groundtruth_merged.json` (총 10,000개 항목)

**통계 예시:**
```
문서 타입별 통계:
  custom_form: 2000개
  invoice: 2000개
  passport: 2000개
  purchase_order: 2000개
  resume: 2000개

총 항목 수: 10000
```

### 2단계: OCR 실행

학습 데이터에 대해 OCR을 실행합니다:

```bash
python src/ocr/batch_ocr_vl.py \
  --input data/input \
  --output data/output/training_ocr.json \
  --gpu
```

### 3단계: 분류 모델 학습

병합된 groundtruth와 OCR 결과를 사용하여 학습합니다:

```bash
python src/classification/trainer.py \
  --groundtruth config/groundtruth_merged.json \
  --ocr data/output/training_ocr.json \
  --output models/classifier
```

**파라미터:**
- `--groundtruth`: 병합된 groundtruth JSON 파일 경로
- `--ocr`: OCR 결과 JSON 파일 경로
- `--output`: 학습된 모델을 저장할 디렉토리

**학습 과정:**
```
Training Classification Model

Step 1: Loading data...
Loaded 10000 labels from groundtruth JSON
Loaded 10000 OCR results

Step 2: Preparing training data...
Prepared 9985 training samples
Skipped 15 samples due to errors

Step 3: Creating dataset...
Dataset created with 9985 samples

Step 3.5: Splitting train/validation...
  Train: 7988 samples
  Validation: 1997 samples

...

Final Validation Results:
  Validation Loss:     0.0234
  Validation Accuracy: 97.45%
  Validation F1:       0.9741
```

## 🔍 문서 타입 추론 로직

`classifier.py`의 train 메서드에서 파일명을 기반으로 문서 타입을 자동 추론합니다:

```python
for filename in groundtruth.keys():
    # 파일명에서 문서 타입 추론
    if filename.startswith('invoice_'):
        doc_type = 'invoice'
    elif filename.startswith('passport_'):
        doc_type = 'passport'
    elif filename.startswith('resume_'):
        doc_type = 'resume'
    elif filename.startswith('PO_'):
        doc_type = 'purchase_order'
    elif filename.startswith('Customs_Form_'):
        doc_type = 'custom_form'
    else:
        print(f"Warning: {filename} 문서 타입을 알 수 없습니다, skipping...")
        continue
```

## 📊 장점

### CSV 방식 (이전)
```
filename,doc_type
invoice_001.pdf,invoice
passport_001.png,passport
...
```

**단점:**
- 별도의 CSV 파일 관리 필요
- 파일 sync 문제
- 데이터 중복

### JSON 방식 (현재)
```json
{
  "invoice_001.pdf": { "invoice_id": "...", ... },
  "passport_001.png": { "passport_number": "...", ... }
}
```

**장점:**
- ✅ 단일 파일로 관리
- ✅ 문서 타입 자동 추론
- ✅ Groundtruth 데이터 포함
- ✅ 확장성 높음
- ✅ 유지보수 용이

## 🚨 주의사항

1. **파일명 규칙 준수**: 파일명은 반드시 정해진 prefix를 사용해야 합니다
   - 잘못된 예: `inv_001.pdf` (invoice_가 아님)
   - 올바른 예: `invoice_001.pdf`

2. **OCR 결과 매칭**: groundtruth의 파일명과 OCR 결과의 파일명이 정확히 일치해야 합니다

3. **병합 순서**: 항상 개별 파일을 먼저 병합한 후 학습을 진행하세요

## 🔄 전체 워크플로우

```
config/groundtruth*.json (5개 파일)
        ↓
scripts/merge_groundtruth.py
        ↓
config/groundtruth_merged.json (10,000개)
        ↓
src/classification/trainer.py (+ OCR 결과)
        ↓
models/classifier (학습된 모델)
```

## 💡 Tips

- **빠른 테스트**: 작은 groundtruth 샘플로 먼저 테스트
- **검증**: 병합 후 통계를 확인하여 데이터 무결성 검증
- **백업**: 원본 파일은 항상 백업 보관

## 📞 문제 해결

### 문제: "문서 타입을 알 수 없습니다"
**해결:** 파일명이 정해진 prefix로 시작하는지 확인

### 문제: "OCR results에서 찾을 수 없습니다"
**해결:** OCR 결과 파일의 키와 groundtruth의 키가 일치하는지 확인

### 문제: 병합된 파일이 너무 큼
**해결:** 이것은 정상입니다. JSON 파일은 10MB 이상이 될 수 있습니다

---

**✅ 이제 JSON groundtruth로 모델을 학습할 준비가 되었습니다!**

