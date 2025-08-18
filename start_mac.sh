#!/bin/bash

# 小红书AI发布助手 - Mac启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
GREEN='\033[92m'
BLUE='\033[94m'
RED='\033[91m'
END='\033[0m'

echo -e "${BLUE}🚀 启动小红书AI发布助手...${END}"

# 检查虚拟环境是否存在
if [[ ! -d "venv" ]]; then
    echo -e "${RED}❌ 虚拟环境不存在，请先运行 ./install_mac.sh${END}"
    exit 1
fi

# 检查main.py是否存在
if [[ ! -f "main.py" ]]; then
    echo -e "${RED}❌ main.py文件不存在${END}"
    exit 1
fi

# 激活虚拟环境并启动程序
source venv/bin/activate
python main.py

echo -e "${GREEN}✅ 程序已退出${END}"
