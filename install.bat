@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo.
echo ==========================================
echo   小红书AI发布助手 - 一键安装
echo ==========================================
echo.

REM 检查项目文件
if not exist "main.py" (
    echo 错误: 请在项目根目录中运行此脚本
    echo 项目根目录应包含 main.py 和 deploy.py 文件
    pause
    exit /b 1
)

if not exist "deploy.py" (
    echo 错误: 找不到 deploy.py 文件
    echo 项目根目录应包含 main.py 和 deploy.py 文件
    pause
    exit /b 1
)

REM 检测Python环境
echo 检测Python环境...
set PYTHON_CMD=
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYTHON_CMD=python
    echo 找到Python: python
) else (
    python3 --version >nul 2>&1
    if !errorlevel! equ 0 (
        set PYTHON_CMD=python3
        echo 找到Python: python3
    ) else (
        py --version >nul 2>&1
        if !errorlevel! equ 0 (
            set PYTHON_CMD=py
            echo 找到Python: py
        )
    )
)

if "!PYTHON_CMD!"=="" (
    echo 错误: 未找到Python环境
    echo 请安装Python 3.8+: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查pip
echo 检查pip工具...
!PYTHON_CMD! -m pip --version >nul 2>&1
if !errorlevel! neq 0 (
    echo 错误: pip工具不可用
    pause
    exit /b 1
)

echo pip工具可用

REM 运行Python部署脚本
echo 开始运行部署脚本...
!PYTHON_CMD! deploy.py

if !errorlevel! equ 0 (
    echo.
    echo 安装完成！
    echo 启动程序: 双击运行 "启动程序.bat"
) else (
    echo 安装过程中出现错误
)

echo.
pause