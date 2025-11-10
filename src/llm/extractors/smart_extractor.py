import os
import json
import re
import requests
from typing import Dict, Any, List, Tuple, Optional

from jsonschema import validate as json_validate, ValidationError
from src.llm.config import read_prompt, load_schema

SEED_KV_LIMIT = 12  # sections에서 힌트로 넣을 key_value 개수
DEFAULT_TIMEOUT = 180


class SmartExtractor:
    """
    sections(키-값) 우선 → 부족 시 LLM 호출(프롬프트/스키마 분리) → JSON Guard 재시도
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: Optional[str] = None,
        retries: int = 2,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.ollama_url = ollama_url
        self.model = model or os.environ.get("LLM_MODEL", "qwen2.5:7b")
        self.retries = int(retries)
        self.timeout = int(timeout)

    # ---------- public ----------
    def extract(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        prediction: predictions_with_types.json의 각 항목
        returns: extracted_data dict
        """
        doc_type = (prediction.get("classification", {}) or {}).get("doc_type", "unknown").lower()
        if doc_type not in {"invoice", "receipt", "report", "resume", "contract"}:
            return {}

        full_text = prediction.get("full_text_ocr", "") or ""
        layout = prediction.get("layout", {}) or {}
        sections = layout.get("sections", []) or []

        # 1) sections에서 seed 값 뽑기
        seed = self._sections_to_seed(sections)

        # 2) prompt / schema 로드
        prompt_key = f"extract_{doc_type}"
        tpl = read_prompt(prompt_key)
        schema = load_schema(doc_type)

        # 3) 프롬프트 구성 (TEXT + seed힌트)
        prompt = self._build_prompt(tpl, full_text, seed)

        # 4) 호출 + 가드(재시도)
        parsed = self._guarded_json(prompt, schema, self.retries)

        # 5) fail-safe: dict 아니면 빈 dict
        return parsed if isinstance(parsed, dict) else {}

    # ---------- helpers ----------
    def _sections_to_seed(self, sections: List[Dict[str, Any]]) -> List[str]:
        """layout.sections 중 type='key_value'만 최대 N개 수집"""
        out = []
        for sec in sections:
            if len(out) >= SEED_KV_LIMIT:
                break
            if sec.get("type") == "key_value":
                text = (sec.get("text") or "").strip()
                if text:
                    out.append(text)
        return out

    def _build_prompt(self, template: str, full_text: str, seed_pairs: List[str]) -> str:
        # {TEXT} 치환
        prompt = template.replace("{TEXT}", full_text)
        prompt = prompt.replace("{{TEXT}}", full_text)

        # 템플릿 하단에 seed를 주석 아닌 본문 힌트로 추가 (모델이 활용)
        if seed_pairs:
            seed_str = "\n".join(f"- {kv}" for kv in seed_pairs)
            prompt += f"\n\n# Hints from layout key-value pairs (up to {SEED_KV_LIMIT}):\n{seed_str}\n"
        else:
            prompt += "\n\n# Hints from layout key-value pairs: (none)\n"
        return prompt

    def _call_ollama(self, prompt: str) -> str:
        url = f"{self.ollama_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.0,
            "options": {"num_predict": 700, "top_p": 1.0},
        }
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json().get("response", "") or ""

    # ---- JSON guard w/ retries ----
    def _parse_first_json(self, text: str) -> Optional[dict]:
        if not text:
            return None
        # ```json ... ``` 우선
        m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        js = None
        if m:
            js = m.group(1)
        else:
            # 가장 바깥 {} 블록
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                js = m.group(0)
            else:
                js = text.strip()
        try:
            obj = json.loads(js)
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    def _fix_prompt(self, bad_json: str, schema: dict, err: str) -> str:
        return (
            "You must output ONLY valid JSON matching this JSON Schema.\n"
            f"JSON Schema:\n{json.dumps(schema, ensure_ascii=False)}\n"
            f"Your previous output (invalid JSON):\n{bad_json}\n"
            f"Validation error:\n{err}\n"
            "Return only corrected JSON.\n"
        )

    def _guarded_json(self, base_prompt: str, schema: dict, retries: int) -> Optional[dict]:
        # 1st try
        out = self._call_ollama(base_prompt)
        obj = self._parse_first_json(out)
        if obj is not None:
            try:
                json_validate(obj, schema)
                return obj
            except ValidationError as e:
                last_err = str(e)
        else:
            last_err = "JSON parse failed"

        # retries
        bad = out
        for _ in range(max(retries, 0)):
            fix = self._fix_prompt(bad, schema, last_err)
            out = self._call_ollama(fix)
            obj = self._parse_first_json(out)
            if obj is None:
                bad = out
                last_err = "JSON parse failed"
                continue
            try:
                json_validate(obj, schema)
                return obj
            except ValidationError as e:
                bad = out
                last_err = str(e)
                continue

        # give up
        try:
            # 마지막이라도 dict면 반환
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None