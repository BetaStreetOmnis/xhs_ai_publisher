#!/bin/bash

# 小红书AI发布助手 - Mac一键安装脚本
# 适配macOS系统的完整安装解决方案

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

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

# 项目信息
PROJECT_NAME="小红书AI发布助手"
MIN_PYTHON_VERSION="3.8"

# 打印横幅
print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║            🍎 小红书AI发布助手 - Mac一键安装            ║"
    echo "║                                                          ║"
    echo "║  🔍 自动检测并安装Python环境                             ║"
    echo "║  📦 自动配置虚拟环境和依赖                               ║"
    echo "║  🚀 一键完成所有配置                                     ║"
    echo "║  🌟 专为macOS优化                                       ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${END}"
    echo ""
}

# 检查是否在macOS上运行
check_macos() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        echo -e "${RED}❌ 此脚本仅适用于macOS系统${END}"
        echo "请使用 install.sh 脚本"
        exit 1
    fi
    echo -e "${GREEN}✅ 检测到 macOS 系统${END}"
}

# 检查Python版本
check_python_version() {
    local python_cmd=$1
    if command -v "$python_cmd" &> /dev/null; then
        local version=$($python_cmd -c "import sys; print('.'.join(map(str, sys.version_info[:2])))" 2>/dev/null)
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

# 安装Homebrew
install_homebrew() {
    echo -e "${BLUE}🍺 安装Homebrew...${END}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # 添加Homebrew到PATH
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        # Apple Silicon Mac
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f "/usr/local/bin/brew" ]]; then
        # Intel Mac
        echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    echo -e "${GREEN}✅ Homebrew安装完成${END}"
}

# 安装Python
install_python() {
    echo -e "${BLUE}🐍 安装Python...${END}"
    
    # 检查是否有Homebrew
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}⚠️ 未检测到Homebrew，正在安装...${END}"
        install_homebrew
    fi
    
    echo -e "${BLUE}📦 使用Homebrew安装Python...${END}"
    brew install python@3.11
    
    # 创建软链接
    brew link python@3.11 --overwrite
    
    # 验证安装
    if detect_python; then
        echo -e "${GREEN}✅ Python安装成功${END}"
    else
        echo -e "${RED}❌ Python安装失败${END}"
        exit 1
    fi
}

# 创建虚拟环境
create_virtual_env() {
    echo -e "${BLUE}🏗️ 创建虚拟环境...${END}"
    
    cd "$PROJECT_DIR"
    
    # 删除旧的虚拟环境（如果存在）
    if [[ -d "venv" ]]; then
        echo -e "${YELLOW}⚠️ 发现旧的虚拟环境，正在删除...${END}"
        rm -rf venv
    fi
    
    # 创建新的虚拟环境
    $PYTHON_CMD -m venv venv
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    echo -e "${BLUE}🔄 升级pip...${END}"
    pip install --upgrade pip
    
    echo -e "${GREEN}✅ 虚拟环境创建成功${END}"
}

# 安装依赖
install_dependencies() {
    echo -e "${BLUE}📦 安装项目依赖...${END}"
    
    cd "$PROJECT_DIR"
    source venv/bin/activate
    
    # 检查requirements.txt是否存在
    if [[ ! -f "requirements.txt" ]]; then
        echo -e "${RED}❌ 找不到requirements.txt文件${END}"
        exit 1
    fi
    
    # 安装依赖
    pip install -r requirements.txt
    
    echo -e "${GREEN}✅ 依赖安装完成${END}"
}

# 初始化数据库
initialize_database() {
    echo -e "${BLUE}🗄️ 初始化数据库...${END}"
    
    cd "$PROJECT_DIR"
    source venv/bin/activate
    
    # 检查是否有数据库初始化脚本
    if [[ -f "init_db.py" ]]; then
        echo -e "${BLUE}🔄 运行数据库初始化脚本...${END}"
        python init_db.py
    fi
    
    echo -e "${GREEN}✅ 数据库初始化完成${END}"
}

# 创建启动脚本
create_launch_script() {
    echo -e "${BLUE}📝 创建启动脚本...${END}"
    
    cd "$PROJECT_DIR"
    
    cat > start_mac.sh << 'EOF'
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
EOF

    chmod +x start_mac.sh
    
    echo -e "${GREEN}✅ 启动脚本创建完成: start_mac.sh${END}"
}

# 主函数
main() {
    print_banner
    
    # 检查macOS
    check_macos
    
    # 检测Python环境
    if ! detect_python; then
        echo -e "${YELLOW}⚠️ 需要安装Python环境${END}"
        echo -e "${BLUE}💡 是否自动安装Python? (y/n)${END}"
        read -p "请选择: " install_choice
        
        if [[ "$install_choice" =~ ^[Yy]$ ]]; then
            install_python
        else
            echo -e "${YELLOW}请手动安装Python 3.8+后重新运行此脚本${END}"
            echo "推荐使用Homebrew安装: brew install python@3.11"
            exit 1
        fi
    fi
    
    # 创建虚拟环境
    create_virtual_env
    
    # 安装依赖
    install_dependencies
    
    # 初始化数据库
    initialize_database
    
    # 创建启动脚本
    create_launch_script
    
    echo ""
    echo -e "${GREEN}${BOLD}🎉 Mac安装完成！${END}"
    echo ""
    echo -e "${BLUE}💡 使用方法：${END}"
    echo -e "   启动程序: ${CYAN}./start_mac.sh${END}"
    echo -e "   重新安装: ${CYAN}./install_mac.sh${END}"
    echo ""
    echo -e "${YELLOW}📝 注意事项：${END}"
    echo "   • 首次运行可能需要配置浏览器驱动"
    echo "   • 请确保网络连接正常"
    echo "   • 如遇问题请查看项目文档"
    echo ""
}

# 错误处理
trap 'echo -e "${RED}❌ 安装过程中出现错误${END}"; exit 1' ERR

# 确保在项目目录中运行
if [[ ! -f "main.py" ]]; then
    echo -e "${RED}❌ 请在项目根目录中运行此脚本${END}"
    echo "项目根目录应包含 main.py 文件"
    exit 1
fi

# 运行主函数
main "$@"