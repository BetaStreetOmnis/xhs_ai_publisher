@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 小红书AI发布助手 - 一键安装脚本 (Windows)
:: 自动检测和安装Python环境，无需用户预先安装Python

:: 颜色定义 (Windows 10+ 支持ANSI颜色)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "PURPLE=[95m"
set "CYAN=[96m"
set "WHITE=[97m"
set "BOLD=[1m"
set "END=[0m"

:: 项目信息
set "PROJECT_NAME=小红书AI发布助手"
set "MIN_PYTHON_VERSION=3.8"
set "REQUIRED_PYTHON_VERSION=3.9"
set "PYTHON_CMD="
set "PYTHON_VERSION="

:: 启用ANSI颜色支持 (Windows 10+)
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

goto :main

:: 打印横幅
:print_banner
echo %CYAN%%BOLD%
echo ╔══════════════════════════════════════════════════════════╗
echo ║              🌟 小红书AI发布助手 - 一键安装             ║
echo ║                                                          ║
echo ║  🔍 自动检测Python环境                                   ║
echo ║  📦 自动安装所需依赖                                     ║
echo ║  🚀 一键完成所有配置                                     ║
echo ╚══════════════════════════════════════════════════════════╝
echo %END%
echo.
echo %GREEN%✅ 检测到 Windows 系统%END%
echo.
goto :eof

:: 检查Python版本
:check_python_version
set "cmd=%~1"
%cmd% --version >nul 2>&1
if !errorlevel! neq 0 (
    exit /b 1
)

for /f "tokens=2" %%i in ('%cmd% --version 2^>^&1') do (
    set "version=%%i"
    for /f "tokens=1,2 delims=." %%a in ("!version!") do (
        set "major=%%a"
        set "minor=%%b"
        set /a "version_num=!major!*10+!minor!"
        if !version_num! geq 38 (
            set "PYTHON_VERSION=!major!.!minor!"
            exit /b 0
        )
    )
)
exit /b 1

:: 检测Python环境
:detect_python
echo %BLUE%🔍 检测Python环境...%END%

:: 检测可能的Python命令
set "python_commands=python python3 py"
set "found_python="

for %%i in (%python_commands%) do (
    call :check_python_version "%%i"
    if !errorlevel! equ 0 (
        echo   发现: %%i (版本 !PYTHON_VERSION!)
        if "!found_python!"=="" (
            set "found_python=%%i"
            set "PYTHON_CMD=%%i"
        )
    )
)

if not "!found_python!"=="" (
    echo %GREEN%✅ 找到合适的Python: !PYTHON_CMD! (版本 !PYTHON_VERSION!)%END%
    exit /b 0
) else (
    echo %YELLOW%⚠️ 未找到合适的Python环境 (需要 >= %MIN_PYTHON_VERSION%)%END%
    exit /b 1
)

:: 下载文件
:download_file
set "url=%~1"
set "output=%~2"

echo %BLUE%📥 下载: %output%...%END%

:: 尝试使用PowerShell下载
powershell -Command "try { Invoke-WebRequest -Uri '%url%' -OutFile '%output%' -UseBasicParsing } catch { exit 1 }" >nul 2>&1
if !errorlevel! equ 0 (
    echo %GREEN%✅ 下载成功%END%
    exit /b 0
)

:: 尝试使用curl下载
curl -L -o "%output%" "%url%" >nul 2>&1
if !errorlevel! equ 0 (
    echo %GREEN%✅ 下载成功%END%
    exit /b 0
)

:: 尝试使用certutil下载
certutil -urlcache -split -f "%url%" "%output%" >nul 2>&1
if !errorlevel! equ 0 (
    echo %GREEN%✅ 下载成功%END%
    exit /b 0
)

echo %RED%❌ 下载失败%END%
exit /b 1

:: 安装Python
:install_python
echo %BLUE%🚀 开始安装Python环境...%END%

:: 检查Windows版本
for /f "tokens=4-5 delims=. " %%i in ('ver') do set "version=%%i.%%j"
echo 检测到Windows版本: %version%

:: 设置Python下载URL (根据系统架构)
if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    set "python_url=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    set "python_installer=python-3.11.9-amd64.exe"
) else (
    set "python_url=https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe"
    set "python_installer=python-3.11.9.exe"
)

echo %BLUE%📥 下载Python安装包...%END%
call :download_file "!python_url!" "!python_installer!"
if !errorlevel! neq 0 (
    echo %RED%❌ Python下载失败%END%
    echo %BLUE%💡 请手动下载安装Python:
    echo    https://www.python.org/downloads/windows/%END%
    pause
    exit /b 1
)

echo %BLUE%📦 安装Python (这可能需要几分钟)...%END%
echo %YELLOW%⚠️ 请在安装向导中勾选 "Add Python to PATH"%END%

:: 静默安装Python
"!python_installer!" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if !errorlevel! neq 0 (
    echo %YELLOW%⚠️ 静默安装失败，启动图形安装程序...%END%
    "!python_installer!"
    echo %BLUE%💡 请手动安装Python，完成后按任意键继续...%END%
    pause
)

:: 清理安装包
del "!python_installer!" >nul 2>&1

:: 刷新环境变量
echo %BLUE%🔄 刷新环境变量...%END%
call :refresh_env

:: 验证安装
call :detect_python
if !errorlevel! equ 0 (
    echo %GREEN%✅ Python安装成功%END%
    exit /b 0
) else (
    echo %RED%❌ Python安装失败%END%
    echo %BLUE%💡 请尝试：%END%
    echo 1. 重新启动命令提示符
    echo 2. 手动将Python添加到PATH环境变量
    echo 3. 从 https://www.python.org/downloads/ 重新下载安装
    pause
    exit /b 1
)

:: 刷新环境变量
:refresh_env
:: 重新加载PATH环境变量
for /f "usebackq tokens=2,*" %%A in (`reg query HKCU\Environment /v PATH 2^>nul`) do set "UserPath=%%B"
for /f "usebackq tokens=2,*" %%A in (`reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul`) do set "SystemPath=%%B"
set "PATH=%SystemPath%;%UserPath%"
goto :eof

:: 检查pip
:check_pip
echo %BLUE%🔍 检查pip工具...%END%

%PYTHON_CMD% -m pip --version >nul 2>&1
if !errorlevel! equ 0 (
    echo %GREEN%✅ pip工具可用%END%
    exit /b 0
) else (
    echo %YELLOW%⚠️ pip工具不可用，尝试安装...%END%
    
    :: 下载get-pip.py
    call :download_file "https://bootstrap.pypa.io/get-pip.py" "get-pip.py"
    if !errorlevel! neq 0 (
        echo %RED%❌ 无法下载pip安装脚本%END%
        exit /b 1
    )
    
    :: 安装pip
    %PYTHON_CMD% get-pip.py
    if !errorlevel! equ 0 (
        echo %GREEN%✅ pip安装成功%END%
        del get-pip.py >nul 2>&1
        exit /b 0
    ) else (
        echo %RED%❌ pip安装失败%END%
        del get-pip.py >nul 2>&1
        exit /b 1
    )
)

:: 运行Python部署脚本
:run_python_deployment
echo %BLUE%🚀 开始运行部署脚本...%END%

:: 确保deploy.py存在
if not exist "deploy.py" (
    echo %RED%❌ 找不到deploy.py文件%END%
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

:: 运行Python部署脚本
%PYTHON_CMD% deploy.py
exit /b !errorlevel!

:: 主函数
:main
call :print_banner

:: 检查项目文件
if not exist "main.py" (
    echo %RED%❌ 请在项目根目录中运行此脚本%END%
    echo 项目根目录应包含 main.py 和 deploy.py 文件
    pause
    exit /b 1
)

if not exist "deploy.py" (
    echo %RED%❌ 请在项目根目录中运行此脚本%END%
    echo 项目根目录应包含 main.py 和 deploy.py 文件
    pause
    exit /b 1
)

:: 检测Python环境
call :detect_python
if !errorlevel! equ 0 (
    echo %GREEN%✅ Python环境检查通过%END%
) else (
    echo %YELLOW%⚠️ 需要安装Python环境%END%
    echo %BLUE%💡 是否自动安装Python? (y/n)%END%
    set /p "install_choice=请选择: "
    
    if /i "!install_choice!"=="y" (
        call :install_python
        if !errorlevel! neq 0 exit /b 1
    ) else (
        echo %YELLOW%请手动安装Python 3.8+后重新运行此脚本%END%
        echo 下载地址: https://www.python.org/downloads/windows/
        pause
        exit /b 1
    )
)

:: 检查pip
call :check_pip
if !errorlevel! neq 0 exit /b 1

:: 运行Python部署脚本
call :run_python_deployment
if !errorlevel! equ 0 (
    echo.
    echo %GREEN%%BOLD%🎉 安装完成！%END%
    echo %BLUE%💡 启动程序: 双击运行 "启动程序.bat"%END%
) else (
    echo %RED%❌ 安装过程中出现错误%END%
)

echo.
pause
goto :eof