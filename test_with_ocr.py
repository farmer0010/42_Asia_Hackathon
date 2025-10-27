from src.extraction_module import DataExtractor
import json

print("=" * 60)
print("Testing Extraction with Real OCR Results")
print("=" * 60)

# 1. OCR 결과 로드
print("\n[Step 1] Loading OCR results...")
with open('outputs/ocr_test_results.json', 'r', encoding='utf-8') as f:
    ocr_results = json.load(f)
print(f"✓ Loaded {len(ocr_results)} documents")

# 2. Extractor 초기화
print("\n[Step 2] Initializing extractor...")
extractor = DataExtractor()
print("✓ Extractor ready!")

# 3. 각 문서 테스트
print("\n" + "=" * 60)
print("Testing Documents")
print("=" * 60)

for result in ocr_results:
    if 'error' in result:
        continue
    
    filename = result['filename']
    text = result['text']
    
    print(f"\n📄 {filename}")
    print(f"   Text length: {len(text)} chars")
    print(f"   Confidence: {result['confidence']:.2%}")
    
    # NER 실행
    entities = extractor._run_ner(text)
    
    # 결과 출력
    print("\n   Entities found:")
    if entities['ORG']:
        print(f"   → Organizations: {entities['ORG'][:2]}")
    if entities['PER']:
        print(f"   → Persons: {entities['PER'][:2]}")
    if entities['LOC']:
        print(f"   → Locations: {entities['LOC'][:2]}")
    
    # 패턴 추출
    patterns = extractor._extract_patterns(text)
    print("\n   Patterns found:")
    if patterns['dates']:
        print(f"   → Dates: {patterns['dates'][:3]}")
    if patterns['amounts']:
        print(f"   → Amounts: {patterns['amounts'][:3]}")
    if patterns['currency']:
        print(f"   → Currency: {patterns['currency']}")
    
    print("-" * 60)

print("\n" + "=" * 60)
print("✓ All documents tested!")
print("=" * 60)