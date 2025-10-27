import json
import pathlib
import re
from json import loads

from client import LLMClient
from guards import guarded_json

# ---------- utils ----------
def read(p: str) -> str:
    return pathlib.Path(p).read_text(encoding="utf-8")

def fill(tpl: str, text: str) -> str:
    # {TEXT} 와 {{TEXT}} 모두 치환 (프롬프트 파일 형식 차이 방지)
    return tpl.replace("{{TEXT}}", text).replace("{TEXT}", text)

# ---------- heuristic fallback for classification ----------
def heuristic_classify(text: str):
    t = text.lower()

    # 단서 키워드
    invoice_hits = any(k in t for k in ["invoice", "bill to", "invoice date", "subtotal", "tax invoice"])
    receipt_hits = any(k in t for k in ["receipt", "thank you for your purchase", "cashier", "pos", "change"])
    report_hits  = any(k in t for k in ["report", "executive summary", "introduction", "conclusion"])

    if invoice_hits and not receipt_hits:
        return {"doc_type": "invoice", "confidence": 0.80}
    if receipt_hits and not invoice_hits:
        return {"doc_type": "receipt", "confidence": 0.75}
    if report_hits:
        return {"doc_type": "report", "confidence": 0.70}

    # 금액/통화 패턴이 많으면 영수증/인보이스 가중치
    money = len(re.findall(r"\b\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?\s?(?:usd|thb|krw|jpy|eur|\$)", t))
    if money >= 2:
        return {"doc_type": "invoice", "confidence": 0.65}

    return {"doc_type": "report", "confidence": 0.60}

# ---------- LLM tasks ----------
async def classify(text: str, llm: LLMClient):
    prompt = read("prompts/classify.txt")
    out = await llm.generate(fill(prompt, text), max_tokens=220, temperature=0.0)
    try:
        obj = loads(out)
        if not isinstance(obj, dict) or "doc_type" not in obj:
            raise ValueError("bad json")
        # 신뢰도 낮으면 휴리스틱으로 보정
        conf = float(obj.get("confidence", 0.0))
        if conf < 0.60:
            return heuristic_classify(text)
        return obj
    except Exception:
        return heuristic_classify(text)

async def extract_invoice(text: str, llm: LLMClient, schema: dict):
    tpl = read("prompts/extract_invoice.txt")
    return await guarded_json(llm, fill(tpl, text), schema)

async def extract_receipt(text: str, llm: LLMClient, schema: dict):
    tpl = read("prompts/extract_receipt.txt")
    return await guarded_json(llm, fill(tpl, text), schema)

async def summarize(text: str, llm: LLMClient):
    tpl = read("prompts/summarize.txt")
    s = await llm.generate(fill(tpl, text), max_tokens=200, temperature=0.0)
    return s.replace("\n", " ").strip()

# ---------- PII (LLM + Regex merge) ----------
def regex_pii(text: str):
    found = []
    # email
    for m in re.finditer(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        found.append({"type": "EMAIL", "text": m.group(0)})
    # phone (단순)
    for m in re.finditer(r"\+?\d[\d\s\-]{7,}\d", text):
        found.append({"type": "PHONE", "text": m.group(0)})
    # 태국 ID 예시: 1-1020-30405-60-7
    for m in re.finditer(r"\b\d-\d{4}-\d{5}-\d{2}-\d\b", text):
        found.append({"type": "THAI_ID", "text": m.group(0)})
    return found

async def detect_pii(text: str, llm: LLMClient):
    tpl = read("prompts/pii.txt")
    out = await llm.generate(fill(tpl, text), max_tokens=400, temperature=0.0)
    llm_list = []
    try:
        llm_list = loads(out) if out.strip().startswith("[") else []
    except Exception:
        llm_list = []

    regex_list = regex_pii(text)

    # 병합(중복 제거)
    seen = set()
    merged = []
    for item in (llm_list + regex_list):
        k = (item.get("type", ""), item.get("text", ""))
        if k not in seen:
            seen.add(k)
            merged.append(item)
    return merged