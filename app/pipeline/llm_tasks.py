import os
import json
from functools import lru_cache, partial
from typing import Optional, Callable, Dict, Any
import requests

from .guards import parse_json_from_llm
from ..config import settings
from ..logger_config import setup_logging

log = setup_logging()


# --- 프롬프트/스키마 로드 헬퍼 ---
@lru_cache(maxsize=32)
def load_asset(file_path: str) -> str:
    """
    ./prompts 또는 ./schemas 디렉토리에서 파일을 로드합니다.
    (llm/tasks.py 와 동일한 로직)
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, file_path)
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        log.error(f"Failed to load asset {full_path}: {e}")
        raise


# --- LLM API 호출 ---
def call_llm(system_prompt: str, user_prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Shimmy LLM 서버에 JSON 모드로 요청을 보냅니다.
    (llm/client.py 로직을 통합)
    """
    url = f"{settings.LLM_API_BASE_URL}/chat/completions"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": settings.LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "response_format": {
            "type": "json_object",
            "schema": schema
        }
    }

    try:
        log.debug(f"Calling LLM API at {url} with model {settings.LLM_MODEL_NAME}")
        response = requests.post(url, headers=headers, json=payload, timeout=settings.LLM_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        raw_json_str = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")

        # LLM이 스키마를 따르지 않을 경우를 대비한 가드
        parsed_json = parse_json_from_llm(raw_json_str, schema)
        return parsed_json

    except requests.exceptions.Timeout:
        log.error(f"LLM API request timed out after {settings.LLM_TIMEOUT}s")
        return {"error": "LLM request timed out"}
    except requests.exceptions.RequestException as e:
        log.error(f"LLM API request failed: {e}")
        return {"error": f"LLM API request failed: {e}"}
    except Exception as e:
        log.error(f"Failed to parse LLM response: {e}")
        return {"error": f"Failed to parse LLM response: {e}"}


# --- 태스크 정의 ---

def extract_invoice_data(text: str) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/extract_invoice.txt")
    schema = json.loads(load_asset("schemas/invoice_v1.json"))
    return call_llm(system_prompt, text, schema)


def extract_receipt_data(text: str) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/extract_receipt.txt")
    schema = json.loads(load_asset("schemas/receipt_v1.json"))
    return call_llm(system_prompt, text, schema)


# ◀◀◀ [추가] ocr/llm/tasks.py 에서 가져온 기능 ◀◀◀
def extract_contract_data(text: str) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/extract_contract.txt")
    schema = json.loads(load_asset("schemas/contract_v1.json"))
    return call_llm(system_prompt, text, schema)


def extract_report_data(text: str) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/extract_report.txt")
    schema = json.loads(load_asset("schemas/report_v1.json"))
    return call_llm(system_prompt, text, schema)


def extract_resume_data(text: str) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/extract_resume.txt")
    schema = json.loads(load_asset("schemas/resume_v1.json"))
    return call_llm(system_prompt, text, schema)


# ◀◀◀ [추가 완료] ◀◀◀

def perform_pii_masking(text: str) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/pii.txt")
    # PII는 스키마가 없으므로(자유 형식), 기본 JSON 스키마 사용
    schema = {"type": "object", "properties": {"pii_detected": {"type": "array", "items": {"type": "object"}}}}
    log.warning("PII Masking is using general JSON mode. Review prompt for optimal output.")
    return call_llm(system_prompt, text, schema)


def perform_summarization(text: str) -> str:
    system_prompt = load_asset("prompts/summarize.txt")
    schema = {"type": "object", "properties": {"summary": {"type": "string"}}}

    result = call_llm(system_prompt, text, schema)
    return result.get("summary", "Summary generation failed.")


# --- 태스크 매핑 ---
EXTRACTION_TASKS: Dict[str, Callable[[str], Dict[str, Any]]] = {
    "invoice": extract_invoice_data,
    "receipt": extract_receipt_data,
    "contract": extract_contract_data,  # ◀◀◀ [추가]
    "report": extract_report_data,  # ◀◀◀ [추가]
    "resume": extract_resume_data,  # ◀◀◀ [추가]
}


def get_llm_extraction_task(doc_type: str) -> Optional[Callable[[str], Dict[str, Any]]]:
    return EXTRACTION_TASKS.get(doc_type)