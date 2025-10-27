import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from client import LLMClient
from tasks import classify, extract_invoice, extract_receipt, summarize, detect_pii

def load_schema(p: str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))

def build_final_json(filename: str,
                     classification: dict,
                     full_text: str,
                     extracted: Optional[dict],
                     summary: str,
                     pii: Optional[list]) -> dict:
    return {
        "filename": filename,
        "classification": {
            "doc_type": classification.get("doc_type", "report"),
            "confidence": float(classification.get("confidence", 0.0))
        },
        "full_text_ocr": full_text,
        "extracted_data": extracted or {},
        "summary": summary,
        "pii_detected": pii or []
    }

async def process_one(ocr_txt_path: str,
                      out_dir: str,
                      doc_filename_or_path: Optional[str],
                      model_name: str = "gemma3:4b"):
    ocr_path = Path(ocr_txt_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1) OCR 텍스트
    full_text = ocr_path.read_text(encoding="utf-8", errors="ignore")

    # 2) LLM
    llm = LLMClient(model=model_name)

    # 3) 분류
    cls = await classify(full_text, llm)
    doc_type = cls.get("doc_type", "report")

    # 4) 스키마
    invoice_schema = load_schema("schemas/invoice_v1.json")
    receipt_schema = load_schema("schemas/receipt_v1.json")

    # 5) 구조화
    extracted = {}
    if doc_type == "invoice":
        extracted = await extract_invoice(full_text, llm, invoice_schema) or {}
    elif doc_type == "receipt":
        extracted = await extract_receipt(full_text, llm, receipt_schema) or {}

    # 6) 요약
    summary = await summarize(full_text, llm)

    # 7) PII
    pii = await detect_pii(full_text, llm)

    # 8) 파일명 결정
    filename = Path(doc_filename_or_path).name if doc_filename_or_path else ocr_path.name

    # 9) 최종 JSON
    final_json = build_final_json(
        filename=filename,
        classification=cls,
        full_text=full_text,
        extracted=extracted,
        summary=summary,
        pii=pii
    )

    # 10) 저장
    (out / "ocr.txt").write_text(full_text, encoding="utf-8")
    (out / "summary.txt").write_text(summary.replace("\n", " ").strip(), encoding="utf-8")
    (out / "result.json").write_text(json.dumps(final_json, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] saved → {out.resolve()}")

def parse_args(argv):
    """
    Usage:
      python3 batch_run.py <ocr.txt> <output_dir> [doc_filename_or_path] [model]
    예시:
      python3 batch_run.py ocr.txt outputs
      python3 batch_run.py ocr.txt outputs hackathon_dataset/testing_set/documents/test_doc_01.pdf
      python3 batch_run.py ocr.txt outputs invoice_123.pdf qwen2.5:7b-instruct
    """
    if len(argv) < 3:
        print(parse_args.__doc__)
        sys.exit(1)

    ocr_txt = argv[1]
    out_dir = argv[2]
    doc_hint = None
    model = "gemma3:4b"

    if len(argv) >= 4:
        third = argv[3]
        if third.endswith((".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")) or "." in third:
            doc_hint = third
        else:
            model = third

    if len(argv) >= 5:
        model = argv[4]

    return ocr_txt, out_dir, doc_hint, model

if __name__ == "__main__":
    ocr_txt, out_dir, doc_hint, model = parse_args(sys.argv)
    asyncio.run(process_one(ocr_txt, out_dir, doc_hint, model))