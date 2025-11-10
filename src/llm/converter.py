import argparse
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

from src.llm.extractors.smart_extractor import SmartExtractor
from src.llm.extractors.pii_detector import PIIDetector
from src.llm.extractors.summarizer import DocumentSummarizer


# ------------------------- Utilities -------------------------
def _now_iso_utc() -> str:
    return datetime.utcnow().isoformat() + "Z"


def mask_text_with_pii(full_text: str, pii_list: List[Dict]) -> Tuple[str, List[Dict]]:
    """
    pii_list 각 항목에 'masked'를 채우고, 마스킹된 텍스트를 반환한다.
    단순 전략: 발견된 원문 문자열을 길이 8까지 '★'로 치환.
    (과도한 전역치환을 피하려면 실제 서비스에선 위치기반 마스킹 권장)
    """
    masked_text = full_text
    updated = []
    for item in pii_list:
        raw = (item.get("text") or "").strip()
        if not raw:
            updated.append({**item, "masked": False, "masking_error": "empty"})
            continue
        try:
            masked_text = masked_text.replace(raw, "★" * min(len(raw), 8))
            updated.append({**item, "masked": True})
        except Exception as e:
            updated.append({**item, "masked": False, "masking_error": str(e)})
    return masked_text, updated


def calculate_compliance_level(pii_items: List[Dict]) -> Tuple[str, str]:
    """
    매우 단순한 규칙:
    - PII 없음: full
    - PII 있고 모두 masked=True: full
    - 일부라도 mask 실패: partial
    """
    if not pii_items:
        return "full", "No personal data detected"
    all_masked = all(bool(x.get("masked")) for x in pii_items)
    if all_masked:
        return "full", f"All {len(pii_items)} PII items detected and masked"
    failed = [x for x in pii_items if not x.get("masked")]
    return "partial", f"{len(failed)} of {len(pii_items)} PII items could not be masked"


def _doc_type_of(pred: Dict) -> str:
    cls = pred.get("classification") or {}
    return (cls.get("doc_type") or "unknown").lower()


def _default_result(pred: Dict) -> Dict:
    return {
        "filename": pred.get("filename", ""),
        "classification": pred.get("classification", {"doc_type": "unknown", "confidence": 0.0}),
        "full_text_ocr": pred.get("full_text_ocr", ""),
        "extracted_data": {},
        "pii_detected": [],
        "full_text_masked": pred.get("full_text_ocr", ""),
        "compliance": {
            "compliance_level": "full",
            "compliance_notes": "No personal data detected",
            "pii_handling": {
                "detected": False,
                "count": 0,
                "types_found": [],
                "all_masked": True,
                "storage_policy": "not_stored_permanently",
            },
            "gdpr_compliant": True,
            "pdpa_compliant": True,
            "data_minimization": True,
            "purpose": "document_processing_only",
            "can_be_deleted": True,
            "processed_at": _now_iso_utc(),
            "summary": [
                "Processing with user consent",
                "No permanent storage of personal data",
                "Right to deletion available on request",
                "Processing for legitimate business purpose only",
            ],
        },
    }


# --------------------------- Main Pipeline ---------------------------
def convert_prediction_to_final(
    prediction: Dict,
    extractor: SmartExtractor,
    pii_detector: PIIDetector,
    summarizer: DocumentSummarizer,
) -> Dict:
    """
    v5 입력(predictions_with_types.json의 각 항목)을 최종 결과 객체로 변환
    - sections 기반 → 부족 시 LLM 가드가 포함된 SmartExtractor가 내부적으로 처리
    - PII는 타입 정규화 & 마스킹 플래그 채움
    - report/contract만 요약 생성(고급요약은 summarizer.py에 위임)
    """
    result = _default_result(prediction)

    # 1) 기본 필드
    full_text = prediction.get("full_text_ocr", "")
    result["filename"] = prediction.get("filename", result["filename"])
    result["classification"] = prediction.get("classification", result["classification"])
    result["full_text_ocr"] = full_text

    # 2) 추출(섹션 우선 → LLM 백업은 SmartExtractor가 내부 처리)
    try:
        extracted = extractor.extract(prediction)
        if isinstance(extracted, dict):
            result["extracted_data"] = extracted
    except Exception as e:
        # 추출 실패여도 파이프라인은 계속
        result["extracted_data"] = {}
        print(f"[WARN] extract() failed for {result['filename']}: {e}")

    # 3) 요약 (report/contract)
    doc_type = _doc_type_of(prediction)
    if doc_type in ("report", "contract"):
        try:
            summary = summarizer.summarize(full_text, doc_type)
            if summary and isinstance(summary, str):
                result["summary"] = summary.strip()
        except Exception as e:
            print(f"[WARN] summarize() failed for {result['filename']}: {e}")

    # 4) PII 탐지 + 마스킹
    try:
        pii_items = pii_detector.detect(full_text, use_llm=True)
    except Exception as e:
        pii_items = []
        print(f"[WARN] pii.detect() failed for {result['filename']}: {e}")

    full_text_masked, pii_with_flags = mask_text_with_pii(full_text, pii_items)
    level, notes = calculate_compliance_level(pii_with_flags)

    result["pii_detected"] = pii_with_flags
    result["full_text_masked"] = full_text_masked
    result["compliance"] = {
        "compliance_level": level,
        "compliance_notes": notes,
        "pii_handling": {
            "detected": bool(pii_with_flags),
            "count": len(pii_with_flags),
            "types_found": sorted(list({x.get("type") for x in pii_with_flags if x.get("type")})),
            "all_masked": all(bool(x.get("masked")) for x in pii_with_flags) if pii_with_flags else True,
            "storage_policy": "not_stored_permanently",
        },
        "gdpr_compliant": True,
        "pdpa_compliant": True,
        "data_minimization": True,
        "purpose": "document_processing_only",
        "can_be_deleted": True,
        "processed_at": _now_iso_utc(),
        "assumptions": [
            "Processing with user consent",
            "No permanent storage of personal data",
            "Right to deletion available on request",
            "Processing for legitimate business purpose only",
        ],
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Convert OCR+Type predictions to final results (v5)")
    parser.add_argument("--input", required=True, help="Input JSON file (predictions_with_types.json)")
    parser.add_argument("--output", required=True, help="Output JSON file (final_results.json)")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama server URL")
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL", "gemma3:4b"), help="LLM model name")
    parser.add_argument("--retries", type=int, default=int(os.environ.get("LLM_RETRIES", "2")), help="Guard retries")

    args = parser.parse_args()

    print("=" * 60)
    print("Convert to Final Results (sections-first, LLM-backed)")
    print("=" * 60)

    # 1. Load input
    print(f"\n1) Loading input: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        predictions = json.load(f)
    print(f"   Loaded {len(predictions)} documents")

    # 2. Initialize modules
    print("\n2) Initializing modules...")
    extractor = SmartExtractor(ollama_url=args.ollama_url, model=args.model, retries=args.retries)
    pii_detector = PIIDetector(ollama_url=args.ollama_url, model=args.model)
    summarizer = DocumentSummarizer(ollama_url=args.ollama_url)
    print(f"   Extractor Model: {extractor.model}, Retries: {extractor.retries}")
    print(f"   PII Detector Model: {pii_detector.model}")
    print(f"   Summarizer ready")

    # 3. Process each document
    print("\n3) Processing documents...")
    results: List[Dict] = []
    for i, pred in enumerate(predictions, 1):
        filename = pred.get("filename", f"doc_{i}")
        print(f"   [{i}/{len(predictions)}] {filename}", end="")
        try:
            res = convert_prediction_to_final(pred, extractor, pii_detector, summarizer)
            results.append(res)
            print(" ✓")
        except Exception as e:
            print(f" ✗ Error: {e}")
            # 최소한의 정보라도
            fallback = _default_result(pred)
            fallback["error"] = str(e)
            results.append(fallback)

    # 4. Save output
    print(f"\n4) Saving output: {args.output}")
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"   Saved {len(results)} documents")

    # 5. Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    doc_types = {}
    for r in results:
        dt = (r.get("classification") or {}).get("doc_type", "unknown")
        doc_types[dt] = doc_types.get(dt, 0) + 1
    print("Document types:")
    for dt, count in doc_types.items():
        print(f"  - {dt}: {count}")
    print("\n✓ Complete.")


if __name__ == "__main__":
    main()