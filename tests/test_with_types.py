#!/usr/bin/env python3
"""
테스트용 Doc Type 할당 스크립트
분류 모델이 학습되지 않았을 때 수동으로 doc_type을 할당합니다.

사용법 1 (단독 실행):
    python tests/test_with_types.py
    python src/llm/converter.py --input data/output/predictions_with_types.json --output data/output/final.json

사용법 2 (통합 스크립트):
    ./scripts/test_pipeline_notrain.sh
"""

import json
import sys

print("=" * 60)
print("Adding Manual Doc Types for Testing")
print("=" * 60)

# 1. predictions_ocr_only.json 로드
print("\n1. Loading predictions_ocr_only.json...")
with open('data/output/predictions_ocr_only.json', 'r', encoding='utf-8') as f:
    predictions = json.load(f)
print(f"   Loaded {len(predictions)} documents")

# 2. 각 파일 내용 미리보기
print("\n2. Current documents:")
for i, pred in enumerate(predictions, 1):
    filename = pred['filename']
    text_preview = pred['full_text_ocr'][:50].replace('\n', ' ')
    print(f"   [{i}] {filename}: {text_preview}...")

# 3. 수동으로 doc_type 할당
print("\n3. Assigning doc_types manually...")

# 파일명 기반 자동 매핑 (키워드 매칭)
def auto_assign_type(filename, text):
    """파일명과 텍스트 내용으로 자동 타입 할당"""
    filename_lower = filename.lower()
    text_lower = text.lower()
    
    # 파일명 기반
    if 'invoice' in filename_lower:
        return 'invoice'
    elif 'receipt' in filename_lower:
        return 'receipt'
    elif 'resume' in filename_lower or 'cv' in filename_lower:
        return 'resume'
    elif 'report' in filename_lower:
        return 'report'
    elif 'contract' in filename_lower:
        return 'contract'
    
    # 텍스트 내용 기반 (간단한 휴리스틱)
    if 'invoice' in text_lower and 'total' in text_lower:
        return 'invoice'
    elif 'receipt' in text_lower:
        return 'receipt'
    elif 'experience' in text_lower or 'education' in text_lower:
        return 'resume'
    elif 'summary' in text_lower or 'conclusion' in text_lower:
        return 'report'
    elif 'agreement' in text_lower or 'party' in text_lower:
        return 'contract'
    
    # 기본값 (다양하게 테스트하기 위해 순환 할당)
    defaults = ['invoice', 'receipt', 'resume', 'report', 'contract']
    return defaults[hash(filename) % len(defaults)]

# 수동 매핑 (우선순위 높음)
manual_mapping = {
    'sample4.jpg': 'receipt',
    'sample1.jpg': 'invoice',
    'invoice1.jpg': 'report',
    'sample3.jpeg': 'receipt',
    'testtest.png': 'contract',
    'sample2.png': 'receipt'
}

for pred in predictions:
    filename = pred['filename']
    text = pred.get('full_text_ocr', '')
    
    # 수동 매핑이 있으면 사용, 없으면 자동 할당
    if filename in manual_mapping:
        doc_type = manual_mapping[filename]
        print(f"   ✓ {filename} → {doc_type} (manual)")
    else:
        doc_type = auto_assign_type(filename, text)
        print(f"   ✓ {filename} → {doc_type} (auto)")
    
    pred['classification']['doc_type'] = doc_type
    pred['classification']['confidence'] = 0.95

# 4. 저장
output_path = 'data/output/predictions_with_types.json'
print(f"\n4. Saving to {output_path}...")
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(predictions, f, indent=2, ensure_ascii=False)

print(f"   ✓ Saved {len(predictions)} documents")

# 5. 요약
print("\n" + "=" * 60)
print("Summary")
print("=" * 60)
doc_types = {}
for pred in predictions:
    dt = pred['classification']['doc_type']
    doc_types[dt] = doc_types.get(dt, 0) + 1

for dt, count in doc_types.items():
    print(f"  - {dt}: {count}")

print(f"\n✓ Ready for extraction test!")
print(f"\nNext command:")
print(f"  python src/llm/converter.py \\")
print(f"    --input {output_path} \\")
print(f"    --output data/output/hackathon_results_test.json")