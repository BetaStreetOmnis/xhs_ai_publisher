@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 小红书AI发布助手 - Windows一键安装脚本
:: 完整的自动化安装解决方案

:: 颜色定义
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "BOLD=[1m"
set "END=[0m"

:: 项目信息
set "PROJECT_NAME=小红书AI发布助手"
set "MIN_PYTHON_VERSION=3.8"
set "PYTHON_CMD="
set "PYTHON_VERSION="

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: 启用ANSI颜色支持
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

goto :main

:: 打印横幅
:print_banner
echo %CYAN%%BOLD%
echo ╔══════════════════════════════════════════════════════════╗
echo ║            💻 小红书AI发布助手 - Windows安装           ║
echo ║                                                          ║
echo ║  🔍 自动检测并安装Python环境                             ║
echo ║  📦 自动配置虚拟环境和依赖                               ║
echo ║  🚀 一键完成所有配置                                     ║
echo ║  🌟 专为Windows优化                                     ║
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

:: 安装Python
:install_python
echo %BLUE%🐍 安装Python...%END%
echo %YELLOW%💡 即将打开Python官网下载页面%END%
echo %BLUE%请下载Python 3.11或更高版本，安装时务必勾选 "Add Python to PATH"%END%
echo.
pause
start https://www.python.org/downloads/windows/
echo.
echo %BLUE%Python安装完成后，请重新运行此脚本%END%
pause
exit /b 1

:: 创建虚拟环境
:create_virtual_env
echo %BLUE%🏗️ 创建虚拟环境...%END%

:: 删除旧的虚拟环境
if exist "venv" (
    echo %YELLOW%⚠️ 发现旧的虚拟环境，正在删除...%END%
    rmdir /s /q "venv" >nul 2>&1
)

:: 创建新的虚拟环境
%PYTHON_CMD% -m venv venv
if !errorlevel! neq 0 (
    echo %RED%❌ 虚拟环境创建失败%END%
    exit /b 1
)

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 升级pip
echo %BLUE%🔄 升级pip...%END%
python -m pip install --upgrade pip

echo %GREEN%✅ 虚拟环境创建成功%END%
exit /b 0

:: 安装依赖
:install_dependencies
echo %BLUE%📦 安装项目依赖...%END%

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 检查requirements.txt
if not exist "requirements.txt" (
    echo %RED%❌ 找不到requirements.txt文件%END%
    exit /b 1
)

:: 安装依赖
python -m pip install -r requirements.txt
if !errorlevel! neq 0 (
    echo %RED%❌ 依赖安装失败%END%
    exit /b 1
)

echo %GREEN%✅ 依赖安装完成%END%
exit /b 0

:: 初始化数据库
:initialize_database
echo %BLUE%🗄️ 初始化数据库...%END%

call venv\Scripts\activate.bat

:: 检查并运行数据库初始化
if exist "init_db.py" (
    echo %BLUE%🔄 运行数据库初始化脚本...%END%
    python init_db.py
)

echo %GREEN%✅ 数据库初始化完成%END%
exit /b 0

:: 创建启动脚本
:create_launch_script
echo %BLUE%📝 创建启动脚本...%END%

:: 创建Windows启动脚本
echo @echo off > start_windows.bat
echo chcp 65001 ^>nul >> start_windows.bat
echo. >> start_windows.bat
echo :: 小红书AI发布助手 - Windows启动脚本 >> start_windows.bat
echo. >> start_windows.bat
echo :: 获取脚本所在目录 >> start_windows.bat
echo set "SCRIPT_DIR=%%~dp0" >> start_windows.bat
echo cd /d "%%SCRIPT_DIR%%" >> start_windows.bat
echo. >> start_windows.bat
echo :: 颜色定义 >> start_windows.bat
echo set "GREEN=[92m" >> start_windows.bat
echo set "BLUE=[94m" >> start_windows.bat
echo set "RED=[91m" >> start_windows.bat
echo set "END=[0m" >> start_windows.bat
echo. >> start_windows.bat
echo echo %%BLUE%%🚀 启动小红书AI发布助手...%%END%% >> start_windows.bat
echo. >> start_windows.bat
echo :: 检查虚拟环境 >> start_windows.bat
echo if not exist "venv" ^( >> start_windows.bat
echo     echo %%RED%%❌ 虚拟环境不存在，请先运行 install_windows.bat%%END%% >> start_windows.bat
echo     pause >> start_windows.bat
echo     exit /b 1 >> start_windows.bat
echo ^) >> start_windows.bat
echo. >> start_windows.bat
echo :: 检查main.py >> start_windows.bat
echo if not exist "main.py" ^( >> start_windows.bat
echo     echo %%RED%%❌ main.py文件不存在%%END%% >> start_windows.bat
echo     pause >> start_windows.bat
echo     exit /b 1 >> start_windows.bat
echo ^) >> start_windows.bat
echo. >> start_windows.bat
echo :: 激活虚拟环境并启动程序 >> start_windows.bat
echo call venv\Scripts\activate.bat >> start_windows.bat
echo python main.py >> start_windows.bat
echo. >> start_windows.bat
echo echo %%GREEN%%✅ 程序已退出%%END%% >> start_windows.bat
echo pause >> start_windows.bat

echo %GREEN%✅ 启动脚本创建完成: start_windows.bat%END%
exit /b 0

:: 主函数
:main
call :print_banner

:: 检查项目文件
if not exist "main.py" (
    echo %RED%❌ 请在项目根目录中运行此脚本%END%
    echo 项目根目录应包含 main.py 文件
    pause
    exit /b 1
)

:: 检测Python环境
call :detect_python
if !errorlevel! neq 0 (
    echo %YELLOW%⚠️ 需要安装Python环境%END%
    echo %BLUE%💡 是否打开Python下载页面? (y/n)%END%
    set /p "install_choice=请选择: "
    
    if /i "!install_choice!"=="y" (
        call :install_python
        exit /b 1
    ) else (
        echo %YELLOW%请手动安装Python 3.8+后重新运行此脚本%END%
        pause
        exit /b 1
    )
)

:: 创建虚拟环境
call :create_virtual_env
if !errorlevel! neq 0 exit /b 1

:: 安装依赖
call :install_dependencies
if !errorlevel! neq 0 exit /b 1

:: 初始化数据库
call :initialize_database

:: 创建启动脚本
call :create_launch_script

echo.
echo %GREEN%%BOLD%🎉 Windows安装完成！%END%
echo.
echo %BLUE%💡 使用方法：%END%
echo    启动程序: %CYAN%start_windows.bat%END%
echo    重新安装: %CYAN%install_windows.bat%END%
echo.
echo %YELLOW%📝 注意事项：%END%
echo    • 首次运行可能需要配置浏览器驱动
echo    • 请确保网络连接正常
echo    • 如遇问题请查看项目文档
echo.
pause
goto :eof

:: 错误处理
:error
echo %RED%❌ 安装过程中出现错误%END%
pause
exit /b 1