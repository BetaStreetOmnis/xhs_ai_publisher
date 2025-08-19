#!/bin/bash

# 小红书AI发布助手 - 跨平台一键安装脚本
# 支持 macOS、Linux 系统的通用安装解决方案

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
CYAN='\033[96m'
BOLD='\033[1m'
END='\033[0m'

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 打印横幅
print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║            🚀 小红书AI发布助手 - 一键安装              ║"
    echo "║                                                          ║"
    echo "║  🔍 自动检测系统环境                                     ║"
    echo "║  📦 自动安装所需依赖                                     ║"
    echo "║  🌟 跨平台支持 (macOS/Linux)                            ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${END}"
    echo ""
}

# 主函数
main() {
    print_banner
    
    # 检查项目文件
    if [[ ! -f "main.py" ]]; then
        echo -e "${RED}❌ 请在项目根目录中运行此脚本${END}"
        echo "项目根目录应包含 main.py 文件"
        exit 1
    fi
    
    if [[ ! -f "deploy.py" ]]; then
        echo -e "${RED}❌ 请在项目根目录中运行此脚本${END}"
        echo "项目根目录应包含 deploy.py 文件"
        exit 1
    fi
    
    # 检测Python环境
    echo -e "${BLUE}🔍 检测Python环境...${END}"
    
    # 查找Python命令
    PYTHON_CMD=""
    for cmd in python3 python python3.9 python3.10 python3.11 python3.12; do
        if command -v "$cmd" &> /dev/null; then
            version=$($cmd -c "import sys; print('.'.join(map(str, sys.version_info[:2])))" 2>/dev/null || echo "")
            if [[ -n "$version" ]]; then
                # 检查版本是否 >= 3.8
                if [[ "$(printf '%s\n' "$version" "3.8" | sort -V | head -n1)" == "3.8" ]]; then
                    PYTHON_CMD="$cmd"
                    echo -e "${GREEN}✅ 找到Python: $cmd (版本 $version)${END}"
                    break
                fi
            fi
        fi
    done
    
    if [[ -z "$PYTHON_CMD" ]]; then
        echo -e "${RED}❌ 未找到合适的Python环境 (需要 >= 3.8)${END}"
        echo -e "${BLUE}请先安装Python 3.8+：${END}"
        echo "  macOS: brew install python@3.11"
        echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
        exit 1
    fi
    
    # 运行Python部署脚本
    echo -e "${BLUE}🚀 启动Python部署脚本...${END}"
    "$PYTHON_CMD" deploy.py
    
    if [[ $? -eq 0 ]]; then
        echo ""
        echo -e "${GREEN}${BOLD}🎉 安装完成！${END}"
        echo -e "${BLUE}💡 启动程序: ${CYAN}./启动程序.sh${END}"
    else
        echo -e "${RED}❌ 安装过程中出现错误${END}"
        exit 1
    fi
}

# 错误处理
trap 'echo -e "${RED}❌ 安装过程中出现错误${END}"; exit 1' ERR

# 运行主函数
main "$@"