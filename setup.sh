#!/bin/bash
set -e

# 문서 OCR 및 분류 시스템 - 자동 설치 스크립트 (macOS/Apple Silicon 호환 개선)

echo "=========================================="
echo "  문서 OCR 시스템 환경 설정 시작"
echo "=========================================="

# 1. Python 위치/버전 확인 (우선순위: Homebrew Python 3.11)
echo ""
echo "[1/5] Python 버전 확인 중..."
if [ -x "/opt/homebrew/opt/python@3.11/bin/python3.11" ]; then
    PY="/opt/homebrew/opt/python@3.11/bin/python3.11"
else
    if ! command -v python3 >/dev/null 2>&1; then
        echo "❌ Python3가 설치되어 있지 않습니다. Homebrew로 설치하세요: brew install python@3.11"
        exit 1
    fi
    PY="$(command -v python3)"
fi

PY_VER="$($PY -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
PY_MAJ="$($PY -c 'import sys; print(sys.version_info[0])')"
PY_MIN="$($PY -c 'import sys; print(sys.version_info[1])')"
OS_NAME="$(uname -s)"

echo "✓ Python ${PY_VER} (${PY}) 발견"

# macOS에서 PaddlePaddle 호환 가드 (>=3.12 차단)
if [ "$OS_NAME" = "Darwin" ] && [ "$PY_MAJ" -ge 3 ] && [ "$PY_MIN" -ge 12 ]; then
    echo "⚠️  macOS에서 Python ${PY_VER} 감지: PaddlePaddle 휠이 3.12 이상에서 제공되지 않을 수 있음"
    echo "   -> 권장: brew install python@3.11 && /opt/homebrew/opt/python@3.11/bin/python3.11 -m venv .venv"
    exit 1
fi

# 2. 가상환경 생성 (.venv 사용, venv 심볼릭 링크로 호환)
echo ""
echo "[2/5] 가상환경 생성 중..."
VENV_DIR=".venv"
if [ -d "$VENV_DIR" ]; then
    echo "⚠️  기존 ${VENV_DIR} 폴더가 존재합니다."
    read -p "   삭제하고 새로 만드시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        echo "   기존 ${VENV_DIR} 삭제 완료"
    else
        echo "   기존 ${VENV_DIR} 사용"
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    "$PY" -m venv "$VENV_DIR"
    echo "✓ 가상환경 생성 완료"
else
    echo "✓ 기존 가상환경 사용"
fi

# 호환성을 위해 venv -> .venv 심볼릭 링크 제공 (실패해도 무시)
if [ ! -e "venv" ]; then
    ln -s "$VENV_DIR" venv 2>/dev/null || true
fi

# 3. 가상환경 활성화
echo ""
echo "[3/5] 가상환경 활성화 중..."
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
echo "✓ 가상환경 활성화 완료"

# 4. pip 업그레이드 (항상 python -m pip 형태 사용)
echo ""
echo "[4/5] pip 업그레이드 중..."
python -m pip install --upgrade pip -q
python -m pip --version | sed 's/^/  - /'
echo "✓ pip 업그레이드 완료"

# 5. 패키지 설치 (macOS에선 Paddle 먼저 시도)
echo ""
echo "[5/5] 필수 패키지 설치 중..."
echo "   (시간이 다소 걸릴 수 있습니다...)"

INSTALL_OK=0
if [ "$OS_NAME" = "Darwin" ]; then
    echo "   • macOS 감지: PaddlePaddle 선 설치 시도 (2.6.1)"
    if python -m pip install "paddlepaddle==2.6.1" -q -i https://www.paddlepaddle.org.cn/whl/macos.html; then
        echo "   ✓ PaddlePaddle(2.6.1) 설치 성공"
    else
        echo "   ↩︎ 전용 인덱스 설치 실패, 기본 인덱스로 재시도"
        python -m pip install "paddlepaddle==2.6.1" -q || true
    fi
fi

# 나머지 의존성 설치
if python -m pip install -r requirements.txt -q; then
    INSTALL_OK=1
fi

if [ $INSTALL_OK -eq 1 ]; then
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
echo "  source ${VENV_DIR}/bin/activate   # (또는 source venv/bin/activate)"
echo ""
echo "테스트 실행:"
echo "  python quick_demo.py"
echo ""
echo "=========================================="