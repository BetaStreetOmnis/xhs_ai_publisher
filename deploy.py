#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书AI发布助手 - 一键部署脚本
支持 Windows、macOS、Linux 系统
自动安装依赖并配置环境
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

# 设置Windows下的UTF-8输出
if platform.system() == "Windows":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    # 设置控制台编码
    os.system('chcp 65001 >nul')

class Colors:
    """终端颜色定义"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class DeploymentManager:
    """部署管理器"""
    
    def __init__(self):
        self.system = platform.system()
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        self.project_root = Path(__file__).parent.absolute()
        self.venv_path = self.project_root / "venv"
        
    def print_banner(self):
        """打印欢迎横幅"""
        banner = f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════╗
║              🌟 小红书AI发布助手 - 一键部署             ║
║                                                          ║
║  🚀 自动检测系统环境并安装所需依赖                      ║
║  📦 创建独立的虚拟环境                                   ║
║  ⚡ 一键启动应用程序                                     ║
╚══════════════════════════════════════════════════════════╝
{Colors.END}

{Colors.BLUE}检测到的系统信息:{Colors.END}
  🖥️  操作系统: {Colors.GREEN}{self.system}{Colors.END}
  🐍 Python版本: {Colors.GREEN}{self.python_version}{Colors.END}
  📁 项目路径: {Colors.GREEN}{self.project_root}{Colors.END}
"""
        print(banner)
    
    def check_python_version(self):
        """检查Python版本"""
        print(f"{Colors.BLUE}🔍 检查Python版本...{Colors.END}")
        
        if sys.version_info < (3, 8):
            print(f"{Colors.RED}❌ Python版本过低！{Colors.END}")
            print(f"   当前版本: {self.python_version}")
            print(f"   要求版本: 3.8+")
            print(f"\n请升级Python后重试: https://www.python.org/downloads/")
            return False
        
        print(f"{Colors.GREEN}✅ Python版本检查通过 (v{self.python_version}){Colors.END}")
        return True
    
    def check_pip(self):
        """检查pip是否可用"""
        print(f"{Colors.BLUE}🔍 检查pip工具...{Colors.END}")
        
        try:
            subprocess.run([sys.executable, "-m", "pip", "--version"], 
                         check=True, capture_output=True)
            print(f"{Colors.GREEN}✅ pip工具可用{Colors.END}")
            return True
        except subprocess.CalledProcessError:
            print(f"{Colors.RED}❌ pip工具不可用{Colors.END}")
            print(f"请安装pip: https://pip.pypa.io/en/stable/installing/")
            return False
    
    def create_virtual_environment(self):
        """创建虚拟环境"""
        print(f"{Colors.BLUE}📦 创建虚拟环境...{Colors.END}")
        
        if self.venv_path.exists():
            print(f"{Colors.YELLOW}⚠️  虚拟环境已存在{Colors.END}")
            # 在非交互环境下直接使用现有虚拟环境
            try:
                choice = input(f"请输入 y/n (默认n): ").lower().strip()
            except EOFError:
                choice = 'n'
                print("n (自动选择)")
            
            if choice == 'y':
                print(f"{Colors.BLUE}🗑️  删除现有虚拟环境...{Colors.END}")
                shutil.rmtree(self.venv_path)
            else:
                print(f"{Colors.GREEN}✅ 使用现有虚拟环境{Colors.END}")
                return True
        
        try:
            print(f"{Colors.BLUE}🔧 正在创建虚拟环境...{Colors.END}")
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_path)], 
                         check=True)
            print(f"{Colors.GREEN}✅ 虚拟环境创建成功{Colors.END}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}❌ 虚拟环境创建失败: {e}{Colors.END}")
            return False
    
    def get_venv_python(self):
        """获取虚拟环境中的Python路径"""
        if self.system == "Windows":
            return self.venv_path / "Scripts" / "python.exe"
        else:
            return self.venv_path / "bin" / "python"
    
    def get_venv_pip(self):
        """获取虚拟环境中的pip路径"""
        if self.system == "Windows":
            return self.venv_path / "Scripts" / "pip.exe"
        else:
            return self.venv_path / "bin" / "pip"
    
    def install_dependencies(self):
        """安装项目依赖"""
        print(f"{Colors.BLUE}📋 安装项目依赖...{Colors.END}")
        
        # 更新pip到最新版本
        print(f"{Colors.BLUE}🔄 更新pip到最新版本...{Colors.END}")
        try:
            subprocess.run([str(self.get_venv_python()), "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True)
            print(f"{Colors.GREEN}✅ pip更新完成{Colors.END}")
        except subprocess.CalledProcessError:
            print(f"{Colors.YELLOW}⚠️  pip更新失败，继续安装依赖...{Colors.END}")
        
        # 安装基础依赖
        print(f"{Colors.BLUE}📦 安装基础依赖包...{Colors.END}")
        basic_packages = [
            "requests>=2.28.0",
            "SQLAlchemy>=1.4.0",
            "playwright>=1.40.0",
            "Pillow>=9.0.0"
        ]
        
        for package in basic_packages:
            try:
                print(f"   安装 {package}...")
                subprocess.run([str(self.get_venv_pip()), "install", package], 
                             check=True, capture_output=True)
                print(f"{Colors.GREEN}   ✅ {package} 安装成功{Colors.END}")
            except subprocess.CalledProcessError as e:
                print(f"{Colors.RED}   ❌ {package} 安装失败{Colors.END}")
                return False
        
        # 安装PyQt5 (更好的兼容性)
        print(f"{Colors.BLUE}🎨 安装PyQt5 GUI框架...{Colors.END}")
        try:
            subprocess.run([str(self.get_venv_pip()), "install", "PyQt5>=5.15.0"], 
                         check=True, capture_output=True)
            print(f"{Colors.GREEN}✅ PyQt5安装成功{Colors.END}")
        except subprocess.CalledProcessError:
            print(f"{Colors.RED}❌ PyQt5安装失败{Colors.END}")
            print(f"{Colors.YELLOW}尝试安装备用GUI库...{Colors.END}")
            try:
                subprocess.run([str(self.get_venv_pip()), "install", "tkinter"], 
                             check=True, capture_output=True)
                print(f"{Colors.GREEN}✅ 备用GUI库安装成功{Colors.END}")
            except subprocess.CalledProcessError:
                print(f"{Colors.RED}❌ GUI库安装失败，程序可能无法显示界面{Colors.END}")
                return False
        
        # 如果存在requirements.txt，安装其中的依赖
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            print(f"{Colors.BLUE}📄 安装requirements.txt中的依赖...{Colors.END}")
            try:
                subprocess.run([str(self.get_venv_pip()), "install", "-r", str(requirements_file)], 
                             check=True, capture_output=True)
                print(f"{Colors.GREEN}✅ requirements.txt依赖安装完成{Colors.END}")
            except subprocess.CalledProcessError:
                print(f"{Colors.YELLOW}⚠️  requirements.txt安装部分失败，继续...{Colors.END}")
        
        return True
    
    def install_playwright_browsers(self):
        """安装Playwright浏览器"""
        print(f"{Colors.BLUE}🌐 安装Playwright浏览器...{Colors.END}")
        
        try:
            print(f"   正在下载Chromium浏览器...")
            subprocess.run([str(self.get_venv_python()), "-m", "playwright", "install", "chromium"], 
                         check=True, capture_output=True)
            print(f"{Colors.GREEN}✅ Chromium浏览器安装成功{Colors.END}")
            return True
        except subprocess.CalledProcessError:
            print(f"{Colors.YELLOW}⚠️  浏览器安装失败，部分功能可能不可用{Colors.END}")
            return False
    
    def initialize_database(self):
        """初始化数据库"""
        print(f"{Colors.BLUE}🗄️  初始化数据库...{Colors.END}")
        
        try:
            # 运行数据库初始化
            result = subprocess.run([str(self.get_venv_python()), "-c", 
                                   "from src.core.database_manager import database_manager; "
                                   "success = database_manager.ensure_database_ready(); "
                                   "print('数据库初始化成功' if success else '数据库初始化失败')"],
                                  cwd=self.project_root, capture_output=True, text=True)
            
            if "数据库初始化成功" in result.stdout:
                print(f"{Colors.GREEN}✅ 数据库初始化成功{Colors.END}")
                return True
            else:
                print(f"{Colors.YELLOW}⚠️  数据库初始化失败，程序启动时会自动初始化{Colors.END}")
                return True  # 不阻塞安装过程
                
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️  数据库初始化失败: {e}{Colors.END}")
            print(f"   程序启动时会自动初始化数据库")
            return True
    
    def create_startup_scripts(self):
        """创建启动脚本"""
        print(f"{Colors.BLUE}📝 创建启动脚本...{Colors.END}")
        
        # Windows启动脚本
        if self.system == "Windows":
            bat_content = f"""@echo off
echo 🚀 启动小红书AI发布助手...
cd /d "{self.project_root}"
"{self.get_venv_python()}" main.py
pause
"""
            bat_file = self.project_root / "启动程序.bat"
            with open(bat_file, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            print(f"{Colors.GREEN}✅ Windows启动脚本创建: 启动程序.bat{Colors.END}")
        
        # Unix启动脚本 (macOS/Linux)
        sh_content = f"""#!/bin/bash
echo "🚀 启动小红书AI发布助手..."
cd "{self.project_root}"
"{self.get_venv_python()}" main.py
"""
        sh_file = self.project_root / "启动程序.sh"
        with open(sh_file, 'w', encoding='utf-8') as f:
            f.write(sh_content)
        
        # 给Shell脚本执行权限
        if self.system != "Windows":
            os.chmod(sh_file, 0o755)
        
        print(f"{Colors.GREEN}✅ Unix启动脚本创建: 启动程序.sh{Colors.END}")
        
        return True
    
    def create_env_info(self):
        """创建环境信息文件"""
        env_info = f"""# 小红书AI发布助手 - 环境信息

## 部署信息
- 部署时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 操作系统: {self.system}
- Python版本: {self.python_version}
- 项目路径: {self.project_root}
- 虚拟环境: {self.venv_path}

## 启动方法

### 方法一：使用启动脚本
```bash
# Windows
双击运行: 启动程序.bat

# macOS/Linux  
./启动程序.sh
```

### 方法二：命令行启动
```bash
# 激活虚拟环境
# Windows
{self.venv_path}\\Scripts\\activate.bat

# macOS/Linux
source {self.venv_path}/bin/activate

# 启动程序
python main.py
```

### 方法三：直接启动
```bash
{self.get_venv_python()} main.py
```

## 功能说明
- 🏠 主页：内容生成和发布
- 👤 用户管理：多账户管理
- 🧰 工具箱：视频处理和数据库管理
- ⚙️ 设置：应用配置

## 数据存储
- 用户数据: ~/.xhs_system/xhs_data.db
- 配置文件: ~/.xhs_system/
- 备份文件: ~/.xhs_system/backups/

## 故障排除
1. 如果程序无法启动，请检查Python版本是否>=3.8
2. 如果界面无法显示，请确认PyQt5安装正确
3. 如果浏览器功能异常，请运行: playwright install chromium
4. 数据库问题会在程序启动时自动修复

## 技术支持
- 项目地址: https://github.com/BetaStreetOmnis/xhs_ai_publisher
- 问题反馈: 请在GitHub Issues中提交问题
"""
        
        info_file = self.project_root / "部署信息.md"
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(env_info)
        
        print(f"{Colors.GREEN}✅ 环境信息文件创建: 部署信息.md{Colors.END}")
    
    def run_deployment(self):
        """运行完整部署流程"""
        self.print_banner()
        
        # 检查基础环境
        if not self.check_python_version():
            return False
        
        if not self.check_pip():
            return False
        
        # 创建虚拟环境
        if not self.create_virtual_environment():
            return False
        
        # 安装依赖
        if not self.install_dependencies():
            return False
        
        # 安装浏览器
        self.install_playwright_browsers()
        
        # 初始化数据库
        self.initialize_database()
        
        # 创建启动脚本
        self.create_startup_scripts()
        
        # 创建环境信息
        self.create_env_info()
        
        # 部署完成
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 部署完成！{Colors.END}")
        print(f"""
{Colors.CYAN}启动方法:{Colors.END}
  {Colors.BLUE}Windows:{Colors.END} 双击运行 {Colors.GREEN}启动程序.bat{Colors.END}
  {Colors.BLUE}macOS/Linux:{Colors.END} 运行 {Colors.GREEN}./启动程序.sh{Colors.END}
  {Colors.BLUE}或直接运行:{Colors.END} {Colors.GREEN}{self.get_venv_python()} main.py{Colors.END}

{Colors.CYAN}功能介绍:{Colors.END}
  🏠 主页 - AI内容生成和发布
  👤 用户管理 - 多账户管理和配置  
  🧰 工具箱 - 视频处理和数据库管理
  ⚙️ 设置 - 应用程序配置

{Colors.YELLOW}提示:{Colors.END} 详细信息请查看 {Colors.GREEN}部署信息.md{Colors.END} 文件
""")
        
        # 询问是否立即启动
        print(f"{Colors.BLUE}是否现在启动程序？{Colors.END}")
        try:
            choice = input(f"请输入 y/n (默认y): ").lower().strip()
        except EOFError:
            choice = 'n'
            print("n (自动选择，在非交互环境下不启动)")
            
        if choice != 'n':
            print(f"{Colors.BLUE}🚀 正在启动程序...{Colors.END}")
            try:
                subprocess.run([str(self.get_venv_python()), "main.py"], 
                             cwd=self.project_root)
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}程序已停止{Colors.END}")
            except Exception as e:
                print(f"{Colors.RED}启动失败: {e}{Colors.END}")
        else:
            print(f"{Colors.GREEN}✅ 部署完成，可运行 启动程序.bat 启动应用{Colors.END}")
        
        return True

def main():
    """主函数"""
    try:
        manager = DeploymentManager()
        success = manager.run_deployment()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}部署被用户中断{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}部署失败: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()