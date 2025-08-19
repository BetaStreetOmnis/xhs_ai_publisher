@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 小红书AI发布助手 - Windows启动脚本

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 颜色定义
set "GREEN=[92m"
set "BLUE=[94m"
set "RED=[91m"
set "YELLOW=[93m"
set "END=[0m"

echo %BLUE%🚀 启动小红书AI发布助手...%END%
echo.

:: 检查虚拟环境
if not exist "venv" (
    echo %RED%❌ 虚拟环境不存在，请先运行安装脚本%END%
    echo %YELLOW%💡 请运行 install.bat%END%
    pause
    exit /b 1
)

:: 检查main.py
if not exist "main.py" (
    echo %RED%❌ main.py文件不存在%END%
    pause
    exit /b 1
)

:: 激活虚拟环境并启动程序
call venv\Scripts\activate.bat
python main.py

echo.
echo %GREEN%✅ 程序已退出%END%
pause