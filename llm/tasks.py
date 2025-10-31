import json
import pathlib
import re
from json import loads
from pathlib import Path

from client import LLMClient
from guards import guarded_json

BASE = Path(__file__).resolve().parent
PROMPTS = BASE / "prompts"

# ---------- utils ----------
def read(p: str | Path) -> str:
    p = Path(p)
    if not p.is_absolute():
        p = PROMPTS / p
    return p.read_text(encoding="utf-8")

def fill(tpl: str, text: str) -> str:
    return tpl.replace("{{TEXT}}", text).replace("{TEXT}", text)

# ---------- heuristic fallback ----------
def heuristic_classify(text: str):
    t = text.lower()
    invoice_hits = any(k in t for k in ["invoice", "bill to", "invoice date", "subtotal", "tax invoice"])
    receipt_hits = any(k in t for k in ["receipt", "thank you for your purchase", "cashier", "pos", "change"])
    report_hits  = any(k in t for k in ["report", "executive summary", "introduction", "conclusion"])

    if invoice_hits and not receipt_hits:
        return {"doc_type": "invoice", "confidence": 0.80}
    if receipt_hits and not invoice_hits:
        return {"doc_type": "receipt", "confidence": 0.75}
    if report_hits:
        return {"doc_type": "report", "confidence": 0.70}

    money = len(re.findall(r"\b\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?\s?(?:usd|thb|krw|jpy|eur|\$)", t))
    if money >= 2:
        return {"doc_type": "invoice", "confidence": 0.65}

    return {"doc_type": "report", "confidence": 0.60}

# ---------- LLM tasks ----------
async def classify(text: str, llm: LLMClient):
    prompt = read("classify.txt")
    out = await llm.generate(fill(prompt, text), max_tokens=220, temperature=0.0)
    try:
        obj = loads(out)
        if not isinstance(obj, dict) or "doc_type" not in obj:
            raise ValueError("bad json")
        conf = float(obj.get("confidence", 0.0))
        if conf < 0.60:
            return heuristic_classify(text)
        return obj
    except Exception:
        return heuristic_classify(text)

# 통합 구조화 추출 (doc_type 별로 프롬프트/스키마 선택)
async def extract_structured(text: str, llm: LLMClient, doc_type: str, schema_map: dict):
    doc_type = (doc_type or "report").lower()
    if doc_type == "invoice":
        tpl = read("extract_invoice.txt")
        schema = schema_map.get("invoice", {})
        return await guarded_json(llm, fill(tpl, text), schema)
    if doc_type == "receipt":
        tpl = read("extract_receipt.txt")
        schema = schema_map.get("receipt", {})
        return await guarded_json(llm, fill(tpl, text), schema)
    # report/resume/contract 는 지금은 핵심 필수 아님 -> 빈 dict
    return {}

async def summarize(text: str, llm: LLMClient):
    tpl = read("summarize.txt")
    s = await llm.generate(fill(tpl, text), max_tokens=200, temperature=0.0)
    return s.replace("\n", " ").strip()

# ---------- PII ----------
ORG_SUFFIXES = (" inc", " ltd", " co", " corp", " llc", " gmbh", " s.a.", " s.p.a", " pte", " plc")

def _is_org_name(s: str) -> bool:
    t = s.lower().strip()
    return any(t.endswith(sfx) or sfx in t for sfx in ORG_SUFFIXES)

def _line_has_phone_keyword(line: str) -> bool:
    t = line.lower()
    return any(k in t for k in ["phone", "tel", "contact", "전화", "연락"])

def regex_pii_strict(text: str):
    res = []
    lines = [ln for ln in text.splitlines()]

    for m in re.finditer(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        res.append({"type": "EMAIL", "text": m.group(0)})

    for m in re.finditer(r"\b\d-\d{4}-\d{5}-\d{2}-\d\b", text):
        res.append({"type": "THAI_ID", "text": m.group(0)})

    phone_re = re.compile(r"(?:\+?\d[\d\s\-]{7,}\d)")
    for ln in lines:
        if _line_has_phone_keyword(ln):
            for m in phone_re.finditer(ln):
                num = m.group(0)
                if len(re.sub(r"\D", "", num)) < 8:
                    continue
                res.append({"type": "PHONE", "text": num})

    for m in re.finditer(r"\b(Name|Contact Name|담당자명)\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text):
        candidate = m.group(2).strip()
        if not _is_org_name(candidate):
            res.append({"type": "PERSON_NAME", "text": candidate})
    return res

def _merge_pii(a, b):
    seen = set()
    out = []
    for item in (a or []) + (b or []):
        k = (item.get("type", ""), item.get("text", "").strip())
        if k not in seen and item.get("text"):
            seen.add(k)
            out.append({"type": item["type"], "text": item["text"].strip()})
    return out

async def detect_pii(text: str, llm: LLMClient):
    tpl = read("pii.txt")
    out = await llm.generate(fill(tpl, text), max_tokens=500, temperature=0.0)

    llm_list = []
    try:
        if out.strip().startswith("["):
            llm_list = json.loads(out)
    except Exception:
        llm_list = []

    rx_list = regex_pii_strict(text)
    merged = _merge_pii(llm_list, rx_list)
    whitelist = {"PERSON_NAME", "PHONE", "EMAIL", "ADDRESS", "NATIONAL_ID", "PASSPORT", "THAI_ID"}
    merged = [x for x in merged if x.get("type") in whitelist]
    return merged