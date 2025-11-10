import json
from src.llm.extractors.smart_extractor import SmartExtractor

def main():
    print("=" * 60)
    print("Smart Extractor Test")
    print("=" * 60)
    
    # 1. predictions_ocr_only.json 로드
    print("\n1. Loading predictions...")
    with open('data/output/predictions_ocr_only.json', 'r', encoding='utf-8') as f:
        predictions = json.load(f)
    print(f"   Loaded {len(predictions)} documents")
    
    # 2. SmartExtractor 초기화
    print("\n2. Initializing SmartExtractor...")
    extractor = SmartExtractor()
    print(f"   Model: {extractor.model}")
    print(f"   Ollama URL: {extractor.ollama_url}")
    
    # 3. 첫 번째 문서 선택 (receipt)
    sample = predictions[0].copy()  # 복사본 사용
    print(f"\n3. Testing with: {sample['filename']}")
    
    # 임시로 doc_type 수정 (현재는 "unknown"이니까)
    sample['classification']['doc_type'] = 'receipt'
    sample['classification']['confidence'] = 0.95
    
    print(f"   Doc Type: {sample['classification']['doc_type']}")
    print(f"   Text Preview: {sample['full_text_ocr'][:100]}...")
    print(f"   Key-Value Pairs: {len([s for s in sample['layout']['sections'] if s['type'] == 'key_value'])}")
    
    # 4. 추출 실행
    print("\n4. Extracting data...")
    print("   (This may take 10-30 seconds...)")
    
    result = extractor.extract(sample)
    
    # 5. 결과 출력
    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 6. 결과 분석
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    if result:
        print(f"✓ Extracted {len(result)} fields:")
        for key, value in result.items():
            status = "✓" if value else "✗"
            print(f"  {status} {key}: {value}")
    else:
        print("✗ No data extracted (check Ollama connection)")

if __name__ == "__main__":
    main()