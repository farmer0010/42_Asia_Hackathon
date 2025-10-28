import json
import pathlib
import re
from json import loads
from typing import List

from .client import LLMClient
from .guards import guarded_json

def read(p: str) -> str:
    return pathlib.Path(p).read_text(encoding="utf-8")

def fill(tpl: str, text: str) -> str:
    return tpl.replace("{{TEXT}}", text).replace("{TEXT}", text)

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

async def classify(text: str, llm: LLMClient):
    prompt = read("app/pipeline/prompts/classify.txt")
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

async def extract_invoice(text: str, llm: LLMClient, schema: dict):
    tpl = read("app/pipeline/prompts/extract_invoice.txt")
    return await guarded_json(llm, fill(tpl, text), schema)

async def extract_receipt(text: str, llm: LLMClient, schema: dict):
    tpl = read("app/pipeline/prompts/extract_receipt.txt")
    return await guarded_json(llm, fill(tpl, text), schema)

async def summarize(text: str, llm: LLMClient):
    tpl = read("app/pipeline/prompts/summarize.txt")
    s = await llm.generate(fill(tpl, text), max_tokens=200, temperature=0.0)
    return s.replace("\n", " ").strip()

def regex_pii(text: str):
    found = []
    for m in re.finditer(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        found.append({"type": "EMAIL", "text": m.group(0)})
    for m in re.finditer(r"\+?\d[\d\s\-]{7,}\d", text):
        found.append({"type": "PHONE", "text": m.group(0)})
    for m in re.finditer(r"\b\d-\d{4}-\d{5}-\d{2}-\d\b", text):
        found.append({"type": "THAI_ID", "text": m.group(0)})
    return found

async def detect_pii(text: str, llm: LLMClient):
    tpl = read("app/pipeline/prompts/pii.txt")
    out = await llm.generate(fill(tpl, text), max_tokens=400, temperature=0.0)
    llm_list = []
    try:
        llm_list = loads(out) if out.strip().startswith("[") else []
    except Exception:
        llm_list = []
    regex_list = regex_pii(text)
    seen = set()
    merged = []
    for item in (llm_list + regex_list):
        k = (item.get("type", ""), item.get("text", ""))
        if k not in seen:
            seen.add(k)
            merged.append(item)
    return merged

# === 임베딩 작업 함수 추가 ===
async def get_embedding(text: str, llm: LLMClient, model_name: str) -> List[float]:
    """텍스트를 받아 임베딩 벡터를 반환합니다."""
    safe_text = (text or "")[:4096]
    if not safe_text:
        return []
    return await llm.embed(safe_text, model_name)