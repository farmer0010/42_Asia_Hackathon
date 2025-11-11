# [수정 후: app/pipeline/llm_tasks.py]
import os
import json
from functools import lru_cache
from typing import Optional, Callable, Dict, Any
import requests

from .guards import parse_json_from_llm
from ..config import settings
from ..logger_config import setup_logging

log = setup_logging()


# --- 프롬프트/스키마 로드 헬퍼 (유지) ---
@lru_cache(maxsize=32)
def load_asset(file_path: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, file_path)
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        log.error(f"Failed to load asset {full_path}: {e}")
        raise


# --- 🔴 [!!! 수정 !!!] LLM API 호출 (입력값 변경) ---
def call_llm(
        system_prompt: str,
        # 🔴 [수정] text: str 대신 ocr_data: Dict를 받습니다.
        ocr_data: Dict[str, Any],
        schema: Dict[str, Any],
        # 🔴 [추가] 규칙 기반 1차 추출 데이터를 선택적으로 받습니다.
        heuristic_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Shimmy LLM 서버에 JSON 모드로 요청을 보냅니다.
    (OCR_TO_LLM_INTERFACE.md가이드라인 적용)
    """
    url = f"{settings.LLM_API_BASE_URL}/chat/completions"
    headers = {"Content-Type": "application/json"}

    # --- 🔴 [수정] User Prompt 생성 로직 ---
    # 1. OCR 텍스트
    full_text = ocr_data.get("full_text", "No text detected.")

    # 2. 레이아웃 정보 (all_boxes)
    # 너무 길 수 있으므로, 20개까지만 힌트로 제공합니다.
    layout = ocr_data.get("layout", {})
    all_boxes = layout.get("all_boxes", [])
    boxes_hint = json.dumps(all_boxes[:20])  # 처음 20개 박스만

    # 3. (선택적) 규칙 기반 1차 추출 결과
    heuristic_hint = ""
    if heuristic_data:
        heuristic_hint = f"""
--- HEURISTIC PRE-EXTRACTION (High Accuracy) ---
{json.dumps(heuristic_data)}
--- END HEURISTIC DATA ---
"""

    # 4. 최종 User Prompt 조합
    user_prompt = f"""
--- OCR FULL TEXT ---
{full_text}
--- END OCR FULL TEXT ---

--- LAYOUT HINT (first 20 boxes 'all_boxes') ---
[bbox format is [left, top, right, bottom]]
{boxes_hint}
--- END LAYOUT HINT ---

{heuristic_hint}

Please analyze the full text and layout hints to extract the data strictly following the JSON schema.
If heuristic data is provided, prioritize its values unless they clearly contradict the OCR text.
"""
    # --- [수정 완료] ---

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


# --- 🔴 [!!! 수정 !!!] 태스크 정의 (입력값 변경) ---

# 🔴 [수정] (text: str) -> (pipeline_input: Dict[str, Any])
def extract_invoice_data(pipeline_input: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/extract_invoice.txt")
    schema = json.loads(load_asset("schemas/invoice_v1.json"))
    # 🔴 [수정] 입력값(dict)을 그대로 전달
    return call_llm(
        system_prompt,
        ocr_data=pipeline_input.get("ocr", {}),
        schema=schema,
        heuristic_data=pipeline_input.get("heuristic")
    )


# 🔴 [수정]
def extract_receipt_data(pipeline_input: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/extract_receipt.txt")
    schema = json.loads(load_asset("schemas/receipt_v1.json"))
    return call_llm(
        system_prompt,
        ocr_data=pipeline_input.get("ocr", {}),
        schema=schema,
        heuristic_data=pipeline_input.get("heuristic")
    )


# 🔴 [수정]
def extract_contract_data(pipeline_input: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/extract_contract.txt")
    schema = json.loads(load_asset("schemas/contract_v1.json"))
    return call_llm(
        system_prompt,
        ocr_data=pipeline_input.get("ocr", {}),
        schema=schema,
        heuristic_data=pipeline_input.get("heuristic")
    )


# 🔴 [수정]
def extract_report_data(pipeline_input: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/extract_report.txt")
    schema = json.loads(load_asset("schemas/report_v1.json"))
    return call_llm(
        system_prompt,
        ocr_data=pipeline_input.get("ocr", {}),
        schema=schema,
        heuristic_data=pipeline_input.get("heuristic")
    )


# 🔴 [수정]
def extract_resume_data(pipeline_input: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/extract_resume.txt")
    schema = json.loads(load_asset("schemas/resume_v1.json"))
    return call_llm(
        system_prompt,
        ocr_data=pipeline_input.get("ocr", {}),
        schema=schema,
        heuristic_data=pipeline_input.get("heuristic")
    )


# 🔴 [!!! 추가 !!!] java_tls의 smart_extractor.py를 대체할 Passport 태스크
def extract_passport_data(pipeline_input: Dict[str, Any]) -> Dict[str, Any]:
    # 여권은 프롬프트가 매우 중요 (MRZ, 레이아웃 힌트)
    system_prompt = load_asset("prompts/extract_passport.txt")  # (이 프롬프트 파일은 새로 만드셔야 합니다!)
    schema = json.loads(load_asset("schemas/passport_v1.json"))  # (이 스키마 파일은 새로 만드셔야 합니다!)
    return call_llm(
        system_prompt,
        ocr_data=pipeline_input.get("ocr", {}),
        schema=schema,
        heuristic_data=pipeline_input.get("heuristic")  # heuristic_data에 MRZ 파싱 결과가 들어옴
    )


# (PII, Summarization은 단순 text만 필요하므로 수정 방식이 다름)
def perform_pii_masking(pipeline_input: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = load_asset("prompts/pii.txt")
    schema = {"type": "object", "properties": {"pii_detected": {"type": "array", "items": {"type": "object"}}}}

    # 🔴 [수정] OCR 데이터에서 full_text만 뽑아서 별도 user_prompt 생성
    ocr_data = pipeline_input.get("ocr", {})
    full_text = ocr_data.get("full_text", "No text detected.")

    # 🔴 [수정] text만 쓰는 태스크를 위해 call_llm을 한 번 더 래핑
    return _call_llm_with_text(system_prompt, full_text, schema)


def perform_summarization(pipeline_input: Dict[str, Any]) -> str:
    system_prompt = load_asset("prompts/summarize.txt")
    schema = {"type": "object", "properties": {"summary": {"type": "string"}}}

    ocr_data = pipeline_input.get("ocr", {})
    full_text = ocr_data.get("full_text", "No text detected.")

    result = _call_llm_with_text(system_prompt, full_text, schema)
    return result.get("summary", "Summary generation failed.")


def _call_llm_with_text(system_prompt: str, text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    단순 텍스트 입력을 사용하는 (Summarize, PII 등) 태스크를 위한 래퍼.
    call_llm의 ocr_data 시그니처를 맞추기 위해 text를 dict로 감쌉니다.
    """
    ocr_data_mock = {
        "full_text": text,
        "layout": {"all_boxes": []}  # 레이아웃 힌트 없음
    }
    return call_llm(system_prompt, ocr_data=ocr_data_mock, schema=schema)


# --- 🔴 [!!! 수정 !!!] 태스크 매핑 (입력 타입 통일) ---
EXTRACTION_TASKS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "invoice": extract_invoice_data,
    "receipt": extract_receipt_data,
    "contract": extract_contract_data,
    "report": extract_report_data,
    "resume": extract_resume_data,
    "passport": extract_passport_data,  # 🔴 [추가]
}


def get_llm_extraction_task(doc_type: str) -> Optional[Callable[[Dict[str, Any]], Dict[str, Any]]]:
    return EXTRACTION_TASKS.get(doc_type)