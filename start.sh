#source .venv/bin/activate
#python quick_demo.py
#python llm/batch_run.py outputs/demo_test_results.json real_outputs

#!/usr/bin/env bash
set -e

# (있어도 되고 없어도 됨)
source .venv/bin/activate || true

# 디버그: 실제 파이썬 확인
python -c "import sys; print('[PY]', sys.executable)"

# 네가 요구한 실행 순서
python quick_demo.py
python llm/batch_run.py outputs/demo_test_results.json real_outputs