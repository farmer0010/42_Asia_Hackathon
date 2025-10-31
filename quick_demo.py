"""
학습 없이 바로 테스트하는 데모 스크립트
Zero-shot classification + 룰 베이스 추출
"""

import json
import re
from pathlib import Path
from transformers import pipeline
import torch

# GPU 설정
device = 0 if torch.cuda.is_available() else -1
if device == -1 and torch.backends.mps.is_available():
    device = "mps"

print(f"Using device: {device}")
print("=" * 60)

# 1. Zero-shot classifier 초기화 (학습 불필요!)
print("\n[1/4] Initializing zero-shot classifier...")
classifier = pipeline(
    "zero-shot-classification",
    model="facebook/bart-large-mnli",
    device=device
)
print("✓ Classifier ready!")

# 2. OCR 결과 로드
print("\n[2/4] Loading OCR results...")
ocr_path = "outputs/ocr_test_results.json"

if not Path(ocr_path).exists():
    print(f"Error: {ocr_path} not found!")
    print("Please run OCR first: python src/ocr_module.py")
    exit(1)

with open(ocr_path, 'r', encoding='utf-8') as f:
    ocr_results = json.load(f)

print(f"✓ Loaded {len(ocr_results)} OCR results")

# 3. 문서 분류 및 정보 추출
print("\n[3/4] Processing documents...")
results = []

candidate_labels = ["invoice", "receipt", "resume", "report", "contract"]

for ocr_data in ocr_results:
    filename = ocr_data.get('filename', 'unknown')
    print(f"\nProcessing: {filename}")
    
    if 'error' in ocr_data:
        print(f"  ⚠ Skipping (OCR error)")
        continue
    
    text = ocr_data['text']
    
    # Zero-shot classification (학습 없이 분류!)
    classification_result = classifier(
        text[:1024],  # 처음 1024 characters만 사용 (속도 향상)
        candidate_labels,
        multi_label=False
    )
    
    doc_type = classification_result['labels'][0]
    confidence = classification_result['scores'][0]
    
    print(f"  → Classified as: {doc_type} ({confidence:.2%})")
    
    # # 룰 베이스 정보 추출
    # extracted_data = {}
    
    # if doc_type == "invoice":
    #     # 인보이스 정보 추출
    #     # Vendor/Company
    #     vendor_match = re.search(r'(?:Company Name|Exporter|Vendor)[:\s]*([A-Za-z0-9\s&.,]+(?:Ltd|Inc|Corp|LLC)?)', text, re.IGNORECASE)
    #     if vendor_match:
    #         extracted_data['vendor'] = vendor_match.group(1).strip()
    #     
    #     # Date
    #     date_match = re.search(r'(?:Invoice Date|Date)[:\s]*(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})', text, re.IGNORECASE)
    #     if date_match:
    #         extracted_data['invoice_date'] = date_match.group(1).strip()
    #     
    #     # Total amount
    #     total_match = re.search(r'(?:Total Amount|Total|Amount Due)[:\s]*(?:USD|THB|\$|฿)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
    #     if total_match:
    #         amount_str = total_match.group(1).replace(',', '')
    #         try:
    #             extracted_data['total_amount'] = float(amount_str)
    #         except:
    #             pass
    #     
    #     # Currency
    #     currency_match = re.search(r'(?:USD|THB|EUR|GBP)', text, re.IGNORECASE)
    #     if currency_match:
    #         extracted_data['currency'] = currency_match.group(0).upper()
    #     elif '$' in text:
    #         extracted_data['currency'] = 'USD'
    #     elif '฿' in text:
    #         extracted_data['currency'] = 'THB'
    # 
    # elif doc_type == "receipt":
    #     # 영수증 정보 추출
    #     # Store name (보통 첫 줄)
    #     lines = text.split('\n')
    #     if lines:
    #         extracted_data['store'] = lines[0].strip()
    #     
    #     # Date
    #     date_match = re.search(r'(?:Date)[:\s]*(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})', text, re.IGNORECASE)
    #     if date_match:
    #         extracted_data['date'] = date_match.group(1).strip()
    #     
    #     # Total
    #     total_match = re.search(r'(?:^Total|Grand Total)[:\s]*(?:\$|฿)?\s*([\d,]+\.?\d*)', text, re.IGNORECASE | re.MULTILINE)
    #     if total_match:
    #         amount_str = total_match.group(1).replace(',', '')
    #         try:
    #             extracted_data['total'] = float(amount_str)
    #         except:
    #             pass
    #     
    #     # Currency
    #     if '$' in text:
    #         extracted_data['currency'] = 'USD'
    #     elif '฿' in text:
    #         extracted_data['currency'] = 'THB'
    
    # extracted_data 비활성화 - 빈 딕셔너리로 설정
    extracted_data = {}
    
    # 결과 저장
    result = {
        "filename": filename,
        "full_text_ocr": text,
        "ocr_confidence": ocr_data.get('confidence', 0.0),
        "classification": {
            "doc_type": doc_type,
            "confidence": round(confidence, 4)
        },
        "extracted_data": extracted_data,
        "processing_time": ocr_data.get('processing_time', 0.0)
    }
    
    results.append(result)

# 4. 결과 저장
print("\n[4/4] Saving results...")
output_path = "outputs/demo_test_results.json"
Path("outputs").mkdir(exist_ok=True)

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"✓ Results saved to: {output_path}")

# 요약 출력
print("\n" + "=" * 60)
print("DEMO TEST SUMMARY")
print("=" * 60)
print(f"Total documents processed: {len(results)}")
print("\nClassification results:")
for result in results:
    doc_type = result['classification']['doc_type']
    conf = result['classification']['confidence']
    print(f"  • {result['filename']}: {doc_type} ({conf:.1%})")

# print("\nExtraction results:")
# for result in results:
#     if result['extracted_data']:
#         print(f"  • {result['filename']}:")
#         for key, value in result['extracted_data'].items():
#             print(f"      {key}: {value}")

print("\n" + "=" * 60)
print(f"✓ Full results saved to: {output_path}")
print("=" * 60)

