#!/bin/bash

echo "=========================================="
echo "Document Processing Pipeline"
echo "=========================================="

# PYTHONPATH 설정 (Docker 환경)
export PYTHONPATH="/app:${PYTHONPATH}"

# 환경 변수 설정
INPUT_DIR=${INPUT_DIR:-/app/data/input}
OUTPUT_DIR=${OUTPUT_DIR:-/app/data/output}
CLASSIFIER_PATH=${CLASSIFIER_PATH:-/app/data/models/classifier.pth}
OLLAMA_URL=${OLLAMA_URL:-http://ollama:11434}

echo ""
echo "Configuration:"
echo "  Input:      $INPUT_DIR"
echo "  Output:     $OUTPUT_DIR"
echo "  Classifier: $CLASSIFIER_PATH"
echo "  Ollama:     $OLLAMA_URL"
echo ""

# Ollama 연결 대기
echo "Waiting for Ollama service..."
until curl -s "$OLLAMA_URL" > /dev/null 2>&1; do
    echo "  Ollama not ready, waiting..."
    sleep 5
done
echo "✓ Ollama service ready!"
echo ""

# Step 1: OCR + Classification
echo "Step 1: OCR + Classification"
echo "----------------------------------------"

if [ -f "$CLASSIFIER_PATH" ]; then
    echo "Using trained classifier: $CLASSIFIER_PATH"
    python src/pipeline/predict.py \
        --input "$INPUT_DIR" \
        --output "$OUTPUT_DIR/predictions.json" \
        --classifier "$CLASSIFIER_PATH"
else
    echo "No classifier found, running OCR only"
    python src/pipeline/predict.py \
        --input "$INPUT_DIR" \
        --output "$OUTPUT_DIR/predictions.json"
fi

if [ $? -ne 0 ]; then
    echo "✗ OCR + Classification failed!"
    exit 1
fi
echo "✓ OCR + Classification complete"
echo ""

# Step 2: LLM Extraction + PII + Summary
echo "Step 2: LLM Processing"
echo "----------------------------------------"
python src/llm/converter.py \
    --input "$OUTPUT_DIR/predictions.json" \
    --output "$OUTPUT_DIR/final_results.json" \
    --ollama-url "$OLLAMA_URL"

if [ $? -ne 0 ]; then
    echo "✗ LLM Processing failed!"
    exit 1
fi
echo "✓ LLM Processing complete"
echo ""

# 완료
echo "=========================================="
echo "Pipeline Complete!"
echo "=========================================="
echo ""
echo "Output files:"
echo "  - $OUTPUT_DIR/predictions.json"
echo "  - $OUTPUT_DIR/final_results.json"
echo ""