import json
import pathlib
import re
from json import loads
from typing import Dict

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

    # 단서 키워드 (resume, contract 추가)
    invoice_hits = any(k in t for k in ["invoice", "bill to", "invoice date", "subtotal", "tax invoice"])
    receipt_hits = any(k in t for k in ["receipt", "thank you for your purchase", "cashier", "pos", "change"])
    report_hits  = any(k in t for k in ["report", "executive summary", "introduction", "conclusion"])
    resume_hits  = any(k in t for k in ["resume", "curriculum vitae", "education", "work experience"])
    contract_hits= any(k in t for k in ["contract", "agreement", "party", "effective date", "terms and conditions"])

    if invoice_hits and not (receipt_hits or resume_hits or contract_hits):
        return {"doc_type": "invoice", "confidence": 0.82}
    if receipt_hits and not (invoice_hits or resume_hits or contract_hits):
        return {"doc_type": "receipt", "confidence": 0.78}
    if resume_hits and not (invoice_hits or receipt_hits or contract_hits):
        return {"doc_type": "resume", "confidence": 0.75}
    if contract_hits and not (invoice_hits or receipt_hits or resume_hits):
        return {"doc_type": "contract", "confidence": 0.74}
    if report_hits:
        return {"doc_type": "report", "confidence": 0.70}

    # 금액/통화 패턴이 많으면 영수증/인보이스 가중치
    money = len(re.findall(r"\b\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?\s?(?:usd|thb|krw|jpy|eur|\$)", t))
    if money >= 2:
        return {"doc_type": "invoice", "confidence": 0.66}

    return {"doc_type": "report", "confidence": 0.60}


# ---------- LLM tasks ----------
async def classify(text: str, llm: LLMClient):
    prompt = read("prompts/classify.txt")  # 프롬프트 안에 5종 타입 규칙이 있어야 함
    out = await llm.generate(fill(prompt, text), max_tokens=220, temperature=0.0)
    try:
        obj = loads(out)
        if not isinstance(obj, dict) or "doc_type" not in obj:
            raise ValueError("bad json")
        # 신뢰도 낮으면 휴리스틱으로 보정
        conf = float(obj.get("confidence", 0.0))
        if conf < 0.60:
            return heuristic_classify(text)
        # 5종 이외면 보정
        if obj["doc_type"] not in {"invoice","receipt","report","resume","contract"}:
            return heuristic_classify(text)
        return obj
    except Exception:
        return heuristic_classify(text)


async def extract_structured(text: str, llm: LLMClient, doc_type: str, schema_map: Dict[str, dict]):
    """
    타입별 프롬프트/스키마에 따라 구조화 추출.
    prompts/
      - extract_invoice.txt
      - extract_receipt.txt
      - extract_report.txt
      - extract_resume.txt
      - extract_contract.txt
    schemas/
      - invoice_v1.json
      - receipt_v1.json
      - report_v1.json
      - resume_v1.json
      - contract_v1.json
    """
    name = doc_type.lower()
    if name not in schema_map:
        return {}

    prompt_files = {
        "invoice":  "prompts/extract_invoice.txt",
        "receipt":  "prompts/extract_receipt.txt",
        "report":   "prompts/extract_report.txt",
        "resume":   "prompts/extract_resume.txt",
        "contract": "prompts/extract_contract.txt",
    }
    tpl_path = prompt_files.get(name)
    if not tpl_path:
        return {}

    tpl = read(tpl_path)
    schema = schema_map[name]
    return await guarded_json(llm, fill(tpl, text), schema)


async def summarize(text: str, llm: LLMClient):
    tpl = read("prompts/summarize.txt")
    s = await llm.generate(fill(tpl, text), max_tokens=200, temperature=0.0)
    return s.replace("\n", " ").strip()


# ---------- PII (LLM + Regex merge with strict rules) ----------
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

    # EMAIL
    for m in re.finditer(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        res.append({"type": "EMAIL", "text": m.group(0)})

    # THAI_ID: 1-2345-67890-12-3
    for m in re.finditer(r"\b\d-\d{4}-\d{5}-\d{2}-\d\b", text):
        res.append({"type": "THAI_ID", "text": m.group(0)})

    # PHONE: “전화/Phone/Tel/Contact”가 있는 라인에서만 숫자 추출
    phone_re = re.compile(r"(?:\+?\d[\d()\s\-]{7,}\d)")
    for ln in lines:
        if _line_has_phone_keyword(ln):
            for m in phone_re.finditer(ln):
                num = m.group(0)
                # 너무 짧거나 명백히 다른 식별자면 제외
                if len(re.sub(r"\D", "", num)) < 8:
                    continue
                res.append({"type": "PHONE", "text": num})

    # PERSON_NAME: "Name:" 패턴 + 법인표기 제외
    for m in re.finditer(r"\b(Name|Contact Name|담당자명|Payee Name)\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text):
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
    tpl = read("prompts/pii.txt")
    out = await llm.generate(fill(tpl, text), max_tokens=500, temperature=0.0)

    llm_list = []
    try:
        if out.strip().startswith("["):
            llm_list = json.loads(out)
    except Exception:
        llm_list = []

    # 정규식 보조 (엄격)
    rx_list = regex_pii_strict(text)

    # 병합 + 화이트리스트
    merged = _merge_pii(llm_list, rx_list)
    whitelist = {"PERSON_NAME", "PHONE", "EMAIL", "ADDRESS", "NATIONAL_ID", "PASSPORT", "THAI_ID"}
    merged = [x for x in merged if x.get("type") in whitelist]

    return merged
