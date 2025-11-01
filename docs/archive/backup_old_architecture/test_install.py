"""
환경 설정 확인 스크립트
모든 필수 패키지가 제대로 설치되었는지 확인합니다.
"""

import sys

print("=" * 60)
print("환경 설정 확인 중...")
print("=" * 60)

# Python 버전 확인
print(f"\n✓ Python 버전: {sys.version}")

# 필수 패키지 확인
packages = {
    'torch': 'PyTorch',
    'transformers': 'Transformers',
    'cv2': 'OpenCV',
    'PIL': 'Pillow',
    'numpy': 'NumPy',
    'pandas': 'Pandas',
}

# PaddleOCR은 별도 확인 (import 방식이 다름)
special_packages = {
    'paddleocr': ('PaddleOCR', 'from paddleocr import PaddleOCR')
}

failed = []

print("\n패키지 확인:")
for module, name in packages.items():
    try:
        mod = __import__(module)
        version = getattr(mod, '__version__', 'unknown')
        print(f"  ✓ {name}: {version}")
    except ImportError as e:
        print(f"  ✗ {name}: 설치되지 않음")
        failed.append(name)

# 특수 패키지 확인
for module, (name, import_cmd) in special_packages.items():
    try:
        exec(import_cmd)
        print(f"  ✓ {name}: 설치됨")
    except Exception as e:
        print(f"  ✗ {name}: 설치되지 않음")
        failed.append(name)

# 디바이스 확인
if 'torch' in sys.modules:
    import torch
    print("\n디바이스 확인:")
    
    # CUDA
    if torch.cuda.is_available():
        print(f"  ✓ CUDA 사용 가능")
        print(f"    - GPU 수: {torch.cuda.device_count()}")
        print(f"    - GPU 이름: {torch.cuda.get_device_name(0)}")
        device = torch.device('cuda')
    # MPS (Apple Silicon)
    elif torch.backends.mps.is_available():
        print(f"  ✓ MPS (Apple Silicon) 사용 가능")
        device = torch.device('mps')
    # CPU
    else:
        print(f"  ℹ CPU 사용 (GPU 없음)")
        device = torch.device('cpu')
    
    print(f"  → 사용 디바이스: {device}")

# 결과 요약
print("\n" + "=" * 60)
if failed:
    print(f"✗ 설치 실패: {len(failed)}개 패키지")
    print(f"  실패한 패키지: {', '.join(failed)}")
    print("\n다음 명령어로 재설치하세요:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
else:
    print("✓ 모든 패키지가 정상적으로 설치되었습니다!")
    print("\n다음 단계:")
    print("  1. OCR 실행: python src/ocr_module.py")
    print("  2. 데모 실행: python quick_demo.py")

print("=" * 60)

