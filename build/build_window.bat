@echo off
chcp 65001 >nul

:: 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo Python未安装，请先安装Python
    pause
    exit /b
)

:: 检查并安装必要的包
echo 检查并安装必要的包...

:: 检查 playwright 是否安装
pip show playwright >nul 2>&1
if errorlevel 1 (
    echo 正在安装 playwright...
    pip install playwright
    playwright install
)

:: 检查 pyinstaller 是否安装
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 正在安装 pyinstaller...
    pip install pyinstaller
)

:: 检查 certifi 是否安装 
pip show certifi >nul 2>&1
if errorlevel 1 (
    echo 正在安装 certifi...
    pip install certifi
)

:: 检查文件是否存在
if not exist "icon.png" (
    echo icon.png 文件不存在
    pause
    exit /b
)

if not exist "create_ico.py" (
    echo create_ico.py 文件不存在
    pause
    exit /b
)

python create_ico.py

:: 清理之前的构建
rmdir /s /q build dist
rmdir /s /q temp_build

:: 创建临时目录
mkdir temp_build

:: 获取 Python 证书路径
for /f "tokens=*" %%i in ('python -c "import certifi; print(certifi.where())"') do set CERT_PATH=%%i

:: 打包命令
pyinstaller ^
    --workpath temp_build ^
    --distpath dist ^
    --clean ^
    --onefile ^
    --noconsole ^
    --name "XhsAi" ^
    --icon icon.png ^
    --add-data "%CERT_PATH%;certifi" ^
    --paths "%SITE_PACKAGES%" ^
    --collect-submodules src ^
    --hidden-import imaplib ^
    --hidden-import playwright ^
    --hidden-import playwright.sync_api ^
    --hidden-import playwright._impl._driver ^
    --hidden-import playwright.async_api ^
    --add-data "%LOCALAPPDATA%\ms-playwright\chromium-*;ms-playwright" ^
    ../main.py

:: 打包完成后清理临时文件
rmdir /s /q temp_build
rmdir /s /q build 

:: 添加暂停以查看错误信息
echo 打包完成,按任意键继续...
pause