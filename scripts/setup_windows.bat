@echo off
REM ============================================================
REM Windows 환경 설정 스크립트
REM ============================================================
REM 
REM 사용법:
REM   scripts\setup_windows.bat
REM
REM 요구사항:
REM   - Python 3.11+ 설치 (https://www.python.org/downloads/)
REM   - Git Bash 권장 (https://git-scm.com/downloads)
REM ============================================================

echo.
echo ==========================================
echo 🚀 42 Asia Hackathon - Windows Setup
echo ==========================================
echo.

REM 프로젝트 루트로 이동
cd /d "%~dp0\.."

REM ============================================================
REM Step 1: Python 확인
REM ============================================================
echo [1/6] Python 설치 확인 중...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python을 찾을 수 없습니다!
    echo.
    echo Python 3.11 이상을 설치해주세요:
    echo https://www.python.org/downloads/
    echo.
    echo 설치할 때 "Add Python to PATH" 체크박스를 꼭 선택하세요!
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✓ Python %PYTHON_VERSION% 발견
echo.

REM ============================================================
REM Step 2: 가상환경 생성
REM ============================================================
echo [2/6] 가상환경 생성 중...
if exist venv (
    echo ⚠ venv가 이미 존재합니다, 건너뛰기...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo ❌ 가상환경 생성 실패
        pause
        exit /b 1
    )
    echo ✓ 가상환경 생성 완료
)
echo.

REM ============================================================
REM Step 3: 가상환경 활성화
REM ============================================================
echo [3/6] 가상환경 활성화 중...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ 가상환경 활성화 실패
    pause
    exit /b 1
)
echo ✓ 가상환경 활성화 완료
echo.

REM ============================================================
REM Step 4: pip 업그레이드
REM ============================================================
echo [4/6] pip 업그레이드 중...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo ❌ pip 업그레이드 실패
    pause
    exit /b 1
)
echo ✓ pip 업그레이드 완료
echo.

REM ============================================================
REM Step 5: 패키지 설치
REM ============================================================
echo [5/6] 패키지 설치 중...
echo 5-10분 정도 걸릴 수 있습니다...
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 패키지 설치 실패
    pause
    exit /b 1
)
echo ✓ 모든 패키지 설치 완료
echo.

REM ============================================================
REM Step 6: Ollama 설치 안내
REM ============================================================
echo [6/6] Ollama 설정...
echo.
echo ⚠ Windows에서 Ollama 설치 방법:
echo.
echo 1. Windows용 Ollama 다운로드:
echo    https://ollama.ai/download
echo.
echo 2. 설치 파일 실행 (OllamaSetup.exe)
echo.
echo 3. 설치 후 명령 프롬프트에서 실행:
echo    ollama pull qwen2.5:7b
echo.
echo 4. Ollama 서버 시작하기:
echo    ollama serve
echo.

REM ============================================================
REM 디렉토리 생성
REM ============================================================
echo 프로젝트 디렉토리 생성 중...
if not exist data\input mkdir data\input
if not exist data\output mkdir data\output
if not exist data\models mkdir data\models
if not exist data\test_samples mkdir data\test_samples
echo ✓ 디렉토리 생성 완료
echo.

REM ============================================================
REM 완료
REM ============================================================
echo ==========================================
echo ✅ 설정 완료!
echo ==========================================
echo.
echo 다음 단계:
echo.
echo 1. Ollama 설치 (위의 안내 참고)
echo.
echo 2. 모델 다운로드:
echo    ollama pull qwen2.5:7b
echo.
echo 3. 테스트 파일을 data\input\ 폴더에 추가
echo.
echo 4. 테스트 파이프라인 실행:
echo    venv\Scripts\activate
echo    python -m pytest  (유닛 테스트용)
echo.
echo    또는 Python으로 직접 실행:
echo    python src\pipeline\predict.py --input data\input --output data\output\predictions.json
echo.
echo 💡 팁: Git Bash를 사용하면 bash 스크립트를 바로 실행할 수 있습니다!
echo    설치 후: scripts/test_pipeline_notrain.sh
echo.
pause

