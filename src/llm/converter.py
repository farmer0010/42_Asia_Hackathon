import json
import sys
import os
from typing import Dict, Any, List
from src.llm.extractors.smart_extractor import SmartExtractor
from src.llm.extractors.pii_detector import PIIDetector
from src.llm.extractors.summarizer import DocumentSummarizer

def convert_prediction_to_hackathon(prediction: Dict, extractor: SmartExtractor, pii_detector: PIIDetector, summarizer: DocumentSummarizer) -> Dict:
    """
    하나의 prediction을 해커톤 형식으로 변환
    """
    doc_type = prediction.get('classification', {}).get('doc_type', 'unknown')
    full_text = prediction.get('full_text_ocr', '')
    
    # 기본 구조
    result = {
        "filename": prediction.get("filename", ""),
        "classification": {
            "doc_type": doc_type,
            "confidence": prediction.get('classification', {}).get('confidence', 0.0)
        },
        "full_text_ocr": full_text
    }
    
    # extracted_data: invoice/receipt/resume 추출
    if doc_type in ['invoice', 'receipt', 'resume']:
        extracted = extractor.extract(prediction)
        result["extracted_data"] = extracted
    
    # summary: report/contract 요약 (나중에 구현)
    if doc_type in ['report', 'contract']:
        summary = summarizer.summarize(full_text, doc_type)
        result["summary"] = summary
    
    # pii_detected: 모든 문서 탐지
    pii_list = pii_detector.detect(full_text, use_llm=True)
    result["pii_detected"] = pii_list
    
    return result

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert OCR results to hackathon format')
    parser.add_argument('--input', required=True, help='Input JSON file (predictions_ocr_only.json)')
    parser.add_argument('--output', required=True, help='Output JSON file')
    parser.add_argument('--ollama-url', default='http://localhost:11434', help='Ollama server URL')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Convert to Hackathon Format")
    print("=" * 60)
    
    # 1. Load input
    print(f"\n1. Loading input: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        predictions = json.load(f)
    print(f"   Loaded {len(predictions)} documents")
    
    # 2. Initialize modules
    print(f"\n2. Initializing modules...")
    extractor = SmartExtractor(ollama_url=args.ollama_url)
    pii_detector = PIIDetector(ollama_url=args.ollama_url)
    summarizer = DocumentSummarizer(ollama_url=args.ollama_url)
    print(f"   Extractor Model: {extractor.model}")
    print(f"   PII Detector ready")
    print(f"   Summarizer ready")
    
    # 3. Process each document
    print(f"\n3. Processing documents...")
    results = []
    
    for i, pred in enumerate(predictions, 1):
        filename = pred.get('filename', f'unknown_{i}')
        doc_type = pred.get('classification', {}).get('doc_type', 'unknown')
        
        print(f"   [{i}/{len(predictions)}] {filename} ({doc_type})", end='')
        
        try:
            result = convert_prediction_to_hackathon(pred, extractor, pii_detector, summarizer)
            results.append(result)
            print(" ✓")
        except Exception as e:
            print(f" ✗ Error: {e}")
            # 에러 나도 기본 구조는 추가
            results.append({
                "filename": filename,
                "classification": pred.get('classification', {}),
                "full_text_ocr": pred.get('full_text_ocr', ''),
                "error": str(e)
            })
    
    # 4. Save output
    print(f"\n4. Saving output: {args.output}")
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"   Saved {len(results)} documents")
    
    # 5. Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    doc_types = {}
    for r in results:
        dt = r.get('classification', {}).get('doc_type', 'unknown')
        doc_types[dt] = doc_types.get(dt, 0) + 1
    
    print("Document types:")
    for dt, count in doc_types.items():
        print(f"  - {dt}: {count}")
    
    print(f"\n✓ Complete! Output: {args.output}")

if __name__ == "__main__":
    main()