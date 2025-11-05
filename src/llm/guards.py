import json
import re
from typing import Any, Dict, Tuple, Optional

try:
    import jsonschema
except Exception as e:
    raise RuntimeError("jsonschema가 필요합니다. `pip install jsonschema`") from e


def _validate_json(obj: Any, schema: Dict) -> Tuple[bool, Optional[str]]:
    try:
        jsonschema.validate(obj, schema)
        return True, None
    except Exception as e:
        return False, str(e)


def _first_json_object(text: str) -> Optional[Dict]:
    """응답에서 가장 그럴듯한 JSON object를 느슨하게 추출."""
    if not text:
        return None
    # ```json ... ``` 블록 우선
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        chunk = m.group(1)
        try:
            return json.loads(chunk)
        except Exception:
            pass
    # 일반 object
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        chunk = m.group(0)
        # 흔한 꼬리문자 제거 시도
        chunk = re.sub(r",\s*}", "}", chunk)
        chunk = re.sub(r",\s*\]", "]", chunk)
        try:
            return json.loads(chunk)
        except Exception:
            return None
    return None


def _fix_prompt(bad_json_text: str, schema: Dict, err: str) -> str:
    return (
        "You must return ONLY valid JSON that matches this JSON Schema.\n"
        "Do not include comments, markdown, or extra text.\n"
        f"SCHEMA:\n{json.dumps(schema, ensure_ascii=False)}\n\n"
        "Previous output was invalid.\n"
        f"ERROR:\n{err}\n\n"
        "Fix it and return ONLY the corrected JSON now:\n"
        f"{bad_json_text}\n"
    )


async def guarded_json_best_effort(
    llm_like,              # generate(prompt, max_tokens, temperature) 메서드를 가진 객체
    base_prompt: str,
    schema: Dict,
    retries: int = 2,
    max_tokens: int = 800,
    temperature: float = 0.0,
) -> Dict:
    """
    1) 1차 시도
    2) 실패 시: '스키마 위반 오류'를 첨부해 자동 교정 프롬프트로 최대 retries회 재시도
    3) 그래도 실패면: 응답에서 첫 JSON을 느슨 추출 → 스키마 키에 맞춰 보정(best-effort)

    항상 dict 반환(최악의 경우에도 스키마의 required 키를 만들어 null/기본값 채움)
    """
    # 1차
    out = await llm_like.generate(base_prompt, max_tokens=max_tokens, temperature=temperature)
    cand = None
    try:
        cand = json.loads(out)
    except Exception:
        cand = _first_json_object(out)

    ok = False
    err = "no json"
    if cand is not None:
        ok, err = _validate_json(cand, schema)
        if ok:
            return cand

    # 재시도
    bad_text = out
    for _ in range(max(0, retries)):
        fix = _fix_prompt(bad_text, schema, err or "")
        out2 = await llm_like.generate(fix, max_tokens=max_tokens, temperature=temperature)
        cand2 = None
        try:
            cand2 = json.loads(out2)
        except Exception:
            cand2 = _first_json_object(out2)

        if cand2 is not None:
            ok2, err2 = _validate_json(cand2, schema)
            if ok2:
                return cand2
            bad_text, err = out2, err2
        else:
            bad_text = out2
            err = "no json"

    # 베스트-에포트: 마지막 응답에서 필드 salvage
    salvage = _first_json_object(bad_text) or {}
    return _coerce_to_schema(salvage, schema)


def _coerce_to_schema(data: Dict, schema: Dict) -> Dict:
    """
    스키마의 required + properties 기준으로 빠진 키를 채우고,
    타입이 다르면 안전한 기본값으로 덮어쓰기.
    """
    result: Dict[str, Any] = {}
    props: Dict[str, Any] = schema.get("properties", {})
    required = schema.get("required", [])

    def _default_for(prop_schema: Dict) -> Any:
        t = prop_schema.get("type")
        if isinstance(t, list):
            # ["string","null"] 같은 경우 string 기본값을 null로
            if "null" in t:
                # 가능한 경우들에서 null 허용이면 null
                return None
            t = [x for x in t if x != "null"][0] if t else "string"
        if t == "number" or t == "integer":
            return 0
        if t == "array":
            return []
        if t == "object":
            return {}
        # string or 기타
        return None if "null" in prop_schema.get("type", []) else ""

    for k in required:
        ps = props.get(k, {})
        v = data.get(k) if isinstance(data, dict) else None
        # 타입 검증 실패 시 기본값
        if not _match_type(v, ps):
            v = _default_for(ps)
        result[k] = v

    # properties에 있으나 required가 아닌 것도 보조로 채움
    for k, ps in props.items():
        if k in result:
            continue
        v = None
        if isinstance(data, dict):
            v = data.get(k)
        if not _match_type(v, ps):
            v = _default_for(ps)
        result[k] = v

    return result


def _match_type(value: Any, prop_schema: Dict) -> bool:
    allowed = prop_schema.get("type")
    if allowed is None:
        return True
    if isinstance(allowed, list):
        # null 허용
        if value is None and "null" in allowed:
            return True
        # 리스트에서 첫 타입만 검사(간단화)
        allowed = [t for t in allowed if t != "null"]
        if not allowed:
            return True
        allowed = allowed[0]

    if allowed == "number":
        return isinstance(value, (int, float))
    if allowed == "integer":
        return isinstance(value, int)
    if allowed == "string":
        return isinstance(value, str) or (value is None and "null" in prop_schema.get("type", []))
    if allowed == "array":
        return isinstance(value, list)
    if allowed == "object":
        return isinstance(value, dict)
    return True