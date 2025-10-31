#!/bin/bash

# 문서 OCR 및 분류 시스템 - 자동 설치 스크립트

echo "=========================================="
echo "  문서 OCR 시스템 환경 설정 시작"
echo "=========================================="

# 1. Python 버전 확인
echo ""
echo "[1/5] Python 버전 확인 중..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3가 설치되어 있지 않습니다."
    echo "   Python 3.8 이상을 설치해주세요."
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✓ $PYTHON_VERSION 발견"

# 2. 가상환경 생성
echo ""
echo "[2/5] 가상환경 생성 중..."
if [ -d "venv" ]; then
    echo "⚠️  기존 venv 폴더가 존재합니다."
    read -p "   삭제하고 새로 만드시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        echo "   기존 venv 삭제 완료"
    else
        echo "   기존 venv 사용"
    fi
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ 가상환경 생성 완료"
else
    echo "✓ 기존 가상환경 사용"
fi

# 3. 가상환경 활성화
echo ""
echo "[3/5] 가상환경 활성화 중..."
source venv/bin/activate
echo "✓ 가상환경 활성화 완료"

# 4. pip 업그레이드
echo ""
echo "[4/5] pip 업그레이드 중..."
pip install --upgrade pip -q
echo "✓ pip 업그레이드 완료"

# 5. 패키지 설치
echo ""
echo "[5/5] 필수 패키지 설치 중..."
echo "   (시간이 다소 걸릴 수 있습니다...)"
pip install -r requirements.txt -q
if [ $? -eq 0 ]; then
    echo "✓ 패키지 설치 완료"
else
    echo "❌ 패키지 설치 중 오류 발생"
    exit 1
fi

# 완료 메시지
echo ""
echo "=========================================="
echo "  ✓ 설치 완료!"
echo "=========================================="
echo ""
echo "다음 명령어로 가상환경을 활성화하세요:"
echo "  source venv/bin/activate"
echo ""
echo "테스트 실행:"
echo "  python quick_demo.py"
echo ""
echo "=========================================="

