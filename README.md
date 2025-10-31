# 문서 OCR 및 분류 시스템

PaddleOCR과 Transformers를 활용한 문서 자동 분류 및 정보 추출 시스템입니다.

## 📋 주요 기능

- **OCR 처리**: PaddleOCR을 사용한 다국어 텍스트 인식
- **문서 분류**: Zero-shot classification으로 문서 타입 자동 분류 (Invoice, Receipt, Resume, Report, Contract)
- **정보 추출**: 룰 베이스 방식으로 핵심 정보 추출

## 🚀 빠른 시작

### 1. 필수 요구사항

- Python 3.8 이상
- pip (Python 패키지 관리자)

### 2. 설치 방법

```bash
# 1. 저장소 클론
git clone <your-repository-url>
cd 42_Asia_Hackathon

# 2. 가상환경 생성
python3 -m venv venv

# 3. 가상환경 활성화
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. 필요한 패키지 설치
pip install -r requirements.txt
```

### 3. 사용 방법

#### OCR 실행
```bash
# 가상환경 활성화 (아직 안했다면)
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# OCR 처리
python src/ocr_module.py

# 빠른 데모 (Zero-shot 분류 + 정보 추출)
python quick_demo.py
```

## 📦 주요 패키지

- **paddleocr** (2.8.1): OCR 엔진
- **transformers** (4.46.3): Zero-shot 분류 모델
- **torch** (2.9.0): 딥러닝 프레임워크
- **opencv-python** (4.10.0.84): 이미지 처리
- **pillow** (11.0.0): 이미지 로딩

전체 패키지 목록은 `requirements.txt` 참조

## 📁 프로젝트 구조

```
42_Asia_Hackathon/
├── src/                    # 소스 코드
│   ├── ocr_module.py      # OCR 처리
│   ├── classification_module.py
│   └── extraction_module.py
├── test_samples/          # 테스트 이미지
├── outputs/               # 결과 파일
├── quick_demo.py          # 빠른 데모 스크립트
├── requirements.txt       # 패키지 의존성
└── README.md             # 이 문서
```

## 🖥️ 지원 환경

- **macOS**: CPU, MPS (Apple Silicon)
- **Linux**: CPU, CUDA (GPU)
- **Windows**: CPU, CUDA (GPU)

## 🔧 문제 해결

### 가상환경이 활성화되지 않은 경우
```bash
# ModuleNotFoundError 발생 시
source venv/bin/activate  # macOS/Linux
```

### OCR 결과 파일이 없는 경우
```bash
# 먼저 OCR을 실행하세요
python src/ocr_module.py
```

### GPU/MPS 사용 확인
스크립트 실행 시 첫 줄에 `Using device: mps` 또는 `Using device: cuda:0` 표시 확인

## 📊 출력 결과

실행 후 `outputs/` 폴더에 다음 파일들이 생성됩니다:

- `ocr_test_results.json`: OCR 원본 결과
- `demo_test_results.json`: 분류 및 추출 결과
