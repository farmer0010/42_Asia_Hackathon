
# === 1) Python 3.11 설치 (Homebrew) ===
brew install python@3.11

# === 2) 가상환경 새로 만들기 (.venv) ===
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv .venv

# === 3) 가상환경 활성화 ===
source .venv/bin/activate

# === 4) pip 업그레이드 (가상환경 안에서만!) ===
python -m pip install --upgrade pip

# === 5) (맥 + Py<3.12)에서 필요한 Paddle 버전 고정 준비 ===
#    - requirements.txt가 다른 버전을 요구하더라도, 아래 constraints로 2.6.1을 우선 사용
cat > constraints.txt <<'EOF'
paddlepaddle==2.6.1; platform_system == "Darwin" and python_version < "3.12"
EOF

# === 6) 먼저 PaddlePaddle 설치 (맥 전용 인덱스) ===
python -m pip install "paddlepaddle==2.6.1" -i https://www.paddlepaddle.org.cn/whl/macos.html

# === 7) 나머지 의존성 설치 (constraints 적용) ===
python -m pip install -r requirements.txt -c constraints.txt

# === 8) 정상 설치 확인 ===
python - <<'PY'
import sys
try:
    import paddle
    print("[OK] paddlepaddle:", paddle.__version__)
except Exception as e:
    print("[ERR] paddle import failed:", e)
print("[Python]", sys.version)
PY