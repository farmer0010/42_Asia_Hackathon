python -m src.llm.converter \
 --input data/predictions_ocr_only.json \
 --output outputs/hackathon_results.json \
 --ollama-url http://localhost:11434 \
 --model qwen2.5:3b \
 --retries 3
