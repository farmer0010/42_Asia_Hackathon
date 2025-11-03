#!/bin/bash

# ============================================================
# Mac 환경 설정 스크립트
# ============================================================
# 
# 사용법:
#   chmod +x scripts/setup_mac.sh
#   scripts/setup_mac.sh
#
# 요구사항:
#   - macOS 11.0+ (M1/M2/M3 또는 Intel)
#   - Homebrew 설치 권장
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
echo "🚀 42 Asia Hackathon - Mac Setup"
echo "=========================================="
echo ""

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.." || exit 1

# ============================================================
# Step 1: Python 확인
# ============================================================
echo -e "${BLUE}[1/7] Python 설치 확인 중...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3을 찾을 수 없습니다!${NC}"
    echo ""
    echo "Python 3.11 이상을 설치해주세요:"
    echo "  brew install python@3.11"
    echo ""
    echo "또는 다운로드: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ $PYTHON_VERSION 발견${NC}"
echo ""

# ============================================================
# Step 2: Homebrew 확인 (선택)
# ============================================================
echo -e "${BLUE}[2/7] Homebrew 확인 중...${NC}"

if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}⚠ Homebrew를 찾을 수 없습니다${NC}"
    echo "  Ollama 설치를 위해 Homebrew를 권장합니다"
    echo ""
    echo "Homebrew 설치:"
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo ""
    read -p "Homebrew 없이 계속하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    BREW_VERSION=$(brew --version | head -n1)
    echo -e "${GREEN}✓ $BREW_VERSION 발견${NC}"
fi
echo ""

# ============================================================
# Step 3: 가상환경 생성
# ============================================================
echo -e "${BLUE}[3/7] 가상환경 생성 중...${NC}"

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
# Step 4: 가상환경 활성화
# ============================================================
echo -e "${BLUE}[4/7] 가상환경 활성화 중...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ 가상환경 활성화 완료${NC}"
echo ""

# ============================================================
# Step 5: pip 업그레이드
# ============================================================
echo -e "${BLUE}[5/7] pip 업그레이드 중...${NC}"
pip install --upgrade pip --quiet
echo -e "${GREEN}✓ pip 업그레이드 완료${NC}"
echo ""

# ============================================================
# Step 6: 패키지 설치
# ============================================================
echo -e "${BLUE}[6/7] 패키지 설치 중...${NC}"
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
# Step 7: Ollama 설치
# ============================================================
echo -e "${BLUE}[7/7] Ollama 설치 중...${NC}"

if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>/dev/null || echo "알 수 없음")
    echo -e "${GREEN}✓ Ollama 이미 설치됨 ($OLLAMA_VERSION)${NC}"
else
    if command -v brew &> /dev/null; then
        echo "Homebrew를 통해 Ollama 설치 중..."
        brew install ollama
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Ollama 설치 완료${NC}"
        else
            echo -e "${RED}✗ Ollama 설치 실패${NC}"
            echo "  수동 설치: brew install ollama"
        fi
    else
        echo -e "${YELLOW}⚠ Homebrew 없이는 Ollama를 설치할 수 없습니다${NC}"
        echo ""
        echo "수동으로 설치해주세요:"
        echo "  1. 방문: https://ollama.ai/download"
        echo "  2. macOS용 다운로드"
        echo "  3. 설치 파일 실행"
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
# 완료
# ============================================================
echo "=========================================="
echo "✅ 설정 완료!"
echo "=========================================="
echo ""
echo "📋 요약:"
echo "  ✓ Python: $PYTHON_VERSION"
echo "  ✓ 가상환경: venv/"
echo "  ✓ 패키지: 설치 완료"
if command -v ollama &> /dev/null; then
    echo "  ✓ Ollama: 설치 완료"
    if ollama list | grep -q "qwen2.5:7b"; then
        echo "  ✓ 모델: qwen2.5:7b 준비 완료"
    else
        echo "  ⚠ 모델: 다운로드 필요 (ollama pull qwen2.5:7b)"
    fi
else
    echo "  ⚠ Ollama: 설치 안 됨"
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
echo "  - 자세한 설명: QUICKTEST.md 참고"
echo ""

