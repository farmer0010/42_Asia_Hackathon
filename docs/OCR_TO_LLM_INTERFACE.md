# OCR/분류 → LLM 인터페이스 문서

> **작성일**: 2025-11-10  
> **작성자**: OCR/분류 팀  
> **대상**: LLM 팀

---

## 📋 목차

1. [데이터 구조 (JSON Format)](#1-데이터-구조-json-format)
2. [신규 기능: all_boxes](#2-신규-기능-all_boxes)
3. [문서 타입별 특징 및 주의사항](#3-문서-타입별-특징-및-주의사항)
   - [Passport](#31-passport)
   - [Resume](#32-resume)
   - [Invoice](#33-invoice)
   - [Purchase Order](#34-purchase-order)
   - [Custom Form](#35-custom-form)
4. [활용 가이드](#4-활용-가이드)
5. [문제 해결 (Troubleshooting)](#5-문제-해결-troubleshooting)

---

## 1. 데이터 구조 (JSON Format)

OCR/분류 파이프라인에서 LLM 팀에 전달하는 JSON 구조입니다.

### 전체 구조

```json
{
  "filename": "invoice_001.pdf",
  "full_text_ocr": "전체 텍스트 (순서대로)",
  "ocr_confidence": 0.94,
  "layout": {
    "title": "Invoice",
    "sections": [...],
    "all_boxes": [...],
    "features": {...}
  },
  "classification": {
    "doc_type": "invoice",
    "confidence": 0.95
  },
  "detected_language": "en",
  "processing_time": 2.5
}
```

### 필드 설명

| 필드                        | 타입   | 설명                               |
| --------------------------- | ------ | ---------------------------------- |
| `filename`                  | string | 원본 파일명                        |
| `full_text_ocr`             | string | OCR 추출 텍스트 (줄바꿈 포함)      |
| `ocr_confidence`            | float  | OCR 평균 신뢰도 (0~1)              |
| `layout.title`              | string | 문서 제목 (상단 큰 글씨)           |
| `layout.sections`           | array  | 키-값 쌍 (필터링됨)                |
| `layout.all_boxes`          | array  | **[신규]** 모든 텍스트+위치        |
| `layout.features`           | object | 문서 특징 (테이블 유무 등)         |
| `classification.doc_type`   | string | 문서 타입 (5가지)                  |
| `classification.confidence` | float  | 분류 신뢰도 (0~1)                  |
| `detected_language`         | string | 감지된 언어 (en/thai/korean/japan) |

---

## 2. 신규 기능: all_boxes

### 개요

기존에는 `sections`에서 키-값 쌍만 최대 12개 제공했습니다.  
**이제 `all_boxes`로 모든 텍스트와 정확한 위치 정보를 제공합니다!**

### all_boxes 구조

```json
{
  "all_boxes": [
    {
      "text": "Invoice Number:",
      "bbox": [391.0, 75.0, 500.0, 90.0],
      "confidence": 0.98,
      "width": 109.0,
      "height": 15.0
    },
    {
      "text": "INV-2025-0001",
      "bbox": [510.0, 75.0, 620.0, 90.0],
      "confidence": 0.99,
      "width": 110.0,
      "height": 15.0
    }
  ]
}
```

### bbox 좌표 시스템

```
bbox: [left, top, right, bottom]
       [x1,   y1,  x2,    y2   ]

좌표계:
  (0,0) ────────────→ X
    │
    │    [x1, y1]
    │        ┌─────────┐
    │        │  텍스트  │
    │        └─────────┘
    │              [x2, y2]
    ↓
    Y
```

### 활용 방법

#### 1) 키-값 매칭 (위치 기반)

```python
# "Invoice Number:" 바로 오른쪽 값 찾기
for i, box in enumerate(all_boxes):
    if "invoice number" in box["text"].lower():
        key_box = box
        # 같은 Y좌표 (±5) + 오른쪽(X가 더 큼)인 박스 찾기
        for next_box in all_boxes[i+1:]:
            if abs(next_box["bbox"][1] - key_box["bbox"][1]) < 5:
                if next_box["bbox"][0] > key_box["bbox"][2]:
                    value = next_box["text"]
                    break
```

#### 2) 테이블 파싱 (행/열 그룹핑)

```python
# 같은 Y좌표 = 같은 행
rows = {}
for box in all_boxes:
    y = round(box["bbox"][1] / 10) * 10  # 10px 단위로 반올림
    if y not in rows:
        rows[y] = []
    rows[y].append(box)

# 각 행을 X좌표로 정렬 → 열 순서
for y in sorted(rows.keys()):
    row_boxes = sorted(rows[y], key=lambda b: b["bbox"][0])
    # row_boxes = [Description, Quantity, Price, Total]
```

#### 3) 섹션 구분 (Y좌표 기반)

```python
# 상단 (Y < 200): 헤더 정보
# 중단 (200 < Y < 600): 본문/테이블
# 하단 (Y > 600): 합계/서명

header = [b for b in all_boxes if b["bbox"][1] < 200]
body = [b for b in all_boxes if 200 <= b["bbox"][1] < 600]
footer = [b for b in all_boxes if b["bbox"][1] >= 600]
```

### 장점

✅ **정확한 관계 파악**: 키 옆에 있는 값 자동 매칭  
✅ **테이블 구조 복원**: 행/열 순서 정확하게 파악  
✅ **섹션 분리**: 위치 기반 논리적 그룹핑  
✅ **겹침 처리**: bbox로 겹친 텍스트 구분 가능

---

## 3. 문서 타입별 특징 및 주의사항

### 3.1 Passport

#### 기본 정보

- **doc_type**: `"passport"`
- **정형도**: ⭐⭐⭐⭐⭐ (매우 정형화)
- **난이도**: ⭐ (쉬움)

#### 구조

```json
{
  "passport_number": "PR787836",
  "surname": "JOHNSON",
  "given_names": "BRITTANY",
  "nationality_code": "CAN",
  "nationality_long": "QATAR",
  "sex": "F",
  "date_of_birth": "1988-04-09",
  "date_of_issue": "2010-11-02",
  "date_of_expiry": "2020-10-26",
  "mrz_line1": "P<CANJOHNSON<<BRITTANY<<<<<<<<<<<<<<<<<<<<<<",
  "mrz_line2": "PR787836<7CAN8804097F2010267<<<<<<<<<<<<<<08"
}
```

#### ⚠️ 주의사항

**1. 텍스트 겹침 문제**

```
문제: nationality_long이 길면 date_of_birth를 가려버림
예시:
  "QATAR" bbox: [100, 200, 200, 220]
  "1988-04-09" bbox: [180, 200, 280, 220]  ← 겹침!
```

**해결 방법:**

```python
# 1. MRZ에서 확인 (가장 정확)
# mrz_line2[8:14] = "880409" → 1988-04-09

# 2. bbox로 구분
# 겹친 텍스트 중 오른쪽 것이 date_of_birth
```

**2. MRZ (Machine Readable Zone) 활용**

MRZ는 고정 포맷이므로 파싱 가능:

```
Line 1: P<CCCSSSSSSSSSS<<GGGGGGGGGGGGGGGGGGGGGGGG
        P<국적성(surname)<<이름(given names)

Line 2: PPPPPPPPPNCCCYYMMDDDSYYMMDDDBBBBBBBBBBBCC
        여권번호  국적 생년월일성 만료일  체크섬

위치:
- 여권번호: [0:9]
- 국적: [10:13]
- 생년월일: [13:19] (YYMMDD)
- 성별: [20] (M/F)
- 만료일: [21:27] (YYMMDD)
```

#### 프롬프트 힌트

```
⚠️ IMPORTANT:
- nationality_long may visually overlap with date_of_birth
- Use MRZ (line starting with "P<") for accurate date extraction
- MRZ format: Line2[13:19] = YYMMDD for birth date
- Prefer MRZ data over visual OCR when conflict occurs
```

---

### 3.2 Resume

#### 기본 정보

- **doc_type**: `"resume"`
- **정형도**: ⭐⭐ (비정형)
- **난이도**: ⭐⭐⭐⭐ (어려움)

#### 구조

```json
{
  "template_used": "sidebar | classic | modern",
  "contact_info": {
    "name": "...",
    "email": "...",
    "phone": "...",
    "address": "..."
  },
  "summary": "...",
  "work_experience": [
    {
      "title": "...",
      "company": "...",
      "dates": "2022 - Present",
      "description": ["..."]
    }
  ],
  "education": {...},
  "skills": [...]
}
```

#### ⚠️ 주의사항

**1. 템플릿 3가지**

| 템플릿  | 레이아웃                  | 특징                   |
| ------- | ------------------------- | ---------------------- |
| sidebar | 좌측 사이드바 + 우측 본문 | Y좌표 순서 ≠ 읽기 순서 |
| classic | 단일 컬럼                 | 위→아래 순서           |
| modern  | 2컬럼                     | 좌우 섹션 혼합         |

**2. 섹션 헤더 키워드**

```python
섹션 감지 키워드:
- Contact: "Email", "Phone", "Address"
- Summary: "Summary", "Profile", "About"
- Experience: "Experience", "Work History", "Employment"
- Education: "Education", "Academic"
- Skills: "Skills", "Technical Skills", "Competencies"
```

**3. bbox 활용 전략**

```python
# sidebar 템플릿 감지
sidebar_boxes = [b for b in all_boxes if b["bbox"][0] < 200]  # 좌측
main_boxes = [b for b in all_boxes if b["bbox"][0] >= 200]    # 우측

# 각각 별도로 처리
```

#### 프롬프트 힌트

```
Templates: sidebar / classic / modern
- sidebar: Left column (contact/skills) + Right column (experience/education)
- classic: Single column, top-to-bottom
- modern: Two-column mixed layout

Look for section headers:
- "Work Experience" / "Experience" / "Employment History"
- "Education" / "Academic Background"
- "Skills" / "Technical Skills"

Contact info usually at the top or in sidebar.
Date ranges: "YYYY - Present" or "YYYY - YYYY"
```

---

### 3.3 Invoice

#### 기본 정보

- **doc_type**: `"invoice"`
- **정형도**: ⭐⭐⭐⭐ (준정형)
- **난이도**: ⭐⭐ (중간)

#### 구조

```json
{
  "invoice_id": "INV-2025-0001",
  "issue_date": "2025-11-01",
  "customer_name": "StellarWorks Inc.",
  "customer_address": "...",
  "subtotal": 1434.5,
  "tax_amount": 100.42,
  "total": 1534.91,
  "line_items": [
    {
      "description": "HyperLoop Data Cable (10m)",
      "quantity": 9,
      "unit_price": 75.5,
      "line_total": 679.5
    }
  ]
}
```

#### ⚠️ 주의사항

**1. 테이블 구조**

```
[Description          ] [Quantity] [Unit Price] [Line Total]
[HyperLoop Cable (10m)] [9       ] [$75.50    ] [$679.50   ]
[USB-C Adapter        ] [1       ] [$75.50    ] [$75.50    ]
                                    Subtotal:     $1,434.50
                                    Tax (7%):       $100.42
                                    Total:        $1,534.91
```

**2. bbox 기반 테이블 파싱**

```python
# 테이블 영역 감지
table_boxes = [b for b in all_boxes if "has_table" in features]

# Y좌표로 행 그룹핑
rows = group_by_y(table_boxes, tolerance=5)

# 각 행을 X좌표로 정렬 → 열 순서
for row in rows:
    cells = sorted(row, key=lambda b: b["bbox"][0])
    # cells[0] = Description
    # cells[1] = Quantity
    # cells[2] = Unit Price
    # cells[3] = Line Total
```

**3. 숫자 검증**

```python
# 계산 검증
assert sum(item["line_total"] for item in line_items) ≈ subtotal
assert subtotal + tax_amount ≈ total
```

#### 프롬프트 힌트

```
Table structure:
- Header row: Description | Quantity | Unit Price | Line Total
- Data rows: Item details
- Footer: Subtotal, Tax, Total (usually right-aligned)

Use Y-coordinates to identify table rows.
Use X-coordinates to identify columns.

Validation:
- sum(line_totals) should ≈ subtotal
- subtotal + tax = total
```

---

### 3.4 Purchase Order

#### 기본 정보

- **doc_type**: `"purchase_order"`
- **정형도**: ⭐⭐⭐ (중간)
- **난이도**: ⭐⭐⭐⭐⭐ (가장 어려움!)

#### 구조

```json
{
  "po_number": "PO-2025-0497",
  "po_date": "2025-10-12",
  "delivery_date_str": "January 05, 2026",
  "project_number": "PROJ-2025-59160",
  "project_name": "...",
  "buyer": {
    "name": "...",
    "address": "...",
    "tax_id": "..."
  },
  "vendor": {
    "name": "...",
    "address": "...",
    "tax_id": "..."
  },
  "items": [...],
  "subtotal": 116500.0,
  "vat_amount": 8155.0,
  "grand_total": 124655.0,
  "approver_name": "...",
  "approver_title": "..."
}
```

#### ⚠️ 주의사항 (중요!)

**1. 3가지 형식 변형**

| 형식   | 제목 위치 | PO 정보 위치    | 특징                     |
| ------ | --------- | --------------- | ------------------------ |
| 형식 1 | 좌상단    | 우상단 (텍스트) | 가장 일반적              |
| 형식 2 | 중앙      | 표 형태         | PO/PR/Date가 표로 정리   |
| 형식 3 | 혼합      | 혼합            | 일부는 표, 일부는 텍스트 |

**형식 감지 방법:**

```python
# 제목 위치로 형식 판단
title_box = [b for b in all_boxes if "purchase order" in b["text"].lower()][0]

if title_box["bbox"][0] < 300:  # 좌상단
    format_type = 1
    # PO 정보는 우상단 (X > 400, Y < 200)
elif title_box["bbox"][0] > 300:  # 중앙
    format_type = 2
    # PO 정보는 표 형태 (같은 Y좌표, 작은 bbox들)
```

**2. 레이아웃 구조**

```
┌─────────────────────────────────────┐
│ [제목: Purchase Order]       [PO 정보] │  ← Y < 200
├─────────────────────────────────────┤
│ Buyer:            │ Vendor:         │  ← Y ≈ 250-350
│ (name/address)    │ (name/address)  │
├─────────────────────────────────────┤
│ [Items Table]                       │  ← Y ≈ 400-700
│ Name | Qty | Price | Total          │
├─────────────────────────────────────┤
│               Subtotal: XXX         │  ← Y ≈ 750-850
│               VAT: XXX              │
│               Grand Total: XXX      │
├─────────────────────────────────────┤
│                      [Signature]    │  ← Y > 850
└─────────────────────────────────────┘
```

**3. Buyer vs Vendor 구분**

```python
# 키워드로 구분
buyer_keywords = ["buyer", "purchaser", "bill to"]
vendor_keywords = ["vendor", "supplier", "seller", "ship from"]

# 위치로 구분 (보통 좌우 배치)
left_section = [b for b in all_boxes if b["bbox"][0] < 400]  # Buyer
right_section = [b for b in all_boxes if b["bbox"][0] >= 400]  # Vendor
```

**4. Invoice와 구분 (중요!)**

| 필드   | Purchase Order   | Invoice          |
| ------ | ---------------- | ---------------- |
| 제목   | "Purchase Order" | "Invoice"        |
| 번호   | "PO Number"      | "Invoice Number" |
| 날짜   | "Delivery Date"  | "Due Date"       |
| 상대방 | Buyer/Vendor     | Customer         |
| 서명   | Approver         | 보통 없음        |

#### 프롬프트 힌트

```
⚠️ COMPLEX DOCUMENT - 3 format variations:

Format 1 (most common):
- Title "Purchase Order" at top-left
- PO info (PO No, Date, PR No) at top-right

Format 2:
- Title "Purchase Order" at center
- PO info in table format

Format 3:
- Mixed: some info in table, some as text

Layout structure:
1. Header (Y < 200): Title + PO info
2. Parties (Y ≈ 250-350): Buyer (left) | Vendor (right)
3. Items table (Y ≈ 400-700): Name, Qty, Price, Total
4. Totals (Y ≈ 750-850): Subtotal, VAT, Grand Total
5. Signature (Y > 850): Approver name + title (bottom-right)

Key differences from Invoice:
- Has both "Buyer" AND "Vendor" (Invoice only has "Customer")
- Has "Delivery Date" (Invoice has "Due Date")
- Has signature section (Invoice usually doesn't)
```

---

### 3.5 Custom Form (Customs Declaration)

#### 기본 정보

- **doc_type**: `"custom_form"`
- **정형도**: ⭐⭐⭐⭐ (정형)
- **난이도**: ⭐⭐⭐ (중간)

#### 구조

```json
{
  "formInfo": {
    "documentTitle": "PASSENGER DECLARATION FORM",
    "authority": "The Customs Department, Ministry of Finance...",
    "metadata": "..."
  },
  "passengerInformation": {
    "sectionTitle": "Part 1: Passenger Information",
    "fullName": "Ms. Thanyarat Lertlum",
    "occupation": "Graphic Designer",
    "passportNumber": "AA4028959",
    "arrivingFlightNo": "QR551",
    "dateOfBirth": "18 April 1988",
    "nationality": "Thai",
    "accompanyingFamilyMembers": 0,
    "fromCity": "Paris"
  },
  "declaration": {
    "sectionTitle": "Part 2: Declaration",
    "status": {
      "hasArticlesToDeclare": false,
      "hasExcessCurrency": false,
      "hasNothingToDeclare": true
    },
    "declaredItems": [],
    "signature": "(Ms. Thanyarat Lertlum)",
    "date": "October 16, 2025"
  }
}
```

#### ⚠️ 주의사항

**1. 체크박스 처리 (핵심!)**

OCR 결과:

```
"☑ Nothing to Declare"
"☐ Articles to Declare"
또는
"[X] Nothing to Declare"
"[ ] Articles to Declare"
또는
"✓ Nothing to Declare"
"  Articles to Declare"
```

**체크 감지 패턴:**

```python
checked_patterns = [
    "☑", "[X]", "[x]", "✓", "✔",
    "(checked)", "(selected)", "(yes)"
]

def is_checked(text):
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in checked_patterns)
```

**2. Part 1 / Part 2 구분**

```python
# 섹션 헤더로 구분
part1_start = find_box_with_text("Part 1")
part2_start = find_box_with_text("Part 2")

# Y좌표로 섹션 분리
part1_boxes = [b for b in all_boxes if part1_start["bbox"][1] < b["bbox"][1] < part2_start["bbox"][1]]
part2_boxes = [b for b in all_boxes if b["bbox"][1] >= part2_start["bbox"][1]]
```

**3. 서명 및 날짜**

```
서명: 보통 괄호로 감싸짐 "(Ms. Thanyarat Lertlum)"
날짜: 서명 근처, 오른쪽
위치: 문서 하단 (Y > 800)
```

#### 프롬프트 힌트

```
Two-part structure:
- Part 1: Passenger Information
- Part 2: Declaration

Checkbox detection:
- Look for patterns: ☑, [X], [x], ✓, ✔, (checked)
- Status fields:
  * hasArticlesToDeclare
  * hasExcessCurrency
  * hasNothingToDeclare

Bottom section:
- Signature: usually in parentheses "(Name)"
- Date: near signature, right side
- Both at Y > 800

declaredItems array:
- Empty if "Nothing to Declare" is checked
- Contains items if "Articles to Declare" is checked
```

---

## 4. 활용 가이드

### 4.1 기본 워크플로우

```python
def process_document(prediction):
    # 1. 문서 타입 확인
    doc_type = prediction["classification"]["doc_type"]

    # 2. 품질 확인
    if prediction["ocr_confidence"] < 0.7:
        logger.warning(f"Low OCR confidence: {prediction['ocr_confidence']}")

    # 3. all_boxes 활용
    all_boxes = prediction["layout"]["all_boxes"]

    # 4. 타입별 처리
    if doc_type == "passport":
        return extract_passport(prediction, all_boxes)
    elif doc_type == "invoice":
        return extract_invoice(prediction, all_boxes)
    # ...
```

### 4.2 공통 유틸리티 함수

#### Y좌표 기반 행 그룹핑

```python
def group_by_y(boxes, tolerance=5):
    """같은 Y좌표의 박스들을 그룹핑 (행 감지)"""
    rows = {}
    for box in boxes:
        y = round(box["bbox"][1] / tolerance) * tolerance
        if y not in rows:
            rows[y] = []
        rows[y].append(box)
    return [sorted(row, key=lambda b: b["bbox"][0]) for row in sorted(rows.values())]
```

#### 키-값 매칭

```python
def find_value_for_key(key_text, all_boxes, tolerance=5):
    """키워드 오른쪽의 값 찾기"""
    for i, box in enumerate(all_boxes):
        if key_text.lower() in box["text"].lower():
            key_box = box
            # 같은 행(Y좌표)에서 오른쪽 값 찾기
            for next_box in all_boxes[i+1:]:
                if abs(next_box["bbox"][1] - key_box["bbox"][1]) < tolerance:
                    if next_box["bbox"][0] > key_box["bbox"][2]:
                        return next_box["text"]
    return None
```

#### 영역 필터링

```python
def filter_by_region(boxes, x_min=None, x_max=None, y_min=None, y_max=None):
    """특정 영역의 박스만 필터링"""
    filtered = boxes
    if x_min is not None:
        filtered = [b for b in filtered if b["bbox"][0] >= x_min]
    if x_max is not None:
        filtered = [b for b in filtered if b["bbox"][2] <= x_max]
    if y_min is not None:
        filtered = [b for b in filtered if b["bbox"][1] >= y_min]
    if y_max is not None:
        filtered = [b for b in filtered if b["bbox"][3] <= y_max]
    return filtered
```

### 4.3 품질 확인

```python
def check_quality(prediction):
    """데이터 품질 확인"""
    issues = []

    # OCR 신뢰도
    if prediction["ocr_confidence"] < 0.7:
        issues.append("Low OCR confidence")

    # 분류 신뢰도
    if prediction["classification"]["confidence"] < 0.6:
        issues.append("Low classification confidence")

    # all_boxes 개수
    if len(prediction["layout"]["all_boxes"]) < 10:
        issues.append("Too few text boxes detected")

    return issues
```

---

## 5. 문제 해결 (Troubleshooting)

### 5.1 OCR 품질 문제

**증상**: `ocr_confidence` < 0.7

**원인**:

- 저해상도 이미지
- 워터마크 (예: Passport의 "SPECIMEN")
- 손글씨
- 복잡한 배경

**대응 방법**:

```python
if ocr_confidence < 0.7:
    # 1. 더 관대한 파싱 로직 사용
    # 2. 필수 필드만 추출
    # 3. 신뢰도 낮음을 결과에 표시
    result["quality_warning"] = "Low OCR confidence"
```

### 5.2 분류 오류

**증상**: `classification.doc_type`이 잘못됨

**흔한 케이스**:

- Invoice ↔ Purchase Order 혼동
  - 해결: 키워드 확인 ("Customer" vs "Buyer/Vendor")

**대응 방법**:

```python
# 키워드 기반 검증
full_text = prediction["full_text_ocr"].lower()

if doc_type == "invoice" and "buyer" in full_text and "vendor" in full_text:
    logger.warning("Possible misclassification: might be Purchase Order")
    # 수동 재분류 또는 LLM에게 판단 요청
```

### 5.3 테이블 파싱 실패

**증상**: line_items가 잘못 추출됨

**원인**:

- 테이블 행이 Y좌표로 제대로 그룹핑 안됨
- 열 구분이 애매함

**대응 방법**:

```python
# tolerance 조정
rows = group_by_y(table_boxes, tolerance=10)  # 5 → 10으로 증가

# 헤더 행으로 열 위치 파악
header_row = rows[0]
column_positions = [box["bbox"][0] for box in header_row]

# 각 데이터 행에서 열 위치 기반으로 값 매칭
for data_row in rows[1:]:
    for i, col_x in enumerate(column_positions):
        cell = find_closest_box(data_row, col_x)
```

### 5.4 체크박스 감지 실패 (Custom Form)

**증상**: hasNothingToDeclare 등이 항상 false

**원인**:

- OCR이 체크 기호를 인식 못함
- 체크 패턴이 예상과 다름

**대응 방법**:

```python
# 더 많은 패턴 추가
checked_patterns = [
    "☑", "[X]", "[x]", "✓", "✔", "☒",
    "(checked)", "(selected)", "(yes)", "(v)",
    "marked", "ticked"
]

# 위치 기반 추론
# "Nothing to Declare" 옆에 작은 박스(□) 있으면 체크됨
```

### 5.5 겹친 텍스트 (Passport)

**증상**: nationality_long과 date_of_birth가 합쳐짐

**대응 방법**:

```python
# MRZ 우선 사용
if "mrz_line2" in extracted_data:
    # MRZ에서 생년월일 추출 (더 정확)
    date_of_birth = parse_mrz_date(mrz_line2[13:19])
else:
    # bbox로 구분
    overlapping_boxes = find_overlapping_boxes(all_boxes)
    # 오른쪽 것이 date_of_birth
```

---

## 6. 연락처

**OCR/분류 팀**:

- 질문/이슈: 팀 채팅방 또는 이슈 트래커
- 데이터 문제: OCR 재처리 요청 가능
- 새로운 요구사항: 언제든지 협의 가능

**참고 문서**:

- `QUICKTEST.md`: OCR/분류 파이프라인 테스트 방법
- `COMPLETE_GUIDE.md`: 전체 시스템 가이드
- `MULTILINGUAL_GUIDE.md`: 다국어 처리 가이드

---

**문서 버전**: 1.0  
**마지막 업데이트**: 2025-11-10  
**변경 이력**:

- 2025-11-10: 초안 작성 (all_boxes 추가, 5개 문서 타입 정리)
