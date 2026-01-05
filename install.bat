@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

cd /d "%~dp0"

if not exist "requirements.txt" (
  echo ❌ Missing requirements.txt. Please run in project root.
  exit /b 1
)
if not exist "main.py" (
  echo ❌ Missing main.py. Please run in project root.
  exit /b 1
)

set WITH_BROWSER=0
set SKIP_BROWSER=0
set RECREATE_VENV=0
for %%A in (%*) do (
  if "%%~A"=="--with-browser" set WITH_BROWSER=1
  if "%%~A"=="--skip-browser" set SKIP_BROWSER=1
  if "%%~A"=="--recreate-venv" set RECREATE_VENV=1
)

if exist "venv" (
  if %RECREATE_VENV%==1 (
    echo 🗑️  Removing existing venv\ ...
    rmdir /s /q "venv"
  )
)

set "VENV_PY=venv\\Scripts\\python.exe"

if not exist "%VENV_PY%" (
  set "PYTHON_CMD="
  where py >nul 2>&1 && set "PYTHON_CMD=py -3"
  if "%PYTHON_CMD%"=="" (
    where python >nul 2>&1 && set "PYTHON_CMD=python"
  )
  if "%PYTHON_CMD%"=="" (
    where python3 >nul 2>&1 && set "PYTHON_CMD=python3"
  )

  if "%PYTHON_CMD%"=="" (
    echo ❌ Python not found. Please install Python 3.11/3.12 (64-bit recommended) first.
    exit /b 1
  )

  echo ✅ Using Python to create venv: %PYTHON_CMD%
  %PYTHON_CMD% -V

  echo 🐍 Creating venv\ ...
  %PYTHON_CMD% -m venv venv
  if errorlevel 1 goto :error
)

if not exist "%VENV_PY%" goto :error

for /f "tokens=1,2" %%A in ('"%VENV_PY%" -c "import sys; print(sys.version_info[0], sys.version_info[1])"') do (
  set "PY_MAJOR=%%A"
  set "PY_MINOR=%%B"
)
if "%PY_MAJOR%"=="" goto :badpython
if not "%PY_MAJOR%"=="3" goto :badpython
if %PY_MINOR% LSS 8 goto :badpython
if %PY_MINOR% GEQ 13 goto :pytoonew

for /f "delims=" %%A in ('"%VENV_PY%" -c "import platform; print(platform.architecture()[0])"') do set "PY_ARCH=%%A"
if /I not "%PY_ARCH%"=="64bit" goto :py32bit

echo ✅ Using venv: "%VENV_PY%" (v%PY_MAJOR%.%PY_MINOR%, %PY_ARCH%)
"%VENV_PY%" -V
set PYTHONUTF8=1
set PIP_DISABLE_PIP_VERSION_CHECK=1
set "PIP_ARGS=--timeout 120 --retries 3 --prefer-binary"

echo 📦 Upgrading pip ...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel %PIP_ARGS%

echo 📦 Installing dependencies ...
"%VENV_PY%" -m pip install -r requirements.txt %PIP_ARGS%
if errorlevel 1 (
  echo 🔄 Retry with mirror: https://pypi.tuna.tsinghua.edu.cn/simple
  "%VENV_PY%" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn %PIP_ARGS%
  if errorlevel 1 goto :error
)

echo ✅ Verifying imports ...
"%VENV_PY%" -c "import PyQt5; import sqlalchemy; from playwright.sync_api import sync_playwright; print('ok')"
if errorlevel 1 goto :error

if %SKIP_BROWSER%==1 goto :done_browser

if "%PLAYWRIGHT_BROWSERS_PATH%"=="" set "PLAYWRIGHT_BROWSERS_PATH=%USERPROFILE%\\.xhs_system\\ms-playwright"
if "%PLAYWRIGHT_DOWNLOAD_HOST%"=="" set "PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright"

set NEED_BROWSER=0
if %WITH_BROWSER%==1 set NEED_BROWSER=1

if %NEED_BROWSER%==0 (
  call :check_playwright
  set "PW_RC=%ERRORLEVEL%"
  if not "%PW_RC%"=="0" set NEED_BROWSER=1
)

if %NEED_BROWSER%==1 (
  echo 🌐 Installing Playwright Chromium ...
  echo    PLAYWRIGHT_BROWSERS_PATH=%PLAYWRIGHT_BROWSERS_PATH%
  echo    PLAYWRIGHT_DOWNLOAD_HOST=%PLAYWRIGHT_DOWNLOAD_HOST%
  "%VENV_PY%" -m playwright install chromium
  if errorlevel 1 goto :error
)
:done_browser

echo.
echo 🎉 Done.
echo Start:
echo   启动程序.bat
echo   ^(or^) "%VENV_PY%" main.py
exit /b 0

:error
echo.
echo ❌ Install failed.
exit /b 1

:badpython
echo ❌ Python 3.8–3.12 required. Recommended: Python 3.11/3.12 (64-bit).
if exist "%VENV_PY%" (
  "%VENV_PY%" -V
) else if not "%PYTHON_CMD%"=="" (
  %PYTHON_CMD% -V
)
exit /b 1

:pytoonew
echo ❌ Python version too new (v%PY_MAJOR%.%PY_MINOR%). PyQt5/Playwright may not have wheels yet.
echo 💡 Please install Python 3.11/3.12 (64-bit) and re-run install.bat.
if exist "%VENV_PY%" (
  "%VENV_PY%" -V
) else if not "%PYTHON_CMD%"=="" (
  %PYTHON_CMD% -V
)
exit /b 1

:py32bit
echo ❌ Detected 32-bit Python (%PY_ARCH%). PyQt5/Playwright are likely to fail.
echo 💡 Please install 64-bit Python 3.11/3.12 and re-run install.bat.
if exist "%VENV_PY%" (
  "%VENV_PY%" -V
) else if not "%PYTHON_CMD%"=="" (
  %PYTHON_CMD% -V
)
exit /b 1

:check_playwright
set "PW_CHECK_FILE=%TEMP%\\xhs_pw_check_%RANDOM%.py"
> "%PW_CHECK_FILE%" (
  echo import sys
  echo from playwright.sync_api import sync_playwright
  echo
  echo def main^(^) ^-^> int:
  echo ^    with sync_playwright^(^) as p:
  echo ^        try:
  echo ^            b = p.chromium.launch^(headless=True, timeout=30000^)
  echo ^            b.close^(^)
  echo ^            return 0
  echo ^        except Exception as e:
  echo ^            msg = str^(e^)
  echo ^            if "Executable doesn't exist" not in msg and "not found" not in msg.lower^(^) and "找不到" not in msg:
  echo ^                return 1
  echo
  echo ^        for channel in ^("chrome", "msedge"^):
  echo ^            try:
  echo ^                b = p.chromium.launch^(channel=channel, headless=True, timeout=30000^)
  echo ^                b.close^(^)
  echo ^                return 0
  echo ^            except Exception:
  echo ^                pass
  echo
  echo ^    return 2
  echo
  echo if __name__ == "__main__":
  echo ^    sys.exit^(main^(^)^)
)
"%VENV_PY%" "%PW_CHECK_FILE%" >nul 2>&1
set "PW_RC=%ERRORLEVEL%"
del /q "%PW_CHECK_FILE%" >nul 2>&1
exit /b %PW_RC%
