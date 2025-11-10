# src/llm/config.py
from pathlib import Path
import json

def read_prompt(path: str | Path) -> str:
    """프롬프트 파일을 UTF-8로 읽어 문자열 반환"""
    return Path(path).read_text(encoding="utf-8")

def load_schema(path: str | Path) -> dict:
    """JSON 스키마 파일을 로드해 dict로 반환"""
    return json.loads(Path(path).read_text(encoding="utf-8"))

BASE = Path(__file__).resolve().parent
PROMPTS_DIR = BASE / "prompts"
SCHEMAS_DIR = BASE / "schemas"

DEFAULT_MODEL = "qwen2.5:7b"
DEFAULT_RETRIES = 2
JSON_MAX_TOKENS = 500

DOC_CONFIG = {
    "passport": {
        "schema": SCHEMAS_DIR / "passport_v1.json",
        "prompt": PROMPTS_DIR / "extract_passport.txt",
    },
    "resume": {
        "schema": SCHEMAS_DIR / "resume_v1.json",
        "prompt": PROMPTS_DIR / "extract_resume.txt",
    },
    "invoice": {
        "schema": SCHEMAS_DIR / "invoice_v1.json",
        "prompt": PROMPTS_DIR / "extract_invoice.txt",
    },
    "purchase_order": {
        "schema": SCHEMAS_DIR / "purchase_order_v1.json",
        "prompt": PROMPTS_DIR / "extract_purchase_order.txt",
    },
    "custom_form": {
        "schema": SCHEMAS_DIR / "custom_form_v1.json",
        "prompt": PROMPTS_DIR / "extract_custom_form.txt",
    },
}