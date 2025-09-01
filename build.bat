@echo off
title 小红书发文助手 - Windows打包工具
color 0A
echo.
echo ================================================
echo     小红书发文助手 - Windows EXE打包工具
echo ================================================
echo.

REM 检查Python是否安装
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ 未检测到Python，请先安装Python 3.8或更高版本
    echo 📥 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python环境检测通过

REM 安装依赖
echo 📦 正在安装打包依赖...
pip install -r requirements-build.txt
if errorlevel 1 (
    echo ❌ 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)

echo ✅ 依赖安装完成

REM 开始打包
echo 🏗️ 开始构建Windows可执行文件...
python build.py

if errorlevel 1 (
    echo ❌ 打包失败
    pause
    exit /b 1
)

echo.
echo 🎉 打包完成！
echo 📁 可执行文件位置: dist\小红书发文助手.exe
echo 📦 分发包: 小红书发文助手_Windows.zip
echo.
echo 💡 使用方法:
echo    1. 运行 dist\install_windows.bat 创建桌面快捷方式
echo    2. 或者直接运行 dist\小红书发文助手.exe
echo.
pause