@echo off
chcp 65001 >nul
REM 문서 OCR 및 분류 시스템 - 자동 설치 스크립트 (Windows)

echo ==========================================
echo   문서 OCR 시스템 환경 설정 시작
echo ==========================================

REM 1. Python 버전 확인
echo.
echo [1/5] Python 버전 확인 중...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo    Python 3.8 이상을 설치해주세요.
    echo    다운로드: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✓ %PYTHON_VERSION% 발견

REM 2. 가상환경 생성
echo.
echo [2/5] 가상환경 생성 중...
if exist venv (
    echo ⚠️  기존 venv 폴더가 존재합니다.
    set /p REPLY="   삭제하고 새로 만드시겠습니까? (y/N): "
    if /i "%REPLY%"=="y" (
        rmdir /s /q venv
        echo    기존 venv 삭제 완료
    ) else (
        echo    기존 venv 사용
    )
)

if not exist venv (
    python -m venv venv
    echo ✓ 가상환경 생성 완료
) else (
    echo ✓ 기존 가상환경 사용
)

REM 3. 가상환경 활성화
echo.
echo [3/5] 가상환경 활성화 중...
call venv\Scripts\activate.bat
echo ✓ 가상환경 활성화 완료

REM 4. pip 업그레이드
echo.
echo [4/5] pip 업그레이드 중...
python -m pip install --upgrade pip --quiet
echo ✓ pip 업그레이드 완료

REM 5. 패키지 설치
echo.
echo [5/5] 필수 패키지 설치 중...
echo    (시간이 다소 걸릴 수 있습니다...)
pip install -r requirements.txt --quiet
if %errorlevel% equ 0 (
    echo ✓ 패키지 설치 완료
) else (
    echo ❌ 패키지 설치 중 오류 발생
    pause
    exit /b 1
)

REM 완료 메시지
echo.
echo ==========================================
echo   ✓ 설치 완료!
echo ==========================================
echo.
echo 다음 명령어로 가상환경을 활성화하세요:
echo   venv\Scripts\activate
echo.
echo 테스트 실행:
echo   python quick_demo.py
echo.
echo ==========================================
echo.
pause

