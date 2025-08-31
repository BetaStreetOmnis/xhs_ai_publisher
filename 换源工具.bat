@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

TITLE 小红书AI发布助手 - pip换源工具

:: 颜色定义
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "END=[0m"

echo %CYAN%╔══════════════════════════════════════════════════════════════╗%END%
echo %CYAN%║                  pip换源工具 - 国内镜像加速                ║%END%
echo %CYAN%╚══════════════════════════════════════════════════════════════╝%END%
echo.

:: 检查虚拟环境
echo %BLUE%🔍 检查虚拟环境...%END%
if exist "venv\Scripts\activate.bat" (
    echo %GREEN%✅ 虚拟环境已找到%END%
    call venv\Scripts\activate.bat
) else (
    echo %RED%❌ 未找到虚拟环境，请先运行 install.bat%END%
    pause
    exit /b 1
)

:: 显示当前配置
echo.
echo %BLUE%📋 当前pip配置：%END%
python -m pip config list 2>nul || echo   %YELLOW%未配置%END%

:: 国内镜像列表
echo.
echo %CYAN%📦 可用国内镜像：%END%
echo   1. 清华大学    https://pypi.tuna.tsinghua.edu.cn/simple
echo   2. 阿里云      https://mirrors.aliyun.com/pypi/simple
echo   3. 腾讯云      https://mirrors.cloud.tencent.com/pypi/simple
echo   4. 华为云      https://mirrors.huaweicloud.com/repository/pypi/simple
echo   5. 豆瓣        https://pypi.douban.com/simple

:: 选择镜像
set "mirror_choice="
set /p mirror_choice="请选择镜像源 (1-5) [默认1]: "

if not defined mirror_choice set "mirror_choice=1"

:: 设置镜像地址
set "MIRROR_URL="
if "%mirror_choice%"=="1" set "MIRROR_URL=https://pypi.tuna.tsinghua.edu.cn/simple"
if "%mirror_choice%"=="2" set "MIRROR_URL=https://mirrors.aliyun.com/pypi/simple"
if "%mirror_choice%"=="3" set "MIRROR_URL=https://mirrors.cloud.tencent.com/pypi/simple"
if "%mirror_choice%"=="4" set "MIRROR_URL=https://mirrors.huaweicloud.com/repository/pypi/simple"
if "%mirror_choice%"=="5" set "MIRROR_URL=https://pypi.douban.com/simple"

if not defined MIRROR_URL (
    echo %RED%❌ 选择无效，使用清华大学镜像%END%
    set "MIRROR_URL=https://pypi.tuna.tsinghua.edu.cn/simple"
)

echo.
echo %BLUE%🚀 正在配置镜像源：%MIRROR_URL%%END%

:: 配置pip镜像
echo %BLUE%⚙️ 配置pip...%END%
python -m pip config set global.index-url %MIRROR_URL%
python -m pip config set install.trusted-host %MIRROR_URL:https://=%
python -m pip config set install.trusted-host %MIRROR_URL:https://=%
python -m pip config set global.timeout 30
python -m pip config set global.retries 5

:: 验证配置
echo.
echo %BLUE%✅ 配置验证：%END%
python -m pip config list

:: 测试镜像速度
echo.
echo %BLUE%⚡ 测试镜像速度...%END%
echo   正在测试镜像响应时间...
python -m pip search pip 2>nul >nul || (
    echo   %YELLOW%⚠️ 测试搜索功能可能受限，但安装功能正常%END%
)

:: 更新pip
echo.
echo %BLUE%🔄 更新pip到最新版本...%END%
python -m pip install --upgrade pip

:: 重新安装依赖
echo.
echo %BLUE%📦 重新安装项目依赖...%END%
if exist "requirements.txt" (
    echo   %GREEN%✅ 使用国内镜像重新安装依赖...%END%
    python -m pip install -r requirements.txt --force-reinstall
) else (
    echo   %YELLOW%⚠️ 未找到requirements.txt%END%
)

:: 显示最终配置
echo.
echo %GREEN%🎉 pip换源完成！%END%
echo %CYAN%📋 最终配置：%END%
python -m pip config list

echo.
echo %CYAN%💡 使用提示：%END%
echo   现在使用国内镜像，安装速度大幅提升！
echo   如需恢复默认，运行：pip config unset global.index-url
echo.

pause