# 🚀 빠른 시작 가이드

다른 환경에서 이 프로젝트를 빠르게 설정하고 실행하는 방법입니다.

## 📥 저장소 클론

```bash
git clone <your-repository-url>
cd 42_Asia_Hackathon
```

## ⚡ 자동 설치 (추천)

### macOS/Linux

```bash
./setup.sh
```

### Windows

```cmd
setup.bat
```

자동 설치 스크립트가:
1. Python 버전 확인
2. 가상환경 생성
3. 가상환경 활성화
4. pip 업그레이드
5. 모든 필수 패키지 설치

를 자동으로 수행합니다.

## 🔧 수동 설치

자동 설치가 작동하지 않는 경우:

### 1. 가상환경 생성 및 활성화

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

### 2. 패키지 설치

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 🎯 실행 방법

### 1. OCR 처리

```bash
# 가상환경이 활성화되어 있는지 확인
# 프롬프트 앞에 (venv)가 보여야 함

python src/ocr_module.py
```

### 2. 빠른 데모 실행

```bash
python quick_demo.py
```

## ✅ 설치 확인

제대로 설치되었는지 확인:

```python
# test_install.py
import torch
import transformers
import paddleocr
import cv2

print("✓ 모든 패키지 정상 설치됨")
print(f"PyTorch: {torch.__version__}")
print(f"Transformers: {transformers.__version__}")
print(f"Device: {torch.device('cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu')}")
```

```bash
python test_install.py
```

## 🔄 가상환경 관리

### 활성화

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

### 비활성화

```bash
deactivate
```

### 가상환경 삭제 (재설치 필요시)

**macOS/Linux:**
```bash
rm -rf venv
```

**Windows:**
```cmd
rmdir /s venv
```

## 📋 필수 요구사항

- **Python**: 3.8 이상
- **메모리**: 최소 4GB RAM (8GB 권장)
- **디스크**: 약 5GB 여유 공간 (모델 다운로드 포함)
- **GPU (선택)**: 
  - CUDA 지원 GPU (NVIDIA)
  - Apple Silicon (M1/M2/M3) - MPS 자동 지원

## 🐛 문제 해결

### "command not found: python"

```bash
# python3 사용
python3 -m venv venv
```

### "No module named 'xxx'"

가상환경이 활성화되지 않았을 수 있습니다:
```bash
source venv/bin/activate  # 또는 venv\Scripts\activate (Windows)
pip install -r requirements.txt
```

### "torch" 또는 "transformers" 설치 실패

네트워크 문제일 수 있습니다. 개별 설치 시도:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install transformers
```

### macOS에서 opencv 오류

```bash
brew install opencv
```

### Windows에서 "Microsoft Visual C++ 14.0 is required" 오류

Visual Studio Build Tools 설치 필요:
https://visualstudio.microsoft.com/downloads/

## 📦 패키지 업데이트

```bash
pip install --upgrade -r requirements.txt
```

## 🌐 다른 시스템에 배포

1. **이 저장소 Push**
   ```bash
   git add .
   git commit -m "Add setup files"
   git push origin main
   ```

2. **다른 시스템에서 Clone 및 설치**
   ```bash
   git clone <your-repository-url>
   cd 42_Asia_Hackathon
   ./setup.sh  # 또는 setup.bat (Windows)
   ```

3. **테스트**
   ```bash
   source venv/bin/activate
   python quick_demo.py
   ```

## 📚 추가 문서

- 전체 문서: `README.md`
- 아키텍처: `docs/ARCHITECTURE.md`
- 워크플로우: `docs/HACKATHON_WORKFLOW.md`

## 💡 팁

1. **가상환경은 항상 활성화하세요**
   - 실행 전 `(venv)` 확인

2. **첫 실행은 시간이 걸립니다**
   - Hugging Face 모델 다운로드 (약 1-2GB)
   - 인터넷 연결 필요

3. **GPU 사용**
   - CUDA/MPS 자동 감지
   - CPU도 정상 작동 (속도만 느림)

---

문제가 계속되면 Issue를 열어주세요! 🙋‍♂️

