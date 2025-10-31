#!/usr/bin/env bash
set -euo pipefail

VENV_PY="/app/.venv/bin/python"

# 실제 사용되는 파이썬 경로 확인
"$VENV_PY" -c 'import sys; print("[PY]", sys.executable)'

# 실행 순서 그대로
"$VENV_PY" quick_demo.py
"$VENV_PY" llm/batch_run.py outputs/demo_test_results.json real_outputs