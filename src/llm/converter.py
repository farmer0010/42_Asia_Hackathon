import json
import sys
import os
from typing import Dict, Any, List, Tuple
from datetime import datetime
from src.llm.extractors.smart_extractor import SmartExtractor
from src.llm.extractors.pii_detector import PIIDetector
from src.llm.extractors.summarizer import DocumentSummarizer


def calculate_compliance_level(pii_list: List[Dict]) -> Tuple[str, str]:
    """
    PII 처리 상태에 따라 compliance 레벨 계산
    
    Args:
        pii_list: 탐지된 PII 리스트
    
    Returns:
        (level, notes) - level: "full"/"partial"/"non_compliant", notes: 설명
    """
    if not pii_list:
        return "full", "No personal identifiable information detected"
    
    # 모든 PII가 마스킹되었는지 확인
    all_masked = all(
        pii.get("masked") and "masking_error" not in pii 
        for pii in pii_list
    )
    
    if all_masked:
        return "full", f"All {len(pii_list)} PII items detected and successfully masked"
    else:
        masked_count = sum(1 for pii in pii_list if pii.get("masked") and "masking_error" not in pii)
        if masked_count == 0:
            return "non_compliant", f"0/{len(pii_list)} PII items masked - masking failed"
        else:
            return "partial", f"Only {masked_count}/{len(pii_list)} PII items successfully masked"


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
    
    # summary: report/contract 요약
    if doc_type in ['report', 'contract']:
        summary = summarizer.summarize(full_text, doc_type)
        result["summary"] = summary
    
    # pii_detected: 모든 문서 탐지
    pii_list = pii_detector.detect(full_text, use_llm=True)
    
    # ✨ PII 마스킹 (에러 핸들링 포함)
    for pii in pii_list:
        try:
            pii["masked"] = pii_detector.mask_text(pii["text"], pii["type"])
        except Exception as e:
            pii["masked"] = "***"  # 실패 시 기본값
            pii["masking_error"] = str(e)
    
    result["pii_detected"] = pii_list
    
    # ✨ 마스킹된 전체 텍스트 추가
    if pii_list:
        result["full_text_masked"] = pii_detector.mask_full_text(full_text, pii_list)
    
    # ✨ Compliance 레벨 계산
    compliance_level, compliance_notes = calculate_compliance_level(pii_list)
    
    # 모든 PII가 마스킹되었는지 확인
    all_masked = all(
        pii.get("masked") and "masking_error" not in pii 
        for pii in pii_list
    )
    
    # ✨ GDPR/PDPA Compliance 정보 (조건부)
    result["compliance"] = {
        "compliance_level": compliance_level,
        "compliance_notes": compliance_notes,
        
        "pii_handling": {
            "detected": len(pii_list) > 0,
            "count": len(pii_list),
            "types_found": list(set(p["type"] for p in pii_list)) if pii_list else [],
            "all_masked": all_masked,
            "storage_policy": "not_stored_permanently"
        },
        
        # 조건부: full compliance일 때만 true
        "gdpr_compliant": compliance_level == "full",
        "pdpa_compliant": compliance_level == "full",
        
        "data_minimization": True,
        "purpose": "document_processing_only",
        "can_be_deleted": True,
        "processed_at": datetime.utcnow().isoformat() + "Z",
        
        # 전제 조건 명시
        "assumptions": [
            "Processing with user consent",
            "No permanent storage of personal data",
            "Right to deletion available on request",
            "Processing for legitimate business purpose only"
        ]
    }
    
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