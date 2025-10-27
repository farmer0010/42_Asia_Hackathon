## 🧠 Project: Asia OCR → LLM JSON Extractor

## 📄 Overview

이 프로젝트는 OCR(광학 문자 인식)으로 추출된 텍스트를 입력받아  
오픈소스 LLM을 활용해 문서 유형 분류, 핵심 정보 추출, 요약, PII 탐지를 수행합니다.  
Gemma 3:4B 모델을 로컬(Ollama) 환경에서 구동하며,  
인보이스 / 영수증 / 보고서 형태의 문서를 자동 처리할 수 있습니다.

---

## 🧩 System Architecture

OCR → LLM Classification → Data Extraction → Summarization → PII Detection  
│ │ │ │  
└────────────── batch_run.py orchestrates all modules ─────────┘

---

## 🗂️ Folder Structure

```text
asia/
├── batch_run.py # 메인 실행 파일 (전체 파이프라인)
├── client.py # Ollama LLM 클라이언트
├── guards.py # JSON 스키마 검증 및 복구 로직
├── tasks.py # classify / extract / summarize / pii 함수
├── prompts/ # LLM 프롬프트 템플릿
│   ├── classify.txt
│   ├── extract_invoice.txt
│   ├── extract_receipt.txt
│   ├── pii.txt
│   └── summarize.txt
├── schemas/ # JSON 스키마
│   ├── invoice_v1.json
│   └── receipt_v1.json
├── ocr.txt # OCR 결과 샘플 입력
└── outputs/ # 실행 결과 (ocr.txt, summary.txt, result.json)
```

---

## ⚙️ Installation

1. Prerequisites  
   • Python ≥ 3.9  
   • Ollama 설치  
   • 모델 다운로드:

```bash
ollama pull gemma3:4b
```

2. Python dependencies

```bash
pip install httpx jsonschema
```

3. (선택) macOS에서 brew로 Python 설치 시

```bash
brew install python3
```

---

## 🚀 How to Run

✅ Step 1. OCR 텍스트 준비

ocr.txt 파일에 OCR 결과를 저장합니다.  
예시:

```text
INVOICE
Vendor: ACME Corp.
Invoice Date: 2025-08-19
Total: 1,500.75 THB
```

✅ Step 2. 실행

```bash
python3 batch_run.py ocr.txt outputs
```

✅ Step 3. 결과 확인

outputs/ 폴더에 다음 파일들이 생성됩니다:

```text
outputs/
├── ocr.txt # 입력 OCR 원문
├── summary.txt # 문서 요약 (180자 이내 영어 문장)
└── result.json # 최종 구조화된 결과
```

예시 출력:

```json
{
  "filename": "ocr.txt",
  "classification": {
    "doc_type": "invoice",
    "confidence": 0.93
  },
  "full_text_ocr": "INVOICE\nVendor: ACME Corp.\n...",
  "extracted_data": {
    "vendor": "ACME Corp.",
    "invoice_date": "2025-08-19",
    "total_amount": 1500.75,
    "currency": "THB"
  },
  "summary": "Invoice from ACME Corp. dated August 19, 2025, with total amount 1,500.75 THB.",
  "pii_detected": []
}
```

---

## 🧱 Core Components

| 기능 파일 설명                                                               |
| ---------------------------------------------------------------------------- |
| 문서 분류 prompts/classify.txt 인보이스/영수증/보고서 분류                   |
| 인보이스 추출 prompts/extract_invoice.txt vendor, date, total, currency 추출 |
| 영수증 추출 prompts/extract_receipt.txt merchant, date, total, currency 추출 |
| 요약 생성 prompts/summarize.txt 180자 이내 요약문 생성                       |
| PII 탐지 prompts/pii.txt 이름, ID, 이메일 등 개인 식별 정보 검출             |

---

## 🧠 Models

• LLM: Gemma 3:4B (Ollama)  
• JSON Schema Validation: jsonschema  
• Language: Python 3.9+

---

## 💾 Output Format (Required by Hackathon)

```json
{
  "filename": "invoice_123.pdf",
  "classification": { "doc_type": "invoice", "confidence": 0.98 },
  "full_text_ocr": "...",
  "extracted_data": {
    "vendor": "CDG Group",
    "invoice_date": "2025-08-19",
    "total_amount": 7500.0,
    "currency": "THB"
  },
  "summary": "Concise English summary of the document.",
  "pii_detected": [
    { "type": "PERSON_NAME", "text": "John Doe" },
    { "type": "THAI_ID", "text": "1-1020-30405-60-7" }
  ]
}
```

---

## 🧾 License

This project uses open-source tools and complies with the hackathon requirement:

“Must use open-source AI/ML technologies.”

---

## 👥 Team Roles

OCR 텍스트 추출 (Vision API or OCR library)  
LLM 텍스트 구조화 및 요약 (본 모듈)  
Backend 파이프라인 통합 / Docker 배포  
기획·발표 전체 서비스 기획, UX, 피칭 준비

---
