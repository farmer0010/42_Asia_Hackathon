import re
from typing import List, Dict
from .smart_extractor import SmartExtractor

WHITELIST_TYPES = {"PERSON_NAME", "PHONE", "EMAIL", "ADDRESS", "NATIONAL_ID", "PASSPORT", "THAI_ID"}

def _line_has_phone_keyword(ln: str) -> bool:
    t = ln.lower()
    return any(k in t for k in ["phone", "tel", "contact", "전화", "연락"])


class PIIDetector(SmartExtractor):
    """
    개인식별정보(PII) 탐지:
    - EMAIL/THAI_ID 등은 전역 정규식
    - PHONE은 '전화/Phone/Tel/Contact' 키워드가 있는 라인에서만 허용(오탐 방지)
    - LLM 보조로 PERSON_NAME/ADDRESS 보강
    - 타입을 해커톤 스펙에 맞춰 통일
    """

    def __init__(self, ollama_url="http://localhost:11434", model="gemma3:4b"):
        super().__init__(ollama_url, model=model)
        self.patterns = {
            "EMAIL": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            "THAI_ID": r"\b\d-\d{4}-\d{5}-\d{2}-\d\b",
            "CREDIT_CARD": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        }

    def detect(self, text: str, use_llm: bool = True) -> List[Dict]:
        out: List[Dict] = []
        out.extend(self._regex_email(text))
        out.extend(self._regex_thaiid(text))
        out.extend(self._regex_phone_contextual(text))
        # 카드번호는 보고만 하거나 제외(필요시 타입 추가 가능)
        # out.extend(self._regex_cc(text))

        if use_llm and text.strip():
            out.extend(self._llm_names_addresses(text[:1200]))

        # 중복 제거 + 화이트리스트
        uniq = []
        seen = set()
        for item in out:
            t = item.get("type")
            s = (t, (item.get("text") or "").strip().lower())
            if t in WHITELIST_TYPES and s not in seen and item.get("text"):
                seen.add(s)
                uniq.append({"type": t, "text": item["text"].strip()})
        return uniq

    def _regex_email(self, text: str) -> List[Dict]:
        return [{"type": "EMAIL", "text": m.group(0)} for m in re.finditer(self.patterns["EMAIL"], text)]

    def _regex_thaiid(self, text: str) -> List[Dict]:
        return [{"type": "THAI_ID", "text": m.group(0)} for m in re.finditer(self.patterns["THAI_ID"], text)]

    def _regex_phone_contextual(self, text: str) -> List[Dict]:
        found: List[Dict] = []
        phone_re = re.compile(r"(?:\+?\d[\d()\s\-]{7,}\d)")
        for ln in text.splitlines():
            if _line_has_phone_keyword(ln):
                for m in phone_re.finditer(ln):
                    raw = m.group(0)
                    digits = re.sub(r"\D", "", raw)
                    if len(digits) >= 8:
                        found.append({"type": "PHONE", "text": raw.strip()})
        return found

    def _llm_names_addresses(self, snippet: str) -> List[Dict]:
        prompt = f"""Detect PII in the text snippet.

Return ONLY JSON with two arrays:
{{"names": [], "addresses": []}}

- "names": real person full names (exclude organizations like Inc., Ltd., Co., Corp.)
- "addresses": complete mailing addresses

Text:
{snippet}
"""
        try:
            resp = self._call_ollama(prompt, max_tokens=400, temperature=0.0)
            data = self._parse_json_loose(resp)
            out: List[Dict] = []
            for n in data.get("names", []):
                if isinstance(n, str) and len(n.strip()) > 1:
                    out.append({"type": "PERSON_NAME", "text": n.strip()})
            for a in data.get("addresses", []):
                if isinstance(a, str) and len(a.strip()) > 5:
                    out.append({"type": "ADDRESS", "text": a.strip()})
            return out
        except Exception as e:
            print(f"Warning: LLM PII detection failed: {e}")
            return []

    def _parse_json_loose(self, resp: str) -> Dict:
        if not resp:
            return {}
        m = re.search(r"```json\s*(\{.*?\})\s*```", resp, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        m = re.search(r"\{.*\}", resp, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        return {}