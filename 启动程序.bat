@echo off
chcp 65001 >nul 2>&1
setlocal

cd /d "%~dp0"

set PYTHONUTF8=1
if "%PLAYWRIGHT_BROWSERS_PATH%"=="" set "PLAYWRIGHT_BROWSERS_PATH=%USERPROFILE%\\.xhs_system\\ms-playwright"

if exist "venv\\Scripts\\python.exe" (
  "venv\\Scripts\\python.exe" main.py
) else (
  echo ⚠️  venv not found, trying system python...
  python main.py
)
