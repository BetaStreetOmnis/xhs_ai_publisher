#!/usr/bin/env python3
"""
小红书发文助手 - EXE打包脚本
一键打包为Windows可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_environment():
    """检查打包环境"""
    print("🔍 检查打包环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ Python版本过低，需要Python 3.8或更高版本")
        return False
    
    # 检查必需模块
    required_modules = [
        'PyInstaller',
        'PyQt5',
        'requests',
        'cryptography'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module.lower().replace('-', '_'))
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ 缺少必需模块: {', '.join(missing_modules)}")
        print("📦 请运行: pip install " + " ".join(missing_modules))
        return False
    
    print("✅ 环境检查通过")
    return True

def prepare_build_environment():
    """准备构建环境"""
    print("🛠️ 准备构建环境...")
    
    # 创建构建目录
    build_dir = Path("build")
    dist_dir = Path("dist")
    
    # 清理旧的构建文件
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    # 创建必要的目录
    build_dir.mkdir(exist_ok=True)
    (build_dir / "icon").mkdir(exist_ok=True)
    
    # 检查并创建图标文件
    icon_path = build_dir / "icon.png"
    if not icon_path.exists():
        # 创建默认图标文件
        try:
            from PIL import Image, ImageDraw
            
            # 创建512x512的图标
            img = Image.new('RGBA', (512, 512), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # 绘制小红书风格图标
            draw.ellipse([50, 50, 462, 462], fill='#FF2442', outline='#FF2442')
            draw.ellipse([150, 150, 362, 362], fill='white', outline='white')
            
            # 保存图标
            img.save(str(icon_path))
            print("✅ 已创建默认图标文件")
        except ImportError:
            print("⚠️  无法创建图标，将使用系统默认图标")
    
    print("✅ 构建环境准备完成")

def build_windows_exe():
    """构建Windows可执行文件"""
    print("🏗️ 开始构建Windows可执行文件...")
    
    # PyInstaller命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=小红书发文助手",
        "--onefile",
        "--windowed",
        "--icon=build/icon.png",
        "--clean",
        "--noconfirm",
        "--add-data=src;src",
        "--add-data=templates;templates",
        "--add-data=assets;assets",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.QtNetwork",
        "--hidden-import=src.core.pages.simple_backend_config",
        "--hidden-import=src.core.scheduler.schedule_manager",
        "--hidden-import=src.core.database_manager",
        "--hidden-import=src.logger.logger",
        "--collect-all=PyQt5",
        "--collect-all=requests",
        "--collect-all=cryptography",
        "main.py"
    ]
    
    try:
        # 执行打包命令
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Windows可执行文件构建完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        print("📋 错误输出:")
        print(e.stderr)
        return False

def build_mac_app():
    """构建macOS应用程序"""
    print("🏗️ 开始构建macOS应用程序...")
    
    # macOS专用打包命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=小红书发文助手",
        "--windowed",
        "--icon=build/icon.png",
        "--clean",
        "--noconfirm",
        "--osx-bundle-identifier=com.xhs.poster",
        "--add-data=src:src",
        "--add-data=templates:templates",
        "--add-data=assets:assets",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.QtNetwork",
        "--collect-all=PyQt5",
        "--collect-all=requests",
        "--collect-all=cryptography",
        "main.py"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ macOS应用程序构建完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 构建失败: {e}")
        print("📋 错误输出:")
        print(e.stderr)
        return False

def create_installer_script():
    """创建安装脚本"""
    print("📦 创建安装脚本...")
    
    # Windows安装脚本
    install_bat = """@echo off
echo 小红书发文助手安装程序
echo =========================
echo.
echo 正在安装小红书发文助手...

REM 创建桌面快捷方式
set SCRIPT_DIR=%~dp0
set EXE_PATH=%SCRIPT_DIR%小红书发文助手.exe
set DESKTOP=%USERPROFILE%\Desktop
set SHORTCUT=%DESKTOP%\小红书发文助手.lnk

REM 使用PowerShell创建快捷方式
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%EXE_PATH%'; $Shortcut.Save()"

echo.
echo 安装完成！
echo 桌面已创建快捷方式
pause
"""

    # macOS安装脚本
    install_sh = """#!/bin/bash
echo "小红书发文助手安装程序"
echo "====================="
echo

echo "正在安装小红书发文助手..."

# 复制到应用程序目录
APP_NAME="小红书发文助手.app"
SOURCE_DIR="$(dirname "$0")"
TARGET_DIR="/Applications"

if [ -d "$SOURCE_DIR/$APP_NAME" ]; then
    cp -r "$SOURCE_DIR/$APP_NAME" "$TARGET_DIR/"
    echo "应用程序已安装到: $TARGET_DIR/$APP_NAME"
else
    echo "错误: 找不到应用程序包"
    exit 1
fi

echo "安装完成！"
echo "您可以在应用程序文件夹中找到小红书发文助手"
read -p "按回车键退出..."
"""

    # 保存安装脚本
    with open("dist/install_windows.bat", "w", encoding="gbk") as f:
        f.write(install_bat)
    
    with open("dist/install_mac.sh", "w", encoding="utf-8") as f:
        f.write(install_sh)
    
    # 设置macOS脚本权限
    if sys.platform == "darwin":
        os.chmod("dist/install_mac.sh", 0o755)
    
    print("✅ 安装脚本创建完成")

def package_distribution():
    """打包分发文件"""
    print("📦 打包分发文件...")
    
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ 构建目录不存在")
        return
    
    # 根据平台创建不同的包
    if sys.platform == "win32":
        # Windows ZIP包
        import zipfile
        with zipfile.ZipFile("小红书发文助手_Windows.zip", "w", zipfile.ZIP_DEFLATED) as zf:
            for file in dist_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(dist_dir))
        print("✅ Windows ZIP包创建完成")
    
    elif sys.platform == "darwin":
        # macOS DMG包
        try:
            import dmgbuild
            
            # 创建DMG配置
            dmg_config = {
                "title": "小红书发文助手",
                "icon": "build/icon.png",
                "background": None,
                "format": "UDZO",
                "compression_level": 9,
                "window_rect": ((100, 100), (500, 400)),
                "icon_size": 128,
                "text_size": 16,
                "include_icon_view_settings": "auto",
                "include_list_view_settings": "auto",
                "arrange_by": None,
                "grid_offset": (0, 0),
                "grid_spacing": 100,
                "scroll_position": (0, 0),
                "label_pos": "bottom",
                "text_color": "#000000",
                "background_color": "#FFFFFF",
                "items": [
                    {
                        "type": "file",
                        "path": "dist/小红书发文助手.app",
                        "position": (200, 200),
                        "name": "小红书发文助手"
                    },
                    {
                        "type": "link",
                        "path": "/Applications",
                        "position": (300, 200),
                        "name": "应用程序"
                    }
                ]
            }
            
            # 创建DMG
            dmgbuild.build_dmg("小红书发文助手_macOS.dmg", "小红书发文助手", dmg_config)
            print("✅ macOS DMG包创建完成")
            
        except ImportError:
            # 如果没有dmgbuild，使用简单压缩
            import tarfile
            with tarfile.open("小红书发文助手_macOS.tar.gz", "w:gz") as tar:
                tar.add("dist", arcname="小红书发文助手")
            print("✅ macOS压缩包创建完成")
    
    else:
        # Linux压缩包
        import tarfile
        with tarfile.open("小红书发文助手_Linux.tar.gz", "w:gz") as tar:
            tar.add("dist", arcname="小红书发文助手")
        print("✅ Linux压缩包创建完成")

def main():
    """主函数"""
    print("🚀 小红书发文助手 - EXE打包工具")
    print("=" * 50)
    
    # 检查环境
    if not check_environment():
        return 1
    
    # 准备环境
    prepare_build_environment()
    
    # 根据平台构建
    if sys.platform == "win32":
        success = build_windows_exe()
    elif sys.platform == "darwin":
        success = build_mac_app()
    else:
        print("⚠️  当前平台暂不支持自动打包，请手动配置")
        return 1
    
    if success:
        # 创建安装脚本
        create_installer_script()
        
        # 打包分发
        package_distribution()
        
        print("\n🎉 打包完成！")
        print("📁 输出目录: dist/")
        print("📦 分发包: 当前目录下的压缩文件")
        return 0
    else:
        print("❌ 打包失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())