# 🏆 42 Asia Hackathon - OCR & 문서 분류 시스템

> **담당:** OCR & 분류 파트  
> **기술:** PaddleOCR + DistilBERT  
> **상태:** ✅ 개발 완료

---

## 🎯 시스템 개요

5가지 문서 타입(Invoice, Receipt, Resume, Report, Contract)을 **OCR + 분류**하여 LLM 팀에게 전달하는 시스템

```
Input (이미지/PDF)
    ↓
PaddleOCR (텍스트 + 레이아웃 추출)
    ↓
DistilBERT (문서 타입 분류)
    ↓
Output (JSON) → LLM 팀
```

---

## ⚡ 빠른 시작

### 1. 환경 설정
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 테스트
```bash
# OCR 테스트
python srcs/ocr_vl_module.py

# 분류 테스트
python srcs/classification_module.py

# 통합 테스트
python srcs/predict_ocr_classify.py --input test_samples --output outputs/test.json
```

---

## 📂 프로젝트 구조

```
srcs/
├── ocr_vl_module.py          # OCR + 레이아웃 분석
├── batch_ocr_vl.py           # 배치 OCR 처리
├── classification_module.py  # 문서 분류 모델
├── train_classifier.py       # 모델 학습
└── predict_ocr_classify.py   # 최종 파이프라인

outputs/
├── test_batch.json           # 테스트 결과
└── predictions_final.json    # 최종 출력 (LLM 전달용)

models/
└── classifier/               # 학습된 분류 모델
```

---

## 🚀 해커톤 당일 (3단계)

### Step 1: Training Set OCR (40-50분)
```bash
python srcs/batch_ocr_vl.py \
  --input training_set/documents \
  --output outputs/training_ocr_vl.json \
  --gpu
```

### Step 2: 분류 모델 학습 (60분)
```bash
python srcs/train_classifier.py \
  --labels training_set/labels.csv \
  --ocr outputs/training_ocr_vl.json \
  --output models/classifier
```

### Step 3: Testing Set 처리 (20-30분)
```bash
python srcs/predict_ocr_classify.py \
  --input testing_set/documents \
  --classifier models/classifier \
  --output predictions_final.json \
  --gpu
```

**총 시간: 약 2시간 30분**

---

## 📤 출력 형식 (LLM 팀에게 전달)

```json
[
  {
    "filename": "test001.jpg",
    "full_text_ocr": "INVOICE\nABC Corp\nTotal: $1500...",
    "ocr_confidence": 0.97,
    "layout": {
      "title": "INVOICE",
      "features": {
        "has_table": true,
        "num_key_value_pairs": 26,
        "text_density": 0.56
      }
    },
    "classification": {
      "doc_type": "invoice",
      "confidence": 0.96
    }
  }
]
```

**LLM 팀 작업:**
- 구조화 데이터 추출 (vendor, amount, date 등)
- 요약 생성 (report/contract)
- PII 탐지 (개인정보)

---

## 📊 성능 지표

| 지표 | 값 |
|------|---|
| OCR 신뢰도 | 91.61% |
| 처리 속도 | 4-5초/문서 |
| 분류 정확도 | 90%+ (예상) |
| 메모리 사용 | ~650 MB |

---

## 📖 상세 문서

### 🔥 **[완전 가이드](docs/COMPLETE_GUIDE.md)** (필독!)
- 환경 설정부터 해커톤 당일까지 모든 것
- LLM 팀 인수인계
- 기술적 배경 설명
- FAQ

### 📘 **[기술 문서](docs/MY_PART_ARCHITECTURE.md)**
- 상세 아키텍처
- 코드 예제
- 구현 가이드

---

## 🎤 발표 포인트

### 기술적 우수성
1. ✨ **PaddleOCR 활용**
   - 텍스트 추출 + 레이아웃 분석
   - OCR 신뢰도 91%+

2. 📚 **학습 기반 분류**
   - Training set으로 DistilBERT 학습
   - 레이아웃 정보 활용으로 정확도 향상
   - 5개 문서 타입 분류 (90%+ 예상)

3. 🔗 **LLM 팀과 협업**
   - 구조화된 JSON 출력
   - OCR + 분류 완료 후 전달
   - LLM이 추출/요약/PII 담당

### 혁신성
- 레이아웃 분석 통합 (단순 텍스트 이상)
- Enhanced Text 기법 (텍스트 + 구조 정보)
- 효율적인 파이프라인 (역할 분담 명확)

---

## 🚨 백업 플랜

| 문제 | 해결책 |
|------|--------|
| GPU 없음 | `--gpu` 제거 (CPU 사용, 느려짐) |
| 시간 부족 | Epochs 감소 (3 → 2) |
| OCR 에러 | 2-3% 에러는 정상, 무시 가능 |
| 분류 정확도 낮음 | Learning rate 조정 |

---

## 🛠️ 기술 스택

**OCR:**
- PaddleOCR 2.8.1
- OpenCV 4.10

**ML:**
- PyTorch 2.9.0
- Transformers 4.46.3
- DistilBERT

**Utils:**
- pandas, numpy
- tqdm (진행률)

---

## ✅ 체크리스트

### 개발
- [x] OCR-VL 모듈
- [x] 배치 처리
- [x] 분류 모듈
- [x] 학습 스크립트
- [x] 예측 파이프라인
- [x] 모든 테스트 통과

### 해커톤 당일
- [ ] GPU 확인
- [ ] venv 활성화
- [ ] Training set 받기
- [ ] 명령어 실행
- [ ] LLM 팀 전달

---

## 📞 문의

**문서:**
- 📘 [완전 가이드](docs/COMPLETE_GUIDE.md) - 모든 정보
- 📖 [기술 문서](docs/MY_PART_ARCHITECTURE.md) - 상세 설명

**파트:**
- OCR & 분류: 이 파트 담당
- 추출 & 보너스: LLM 파트 담당

---

**🚀 화이팅!**

*Last Updated: 2025-11-01*
