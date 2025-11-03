# 🧪 빠른 테스트 가이드

**분류 모델 학습 없이 전체 시스템을 바로 테스트하는 방법!**

---

## ⚡ 가장 빠른 방법 (3단계)

### 1️⃣ 준비 (최초 1회)

```bash
# 가상환경 활성화
source venv/bin/activate

# 패키지 설치 (아직 안 했으면)
pip install -r requirements.txt

# Ollama 설치 & 모델 다운로드
brew install ollama
ollama pull qwen2.5:7b
```

### 2️⃣ Ollama 실행

```bash
# 새 터미널 창에서 (또는 백그라운드)
ollama serve &
```

### 3️⃣ 테스트 실행

```bash
# 자동으로 전체 파이프라인 실행
scripts/test_pipeline_notrain.sh
```

**완료!** 🎉

---

## 📊 무엇을 테스트하나?

```
1. OCR + 레이아웃 분석
   ↓
   data/output/predictions_ocr_only.json

2. 수동 Doc Type 할당
   ↓
   data/output/predictions_with_types.json

3. LLM 처리 (추출 + PII + 요약)
   ↓
   data/output/test_final_results.json ← 최종 결과!
```

---

## 📁 입력 파일 준비

테스트 파일을 `data/input/` 폴더에 넣으세요:

```bash
# 예시
cp your_invoice.jpg data/input/
cp your_receipt.png data/input/
```

**지원 형식:** JPG, PNG, JPEG, PDF

---

## 🔍 결과 확인

### 최종 결과 보기

```bash
cat data/output/test_final_results.json
```

### 예시 출력

```json
[
  {
    "filename": "invoice1.jpg",
    "classification": {
      "doc_type": "invoice",
      "confidence": 0.95
    },
    "extracted_data": {
      "vendor": "ABC Company",
      "invoice_number": "INV-001",
      "date": "2024-01-15",
      "total_amount": "$1,250.00",
      "currency": "USD"
    },
    "pii_detected": [
      {
        "type": "EMAIL",
        "value": "contact@abc.com",
        "confidence": 0.95
      }
    ]
  }
]
```

---

## 🎛️ Doc Type 할당 커스터마이징

테스트용 타입 할당을 바꾸고 싶다면:

```bash
# 1. tests/test_with_types.py 편집
vim tests/test_with_types.py

# 2. manual_mapping 수정
manual_mapping = {
    'your_file.jpg': 'invoice',  # 원하는 타입
    'another.png': 'receipt'
}

# 3. 다시 실행
scripts/test_pipeline_notrain.sh
```

**또는** 파일명에 키워드를 포함하면 자동 할당:
- `invoice*.jpg` → invoice
- `receipt*.png` → receipt
- `resume*.pdf` → resume
- `report*.jpg` → report
- `contract*.pdf` → contract

---

## ⏱️ 예상 시간

| 작업 | 시간 (M1 Mac) |
|------|---------------|
| OCR (4개 파일) | 40-80초 |
| 타입 할당 | 즉시 |
| LLM 처리 | 30-60초 |
| **총** | **2-3분** |

---

## 🐛 문제 해결

### "Ollama not running"

```bash
# Ollama 실행
ollama serve &

# 확인
curl http://localhost:11434
```

### "No files in data/input/"

```bash
# 파일 복사
cp test_samples/* data/input/  # (test_samples가 있다면)
# 또는
cp your_files/* data/input/
```

### "ModuleNotFoundError: No module named 'src'"

```bash
# PYTHONPATH 설정 (스크립트가 자동으로 하지만)
export PYTHONPATH="${PWD}:${PYTHONPATH}"
```

### Import 에러

```bash
# 가상환경 확인
source venv/bin/activate

# 패키지 재설치
pip install -r requirements.txt
```

---

## 🔄 다시 실행

결과를 지우고 다시 테스트하려면:

```bash
# 출력 파일 삭제
rm -f data/output/predictions*.json
rm -f data/output/test_final_results.json

# 다시 실행
scripts/test_pipeline_notrain.sh
```

---

## 💡 Tip

### 특정 단계만 실행

```bash
# Step 1: OCR만
python src/pipeline/predict.py \
  --input data/input \
  --output data/output/predictions_ocr_only.json

# Step 2: 타입 할당만
python tests/test_with_types.py

# Step 3: LLM 처리만
python src/llm/converter.py \
  --input data/output/predictions_with_types.json \
  --output data/output/test_final_results.json
```

### 단일 파일 테스트

```python
# Python에서 직접 테스트
from src.ocr.ocr_vl_module import OCRVLModule

ocr = OCRVLModule()
result = ocr.process_document('data/input/test.jpg')
print(result)
```

---

## 📚 다음 단계

### 분류 모델 학습

테스트가 성공했다면, 실제 분류 모델을 학습해보세요:

```bash
# 1. Training set OCR
python src/ocr/batch_ocr_vl.py \
  --input training_set/documents \
  --output data/output/training_ocr.json

# 2. 모델 학습
python src/classification/trainer.py \
  --labels training_set/labels.csv \
  --ocr data/output/training_ocr.json \
  --output data/models/classifier

# 3. 전체 파이프라인 (분류 포함)
scripts/run_local.sh
```

### Docker로 실행

```bash
cd docker
docker compose up
```

---

## 🔗 관련 문서

- **전체 가이드**: `docs/가이드.md`
- **메인 README**: `README.md`
- **Docker 가이드**: `README_DOCKER.md` (docs/ 내)

---

**🎉 테스트 성공하면 이슈나 PR 환영!**

