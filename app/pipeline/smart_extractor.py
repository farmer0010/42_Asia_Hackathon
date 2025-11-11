# [신규 파일: app/pipeline/smart_extractor.py]
# (java_tls의 src/llm/extractors/smart_extractor.py에서
# 순수 파이썬 규칙 기반 로직만 추출)

import re
import datetime as dt
from typing import Any, Dict, List, Optional

# --- 유틸리티 함수 ---

MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "SEPT": 9, "OCT": 10, "NOV": 11, "DEC": 12
}


def _safe_get(d: Dict, *keys, default=None):
    """
    (java_tls원본 함수)
    """
    cur = d or {}
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def as_text_list_from_boxes(pred: Dict[str, Any]) -> List[str]:
    """
    (java_tls원본 함수 수정: 함수명 변경)
    OCR 결과 JSON의 'all_boxes'에서 텍스트 목록을 추출합니다.
    """
    boxes = _safe_get(pred, "layout", "all_boxes", default=[]) or []
    out = []
    for b in boxes:
        t = (b.get("text") or "").strip()
        if t:
            out.append(t)
    return out


def find_likely_mrz_lines(pred: Dict[str, Any]) -> List[str]:
    """
    (java_tls원본 함수 수정: 함수명/입력값 변경)
    OCR 결과 JSON에서 MRZ 후보 라인을 탐색합니다.
    """
    candidates: List[str] = []

    # 1) full_text_ocr에서 추출
    ft = (_safe_get(pred, "full_text", default="") or "")  # 🔴 키 이름 수정
    if ft:
        # line1 후보: 'P<'로 시작하는 20~60자 구간
        for m in re.finditer(r"P<[A-Z0-9<]{15,60}", ft.upper()):
            seg = m.group(0).replace(" ", "")
            if len(seg) >= 20:
                candidates.append(seg)

        # line2 후보: '<'가 많은 25~60자 구간
        for m in re.finditer(r"[A-Z0-9<]{25,60}", ft.upper()):
            seg = m.group(0).replace(" ", "")
            if seg.count("<") >= 3:
                candidates.append(seg)

    # 2) all_boxes에서 추출
    for t in as_text_list_from_boxes(pred):
        s = (t or "").upper().replace(" ", "")
        if s.startswith("P<") and len(s) >= 20:
            candidates.append(s)
        elif len(s) >= 25 and s.count("<") >= 3:
            candidates.append(s)

    # 정제: 중복 제거 + 점수화
    uniq: List[str] = []
    for x in candidates:
        if x not in uniq:
            uniq.append(x)

    def _score(s: str) -> float:
        lt_ratio = s.count("<") / max(1, len(s))
        p_bonus = 0.2 if s.startswith("P<") else 0.0
        length_bonus = min(len(s), 60) / 100.0
        return lt_ratio + p_bonus + length_bonus

    uniq.sort(key=_score, reverse=True)

    return uniq[:4]


def _nationality_long_from_code(code: Optional[str]) -> Optional[str]:
    """
    (java_tls원본 함수)
    """
    if not code:
        return None
    code = code.upper()
    MAP = {
        "GBR": "United Kingdom",
        "USA": "United States",
        "CAN": "Canada",
        "FRA": "France",
        "DEU": "Germany",
        "ESP": "Spain",
        "ITA": "Italy",
        "AUS": "Australia",
        "NZL": "New Zealand",
        "KOR": "Korea, Republic of",
        "JPN": "Japan",
        "THA": "Thailand",
    }
    return MAP.get(code)


def parse_mrz_data(passport_lines: List[str]) -> Dict[str, Optional[str]]:
    """
    (java_tls원본 함수 수정: 함수명 변경)
    MRZ 두 줄에서 핵심 필드 파싱.
    """
    mrz1_candidates = [s for s in (passport_lines or []) if s.upper().startswith("P<")]
    other_candidates = [s for s in (passport_lines or []) if not s.upper().startswith("P<")]

    mrz1 = mrz1_candidates[0] if mrz1_candidates else (passport_lines[0] if passport_lines else None)
    mrz2 = None
    if other_candidates:
        mrz2 = sorted(other_candidates, key=lambda s: s.count("<") / max(1, len(s)), reverse=True)[0]
    elif passport_lines and len(passport_lines) >= 2:
        mrz2 = passport_lines[1]

    out = {
        "mrz_line1": mrz1,
        "mrz_line2": mrz2,
        "passport_number": None,
        "nationality_code": None,
        "surname": None,
        "given_names": None,
        "sex": None,
        "date_of_birth": None,
        "date_of_issue": None,
        "date_of_expiry": None,
        "nationality_long": None,
    }

    if mrz1 and mrz1.upper().startswith("P<"):
        body = mrz1[2:]
        if len(body) >= 4:
            issuing_and_name = body
            name_part = issuing_and_name[3:]
        else:
            name_part = body
        parts = (name_part or "").split("<<", 1)
        if len(parts) == 2:
            sur = parts[0].replace("<", "").strip() or None
            giv = parts[1].replace("<", " ").strip() or None
            out["surname"] = sur
            out["given_names"] = ' '.join(giv.split()) if giv else None

    if mrz2:
        s = re.sub(r"[^A-Z0-9<]", "", mrz2.upper())
        L = len(s)
        if L >= 9:
            out["passport_number"] = s[0:9].replace("<", "") or None
        if L >= 13:
            out["nationality_code"] = s[10:13].replace("<", "") or None

        def _yyymmdd_to_iso(val: str) -> Optional[str]:
            if not re.fullmatch(r"\d{6}", val or ""):
                return None
            yy = int(val[0:2]);
            mm = int(val[2:4]);
            dd = int(val[4:6])
            century = 1900 if yy >= 50 else 2000
            try:
                return dt.date(century + yy, mm, dd).isoformat()
            except Exception:
                return None

        if L >= 19:
            out["date_of_birth"] = _yyymmdd_to_iso(s[13:19])
        if L >= 21:
            sex_char = s[20:21]
            out["sex"] = sex_char if sex_char in ("M", "F", "X") else None
        if L >= 27:
            out["date_of_expiry"] = _yyymmdd_to_iso(s[21:27])

    if out.get("nationality_code"):
        out["nationality_long"] = _nationality_long_from_code(out["nationality_code"])

    return out


def parse_date_human(text: str) -> Optional[str]:
    """
    (java_tls원본 함수)
    '12 MAY 2002', 'November 03, 2025' -> 'YYYY-MM-DD'
    """
    T = (text or "").upper().replace(",", " ")

    m = re.search(r"\b(\d{1,2})\s+([A-Z]{3,9})\s+(\d{4})\b", T)
    if not m:
        m2 = re.search(r"\b([A-Z]{3,9})\s+(\d{1,2})\s+(\d{4})\b", T)
        if m2:
            d = int(m2.group(2));
            mon_key = m2.group(1)[:3];
            y = int(m2.group(3))
        else:
            m3 = re.search(r"\b([A-Z]{3,9})\s+(\d{1,2})\s*,\s*(\d{4})\b", T)
            if not m3:
                return None
            d = int(m3.group(2));
            mon_key = m3.group(1)[:3];
            y = int(m3.group(3))
    else:
        d = int(m.group(1));
        mon_key = m.group(2)[:3];
        y = int(m.group(3))

    mon = MONTHS.get(mon_key)
    if not mon:
        return None
    try:
        return dt.date(y, mon, d).isoformat()
    except Exception:
        return None


def find_value_after_key(all_texts: List[str], key_regex: str) -> Optional[str]:
    """
    (java_tls원본 함수 수정: 함수명 변경)
    'Passport No', 'Date of Issue' 같은 키 다음에 나오는 값을 추정.
    """
    pat = re.compile(key_regex, re.I)
    for i, t in enumerate(all_texts):
        if pat.search(t):
            tail = t[pat.search(t).end():].strip()
            if tail:
                return tail
            for j in (i + 1, i + 2):
                if j < len(all_texts):
                    if all_texts[j].strip():
                        return all_texts[j].strip()
    return None