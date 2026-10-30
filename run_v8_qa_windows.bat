@echo off
setlocal
cd /d "%~dp0"
echo Garak Hansang V8 Local QA (no real payments)
python -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :failed
python tests\v8_full_business_flow.py
if errorlevel 1 goto :failed
python tests\release_audit.py
if errorlevel 1 goto :failed
python tests\concurrency_beta.py
if errorlevel 1 goto :failed
where node >nul 2>nul
if not errorlevel 1 (
  node --test tests\currency_contract.test.mjs
  if errorlevel 1 goto :failed
)
echo Local API / Business / Static / Concurrency QA passed.
echo Browser QA requires Playwright and Chromium and is run separately.
exit /b 0
:failed
echo FAILED: inspect the log above. Do not deploy.
exit /b 1
