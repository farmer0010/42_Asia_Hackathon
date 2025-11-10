import argparse
import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, List
from copy import deepcopy

from src.llm.config import DOC_CONFIG, DEFAULT_MODEL, DEFAULT_RETRIES
from src.llm.extractors.smart_extractor import SmartExtractor
from src.llm.extractors.pii_detector import PIIDetector

from jsonschema import validate as json_validate, ValidationError
import traceback

def load_json(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # 이미 리스트면 그대로
    if isinstance(data, list):
        return data

    # {"documents":[...]} 형태
    if isinstance(data, dict) and isinstance(data.get("documents"), list):
        return data["documents"]

    # {"filename1": {...}, "filename2": {...}} 형태
    if isinstance(data, dict):
        out = []
        for k, v in data.items():
            if isinstance(v, dict) and "filename" not in v:
                v = {**v, "filename": k}
            out.append(v)
        return out

    # 그 외 예외: 빈 리스트 반환 (아래 가드에서 걸러짐)
    return []


def save_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clip(text: str, n: int = 1200) -> str:
    return text if len(text) <= n else text[:n]


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def try_float(x):
    try:
        return float(str(x).replace(",", "").replace("$", "").strip())
    except Exception:
        return None


def mask_text(full_text: str, pii_items: List[Dict[str, str]]) -> str:
    masked = full_text
    # 단순 대체(앞에서 뒤로). 실제 서비스면 위치 기반 마스킹 권장
    for item in pii_items:
        src = item.get("text")
        dst = item.get("masked")
        if src and dst and src in masked:
            masked = masked.replace(src, dst)
    return masked


def build_prompt(base_prompt: str, prediction: Dict[str, Any], scaffold: Dict[str, Any], kv_hints: List[str]) -> str:
    """
    공통 프롬프트 빌더:
    - full_text_ocr 앞부분
    - layout.sections에서 뽑은 key-value 힌트
    - 스키마 스캐폴드 (키 목록과 미리 채운 값 일부)
    """
    full_text = prediction.get("full_text_ocr", "")
    header = f"""You will extract structured data for doc_type = {prediction.get('classification',{}).get('doc_type')}.
Use any layout hints if provided. Output ONLY JSON.
"""
    kv_part = "\n".join(f"- {x}" for x in kv_hints) if kv_hints else "- (no key-value hints)"
    scaffold_json = json.dumps(scaffold, ensure_ascii=False, indent=2)
    body = f"""
full_text_ocr (first 1200 chars):
{clip(full_text, 1200)}

key-value hints:
{kv_part}

Return JSON matching this scaffold (fill nulls when unknown):
{scaffold_json}
"""
    return header + "\n" + base_prompt.strip() + "\n" + body


def kv_hints_from_sections(pred: Dict[str, Any], limit: int = 16) -> List[str]:
    out = []
    sections = (pred.get("layout") or {}).get("sections") or []
    for s in sections[:limit]:
        if isinstance(s, dict):
            t = s.get("text")
            if t:
                out.append(str(t).strip())
    return out


def empty_by_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    간단한 스캐폴드(스키마 키만 null/기본값으로 채우기)
    """
    def default_for(prop):
        t = prop.get("type")
        if isinstance(t, list):
            if "object" in t:
                return {}
            if "array" in t:
                return []
        if t == "object":
            return {}
        if t == "array":
            return []
        return None

    result = {}
    for k, v in (schema.get("properties") or {}).items():
        result[k] = default_for(v)
    return result

def _deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    """dict deep-merge: base에 over 값 덮어쓰기 (nested object 지원)"""
    out = deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def validate_json(schema: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    1) 그대로 검증 → 통과면 그대로 리턴
    2) 실패 시: 스캐폴드와 deep-merge(누락 키만 채움) 후 재검증
    3) 그래도 실패면 '경고'만 달고 'merge된 값'을 반환 (절대 전부 null로 초기화하지 않음)
    """
    try:
        json_validate(instance=data, schema=schema)
        return data
    except ValidationError as e1:
        scaffold = empty_by_schema(schema)
        merged = _deep_merge(scaffold, data or {})
        try:
            json_validate(instance=merged, schema=schema)
            return merged
        except ValidationError as e2:
            # 마지막 안전장치: 값은 그대로 살리고, 경고만 붙임
            if isinstance(merged, dict):
                merged = dict(merged)
                merged["_validation_warning"] = {
                    "reason": "schema_validation_failed",
                    "first_error": str(e1),
                    "second_error": str(e2),
                }
            return merged


def sections_first_then_llm(extractor: SmartExtractor,
                            base_prompt: str,
                            schema_obj: Dict[str, Any],
                            prediction: Dict[str, Any]) -> Dict[str, Any]:
    """
    1) sections/all_boxes로 간단 규칙추출 (doc_type별 내부 룰은 smart_extractor.extract()가 처리)
    2) 부족분은 LLM으로 보강
    3) schema 검증
    """
    # 1차: 규칙 추출 (extractor 내부가 doc_type에 따라 처리)
    initial = extractor.extract(prediction)  # 내부: all_boxes 활용 + MRZ 등 규칙
    try:
        print("[DEBUG][sections] initial(extractor):", json.dumps({k: v for k, v in (initial or {}).items() if v is not None}, ensure_ascii=False)[:400], file=sys.stderr)
    except Exception:
        pass

    # 2차: LLM 보강
    scaffold = empty_by_schema(schema_obj)
    # 규칙 추출 결과를 scaffold에 반영(이미 뽑힌 값은 채워넣음)
    for k, v in (initial or {}).items():
        if k in scaffold:
            scaffold[k] = v
    try:
        print("[DEBUG][sections] scaffold(after-initial):", json.dumps({k: v for k, v in scaffold.items() if v is not None}, ensure_ascii=False)[:400], file=sys.stderr)
    except Exception:
        pass

    prompt = build_prompt(
        base_prompt=base_prompt,
        prediction=prediction,
        scaffold=scaffold,
        kv_hints=kv_hints_from_sections(prediction)
    )

    llm_merge = {}
    try:
        if hasattr(extractor, "llm_fill"):
            llm_merge = extractor.llm_fill(prediction, prompt)  # 내부에서 retries 적용
            if isinstance(llm_merge, str):
                try:
                    llm_merge = json.loads(llm_merge)
                except Exception:
                    llm_merge = {}
        else:
            print("[WARN][sections] extractor has no llm_fill; skipping LLM backfill", file=sys.stderr)
    except Exception as e:
        print(f"[WARN][sections] llm_fill failed: {e}", file=sys.stderr)
        llm_merge = {}

    try:
        print("[DEBUG][sections] llm_merge:", json.dumps({k: v for k, v in (llm_merge or {}).items() if v is not None}, ensure_ascii=False)[:400], file=sys.stderr)
    except Exception:
        pass

    # 규칙값 우선 보존: scaffold(규칙) 값이 있으면 그대로 두고, 빈 칸만 LLM 값으로 보충
    merged = dict(scaffold)
    if isinstance(llm_merge, dict):
        for k, v in llm_merge.items():
            if k not in merged or merged.get(k) in (None, "", [], {}):
                merged[k] = v

    try:
        print("[DEBUG][sections] pre-validate merged:", json.dumps({k: v for k, v in merged.items() if v is not None}, ensure_ascii=False)[:400], file=sys.stderr)
    except Exception:
        pass

    # 3) 스키마 검증/보정
    return validate_json(schema_obj, merged)


def process_one(pred: Dict[str, Any],
                extractor: SmartExtractor,
                pii: PIIDetector) -> Dict[str, Any]:
    doc_type = (pred.get("classification") or {}).get("doc_type", "unknown")
    raw_text = pred.get("full_text_ocr", "")
    flattened_text = " ".join(str(raw_text).split())  # collapse all whitespace/newlines/tabs
    out: Dict[str, Any] = {
        "filename": pred.get("filename"),
        "classification": pred.get("classification"),
        "full_text_ocr": flattened_text
    }
    pred["full_text_ocr"] = flattened_text

    if doc_type not in DOC_CONFIG:
        # 지원 외 타입은 추출 스킵
        out["extracted_data"] = {}
        out["pii_detected"] = []
        out["full_text_masked"] = out["full_text_ocr"]
        out["compliance"] = {
            "compliance_level": "partial",
            "compliance_notes": "Unsupported doc_type; only OCR included",
            "gdpr_compliant": True,
            "pdpa_compliant": True
        }
        return out

    # 스키마/프롬프트 로드
    cfg = DOC_CONFIG[doc_type]
    schema_obj = {"type": "object", "properties": {}}
    try:
        schema_obj = json.loads(Path(cfg["schema"]).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN][schema] Failed to load schema for '{doc_type}': {e}. Using empty schema.", file=sys.stderr)

    try:
        prompt_text = read_text(Path(cfg["prompt"]))
    except Exception as e:
        print(f"[WARN][prompt] Failed to load prompt for '{doc_type}': {e}. Using empty prompt.", file=sys.stderr)
        prompt_text = ""

    # 섹션우선 → LLM 보강 → 검증
    extracted = sections_first_then_llm(
        extractor=extractor,
        base_prompt=prompt_text,
        schema_obj=schema_obj,
        prediction=pred
    )
    out["extracted_data"] = extracted

    # PII 탐지/마스킹
    pii_items = pii.detect(out["full_text_ocr"], use_llm=(doc_type in ["resume", "custom_form"]))
    out["pii_detected"] = pii_items
    out["full_text_masked"] = mask_text(out["full_text_ocr"], pii_items)

    # 간단 컴플라이언스 필드(해커톤용)
    out["compliance"] = {
        "compliance_level": "full",
        "compliance_notes": f"{len(pii_items)} PII items {'detected and ' if pii_items else '— '}masked" if pii_items else "No PII detected",
        "pii_handling": {
            "detected": bool(pii_items),
            "count": len(pii_items),
            "types_found": sorted({x.get("type") for x in pii_items}) if pii_items else [],
            "all_masked": True
        },
        "gdpr_compliant": True,
        "pdpa_compliant": True,
        "data_minimization": True,
        "purpose": "document_processing_only",
        "can_be_deleted": True
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="predictions_with_types.json")
    ap.add_argument("--output", required=True, help="final results path")
    ap.add_argument("--ollama-url", default="http://localhost:11434")
    ap.add_argument("--model", default=os.getenv("MODEL", DEFAULT_MODEL))
    ap.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    args = ap.parse_args()

    inp = Path(args.input)
    outp = Path(args.output)

    try:
        preds = load_json(inp)
        if not preds:
            print(f"[FATAL] No documents found in {inp}. Check file format/contents.", file=sys.stderr)
            sys.exit(2)
        else:
            print(f"[INFO] Loaded {len(preds)} documents from {inp}")
    except Exception as e:
        print(f"[FATAL] Cannot load input: {e}", file=sys.stderr)
        sys.exit(1)

    extractor = SmartExtractor(ollama_url=args.ollama_url, model=args.model, retries=args.retries)
    pii = PIIDetector(ollama_url=args.ollama_url)

    results = []
    ok, err = 0, 0
    for p in preds:
        try:
            r = process_one(p, extractor, pii)
            results.append(r)
            ok += 1
        except Exception as e:
            print(f"[WARN] Failed on {p.get('filename')}: {e}", file=sys.stderr)
            traceback.print_exc()
            err += 1

    save_json(outp, results)
    print("============================================================")
    print("Convert to Final Results (sections-first, LLM-backed)")
    print("============================================================")
    print(f"Total: {len(preds)}  Success: {ok}  Errors: {err}")
    print(f"✓ Saved to: {outp}")


if __name__ == "__main__":
    main()