# 해커톤 문서 처리 시스템 📄

## 🎯 프로젝트 개요

이 프로젝트는 **AI 기반 문서 자동 처리 시스템**입니다. 이미지나 PDF 문서를 입력받아:

1. **OCR (텍스트 추출)** - 문서에서 텍스트를 읽어냅니다
2. **분류 (Classification)** - 문서 종류를 자동으로 판단합니다
3. **추출 (Extraction)** - 중요한 정보를 구조화하여 뽑아냅니다

### 💡 비유로 이해하기

```
우편물 자동 분류기를 상상해보세요:

1단계 (OCR): 봉투에 적힌 글씨를 읽습니다
2단계 (분류): "이건 청구서, 저건 영수증"이라고 분류합니다
3단계 (추출): 청구서에서 "금액, 날짜, 회사명"을 찾아냅니다

→ 사람이 일일이 보지 않아도 자동으로 처리!
```

---

## 🏗️ 시스템 구조 (한눈에)

```
문서 이미지 (PDF/JPG/PNG)
    ↓
[ OCR 모듈 ] ← paddleocr 사용
    ↓ 텍스트 추출
[ 분류 모듈 ] ← DistilBERT 사용
    ↓ invoice? receipt? resume?
[ 추출 모듈 ] ← BERT-NER 사용
    ↓ 금액, 날짜, 회사명 등
결과 JSON 출력
```

---

## 📂 프로젝트 파일 구조

```
방콕 해커톤/
├── src/                        # 핵심 코드
│   ├── ocr_module.py          # 1단계: OCR (텍스트 추출)
│   ├── classification_module.py  # 2단계: 문서 분류
│   ├── extraction_module.py   # 3단계: 정보 추출
│   ├── batch_ocr.py          # 유틸: 여러 문서 한번에 OCR
│   ├── train_classifier.py   # 유틸: 분류 모델 학습
│   ├── main.py               # 통합: 단일 문서 처리
│   └── predict.py            # 통합: 폴더 전체 예측
│
├── models/                    # 학습된 AI 모델 저장
│   └── classifier/           # 분류 모델
│
├── outputs/                   # 결과 파일
│   └── ocr_test_results.json # OCR 결과
│
├── test_samples/             # 테스트 샘플 문서
│   ├── sample1.jpg          # Invoice 샘플
│   └── sample2.png          # Receipt 샘플
│
├── docs/                     # 문서 (지금 보고 있는 파일!)
│   ├── README.md            # ← 여기
│   ├── ARCHITECTURE.md      # 시스템 상세 설명
│   └── HACKATHON_WORKFLOW.md # 해커톤 당일 가이드
│
├── requirements.txt          # 필요한 라이브러리 목록
└── venv/                    # Python 가상환경
```

---

## 🚀 빠른 시작 가이드

### 0단계: 처음 시작하는 경우 (최초 1회만)

**이미 venv가 있다면 이 단계 건너뛰기!**

```bash
# 1. Python 버전 확인 (3.11 권장)
python3 --version
# → Python 3.11.x 또는 3.12.x 확인

# 3.11이 없으면 설치 (Mac)
brew install python@3.11

# 2. 프로젝트 폴더로 이동
cd "/Users/ahnhyunjun/Desktop/방콕 해커톤"

# 3. 가상환경 생성
python3.11 -m venv venv
# → venv/ 폴더가 생성됨

# 4. 가상환경 활성화
source venv/bin/activate
# → (venv) 표시가 나오면 성공!

# 5. pip 업그레이드
pip install --upgrade pip

# 6. 패키지 설치 (5-10분 소요)
pip install -r requirements.txt
# → 약 30개 패키지가 설치됨

# 7. 설치 확인
python -c "from src.ocr_module import OCRModule; print('✓ 설치 성공!')"
```

**주의사항**:
- Python 3.13은 호환성 문제가 있을 수 있음 → 3.11 또는 3.12 사용
- 패키지 설치 중 에러 나면 → 가상환경 삭제 후 재생성
  ```bash
  rm -rf venv
  python3.11 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```

---

### 1단계: 환경 설정 (매번 실행)

**이미 venv가 있고 패키지가 설치되어 있는 경우:**

```bash
# 가상환경 활성화만 하면 됨
source venv/bin/activate

# (venv) 표시 확인
# 비활성화: deactivate
```

### 2단계: 단일 문서 테스트

```bash
# OCR만 테스트
python -c "from src.ocr_module import OCRModule; ocr = OCRModule(); print(ocr.extract_text('test_samples/sample1.jpg'))"

# 전체 파이프라인 (OCR + 분류 + 추출)
# 주의: 모델 학습 후 가능
python src/main.py \
  --input test_samples/sample1.jpg \
  --classifier models/classifier \
  --output result.json
```

### 3단계: 여러 문서 일괄 처리

```bash
# 폴더 내 모든 문서 OCR
python src/batch_ocr.py \
  --input test_samples/ \
  --output outputs/all_ocr.json
```

---

## 📊 작동 예시

### 입력 (Invoice 이미지)
```
Commercial Invoice
Company: ABC Exports Ltd.
Date: September 30, 2030
Total: $13,000.00
```

### 출력 (JSON)
```json
{
  "filename": "invoice.jpg",
  "full_text_ocr": "Commercial Invoice\nCompany: ABC Exports Ltd...",
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

---

## 🧪 테스트 방법

### 간단 테스트 (5분)

```bash
# OCR 테스트
python quick_test.py

# 추출 모듈 테스트
python test_with_ocr.py
```

### 결과 해석
```
✓ "Organizations: ['ABC Exports Ltd']" 
  → 회사명을 찾았다는 뜻

✓ "Amounts: ['$13,000.00', '$5,000.00']"
  → 문서에서 금액을 추출했다는 뜻

✓ "Dates: ['2030-09-30']"
  → 날짜를 찾았다는 뜻
```

---

## 📚 더 알아보기

### 상세 설명이 필요하면
→ **[ARCHITECTURE.md](./ARCHITECTURE.md)** 읽어보세요
- 각 파일이 정확히 뭘 하는지
- 함수별 설명
- 데이터 흐름

### 해커톤 당일 준비
→ **[HACKATHON_WORKFLOW.md](./HACKATHON_WORKFLOW.md)** 읽어보세요
- 당일 실행 순서
- 명령어 복사 붙여넣기
- 예상 시간

---

## ❓ FAQ

### Q1: OCR이 뭔가요?
**A:** Optical Character Recognition의 약자로, 이미지 속 글자를 컴퓨터가 읽을 수 있는 텍스트로 변환하는 기술입니다.
스마트폰으로 명함 사진 찍으면 전화번호가 자동으로 저장되는 것처럼요!

### Q2: 어떤 문서를 처리할 수 있나요?
**A:** 현재 5가지 종류를 분류할 수 있습니다:
- invoice (송장)
- receipt (영수증)
- resume (이력서)
- report (보고서)
- contract (계약서)

### Q3: 추출은 모든 문서에서 하나요?
**A:** 아니요! invoice와 receipt에서만 구조화된 추출을 합니다.
나머지는 텍스트만 추출하고, LLM 팀이 추가 처리합니다.

### Q4: 학습은 얼마나 걸리나요?
**A:** 분류 모델 학습: 30-60분 (CPU 기준, 500-1000개 문서)
추출 모델은 사전학습된 모델을 사용하므로 학습 불필요!

### Q5: GPU가 필요한가요?
**A:** 아니요! CPU만으로도 충분히 작동합니다.
M1/M2 Mac에 최적화되어 있습니다.

---

## 🎓 팀원용 학습 자료

### AI/ML을 처음 접하는 팀원
1. README.md (이 파일) 읽기
2. quick_test.py 실행해보기
3. HACKATHON_WORKFLOW.md로 전체 흐름 파악

### 코드를 이해하고 싶은 팀원
1. ARCHITECTURE.md 정독
2. src/ocr_module.py부터 차례로 읽기
3. main.py에서 통합 과정 확인

### 해커톤 당일 담당자
1. HACKATHON_WORKFLOW.md 숙지
2. 명령어들 미리 메모장에 복사
3. 예상 소요 시간 체크

---

## 📞 문제 발생 시

### 에러가 나면?
1. 에러 메시지 복사
2. 어떤 명령어를 실행했는지 기록
3. venv 활성화 확인: `source venv/bin/activate`

### 결과가 이상하면?
1. OCR 결과 먼저 확인 (outputs/*.json)
2. 입력 이미지 품질 확인 (흐릿하거나 회전되지 않았는지)
3. 분류 confidence 확인 (90% 이상이 정상)

---

## 🎉 프로젝트 특징

### ✅ 장점
- **CPU만으로 작동**: GPU 없어도 OK!
- **빠른 처리**: 문서 1개당 0.5초 (OCR 제외시)
- **낮은 메모리**: 643MB RAM만 사용
- **유연한 추출**: labels.csv에 따라 자동 조정

### ⚠️ 제약사항
- 영어 문서에 최적화 (한글은 정확도 낮음)
- 손글씨는 PaddleOCR 성능에 의존
- 매우 특이한 레이아웃은 추출 실패 가능

---

## 🏆 해커톤 성공 전략

1. **데이터 먼저 확인**: training_set 받자마자 샘플 몇 개 확인
2. **OCR 먼저 실행**: 시간이 오래 걸리니 바로 시작
3. **분류 학습 중 준비**: 학습 돌아가는 동안 testing_set 분석
4. **결과 검증**: predictions.json 열어서 샘플 확인
5. **LLM 팀과 소통**: JSON 형식이 그들에게 맞는지 확인

---

**다음 단계**: [ARCHITECTURE.md](./ARCHITECTURE.md)에서 시스템 구조 자세히 알아보기 →

