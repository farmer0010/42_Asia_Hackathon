#!/bin/bash

# ============================================================
# 로컬 실행 스크립트 (M1 Mac Metal 가속 / 빠른 테스트용)
# ============================================================
# 
# 사용법:
#   ./run_local.sh
#
# 요구사항:
#   - Python 가상환경 활성화 (source venv/bin/activate)
#   - Ollama 설치 (brew install ollama)
#   - Qwen2.5:7b 모델 다운로드 (ollama pull qwen2.5:7b)
# ============================================================

set -e  # 에러 발생 시 중단

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "=========================================="
echo "🚀 Local Document Processing Pipeline"
echo "   (Metal Accelerated - Fast!)"
echo "=========================================="
echo ""

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# 환경 변수 설정
INPUT_DIR=${INPUT_DIR:-data/input}
OUTPUT_DIR=${OUTPUT_DIR:-data/output}
CLASSIFIER_PATH=${CLASSIFIER_PATH:-data/models/classifier.pth}
OLLAMA_URL=${OLLAMA_URL:-http://localhost:11434}

echo "Configuration:"
echo "  Input:      $INPUT_DIR"
echo "  Output:     $OUTPUT_DIR"
echo "  Classifier: $CLASSIFIER_PATH"
echo "  Ollama:     $OLLAMA_URL"
echo ""

# 1. 가상환경 확인
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}✗ Virtual environment not activated!${NC}"
    echo "  Please run: source venv/bin/activate"
    exit 1
fi
echo -e "${GREEN}✓ Virtual environment active${NC}"

# 2. Ollama 확인
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}✗ Ollama not installed!${NC}"
    echo "  Please run: brew install ollama"
    exit 1
fi
echo -e "${GREEN}✓ Ollama installed${NC}"

# 3. Ollama 서비스 확인
echo ""
echo "Checking Ollama service..."
if ! curl -s "$OLLAMA_URL" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Ollama not running, starting...${NC}"
    ollama serve &
    OLLAMA_PID=$!
    sleep 5
    
    # 다시 확인
    if ! curl -s "$OLLAMA_URL" > /dev/null 2>&1; then
        echo -e "${RED}✗ Failed to start Ollama${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Ollama started (PID: $OLLAMA_PID)${NC}"
else
    echo -e "${GREEN}✓ Ollama already running${NC}"
    OLLAMA_PID=""
fi

# 4. 모델 확인
echo ""
echo "Checking Qwen2.5:7b model..."
if ! ollama list | grep -q "qwen2.5:7b"; then
    echo -e "${YELLOW}⚠ Model not found, downloading...${NC}"
    echo "  (This may take 5-10 minutes for first time)"
    ollama pull qwen2.5:7b
fi
echo -e "${GREEN}✓ Model ready${NC}"

# 5. 출력 디렉토리 생성
mkdir -p "$OUTPUT_DIR"

# 6. 입력 파일 확인
if [ ! -d "$INPUT_DIR" ] || [ -z "$(ls -A $INPUT_DIR)" ]; then
    echo -e "${RED}✗ No input files found in $INPUT_DIR${NC}"
    exit 1
fi

FILE_COUNT=$(ls -1 "$INPUT_DIR" | wc -l | tr -d ' ')
echo -e "${GREEN}✓ Found $FILE_COUNT input file(s)${NC}"
echo ""

# ============================================================
# Step 1: OCR + Classification
# ============================================================
echo "=========================================="
echo "📄 Step 1: OCR + Classification"
echo "=========================================="
echo ""

START_TIME=$(date +%s)

if [ -f "$CLASSIFIER_PATH" ]; then
    echo -e "${BLUE}Using trained classifier: $CLASSIFIER_PATH${NC}"
    python src/pipeline/predict.py \
        --input "$INPUT_DIR" \
        --output "$OUTPUT_DIR/predictions.json" \
        --classifier "$CLASSIFIER_PATH"
else
    echo -e "${YELLOW}⚠ No classifier found, running OCR only${NC}"
    python src/pipeline/predict.py \
        --input "$INPUT_DIR" \
        --output "$OUTPUT_DIR/predictions.json"
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ OCR + Classification failed!${NC}"
    [ -n "$OLLAMA_PID" ] && kill $OLLAMA_PID 2>/dev/null
    exit 1
fi

OCR_TIME=$(($(date +%s) - START_TIME))
echo ""
echo -e "${GREEN}✓ OCR + Classification complete (${OCR_TIME}s)${NC}"
echo ""

# ============================================================
# Step 2: LLM Processing (Extraction + PII + Summary)
# ============================================================
echo "=========================================="
echo "🤖 Step 2: LLM Processing"
echo "   (Using Metal acceleration)"
echo "=========================================="
echo ""

START_TIME=$(date +%s)

python src/llm/converter.py \
    --input "$OUTPUT_DIR/predictions.json" \
    --output "$OUTPUT_DIR/final_results.json" \
    --ollama-url "$OLLAMA_URL"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ LLM Processing failed!${NC}"
    [ -n "$OLLAMA_PID" ] && kill $OLLAMA_PID 2>/dev/null
    exit 1
fi

LLM_TIME=$(($(date +%s) - START_TIME))
echo ""
echo -e "${GREEN}✓ LLM Processing complete (${LLM_TIME}s)${NC}"
echo ""

# ============================================================
# 완료
# ============================================================
TOTAL_TIME=$((OCR_TIME + LLM_TIME))

echo "=========================================="
echo "✅ Pipeline Complete!"
echo "=========================================="
echo ""
echo "Performance:"
echo "  OCR Time:   ${OCR_TIME}s"
echo "  LLM Time:   ${LLM_TIME}s"
echo "  Total Time: ${TOTAL_TIME}s"
echo "  Avg/file:   $((TOTAL_TIME / FILE_COUNT))s"
echo ""
echo "Output files:"
echo "  📄 $OUTPUT_DIR/predictions.json      (OCR + Classification)"
echo "  📄 $OUTPUT_DIR/final_results.json    (Final output)"
echo ""

# Ollama 종료 (우리가 시작한 경우)
if [ -n "$OLLAMA_PID" ]; then
    echo -e "${YELLOW}Stopping Ollama service (PID: $OLLAMA_PID)...${NC}"
    kill $OLLAMA_PID 2>/dev/null
    echo -e "${GREEN}✓ Cleaned up${NC}"
fi

echo ""
echo -e "${GREEN}🎉 All done!${NC}"
echo ""

