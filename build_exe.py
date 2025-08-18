#!/usr/bin/env python3
"""
打包exe文件的脚本
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_requirements():
    """安装必要的依赖"""
    print("📦 安装打包依赖...")
    
    # 安装PyInstaller
    try:
        import PyInstaller
        print("✅ PyInstaller已安装")
    except ImportError:
        print("📥 安装PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "PyInstaller"], check=True)
    
    # 安装项目依赖
    print("📥 安装项目依赖...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

def create_spec_file():
    """创建PyInstaller配置文件"""
    print("📝 创建PyInstaller配置文件...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src', 'src'),
        ('init_db.py', '.'),
        ('fix_database.py', '.'),
        ('check_db.py', '.'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'sqlalchemy',
        'sqlalchemy.orm',
        'sqlalchemy.sql',
        'sqlalchemy.pool',
        'sqlalchemy.engine',
        'sqlalchemy.event',
        'sqlalchemy.ext',
        'sqlalchemy.dialects.sqlite',
        'sqlite3',
        'json',
        'threading',
        'asyncio',
        'concurrent.futures',
        'requests',
        'playwright',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'openai',
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='小红书发文助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='build/icon.ico' if os.path.exists('build/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='小红书发文助手',
)
'''
    
    with open('xiaohongshu.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ 配置文件创建完成")

def build_exe():
    """构建exe文件"""
    print("🔨 开始构建exe文件...")
    
    # 使用spec文件构建
    if os.path.exists('xiaohongshu.spec'):
        print("📋 使用spec文件构建...")
        subprocess.run([
            sys.executable, "-m", "PyInstaller", 
            "--clean", "xiaohongshu.spec"
        ], check=True)
    else:
        print("📋 使用默认配置构建...")
        subprocess.run([
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--name=小红书发文助手",
            "--add-data=src;src",
            "--add-data=init_db.py;.",
            "--add-data=fix_database.py;.",
            "--add-data=check_db.py;.",
            "--hidden-import=PyQt6.QtCore",
            "--hidden-import=PyQt6.QtGui",
            "--hidden-import=PyQt6.QtWidgets",
            "--hidden-import=sqlalchemy",
            "--hidden-import=sqlalchemy.orm",
            "--hidden-import=sqlalchemy.sql",
            "--hidden-import=sqlalchemy.pool",
            "--hidden-import=sqlalchemy.engine",
            "--hidden-import=sqlalchemy.event",
            "--hidden-import=sqlalchemy.ext",
            "--hidden-import=sqlalchemy.dialects.sqlite",
            "--hidden-import=sqlite3",
            "--hidden-import=json",
            "--hidden-import=threading",
            "--hidden-import=asyncio",
            "--hidden-import=concurrent.futures",
            "--hidden-import=requests",
            "--hidden-import=playwright",
            "--hidden-import=PIL",
            "--hidden-import=PIL.Image",
            "--hidden-import=PIL.ImageDraw",
            "--hidden-import=PIL.ImageFont",
            "--hidden-import=openai",
            "--hidden-import=dotenv",
            "main.py"
        ], check=True)
    
    print("✅ exe文件构建完成")

def create_icon():
    """创建图标文件"""
    print("🎨 检查图标文件...")
    
    # 检查是否有PNG图标
    png_icon = "build/icon.png"
    ico_icon = "build/icon.ico"
    
    if os.path.exists(png_icon) and not os.path.exists(ico_icon):
        print("🔄 转换PNG图标为ICO格式...")
        try:
            from PIL import Image
            img = Image.open(png_icon)
            img.save(ico_icon, format='ICO')
            print("✅ 图标转换完成")
        except Exception as e:
            print(f"⚠️ 图标转换失败: {e}")
    elif os.path.exists(ico_icon):
        print("✅ ICO图标已存在")
    else:
        print("⚠️ 未找到图标文件")

def create_installer():
    """创建安装包"""
    print("📦 创建安装包...")
    
    # 检查dist目录
    dist_dir = "dist/小红书发文助手"
    if os.path.exists(dist_dir):
        print(f"📁 打包目录: {dist_dir}")
        
        # 创建README文件
        readme_content = """# 小红书发文助手

## 使用说明

1. 双击运行"小红书发文助手.exe"
2. 首次运行会自动初始化数据库
3. 在用户管理中添加用户、代理和浏览器指纹配置
4. 使用发文功能创建和发布内容

## 注意事项

- 请确保有足够的磁盘空间
- 首次启动可能需要较长时间
- 如遇问题，请查看日志文件

## 系统要求

- Windows 10/11
- 至少2GB内存
- 至少500MB磁盘空间
"""
        
        readme_path = os.path.join(dist_dir, "README.txt")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print("✅ 安装包创建完成")
        print(f"📂 可执行文件位置: {dist_dir}")
    else:
        print("❌ 构建失败，未找到输出目录")

def main():
    """主函数"""
    print("🚀 开始打包小红书发文助手...")
    print("=" * 50)
    
    try:
        # 1. 安装依赖
        install_requirements()
        print()
        
        # 2. 创建图标
        create_icon()
        print()
        
        # 3. 创建配置文件
        create_spec_file()
        print()
        
        # 4. 构建exe
        build_exe()
        print()
        
        # 5. 创建安装包
        create_installer()
        print()
        
        print("🎉 打包完成！")
        print("=" * 50)
        print("📂 输出目录: dist/小红书发文助手/")
        print("🚀 可执行文件: 小红书发文助手.exe")
        print("📖 说明文档: README.txt")
        
    except Exception as e:
        print(f"❌ 打包失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 