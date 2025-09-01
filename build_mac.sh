#!/bin/bash

# 小红书发文助手 - macOS打包工具
# 使用方法: chmod +x build_mac.sh && ./build_mac.sh

set -e  # 遇到错误立即退出

echo "🚀 小红书发文助手 - macOS打包工具"
echo "=================================="
echo

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 未检测到Python3，请先安装Python 3.8或更高版本"
    echo "📥 下载地址: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python版本: $PYTHON_VERSION"

# 检查是否安装了pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ 未检测到pip3，请先安装pip"
    exit 1
fi

echo "✅ pip环境检测通过"

# 安装依赖
echo "📦 正在安装打包依赖..."
pip3 install -r requirements-build.txt

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败，请检查网络连接"
    exit 1
fi

echo "✅ 依赖安装完成"

# 开始打包
echo "🏗️ 开始构建macOS应用程序..."
python3 build.py

if [ $? -ne 0 ]; then
    echo "❌ 打包失败"
    exit 1
fi

echo
echo "🎉 打包完成！"
echo "📁 应用程序位置: dist/小红书发文助手.app"
echo "📦 分发包: 小红书发文助手_macOS.dmg"
echo
echo "💡 使用方法:"
echo "   1. 运行 dist/install_mac.sh 安装到应用程序"
echo "   2. 或者直接运行 dist/小红书发文助手.app"
echo