import re
import json
import time
import datetime as dt
from typing import Any, Dict, List, Optional

import requests


MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "SEPT": 9, "OCT": 10, "NOV": 11, "DEC": 12
}


def _safe_get(d: Dict, *keys, default=None):
    cur = d or {}
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def _as_text_list_from_boxes(pred: Dict[str, Any]) -> List[str]:
    boxes = _safe_get(pred, "layout", "all_boxes", default=[]) or []
    out = []
    for b in boxes:
        t = (b.get("text") or "").strip()
        if t:
            out.append(t)
    return out


def _find_likely_mrz_lines(pred: Dict[str, Any]) -> List[str]:
    """줄바꿈 유무에 상관없이 MRZ로 보이는 라인을 찾는다."""
    texts = []

    # 1) full_text_ocr 전체에서
    ft = (_safe_get(pred, "full_text_ocr", default="") or "").strip()
    if ft:
        # 이미 flatten 가능성 있으므로 '<<'나 '<'가 많이 들어간 덩어리를 분리해서 후보로
        chunks = re.split(r"\s+", ft)
        merged = []
        cur = []
        # 긴 '<' 토큰을 만나면 묶는다.
        for tok in chunks:
            if "<" in tok or tok.startswith("P<"):
                cur.append(tok)
            else:
                if cur:
                    merged.append("".join(cur))
                    cur = []
        if cur:
            merged.append("".join(cur))
        # 길이 25 이상 & '<' 3개 이상 정도만 후보로
        for m in merged:
            if len(m) >= 25 and m.count("<") >= 3:
                texts.append(m)

    # 2) all_boxes 에서도 라인 후보 수집
    for t in _as_text_list_from_boxes(pred):
        s = t.replace(" ", "")
        if len(s) >= 25 and s.count("<") >= 3:
            texts.append(s)

    # dedup & 길이순 정렬
    uniq = []
    for x in texts:
        if x not in uniq:
            uniq.append(x)
    uniq.sort(key=len, reverse=True)
    return uniq[:4]


def _parse_mrz(passport_lines: List[str]) -> Dict[str, Optional[str]]:
    """
    MRZ 두 줄에서 핵심 필드 파싱.
    - 라인1 예: P<GBRYORK<<MAURICE<<<<<<<<<<<<<<<<<<<<<<<<<<
    - 라인2 예: 8579523652GBR7407295M2010186<<<<<<<<<<<<<<04
    """
    mrz1 = None
    mrz2 = None
    # 가장 긴 2개를 우선 후보로 본다
    if passport_lines:
        if len(passport_lines) >= 2:
            mrz1, mrz2 = passport_lines[0], passport_lines[1]
        else:
            mrz1 = passport_lines[0]

    out = {
        "mrz_line1": mrz1,
        "mrz_line2": mrz2,
        "passport_number": None,
        "nationality_code": None,
        "surname": None,
        "given_names": None,
        "sex": None,
        "date_of_birth": None,
        "date_of_issue": None,      # 🔧 추가
        "date_of_expiry": None,
    }

    if mrz1 and mrz1.startswith("P<"):
        # 형식: P<ISSUINGCOUNTRY SURNAME<<GIVEN<<...
        # 'P<' 다음 3글자는 보통 발급국 코드(issuing country)지만, 국적코드는 line2에서 더 신뢰
        body = mrz1[2:]
        # SURNAME<<GIVEN...
        # 첫 '<<' 앞은 성, 그 뒤는 이름 여러 단어를 '<'로 분리
        parts = body.split("<<", 1)
        if len(parts) == 2:
            sur = parts[0].replace("<", "").strip() or None
            giv = parts[1].replace("<", " ").strip() or None
            out["surname"] = sur
            out["given_names"] = giv

    if mrz2 and len(mrz2) >= 28:
        # ICAO 포맷 기준(단순화):
        # pos0-8: passport number (may include < padding), pos9: check digit
        # pos10-12: nationality
        # pos13-18: birth (YYMMDD), pos19: check
        # pos20: sex
        # pos21-26: expiry (YYMMDD), pos27: check
        pnum_raw = mrz2[0:9]
        out["passport_number"] = pnum_raw.replace("<", "") or None

        out["nationality_code"] = mrz2[10:13] or None

        def _yyymmdd_to_iso(s: str) -> Optional[str]:
            if not re.fullmatch(r"\d{6}", s or ""):
                return None
            yy = int(s[0:2])
            mm = int(s[2:4])
            dd = int(s[4:6])
            # pivot: 50 이상은 1900s, 미만은 2000s
            century = 1900 if yy >= 50 else 2000
            try:
                return dt.date(century + yy, mm, dd).isoformat()
            except Exception:
                return None

        out["date_of_birth"] = _yyymmdd_to_iso(mrz2[13:19])
        out["sex"] = {"M": "M", "F": "F"}.get(mrz2[20].upper(), None)
        out["date_of_expiry"] = _yyymmdd_to_iso(mrz2[21:27])

    return out


def _parse_date_human(text: str) -> Optional[str]:
    """
    '12 MAY 2002', '15 APR 2012' 같은 포맷 → 'YYYY-MM-DD'
    """
    m = re.search(r"\b(\d{1,2})\s+([A-Z]{3,5})\s+(\d{4})\b", text.upper())
    if not m:
        return None
    d = int(m.group(1))
    mon = MONTHS.get(m.group(2).upper())
    y = int(m.group(3))
    if not mon:
        return None
    try:
        return dt.date(y, mon, d).isoformat()
    except Exception:
        return None


def _find_after_key(all_texts: List[str], key_regex: str) -> Optional[str]:
    """
    'Passport No', 'Date of Issue' 같은 키 다음에 나오는 값을 추정.
    """
    pat = re.compile(key_regex, re.I)
    for i, t in enumerate(all_texts):
        if pat.search(t):
            # 같은 줄에 값이 붙어있을 수도 있고, 다음/다다음 줄일 수도 있음
            # 같은 줄에서 키 다음 숫자/토큰을 먼저 시도
            tail = t[pat.search(t).end():].strip()
            if tail:
                # 숫자/문자 조합 그대로 반환
                return tail
            # 아니면 다음 줄에서 찾기
            for j in (i + 1, i + 2):
                if j < len(all_texts):
                    if all_texts[j].strip():
                        return all_texts[j].strip()
    return None


class SmartExtractor:
    def __init__(self, ollama_url: str = "http://localhost:11434",
                 model: str = "qwen2.5:7b",
                 retries: int = 2,
                 timeout: int = 30):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.retries = max(0, retries)
        self.timeout = timeout

    # ========== LLM backup ==========
    def llm_fill(self, prediction: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """
        Ollama가 안 떠있거나, 모델 에러가 나도 절대 예외로 죽지 않고 {}를 돌려준다.
        """
        url = f"{self.ollama_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        for _ in range(self.retries + 1):
            try:
                r = requests.post(url, json=payload, timeout=self.timeout)
                if r.status_code != 200:
                    time.sleep(0.8)
                    continue
                data = r.json()
                txt = (data.get("response") or "").strip()
                # JSON만 뽑기
                m = re.search(r"\{.*\}", txt, re.S)
                if not m:
                    return {}
                parsed = json.loads(m.group(0))
                return parsed if isinstance(parsed, dict) else {}
            except Exception:
                time.sleep(0.8)
        return {}

    # ========== Router ==========
    def extract(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        doc_type = _safe_get(prediction, "classification", "doc_type", default="unknown")
        if doc_type == "passport":
            return self._extract_passport(prediction)
        elif doc_type == "invoice":
            return self._extract_invoice(prediction)
        elif doc_type == "purchase_order":
            return self._extract_purchase_order(prediction)
        elif doc_type == "resume":
            return self._extract_resume(prediction)
        elif doc_type == "custom_form":
            return self._extract_custom_form(prediction)
        return {}

    # ========== Passport ==========
    def _extract_passport(self, pred: Dict[str, Any]) -> Dict[str, Any]:
        text = (_safe_get(pred, "full_text_ocr", default="") or "").strip()
        boxes_texts = _as_text_list_from_boxes(pred)

        # 1) MRZ 우선
        mrz_candidates = _find_likely_mrz_lines(pred)
        mrz = _parse_mrz(mrz_candidates)

        # 2) 키워드 보조 추출
        # 여권번호
        if not mrz["passport_number"]:
            # 'Passport No' 이후 숫자
            v = _find_after_key(boxes_texts + [text], r"passport\s*no\.?")
            if v:
                m = re.search(r"[A-Z0-9]{5,}", v.replace(" ", ""))
                if m:
                    mrz["passport_number"] = m.group(0)

        # 성별
        if not mrz["sex"]:
            m = re.search(r"\bSex\b[:/ ]*\b([MF])\b", text, re.I)
            if m:
                mrz["sex"] = m.group(1).upper()

        # 발급일/만료일
        if not mrz.get("date_of_issue"):
            v = _find_after_key(boxes_texts + [text], r"(date\s*of\s*issue|issued)")
            if v:
                iso = _parse_date_human(v.upper())
                if iso:
                    mrz["date_of_issue"] = iso
        if not mrz["date_of_expiry"]:
            v = _find_after_key(boxes_texts + [text], r"(date\s*of\s*expiry|expiry\s*date|expires)")
            if v:
                iso = _parse_date_human(v.upper())
                if iso:
                    mrz["date_of_expiry"] = iso

        # 국적 풀네임(가능하면)
        if not mrz.get("nationality_long"):
            # "Nationality ... UNITED STATES ..." 라인에서 가져오기
            nat_line = None
            for t in boxes_texts:
                if re.search(r"\bnationality\b", t, re.I):
                    nat_line = t
                    break
            if not nat_line:
                # 본문에서도 탐색
                m2 = re.search(r"\bnationality\b[^A-Za-z]+([A-Z][A-ZA-Za-z ]{2,})", text, re.I)
                if m2:
                    nat_line = m2.group(1)
            if nat_line:
                # 대문자/단어만 정리
                cand = re.sub(r"[^A-Za-z ]+", " ", nat_line).strip()
                # 너무 길면 끊기
                if len(cand) > 64:
                    cand = cand[:64].rstrip()
                mrz["nationality_long"] = cand or None

        # 최종 스키마 키에 맞춰 반환
        return {
            "passport_number": mrz.get("passport_number"),
            "surname": mrz.get("surname"),
            "given_names": mrz.get("given_names"),
            "nationality_code": mrz.get("nationality_code"),
            "nationality_long": mrz.get("nationality_long"),
            "sex": mrz.get("sex"),
            "date_of_birth": mrz.get("date_of_birth"),
            "date_of_issue": mrz.get("date_of_issue"),
            "date_of_expiry": mrz.get("date_of_expiry"),
            "mrz_line1": mrz.get("mrz_line1"),
            "mrz_line2": mrz.get("mrz_line2"),
        }

    # ========== 이하 타입들은 지금 스키마 필수칸 채우는 최소 구현 (필요시 확장) ==========
    def _extract_invoice(self, pred: Dict[str, Any]) -> Dict[str, Any]:
        # 하드 룰 없이 LLM 보강에 맡기는 경우 최소 스캐폴드만(빈 dict) 반환
        return {}

    def _extract_purchase_order(self, pred: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def _extract_resume(self, pred: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def _extract_custom_form(self, pred: Dict[str, Any]) -> Dict[str, Any]:
        return {}