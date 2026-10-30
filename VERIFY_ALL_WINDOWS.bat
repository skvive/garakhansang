@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (py -3 tools\onepack.py qa) else (python tools\onepack.py qa)
if errorlevel 1 (
  echo QA FAILED. Read QA_V9_RESULTS\V9_RUN_SUMMARY.json
  pause
  exit /b 1
)
echo QA SUCCESS (LOCAL BETA ONLY). Logs: QA_V9_RESULTS\
pause
endlocal
