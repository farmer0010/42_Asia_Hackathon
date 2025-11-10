import os
from pathlib import Path
import json

# 외부 환경변수로 경로 오버라이드 가능
PROMPTS_DIR = Path(os.environ.get("LLM_PROMPTS_DIR", "src/llm/prompts")).resolve()
SCHEMAS_DIR = Path(os.environ.get("LLM_SCHEMAS_DIR", "src/llm/schemas")).resolve()

PROMPT_FILES = {
    "classify": "classify.txt",
    "extract_invoice": "extract_invoice.txt",
    "extract_receipt": "extract_receipt.txt",
    "extract_report": "extract_report.txt",
    "extract_resume": "extract_resume.txt",
    "extract_contract": "extract_contract.txt",
    "pii": "pii.txt",
    "summarize": "summarize.txt",
}

SCHEMA_FILES = {
    "invoice": "invoice_v1.json",
    "receipt": "receipt_v1.json",
    "report": "report_v1.json",
    "resume": "resume_v1.json",
    "contract": "contract_v1.json",
}

def prompt_path(key: str) -> Path:
    return PROMPTS_DIR / PROMPT_FILES[key]

def schema_path(key: str) -> Path:
    return SCHEMAS_DIR / SCHEMA_FILES[key]

def read_prompt(key: str) -> str:
    return prompt_path(key).read_text(encoding="utf-8")

def load_schema(key: str) -> dict:
    return json.loads(schema_path(key).read_text(encoding="utf-8"))