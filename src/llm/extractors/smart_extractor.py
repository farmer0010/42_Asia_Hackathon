import json
import re
import requests
from pathlib import Path
from typing import Dict, Any

from src.llm.guards import guarded_json_best_effort

PROMPTS = {
    "invoice":  "src/llm/prompts/extract_invoice.txt",
    "receipt":  "src/llm/prompts/extract_receipt.txt",
    "report":   "src/llm/prompts/extract_report.txt",
    "resume":   "src/llm/prompts/extract_resume.txt",
    "contract": "src/llm/prompts/extract_contract.txt",
}

SCHEMA_PATHS = {
    "invoice":  "src/llm/schemas/invoice_v1.json",
    "receipt":  "src/llm/schemas/receipt_v1.json",
    "report":   "src/llm/schemas/report_v1.json",
    "resume":   "src/llm/schemas/resume_v1.json",
    "contract": "src/llm/schemas/contract_v1.json",
}

def _read(p: str) -> str:
    return Path(p).read_text(encoding="utf-8")

def _load_json(p: str) -> Dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))

def _fill(tpl: str, text: str) -> str:
    return tpl.replace("{{TEXT}}", text).replace("{TEXT}", text)


class SmartExtractor:
    def __init__(self, ollama_url="http://localhost:11434", model="gemma3:4b", retries: int = 2):
        """LLM 기반 스마트 추출기 (스키마+가드+베스트에포트)"""
        self.ollama_url = ollama_url
        self.model = model
        self.retries = retries

        # 미리 스키마 로드
        self.schemas = {k: _load_json(v) for k, v in SCHEMA_PATHS.items()}

    # ---- LLM I/F ----
    def _call_ollama(self, prompt: str, max_tokens: int = 800, temperature: float = 0.0) -> str:
        url = f"{self.ollama_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 1.0,
                "num_ctx": 4096,
                "num_predict": max_tokens
            }
        }
        try:
            r = requests.post(url, json=payload, timeout=180)
            r.raise_for_status()
            return r.json().get("response", "")
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return ""

    async def generate(self, prompt, max_tokens=800, temperature=0.0):
        # guards.py가 기대하는 async I/F
        # (동기 요청을 단순히 감싸서 사용)
        return self._call_ollama(prompt, max_tokens=max_tokens, temperature=temperature)

    # ---- Main ----
    def extract(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        prediction: {
          "filename": ...,
          "classification": {"doc_type": "...", "confidence": ...},
          "full_text_ocr": "...",
          "layout": {...} (optional)
        }
        """
        doc_type = (prediction.get("classification") or {}).get("doc_type", "unknown").lower()
        if doc_type not in PROMPTS:
            return {}

        full_text = (prediction.get("full_text_ocr") or "")[:4000]  # context 가드
        tpl = _read(PROMPTS[doc_type])
        prompt = _fill(tpl, full_text)
        schema = self.schemas[doc_type]

        # 스키마 검증 + 재시도 + 베스트에포트
        # (동기 함수이므로 간단히 이벤트루프없이 run_until_complete 대체: 여기선 sync wait 없이 호출)
        # 요청: generate는 async이지만 내부는 동기로 돌아가서 문제 없음.
        import asyncio
        try:
            res = asyncio.run(guarded_json_best_effort(
                self, prompt, schema, retries=self.retries, max_tokens=800, temperature=0.0
            ))
        except RuntimeError:
            # 이미 루프가 돌고 있을 수 있는 환경(예: 노트북) 대비
            # 그런 경우엔 직접 한 번 호출
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 임시 태스크로 처리
                fut = asyncio.ensure_future(guarded_json_best_effort(
                    self, prompt, schema, retries=self.retries, max_tokens=800, temperature=0.0
                ))
                res = loop.run_until_complete(fut)
            else:
                raise

        return res or {}