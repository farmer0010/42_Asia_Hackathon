import json
import os
import argparse
from typing import Dict

from src.llm.extractors.smart_extractor import SmartExtractor
from src.llm.extractors.pii_detector import PIIDetector
from src.llm.extractors.summarizer import DocumentSummarizer  # 기존 그대로 사용

def convert_prediction_to_hackathon(
    prediction: Dict,
    extractor: SmartExtractor,
    pii_detector: PIIDetector,
    summarizer: DocumentSummarizer
) -> Dict:
    doc_type = (prediction.get("classification") or {}).get("doc_type", "unknown")
    full_text = prediction.get("full_text_ocr", "")

    result = {
        "filename": prediction.get("filename", ""),
        "classification": {
            "doc_type": doc_type,
            "confidence": (prediction.get("classification") or {}).get("confidence", 0.0),
        },
        "full_text_ocr": full_text,
    }

    # 추출: invoice/receipt/resume/report/contract 모두 스키마 기반 추출 가능
    if doc_type in ["invoice", "receipt", "resume", "report", "contract"]:
        extracted = extractor.extract(prediction)
        if extracted:
            result["extracted_data"] = extracted

    # 요약: report/contract 우선, 필요하면 전타입에 1-2문장 요약 붙여도 됨
    if doc_type in ["report", "contract"]:
        summary = summarizer.summarize(full_text, doc_type)
        if summary:
            result["summary"] = summary

    # PII: 모든 문서 탐지
    pii_list = pii_detector.detect(full_text, use_llm=True)
    result["pii_detected"] = pii_list

    return result


def main():
    ap = argparse.ArgumentParser(description="Convert OCR predictions to hackathon format")
    ap.add_argument("--input", required=True, help="Input JSON file (predictions_ocr_only.json)")
    ap.add_argument("--output", required=True, help="Output JSON file")
    ap.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama server URL")
    ap.add_argument("--model", default="gemma3:4b", help="Model name (e.g., gemma3:4b, qwen2.5:3b)")
    ap.add_argument("--retries", type=int, default=2, help="LLM JSON guard retries")
    args = ap.parse_args()

    print("=" * 60)
    print("Convert to Hackathon Format")
    print("=" * 60)

    print(f"\n1. Loading input: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        predictions = json.load(f)
    print(f"   Loaded {len(predictions)} documents")

    print(f"\n2. Initializing modules...")
    extractor = SmartExtractor(ollama_url=args.ollama_url, model=args.model, retries=args.retries)
    pii_detector = PIIDetector(ollama_url=args.ollama_url, model=args.model)
    summarizer = DocumentSummarizer(ollama_url=args.ollama_url)  # 기존 로직 유지
    print(f"   Extractor Model: {extractor.model}, Retries: {extractor.retries}")
    print(f"   PII Detector Model: {pii_detector.model}")
    print(f"   Summarizer ready")

    print(f"\n3. Processing documents...")
    results = []
    for i, pred in enumerate(predictions, 1):
        filename = pred.get("filename", f"doc_{i}")
        doc_type = (pred.get("classification") or {}).get("doc_type", "unknown")
        print(f"   [{i}/{len(predictions)}] {filename} ({doc_type})", end="")
        try:
            r = convert_prediction_to_hackathon(pred, extractor, pii_detector, summarizer)
            results.append(r)
            print(" ✓")
        except Exception as e:
            print(f" ✗ Error: {e}")
            results.append({
                "filename": filename,
                "classification": pred.get("classification", {}),
                "full_text_ocr": pred.get("full_text_ocr", ""),
                "error": str(e),
            })

    print(f"\n4. Saving output: {args.output}")
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"   Saved {len(results)} documents")

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    counts = {}
    for r in results:
        dt = (r.get("classification") or {}).get("doc_type", "unknown")
        counts[dt] = counts.get(dt, 0) + 1
    for k, v in counts.items():
        print(f"  - {k}: {v}")

    print(f"\n✓ Complete! Output: {args.output}")


if __name__ == "__main__":
    main()