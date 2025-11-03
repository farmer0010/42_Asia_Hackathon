#!/bin/bash

# ============================================================
# Linux 환경 설정 스크립트
# ============================================================
# 
# 사용법:
#   chmod +x scripts/setup_linux.sh
#   scripts/setup_linux.sh
#
# 요구사항:
#   - Ubuntu 20.04+ / Debian 11+ / CentOS 8+ / Fedora 35+
#   - sudo 권한 (시스템 패키지 설치용)
# ============================================================

set -e

# 색상
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "=========================================="
echo "🚀 42 Asia Hackathon - Linux Setup"
echo "=========================================="
echo ""

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.." || exit 1

# ============================================================
# OS 감지
# ============================================================
echo -e "${BLUE}[0/8] OS 확인 중...${NC}"

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$NAME
    OS_ID=$ID
    echo -e "${GREEN}✓ $OS_NAME 감지${NC}"
else
    echo -e "${YELLOW}⚠ OS를 감지할 수 없습니다. Ubuntu/Debian으로 가정합니다.${NC}"
    OS_ID="ubuntu"
fi
echo ""

# 패키지 매니저 결정
case "$OS_ID" in
    ubuntu|debian|linuxmint)
        PKG_MGR="apt-get"
        PKG_UPDATE="sudo apt-get update -qq"
        PKG_INSTALL="sudo apt-get install -y -qq"
        ;;
    fedora|rhel|centos)
        PKG_MGR="dnf"
        PKG_UPDATE="sudo dnf check-update || true"
        PKG_INSTALL="sudo dnf install -y -q"
        ;;
    arch|manjaro)
        PKG_MGR="pacman"
        PKG_UPDATE="sudo pacman -Sy"
        PKG_INSTALL="sudo pacman -S --noconfirm"
        ;;
    *)
        echo -e "${YELLOW}⚠ 알 수 없는 배포판입니다. apt-get으로 시도합니다.${NC}"
        PKG_MGR="apt-get"
        PKG_UPDATE="sudo apt-get update -qq"
        PKG_INSTALL="sudo apt-get install -y -qq"
        ;;
esac

# ============================================================
# Step 1: 시스템 의존성 설치
# ============================================================
echo -e "${BLUE}[1/8] 시스템 패키지 설치 중...${NC}"
echo "필요한 패키지: python3, python3-venv, curl, libgl1, libglib2.0-0"
echo ""

# 패키지 목록 업데이트
echo "패키지 목록 업데이트 중..."
$PKG_UPDATE > /dev/null 2>&1

# 필수 패키지 설치
echo "필수 패키지 설치 중..."
case "$OS_ID" in
    ubuntu|debian|linuxmint)
        $PKG_INSTALL python3 python3-pip python3-venv curl libgl1 libglib2.0-0 wget
        ;;
    fedora|rhel|centos)
        $PKG_INSTALL python3 python3-pip curl mesa-libGL glib2 wget
        ;;
    arch|manjaro)
        $PKG_INSTALL python python-pip curl mesa glib2 wget
        ;;
esac

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 시스템 패키지 설치 완료${NC}"
else
    echo -e "${RED}✗ 시스템 패키지 설치 실패${NC}"
    echo "  수동으로 설치해주세요: python3, python3-venv, curl, libgl1, libglib2.0-0"
    exit 1
fi
echo ""

# ============================================================
# Step 2: Python 확인
# ============================================================
echo -e "${BLUE}[2/8] Python 설치 확인 중...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3을 찾을 수 없습니다!${NC}"
    echo ""
    echo "Python 3.11 이상을 설치해주세요:"
    case "$OS_ID" in
        ubuntu|debian|linuxmint)
            echo "  sudo apt-get install python3 python3-pip python3-venv"
            ;;
        fedora|rhel|centos)
            echo "  sudo dnf install python3 python3-pip"
            ;;
        arch|manjaro)
            echo "  sudo pacman -S python python-pip"
            ;;
    esac
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ $PYTHON_VERSION 발견${NC}"
echo ""

# ============================================================
# Step 3: pip 확인
# ============================================================
echo -e "${BLUE}[3/8] pip 확인 중...${NC}"

if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠ pip3을 찾을 수 없습니다. 설치 중...${NC}"
    case "$OS_ID" in
        ubuntu|debian|linuxmint)
            $PKG_INSTALL python3-pip
            ;;
        fedora|rhel|centos)
            $PKG_INSTALL python3-pip
            ;;
        arch|manjaro)
            $PKG_INSTALL python-pip
            ;;
    esac
fi
echo -e "${GREEN}✓ pip 사용 가능${NC}"
echo ""

# ============================================================
# Step 4: 가상환경 생성
# ============================================================
echo -e "${BLUE}[4/8] 가상환경 생성 중...${NC}"

if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠ venv가 이미 존재합니다${NC}"
    read -p "다시 생성하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
        echo -e "${GREEN}✓ 가상환경 재생성 완료${NC}"
    else
        echo "  건너뛰기..."
    fi
else
    python3 -m venv venv
    echo -e "${GREEN}✓ 가상환경 생성 완료${NC}"
fi
echo ""

# ============================================================
# Step 5: 가상환경 활성화
# ============================================================
echo -e "${BLUE}[5/8] 가상환경 활성화 중...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ 가상환경 활성화 완료${NC}"
echo ""

# ============================================================
# Step 6: pip 업그레이드
# ============================================================
echo -e "${BLUE}[6/8] pip 업그레이드 중...${NC}"
pip install --upgrade pip --quiet
echo -e "${GREEN}✓ pip 업그레이드 완료${NC}"
echo ""

# ============================================================
# Step 7: 패키지 설치
# ============================================================
echo -e "${BLUE}[7/8] 패키지 설치 중...${NC}"
echo "5-10분 정도 걸릴 수 있습니다..."
echo ""

pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 모든 패키지 설치 완료${NC}"
else
    echo -e "${RED}✗ 일부 패키지 설치 실패${NC}"
    echo "  수동 설치: pip install -r requirements.txt"
    exit 1
fi
echo ""

# ============================================================
# Step 8: Ollama 설치
# ============================================================
echo -e "${BLUE}[8/8] Ollama 설치 중...${NC}"

if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>/dev/null || echo "알 수 없음")
    echo -e "${GREEN}✓ Ollama 이미 설치됨 ($OLLAMA_VERSION)${NC}"
else
    echo "Ollama 설치 중..."
    curl -fsSL https://ollama.com/install.sh | sh
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Ollama 설치 완료${NC}"
    else
        echo -e "${RED}✗ Ollama 설치 실패${NC}"
        echo ""
        echo "수동으로 설치해주세요:"
        echo "  curl -fsSL https://ollama.com/install.sh | sh"
        echo ""
        echo "또는 방문: https://ollama.ai/download"
    fi
fi
echo ""

# ============================================================
# Ollama 모델 다운로드
# ============================================================
if command -v ollama &> /dev/null; then
    echo "Qwen2.5:7b 모델 다운로드 중..."
    echo "5-10분 정도 걸릴 수 있습니다 (4.7GB)..."
    echo ""
    
    # Ollama 서비스 시작 (백그라운드)
    if ! pgrep -x "ollama" > /dev/null; then
        ollama serve > /dev/null 2>&1 &
        OLLAMA_PID=$!
        sleep 3
    fi
    
    ollama pull qwen2.5:7b
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 모델 다운로드 완료${NC}"
    else
        echo -e "${YELLOW}⚠ 모델 다운로드 미완료${NC}"
        echo "  나중에 수동 실행: ollama pull qwen2.5:7b"
    fi
    
    # Ollama 프로세스 종료 (우리가 시작한 경우)
    if [ -n "$OLLAMA_PID" ]; then
        kill $OLLAMA_PID 2>/dev/null
    fi
fi
echo ""

# ============================================================
# 디렉토리 생성
# ============================================================
echo "프로젝트 디렉토리 생성 중..."
mkdir -p data/input
mkdir -p data/output
mkdir -p data/models
mkdir -p data/test_samples
echo -e "${GREEN}✓ 디렉토리 생성 완료${NC}"
echo ""

# ============================================================
# 테스트 샘플 확인
# ============================================================
echo "테스트 샘플 확인 중..."
if [ -d "test_samples" ] && [ "$(ls -A test_samples)" ]; then
    echo "테스트 샘플을 data/input/으로 복사 중..."
    cp test_samples/* data/input/ 2>/dev/null || true
    echo -e "${GREEN}✓ 테스트 샘플 복사 완료${NC}"
fi
echo ""

# ============================================================
# 권한 설정
# ============================================================
echo "스크립트 실행 권한 설정 중..."
chmod +x scripts/run_local.sh
chmod +x scripts/test_pipeline_notrain.sh
chmod +x scripts/run_pipeline.sh
echo -e "${GREEN}✓ 스크립트 실행 권한 설정 완료${NC}"
echo ""

# ============================================================
# GPU 확인 (NVIDIA)
# ============================================================
echo "GPU 확인 중..."
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1)
    echo -e "${GREEN}✓ NVIDIA GPU 감지: $GPU_INFO${NC}"
    echo "  PyTorch는 자동으로 GPU를 사용합니다."
else
    echo -e "${YELLOW}⚠ NVIDIA GPU를 찾을 수 없습니다${NC}"
    echo "  CPU 모드로 실행됩니다 (속도가 느릴 수 있음)"
fi
echo ""

# ============================================================
# 완료
# ============================================================
echo "=========================================="
echo "✅ 설정 완료!"
echo "=========================================="
echo ""
echo "📋 요약:"
echo "  ✓ OS: $OS_NAME"
echo "  ✓ Python: $PYTHON_VERSION"
echo "  ✓ 가상환경: venv/"
echo "  ✓ 패키지: 설치 완료"
if command -v ollama &> /dev/null; then
    echo "  ✓ Ollama: 설치 완료"
    if ollama list 2>/dev/null | grep -q "qwen2.5:7b"; then
        echo "  ✓ 모델: qwen2.5:7b 준비 완료"
    else
        echo "  ⚠ 모델: 다운로드 필요 (ollama pull qwen2.5:7b)"
    fi
else
    echo "  ⚠ Ollama: 설치 안 됨"
fi

if command -v nvidia-smi &> /dev/null; then
    echo "  ✓ GPU: NVIDIA GPU 사용 가능"
else
    echo "  ⚠ GPU: CPU 모드"
fi
echo ""
echo "🚀 다음 단계:"
echo ""
echo "1. 가상환경 활성화:"
echo "   source venv/bin/activate"
echo ""
echo "2. Ollama 시작 (새 터미널에서):"
echo "   ollama serve"
echo ""
echo "3. 테스트 파일을 data/input/에 추가"
echo ""
echo "4. 테스트 파이프라인 실행:"
echo "   scripts/test_pipeline_notrain.sh"
echo ""
echo "💡 팁:"
echo "  - 빠른 테스트: scripts/test_pipeline_notrain.sh"
echo "  - 분류 모델 학습 후: scripts/run_local.sh"
echo "  - Docker 사용: cd docker && docker compose up"
echo "  - 자세한 설명: QUICKTEST.md 참고"
echo ""
echo "🐧 Linux 특수 사항:"
case "$OS_ID" in
    ubuntu|debian|linuxmint)
        echo "  - 시스템 패키지: apt-get으로 관리"
        ;;
    fedora|rhel|centos)
        echo "  - 시스템 패키지: dnf/yum으로 관리"
        ;;
    arch|manjaro)
        echo "  - 시스템 패키지: pacman으로 관리"
        ;;
esac
echo "  - GPU: nvidia-docker 사용 권장 (Docker 실행 시)"
echo "  - 백그라운드 실행: nohup ollama serve &"
echo ""

