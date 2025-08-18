#!/usr/bin/env python3
"""
简化的exe打包脚本
"""

import os
import sys
import subprocess

def main():
    """主函数"""
    print("🚀 开始打包小红书发文助手...")
    print("=" * 50)
    
    try:
        # 1. 安装PyInstaller
        print("📦 安装PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "PyInstaller"], check=True)
        print("✅ PyInstaller安装完成")
        
        # 2. 构建exe
        print("🔨 开始构建exe文件...")
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
        print("=" * 50)
        print("📂 输出目录: dist/")
        print("🚀 可执行文件: 小红书发文助手.exe")
        
    except Exception as e:
        print(f"❌ 打包失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 