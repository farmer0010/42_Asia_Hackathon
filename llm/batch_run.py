import asyncio
import json
import sys
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

from client import LLMClient
from tasks import classify, extract_structured, summarize, detect_pii


# ----------------------------- utils -----------------------------
def load_schema(p: str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def build_final_json(
    filename: str,
    classification: dict,
    full_text: str,
    extracted: Optional[dict],
    summary: str,
    pii: Optional[list],
) -> dict:
    return {
        "filename": filename,
        "classification": {
            "doc_type": classification.get("doc_type", "report"),
            "confidence": float(classification.get("confidence", 0.0)),
        },
        "full_text_ocr": full_text,
        "extracted_data": extracted or {},
        "summary": summary,
        "pii_detected": pii or [],
    }


def _safe_name(name: str) -> str:
    """파일/디렉토리 안전 이름으로 정규화 (확장자 포함)"""
    s = Path(name).name  # 경로 제거
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s or "document.txt"


def _safe_stem(name: str) -> str:
    """확장자 제외 파일명 스템만 안전 처리"""
    stem = Path(name).stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)
    return stem or "document"


def _ensure_unique_dir(base: Path) -> Path:
    """이미 존재하면 _2, _3… 식으로 디렉토리명 유니크 보장"""
    if not base.exists():
        return base
    i = 2
    while True:
        cand = base.parent / f"{base.name}_{i}"
        if not cand.exists():
            return cand
        i += 1


def load_input(path: str) -> Tuple[str, Any]:
    """
    입력 자동 인식:
    - JSON(dict): {"filename": "...", "full_text_ocr": "...", "classification": {...}}
    - JSON(list): [{"filename":..., "full_text_ocr":...}, ...]
    - 텍스트: ocr.txt로 간주

    반환:
      ("single", (full_text:str, meta:dict))
      ("batch",  [(full_text:str, meta:dict), ...])

    meta = {"filename": str|None, "classification": dict|None}
    """
    p = Path(path)
    if p.suffix.lower() == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            items: List[Tuple[str, Dict[str, Any]]] = []
            for js in data:
                if not isinstance(js, dict):
                    continue
                text = js.get("full_text_ocr") or ""
                meta = {
                    "filename": js.get("filename"),
                    "classification": js.get("classification") if isinstance(js.get("classification"), dict) else None,
                }
                items.append((text, meta))
            return "batch", items
        elif isinstance(data, dict):
            text = data.get("full_text_ocr") or ""
            meta = {
                "filename": data.get("filename"),
                "classification": data.get("classification") if isinstance(data.get("classification"), dict) else None,
            }
            return "single", (text, meta)
        else:
            raise ValueError("JSON must be an object or an array.")
    else:
        # 일반 텍스트 파일
        text = p.read_text(encoding="utf-8", errors="ignore")
        meta = {"filename": p.name, "classification": None}
        return "single", (text, meta)


# --------------------------- core pipeline ---------------------------
async def process_one_item(
    full_text: str,
    meta: Dict[str, Any],
    out_dir: Path,
    llm: LLMClient,
    schema_map: Dict[str, dict],
):
    # 1) 분류 (meta에 있으면 우선 사용)
    if meta.get("classification"):
        cls = meta["classification"]
    else:
        cls = await classify(full_text, llm)
    doc_type = cls.get("doc_type", "report")

    # 2) 구조화 추출 (타입별 스키마/프롬프트 내부에서 처리)
    extracted = await extract_structured(full_text, llm, doc_type, schema_map) or {}

    # 3) 요약
    summary = await summarize(full_text, llm)

    # 4) PII
    pii = await detect_pii(full_text, llm)

    # 5) 파일명/출력 디렉토리: **원본 filename 사용**
    #    - JSON의 filename 우선, 없으면 "document.txt"
    raw_filename = meta.get("filename") or "document.txt"
    safe_filename = _safe_name(raw_filename)         # 예: invoice_123.pdf
    folder_name = _safe_stem(safe_filename)          # 예: invoice_123
    sub = out_dir / folder_name
    sub = _ensure_unique_dir(sub)
    sub.mkdir(parents=True, exist_ok=True)

    # 6) 최종 JSON (filename 필드에도 원본 파일명 반영)
    final_json = build_final_json(
        filename=safe_filename,
        classification=cls,
        full_text=full_text,
        extracted=extracted,
        summary=summary,
        pii=pii,
    )

    # 7) 저장
    (sub / "ocr.txt").write_text(full_text, encoding="utf-8")
    (sub / "summary.txt").write_text(summary.replace("\n", " ").strip(), encoding="utf-8")
    (sub / "result.json").write_text(json.dumps(final_json, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] saved → {sub.resolve()}")


async def process(
    input_path: str,
    out_dir: str,
    doc_filename_or_path: Optional[str],  # 유지하지만 사용 안 함
    model_name: str = "gemma3:4b",
):
    mode, payload = load_input(input_path)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # LLM & schemas
    llm = LLMClient(model=model_name)
    schema_map = {
        "invoice":  load_schema("schemas/invoice_v1.json"),
        "receipt":  load_schema("schemas/receipt_v1.json"),
        "report":   load_schema("schemas/report_v1.json"),
        "resume":   load_schema("schemas/resume_v1.json"),
        "contract": load_schema("schemas/contract_v1.json"),
    }

    if mode == "single":
        full_text, meta = payload  # type: ignore
        await process_one_item(
            full_text=full_text,
            meta=meta,
            out_dir=out,
            llm=llm,
            schema_map=schema_map,
        )
    else:
        # batch
        items: List[Tuple[str, Dict[str, Any]]] = payload  # type: ignore
        for full_text, meta in items:
            await process_one_item(
                full_text=full_text,
                meta=meta,
                out_dir=out,
                llm=llm,
                schema_map=schema_map,
            )


# ------------------------------ CLI ------------------------------
def parse_args(argv):
    """
    Usage:
      # 텍스트 입력
      python3 batch_run.py <ocr.txt> <output_dir> [doc_filename_or_path] [model]

      # JSON 입력 (dict 또는 list)
      python3 batch_run.py <input.json> <output_dir> [doc_filename_or_path] [model]
    """
    if len(argv) < 3:
        print(parse_args.__doc__)
        sys.exit(1)

    inp = argv[1]
    out_dir = argv[2]
    doc_hint = None  # 유지만 함
    model = "gemma3:4b"

    if len(argv) >= 4:
        third = argv[3]
        if third.endswith((".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")) or "." in third:
            doc_hint = third
        else:
            model = third

    if len(argv) >= 5:
        model = argv[4]

    return inp, out_dir, doc_hint, model


if __name__ == "__main__":
    inp, out_dir, doc_hint, model = parse_args(sys.argv)
    asyncio.run(process(inp, out_dir, doc_hint, model))
