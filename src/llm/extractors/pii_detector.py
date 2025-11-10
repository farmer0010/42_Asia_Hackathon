import re
from typing import List, Dict, Optional
from .smart_extractor import SmartExtractor

class PIIDetector(SmartExtractor):
    """
    정규식 + (옵션) LLM 보조
    LLM 모델/재시도 설정은 SmartExtractor의 __init__ 인자 재사용
    """

    def __init__(self, ollama_url: str = "http://localhost:11434", model: Optional[str] = None, retries: int = 1):
        super().__init__(ollama_url=ollama_url, model=model, retries=retries)

        self.patterns = {
            "EMAIL": r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
            "PHONE_NUMBER": r'[\+]?\d[\d()\s\-]{6,}\d',
            "THAI_ID": r'\b\d-\d{4}-\d{5}-\d{2}-\d\b',
            "CREDIT_CARD": r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
        }

    def detect(self, text: str, use_llm: bool = True) -> List[Dict]:
        out: List[Dict] = []
        out.extend(self._detect_with_regex(text))
        if use_llm and text.strip():
            out.extend(self._detect_with_llm(text))
        # de-dup
        seen = set()
        uniq = []
        for item in out:
            key = (item.get("type", ""), (item.get("text") or "").strip().lower())
            if key not in seen and item.get("text"):
                seen.add(key)
                uniq.append({"type": item["type"], "text": item["text"].strip()})
        return uniq

    def _detect_with_regex(self, text: str) -> List[Dict]:
        found: List[Dict] = []
        for t, pat in self.patterns.items():
            for m in re.finditer(pat, text):
                found.append({"type": t, "text": m.group(0)})
        return found

    def _detect_with_llm(self, text: str) -> List[Dict]:
        snippet = text[:1200]
        prompt = (
            'Find PII in the text. Return ONLY JSON: {"names": [], "addresses": []}\n'
            "- names: real person names (exclude organizations: Inc, Ltd, Co, Corp)\n"
            "- addresses: postal mailing addresses\n\n"
            f"Text:\n{snippet}\n"
        )
        try:
            resp = self._call_ollama(prompt)
            obj = self._parse_first_json(resp) or {}
            out: List[Dict] = []
            for n in obj.get("names", []) or []:
                if isinstance(n, str) and len(n.strip()) > 1:
                    out.append({"type": "PERSON_NAME", "text": n.strip()})
            for a in obj.get("addresses", []) or []:
                if isinstance(a, str) and len(a.strip()) > 5:
                    out.append({"type": "ADDRESS", "text": a.strip()})
            return out
        except Exception:
            return []