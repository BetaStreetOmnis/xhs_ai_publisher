@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

TITLE 小红书AI发布助手 - 国内镜像安装

:: 颜色定义
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "END=[0m"

:: 国内镜像配置
set "MIRROR_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple"
set "MIRROR_ALIYUN=https://mirrors.aliyun.com/pypi/simple"
set "MIRROR_TENCENT=https://mirrors.cloud.tencent.com/pypi/simple"

:: 显示横幅
echo %CYAN%╔══════════════════════════════════════════════════════════════╗%END%
echo %CYAN%║              小红书AI发布助手 - 国内镜像安装                ║%END%
echo %CYAN%║                   高速下载 稳定可靠                        ║%END%
echo %CYAN%╚══════════════════════════════════════════════════════════════╝%END%
echo.

:: 获取脚本目录
cd /d "%~dp0"

:: 检查项目文件完整性
echo %BLUE%🔍 检查项目文件...%END%
for %%f in (main.py requirements.txt deploy.py) do (
    if not exist "%%f" (
        echo %RED%❌ 缺少文件: %%f%END%
        echo %YELLOW%💡 请确保下载完整项目%END%
        pause
        exit /b 1
    )
)
echo %GREEN%✅ 项目文件完整%END%
echo.

:: 检测Python环境（使用国内镜像检测）
echo %BLUE%🔍 检测Python环境...%END%
set "PYTHON_CMD="
for %%p in (python python3 py) do (
    where %%p >nul 2>&1
    if !errorlevel! equ 0 (
        %%p --version >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_CMD=%%p"
            goto :python_found
        )
    )
)

if not defined PYTHON_CMD (
    echo %YELLOW%⚠️ 未找到Python，建议先安装Python 3.8+%END%
    echo %BLUE%💡 下载地址: https://www.python.org/downloads/windows/%END%
    echo %BLUE%💡 或使用国内镜像: https://mirrors.huaweicloud.com/python/%END%
    pause
    exit /b 1
)

:python_found
echo %GREEN%✅ 找到Python: %PYTHON_CMD%%END%
%PYTHON_CMD% --version
echo.

:: 创建虚拟环境
echo %BLUE%🐍 创建虚拟环境...%END%
if exist "venv" (
    echo %YELLOW%⚠️ 检测到现有虚拟环境，正在清理...%END%
    rd /s /q "venv" 2>nul
    timeout /t 2 /nobreak >nul
)

%PYTHON_CMD% -m venv venv
if !errorlevel! neq 0 (
    echo %RED%❌ 虚拟环境创建失败%END%
    pause
    exit /b 1
)
echo %GREEN%✅ 虚拟环境创建成功%END%
echo.

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 配置pip国内镜像
echo %BLUE%⚙️ 配置pip国内镜像...%END%
python -m pip config set global.index-url %MIRROR_INDEX%
python -m pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn
python -m pip config set global.timeout 60
python -m pip config set global.retries 3
echo %GREEN%✅ pip镜像配置完成%END%

:: 更新pip
echo %BLUE%🔄 更新pip到最新版本...%END%
python -m pip install --upgrade pip
echo.

:: 安装依赖（使用国内镜像）
echo %BLUE%📦 开始安装依赖...%END%
echo %CYAN%使用国内镜像加速下载...%END%
python -m pip install -r requirements.txt --timeout 120

if !errorlevel! neq 0 (
    echo %YELLOW%⚠️ 主镜像安装失败，尝试备用镜像...%END%
    
    :: 尝试阿里云镜像
    echo %BLUE%🔄 尝试阿里云镜像...%END%
    python -m pip config set global.index-url %MIRROR_ALIYUN%
    python -m pip config set install.trusted-host mirrors.aliyun.com
    python -m pip install -r requirements.txt --timeout 120
    
    if !errorlevel! neq 0 (
        echo %YELLOW%⚠️ 阿里云镜像失败，尝试腾讯云镜像...%END%
        
        :: 尝试腾讯云镜像
        echo %BLUE%🔄 尝试腾讯云镜像...%END%
        python -m pip config set global.index-url %MIRROR_TENCENT%
        python -m pip config set install.trusted-host mirrors.cloud.tencent.com
        python -m pip install -r requirements.txt --timeout 120
        
        if !errorlevel! neq 0 (
            echo %RED%❌ 所有镜像安装失败%END%
            echo %YELLOW%💡 解决方案：%END%
            echo   1. 检查网络连接
            echo   2. 关闭杀毒软件重试
            echo   3. 手动安装: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
            pause
            exit /b 1
        )
    )
)

echo %GREEN%✅ 依赖安装完成%END%
echo.

:: 安装Playwright浏览器
echo %BLUE%🌐 安装Playwright浏览器...%END%
python -m playwright install chromium
echo %GREEN%✅ Playwright浏览器安装完成%END%
echo.

:: 运行部署脚本
echo %BLUE%🚀 运行部署脚本...%END%
python deploy.py

if !errorlevel! neq 0 (
    echo %RED%❌ 部署脚本运行失败%END%
    pause
    exit /b 1
)

echo.
echo %GREEN%🎉 国内镜像安装完成！%END%
echo.
echo %CYAN%📋 安装摘要：%END%
echo   ✅ 使用国内镜像加速安装
echo   ✅ 虚拟环境已配置
echo   ✅ 所有依赖已安装
echo   ✅ Playwright浏览器已安装
echo.
echo %CYAN%💡 启动方式：%END%
echo   1. 双击运行 启动程序_优化版.bat
echo   2. 或使用 快速启动.bat
echo.
echo %CYAN%📞 遇到问题：%END%
echo   运行 诊断工具.bat 获取帮助
echo   运行 修复工具.bat 自动修复

echo.
pause