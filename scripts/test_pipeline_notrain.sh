#!/bin/bash

# ============================================================
# 테스트 파이프라인 (훈련 없이 전체 테스트)
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
echo "🧪 Test Pipeline (No Training Required)"
echo "=========================================="
echo ""

# 프로젝트 루트로 이동
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# ==== 추가: 기본 모델 설정 (환경변수 MODEL로 override 가능) ====
MODEL=${MODEL:-qwen2.5:7b}

# 환경 확인
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}✗ Virtual environment not activated!${NC}"
    echo "  Please run: source venv/bin/activate"
    exit 1
fi

if ! curl -s "http://localhost:11434" > /dev/null 2>&1; then
    echo -e "${RED}✗ Ollama not running!${NC}"
    echo "  Please run: ollama serve"
    exit 1
fi

# ==== 추가: 해당 모델이 로컬에 있는지 확인 ====
if ! ollama list | awk '{print $1}' | grep -qx "$MODEL"; then
    echo -e "${YELLOW}… Model '$MODEL' not found locally. Pulling…${NC}"
    ollama pull "$MODEL"
fi

# 입력 파일 확인
if [ ! -d "data/input" ] || [ -z "$(ls -A data/input 2>/dev/null)" ]; then
    echo -e "${RED}✗ No files in data/input/${NC}"
    exit 1
fi

FILE_COUNT=$(ls -1 data/input | wc -l | tr -d ' ')
echo -e "${GREEN}✓ Found $FILE_COUNT test file(s) in data/input/${NC}"
echo ""

# 출력 디렉토리 생성
mkdir -p data/output

# ============================================================
# Step 1: OCR + 레이아웃 분석 (분류 없음)
# ============================================================
echo "=========================================="
echo "📄 Step 1: OCR + Layout Analysis"
echo "=========================================="
echo ""

START_TIME=$(date +%s)

python src/pipeline/predict.py \
    --input data/input \
    --output data/output/predictions_ocr_only.json

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ OCR failed!${NC}"
    exit 1
fi

OCR_TIME=$(($(date +%s) - START_TIME))
echo ""
echo -e "${GREEN}✓ OCR complete (${OCR_TIME}s)${NC}"
echo ""

# ============================================================
# Step 2: 수동 Doc Type 할당
# ============================================================
echo "=========================================="
echo "🏷️  Step 2: Manual Doc Type Assignment"
echo "=========================================="
echo ""

python tests/test_with_types.py

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Doc type assignment failed!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Doc types assigned${NC}"
echo ""

# ============================================================
# Step 3: LLM 처리 (추출 + PII + 요약)
# ============================================================
echo "=========================================="
echo "🤖 Step 3: LLM Processing"
echo "   (Extraction + PII + Summary)"
echo "=========================================="
echo ""

START_TIME=$(date +%s)

python src/llm/converter.py \
    --input data/output/predictions_with_types.json \
    --output data/output/test_final_results.json \
    --ollama-url http://localhost:11434 \
    --model "$MODEL"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ LLM processing failed!${NC}"
    exit 1
fi

LLM_TIME=$(($(date +%s) - START_TIME))
echo ""
echo -e "${GREEN}✓ LLM processing complete (${LLM_TIME}s)${NC}"
echo ""

# ============================================================
# 완료
# ============================================================
TOTAL_TIME=$((OCR_TIME + LLM_TIME))

echo "=========================================="
echo "✅ Test Pipeline Complete!"
echo "=========================================="
echo ""
echo "Performance:"
echo "  OCR Time:   ${OCR_TIME}s"
echo "  LLM Time:   ${LLM_TIME}s"
echo "  Total Time: ${TOTAL_TIME}s"
echo "  Avg/file:   $((TOTAL_TIME / FILE_COUNT))s"
echo ""
echo "Output files:"
echo "  📄 data/output/predictions_ocr_only.json       (OCR + Layout)"
echo "  📄 data/output/predictions_with_types.json     (+ Manual Types)"
echo "  📄 data/output/test_final_results.json         (Final Results)"
echo ""
echo -e "${BLUE}💡 Tip: MODEL is '${MODEL}'. Override with: MODEL=qwen2.5:7b ./scripts/test_pipeline_notrain.sh${NC}"
echo ""