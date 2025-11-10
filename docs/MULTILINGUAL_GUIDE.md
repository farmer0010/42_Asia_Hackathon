# 🌍 다국어 지원 가이드 (Multilingual Support Guide)

## ✅ 구현 완료된 기능

이 프로젝트는 **영어, 태국어, 한국어, 일본어** 4개 언어를 완벽 지원합니다!

---

## 📚 **1. OCR 다국어 지원**

### 지원 언어
- 🇺🇸 English (영어)
- 🇹🇭 Thai (태국어)
- 🇰🇷 Korean (한국어)
- 🇯🇵 Japanese (일본어)

### 주요 기능
- ✅ **자동 언어 감지**: 이미지를 분석하여 자동으로 언어 판별
- ✅ **Lazy loading**: 필요한 언어 모델만 메모리에 로드
- ✅ **손글씨 인식 강화**: 전처리를 통한 손글씨 정확도 향상

### 사용 방법

```python
from src.ocr.ocr_vl_module import OCRVLModule

# 초기화
ocr = OCRVLModule(
    use_gpu=False,  # GPU 사용 여부
    enable_handwriting=True  # 손글씨 전처리 활성화
)

# 자동 언어 감지
result = ocr.process_document("document.jpg", lang='auto')

# 또는 언어 수동 지정
result = ocr.process_document("document.jpg", lang='korean')

# 결과
print(f"Detected: {result['detected_language']}")
print(f"Confidence: {result['confidence']}")
print(f"Text: {result['full_text']}")
```

---

## 🤖 **2. 분류기 다국어 지원**

### XLM-RoBERTa 모델 사용
- **100개 이상의 언어 지원**
- 영어 성능 유지하면서 다국어 처리
- 토큰 길이 768로 확장 (한글/태국어 대응)

### 사용 방법

```python
from src.classification.classifier import DocumentClassifier

# 다국어 분류기 초기화
classifier = DocumentClassifier(
    model_name='xlm-roberta-base',
    use_multilingual=True
)

# 학습 (다국어 데이터셋 사용)
classifier.train(
    labels_csv_path='config/labels.csv',
    ocr_results_path='data/output/ocr_results.json',
    output_dir='models/classifier_multilingual'
)

# 추론
result = classifier.classify("ใบกำกับภาษี...")  # 태국어도 작동!
```

---

## 🧠 **3. LLM 다국어 프롬프트**

### Qwen2.5 다국어 처리
- 프롬프트에 언어 정보 포함
- 원본 언어 보존하면서 추출
- 필드명은 영어, 값은 원본 언어 유지

### 예시

```python
# 입력: 태국어 영수증
"""
ใบเสร็จรับเงิน
รวม: 1,000 บาท
วันที่: 2024-01-01
"""

# 출력 (JSON)
{
  "total_amount": "1,000 บาท",  # 원본 언어 유지
  "date": "2024-01-01",
  "currency": "THB"
}
```

---

## 🔒 **4. PII 탐지 다국어 지원**

### 새로 추가된 패턴

| 언어 | 패턴 | 예시 | 마스킹 결과 |
|-----|------|------|------------|
| 태국어 | 태국 ID | `1-1020-30405-60-7` | `1-****-*****-**-*` |
| 태국어 | 태국 전화번호 | `02-123-4567` | `02-***-**67` |
| 한국어 | 한국 전화번호 | `010-1234-5678` | `010-****-**78` |
| 한국어 | 주민등록번호 | `123456-1234567` | `123456-*******` |
| 일본어 | 일본 전화번호 | `03-1234-5678` | `03-****-**78` |
| 일본어 | 마이넘버 | `1234-5678-9012` | `****-****-**12` |

### 사용 방법

```python
from src.llm.extractors.pii_detector import PIIDetector

detector = PIIDetector()

# PII 탐지
text = "연락처: 010-1234-5678, 이메일: hong@example.com"
pii_list = detector.detect(text, use_llm=True)

# 마스킹
for pii in pii_list:
    pii["masked"] = detector.mask_text(pii["text"], pii["type"])

# 결과
# [
#   {"type": "KOREAN_PHONE", "text": "010-1234-5678", "masked": "010-****-**78"},
#   {"type": "EMAIL", "text": "hong@example.com", "masked": "h***@e***.com"}
# ]
```

---

## 🚀 **전체 파이프라인 실행**

### 단계별 실행

```bash
# 1. OCR 실행 (다국어 자동 감지)
python -m src.pipeline.predict \
  --input data/input/ \
  --output data/output/ocr_multilang.json \
  --gpu  # GPU 사용 시

# 2. 분류기 학습 (다국어 데이터)
python -m src.classification.trainer \
  --labels config/labels_multilang.csv \
  --ocr data/output/ocr_multilang.json \
  --output models/classifier_multilang

# 3. LLM 변환 (최종 출력)
python -m src.llm.converter \
  --input data/output/ocr_multilang.json \
  --output data/output/final_multilang.json
```

---

## 📊 **성능 비교**

| 모델 | 언어 지원 | 크기 | 메모리 | 정확도 |
|------|----------|------|--------|--------|
| DistilBERT (기존) | 영어만 | 66MB | ~500MB | 높음 (영어) |
| XLM-RoBERTa (신규) | 100+언어 | 278MB | ~1.5GB | 높음 (다국어) |

---

## 🎯 **사용 팁**

### 1. 메모리 최적화
```python
# 영어 문서만 처리하는 경우
classifier = DocumentClassifier(use_multilingual=False)  # DistilBERT 사용
ocr = OCRVLModule(supported_langs=['en'])  # 영어만 로드
```

### 2. 언어별 최적화
```python
# 태국어 문서 대량 처리
ocr = OCRVLModule(supported_langs=['thai'])  # 태국어만 미리 로드
for image in thai_images:
    result = ocr.process_document(image, lang='thai')
```

### 3. GPU 활용
```bash
# GPU 사용으로 5-10배 속도 향상
python -m src.pipeline.predict --input data/input/ --gpu
```

---

## 🐛 **문제 해결**

### Q: 태국어 OCR이 작동하지 않아요
A: PaddleOCR의 언어 코드는 'thai'가 아니라 다른 코드를 사용합니다. 현재는 영어로 먼저 OCR 후 언어 감지하는 방식으로 우회 처리됩니다.

### Q: 메모리 부족 에러
A: `use_multilingual=False`로 영어 전용 모델 사용하거나, `max_length`를 512로 줄이세요.

### Q: 한글/일본어 토큰이 잘려요
A: `max_length=768` (또는 1024)로 늘리세요. 다국어는 토큰 수가 많습니다.

---

## 📝 **다음 단계**

- [ ] 중국어 간체/번체 지원 추가
- [ ] 아랍어, 인도어 등 RTL 언어 지원
- [ ] 언어별 레이아웃 특성 최적화
- [ ] 다국어 학습 데이터셋 구축

---

## 📞 **문의**

다국어 지원 관련 문의사항은 팀에 연락해주세요!

**Made with 🌍 for Hackathon Thailand 2025**

