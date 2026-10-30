@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 tools\onepack.py run --open-browser
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3.11+ is required: https://www.python.org/downloads/
    pause
    exit /b 1
  )
  python tools\onepack.py run --open-browser
)
if errorlevel 1 (
  echo Local startup failed. Run VERIFY_ALL_WINDOWS.bat for diagnostic tests.
  pause
  exit /b 1
)
endlocal
