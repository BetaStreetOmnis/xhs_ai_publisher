#!/bin/bash

# 小红书AI发布助手 - 一键安装脚本 (macOS/Linux)
# 自动检测和安装Python环境，无需用户预先安装Python

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
PURPLE='\033[95m'
CYAN='\033[96m'
WHITE='\033[97m'
BOLD='\033[1m'
END='\033[0m'

# 项目信息
PROJECT_NAME="小红书AI发布助手"
MIN_PYTHON_VERSION="3.8"
REQUIRED_PYTHON_VERSION="3.9"

# 打印横幅
print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║              🌟 小红书AI发布助手 - 一键安装             ║"
    echo "║                                                          ║"
    echo "║  🔍 自动检测Python环境                                   ║"
    echo "║  📦 自动安装所需依赖                                     ║"
    echo "║  🚀 一键完成所有配置                                     ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${END}"
    echo ""
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        echo -e "${GREEN}✅ 检测到 macOS 系统${END}"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        echo -e "${GREEN}✅ 检测到 Linux 系统${END}"
    else
        echo -e "${RED}❌ 不支持的操作系统: $OSTYPE${END}"
        echo "请使用 macOS 或 Linux 系统"
        exit 1
    fi
}

# 检查Python版本
check_python_version() {
    local python_cmd=$1
    if command -v "$python_cmd" &> /dev/null; then
        local version=$($python_cmd -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
        echo "$version"
        return 0
    else
        return 1
    fi
}

# 比较版本号
version_compare() {
    local version1=$1
    local version2=$2
    if [[ "$(printf '%s\n' "$version1" "$version2" | sort -V | head -n1)" == "$version2" ]]; then
        return 0  # version1 >= version2
    else
        return 1  # version1 < version2
    fi
}

# 检测Python环境
detect_python() {
    echo -e "${BLUE}🔍 检测Python环境...${END}"
    
    # 检测可能的Python命令
    local python_commands=("python3" "python" "python3.9" "python3.10" "python3.11" "python3.12" "python3.13")
    local found_python=""
    local found_version=""
    
    for cmd in "${python_commands[@]}"; do
        if version=$(check_python_version "$cmd"); then
            echo -e "  发现: $cmd (版本 $version)"
            if version_compare "$version" "$MIN_PYTHON_VERSION"; then
                if [[ -z "$found_python" ]] || version_compare "$version" "$found_version"; then
                    found_python="$cmd"
                    found_version="$version"
                fi
            fi
        fi
    done
    
    if [[ -n "$found_python" ]]; then
        PYTHON_CMD="$found_python"
        PYTHON_VERSION="$found_version"
        echo -e "${GREEN}✅ 找到合适的Python: $PYTHON_CMD (版本 $PYTHON_VERSION)${END}"
        return 0
    else
        echo -e "${YELLOW}⚠️ 未找到合适的Python环境 (需要 >= $MIN_PYTHON_VERSION)${END}"
        return 1
    fi
}

# 安装Python (macOS)
install_python_macos() {
    echo -e "${BLUE}📦 在macOS上安装Python...${END}"
    
    # 检查是否有Homebrew
    if command -v brew &> /dev/null; then
        echo -e "${GREEN}✅ 检测到Homebrew${END}"
        echo -e "${BLUE}🔄 使用Homebrew安装Python...${END}"
        brew install python@3.11
        PYTHON_CMD="python3"
    else
        echo -e "${YELLOW}⚠️ 未检测到Homebrew${END}"
        echo -e "${BLUE}💡 请选择安装方式:${END}"
        echo "1. 自动安装Homebrew并通过它安装Python (推荐)"
        echo "2. 手动下载Python安装包"
        echo "3. 退出安装"
        
        read -p "请选择 (1-3): " choice
        case $choice in
            1)
                echo -e "${BLUE}🔄 安装Homebrew...${END}"
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                echo -e "${BLUE}🔄 使用Homebrew安装Python...${END}"
                brew install python@3.11
                PYTHON_CMD="python3"
                ;;
            2)
                echo -e "${BLUE}📖 请访问以下链接下载Python:${END}"
                echo "   https://www.python.org/downloads/macos/"
                echo -e "${YELLOW}⚠️ 下载安装完成后，请重新运行此脚本${END}"
                exit 1
                ;;
            3)
                echo -e "${YELLOW}安装已取消${END}"
                exit 1
                ;;
            *)
                echo -e "${RED}❌ 无效选择${END}"
                exit 1
                ;;
        esac
    fi
}

# 安装Python (Linux)
install_python_linux() {
    echo -e "${BLUE}📦 在Linux上安装Python...${END}"
    
    # 检测Linux发行版
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        echo -e "${GREEN}✅ 检测到 Debian/Ubuntu 系统${END}"
        echo -e "${BLUE}🔄 更新包列表...${END}"
        sudo apt-get update
        echo -e "${BLUE}🔄 安装Python和相关工具...${END}"
        sudo apt-get install -y python3 python3-pip python3-venv python3-dev
        PYTHON_CMD="python3"
    elif command -v yum &> /dev/null; then
        # RHEL/CentOS/Fedora
        echo -e "${GREEN}✅ 检测到 RHEL/CentOS/Fedora 系统${END}"
        echo -e "${BLUE}🔄 安装Python和相关工具...${END}"
        sudo yum install -y python3 python3-pip python3-venv python3-devel
        PYTHON_CMD="python3"
    elif command -v dnf &> /dev/null; then
        # Fedora (新版本)
        echo -e "${GREEN}✅ 检测到 Fedora 系统${END}"
        echo -e "${BLUE}🔄 安装Python和相关工具...${END}"
        sudo dnf install -y python3 python3-pip python3-venv python3-devel
        PYTHON_CMD="python3"
    elif command -v pacman &> /dev/null; then
        # Arch Linux
        echo -e "${GREEN}✅ 检测到 Arch Linux 系统${END}"
        echo -e "${BLUE}🔄 安装Python和相关工具...${END}"
        sudo pacman -S --noconfirm python python-pip
        PYTHON_CMD="python"
    else
        echo -e "${RED}❌ 不支持的Linux发行版${END}"
        echo -e "${BLUE}💡 请手动安装Python 3.8+：${END}"
        echo "   https://www.python.org/downloads/"
        exit 1
    fi
}

# 安装Python环境
install_python() {
    echo -e "${BLUE}🚀 开始安装Python环境...${END}"
    
    case "$OS" in
        macos)
            install_python_macos
            ;;
        linux)
            install_python_linux
            ;;
        *)
            echo -e "${RED}❌ 不支持的操作系统${END}"
            exit 1
            ;;
    esac
    
    # 验证安装
    if detect_python; then
        echo -e "${GREEN}✅ Python安装成功${END}"
    else
        echo -e "${RED}❌ Python安装失败${END}"
        exit 1
    fi
}

# 检查pip是否可用
check_pip() {
    echo -e "${BLUE}🔍 检查pip工具...${END}"
    
    if $PYTHON_CMD -m pip --version &> /dev/null; then
        echo -e "${GREEN}✅ pip工具可用${END}"
        return 0
    else
        echo -e "${YELLOW}⚠️ pip工具不可用，尝试安装...${END}"
        
        # 尝试安装pip
        if command -v curl &> /dev/null; then
            curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
            $PYTHON_CMD get-pip.py
            rm get-pip.py
        elif command -v wget &> /dev/null; then
            wget https://bootstrap.pypa.io/get-pip.py
            $PYTHON_CMD get-pip.py
            rm get-pip.py
        else
            echo -e "${RED}❌ 无法下载pip安装脚本${END}"
            echo "请手动安装pip"
            exit 1
        fi
        
        # 再次检查
        if $PYTHON_CMD -m pip --version &> /dev/null; then
            echo -e "${GREEN}✅ pip安装成功${END}"
            return 0
        else
            echo -e "${RED}❌ pip安装失败${END}"
            exit 1
        fi
    fi
}

# 运行Python部署脚本
run_python_deployment() {
    echo -e "${BLUE}🚀 开始运行部署脚本...${END}"
    
    # 确保deploy.py存在
    if [[ ! -f "deploy.py" ]]; then
        echo -e "${RED}❌ 找不到deploy.py文件${END}"
        echo "请确保在项目根目录运行此脚本"
        exit 1
    fi
    
    # 运行Python部署脚本
    $PYTHON_CMD deploy.py
}

# 主函数
main() {
    print_banner
    
    # 检测操作系统
    detect_os
    
    # 检测Python环境
    if detect_python; then
        echo -e "${GREEN}✅ Python环境检查通过${END}"
    else
        echo -e "${YELLOW}⚠️ 需要安装Python环境${END}"
        echo -e "${BLUE}💡 是否自动安装Python? (y/n)${END}"
        read -p "请选择: " install_choice
        
        if [[ "$install_choice" =~ ^[Yy]$ ]]; then
            install_python
        else
            echo -e "${YELLOW}请手动安装Python 3.8+后重新运行此脚本${END}"
            echo "下载地址: https://www.python.org/downloads/"
            exit 1
        fi
    fi
    
    # 检查pip
    check_pip
    
    # 运行Python部署脚本
    run_python_deployment
    
    echo -e "${GREEN}${BOLD}🎉 安装完成！${END}"
    echo -e "${BLUE}💡 启动程序: ./启动程序.sh${END}"
}

# 错误处理
trap 'echo -e "${RED}❌ 安装过程中出现错误${END}"; exit 1' ERR

# 确保在项目目录中运行
if [[ ! -f "main.py" ]] || [[ ! -f "deploy.py" ]]; then
    echo -e "${RED}❌ 请在项目根目录中运行此脚本${END}"
    echo "项目根目录应包含 main.py 和 deploy.py 文件"
    exit 1
fi

# 运行主函数
main "$@"