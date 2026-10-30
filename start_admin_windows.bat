@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo =============================================
echo   가락한상 통합 운영센터 V6 - 로컬 베타
 echo   실제 주문/결제/외부 API는 연결되지 않습니다.
echo =============================================
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m admin_core.server --port 8099
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3.11+ 를 설치하고 다시 실행하세요.
    pause
    exit /b 1
  )
  python -m admin_core.server --port 8099
)
pause
