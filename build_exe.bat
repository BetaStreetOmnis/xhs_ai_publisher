@echo off
chcp 65001 >nul
echo 🚀 开始打包小红书发文助手...
echo ==================================================

echo 📦 安装PyInstaller...
python -m pip install PyInstaller

echo 🔨 开始构建exe文件...
python -m PyInstaller --onefile --windowed --name="小红书发文助手" --add-data="src;src" --add-data="init_db.py;." --add-data="fix_database.py;." --add-data="check_db.py;." --hidden-import=PyQt6.QtCore --hidden-import=PyQt6.QtGui --hidden-import=PyQt6.QtWidgets --hidden-import=sqlalchemy --hidden-import=sqlalchemy.orm --hidden-import=sqlalchemy.sql --hidden-import=sqlalchemy.pool --hidden-import=sqlalchemy.engine --hidden-import=sqlalchemy.event --hidden-import=sqlalchemy.ext --hidden-import=sqlalchemy.dialects.sqlite --hidden-import=sqlite3 --hidden-import=json --hidden-import=threading --hidden-import=asyncio --hidden-import=concurrent.futures --hidden-import=requests --hidden-import=playwright --hidden-import=PIL --hidden-import=PIL.Image --hidden-import=PIL.ImageDraw --hidden-import=PIL.ImageFont --hidden-import=openai --hidden-import=dotenv main.py

if %errorlevel% equ 0 (
    echo ✅ exe文件构建完成！
    echo ==================================================
    echo 📂 输出目录: dist/
    echo 🚀 可执行文件: 小红书发文助手.exe
    echo.
    echo 🎉 打包成功！请查看dist目录
) else (
    echo ❌ 打包失败！
)

pause 