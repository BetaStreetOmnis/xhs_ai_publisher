@echo off
chcp 65001 >nul 2>&1
setlocal

cd /d "%~dp0"

set PYTHONUTF8=1
if "%PLAYWRIGHT_BROWSERS_PATH%"=="" set "PLAYWRIGHT_BROWSERS_PATH=%USERPROFILE%\\.xhs_system\\ms-playwright"

if not exist "main.py" (
  echo ❌ Missing main.py. Please run this script in the project root.
  pause
  exit /b 1
)

if exist "venv\\Scripts\\python.exe" (
  echo 🚀 Launching with venv\\Scripts\\python.exe ...
  "venv\\Scripts\\python.exe" main.py
) else (
  echo ⚠️  venv not found, trying system python...
  python main.py
)

if errorlevel 1 (
  echo.
  echo ❌ Startup failed.
  echo 💡 Please run install.bat first, then retry 启动程序.bat.
  pause
  exit /b 1
)
