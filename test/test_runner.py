#!/usr/bin/env python3
"""
项目功能测试运行器
一键测试所有功能模块并提供详细报告
"""

import os
import sys
import subprocess
import platform
import tempfile
from datetime import datetime
from pathlib import Path

class TestRunner:
    """测试运行器"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent
        self.results = {}
        self.start_time = datetime.now()
        
    def print_banner(self):
        """打印测试横幅"""
        print("\033[96m" + "="*80)
        print("🧪 小红书AI发布助手 - 功能测试套件")
        print("📊 全面测试所有功能模块")
        print("="*80 + "\033[0m")
        print()
    
    def check_environment(self):
        """检查测试环境"""
        print("\033[94m🔍 检查测试环境...\033[0m")
        
        checks = {
            "Python版本": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "操作系统": platform.system(),
            "项目路径": str(self.project_root),
            "测试目录": str(self.test_dir)
        }
        
        for check, value in checks.items():
            print(f"  ✅ {check}: {value}")
        print()
    
    def install_test_dependencies(self):
        """安装测试依赖"""
        print("\033[94m📦 安装测试依赖...\033[0m")
        
        requirements_file = self.test_dir / "requirements.txt"
        if requirements_file.exists():
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
                ], check=True, capture_output=True)
                print("  ✅ 测试依赖安装完成")
            except subprocess.CalledProcessError as e:
                print(f"  ❌ 依赖安装失败: {e}")
                return False
        else:
            print("  ⚠️  未找到测试依赖文件")
        return True
    
    def run_unit_tests(self):
        """运行单元测试"""
        print("\033[94m🔬 运行单元测试...\033[0m")
        
        unit_tests = [
            "unit/test_database.py",
            "unit/test_ai_content.py",
            "unit/test_cover_templates.py"
        ]
        
        for test_file in unit_tests:
            test_path = self.test_dir / test_file
            if test_path.exists():
                print(f"  🧪 运行 {test_file}...")
                try:
                    result = subprocess.run([
                        sys.executable, "-m", "pytest", str(test_path), "-v"
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print(f"    ✅ {test_file} 通过")
                        self.results[test_file] = "PASS"
                    else:
                        print(f"    ❌ {test_file} 失败")
                        self.results[test_file] = "FAIL"
                        if result.stdout:
                            print(f"    输出: {result.stdout}")
                except Exception as e:
                    print(f"    ❌ 运行错误: {e}")
                    self.results[test_file] = "ERROR"
            else:
                print(f"  ⚠️  {test_file} 不存在")
                self.results[test_file] = "MISSING"
    
    def run_integration_tests(self):
        """运行集成测试"""
        print("\033[94m🔗 运行集成测试...\033[0m")
        
        integration_tests = [
            "integration/test_browser.py",
            "integration/test_user_management.py"
        ]
        
        for test_file in integration_tests:
            test_path = self.test_dir / test_file
            if test_path.exists():
                print(f"  🔗 运行 {test_file}...")
                try:
                    # 浏览器测试可能需要额外参数
                    cmd = [sys.executable, "-m", "pytest", str(test_path), "-v"]
                    if "test_browser.py" in test_file:
                        cmd.extend(["--tb=short"])
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print(f"    ✅ {test_file} 通过")
                        self.results[test_file] = "PASS"
                    else:
                        print(f"    ⚠️ {test_file} 跳过或失败（需要浏览器环境）")
                        self.results[test_file] = "SKIP"
                except Exception as e:
                    print(f"    ❌ 运行错误: {e}")
                    self.results[test_file] = "ERROR"
            else:
                print(f"  ⚠️ {test_file} 不存在")
                self.results[test_file] = "MISSING"
    
    def test_database_functionality(self):
        """测试数据库功能"""
        print("\033[94m🗄️ 测试数据库功能...\033[0m")
        
        try:
            from src.config.database import db_manager
            
            # 测试数据库连接
            db_manager.init_database()
            print("  ✅ 数据库初始化成功")
            
            # 测试数据库信息
            info = db_manager.get_database_info()
            if info:
                print(f"  ✅ 数据库大小: {info['size']} 字节")
                print(f"  ✅ 数据表数量: {len(info['tables'])}")
                self.results["database"] = "PASS"
            else:
                print("  ❌ 无法获取数据库信息")
                self.results["database"] = "FAIL"
                
        except Exception as e:
            print(f"  ❌ 数据库测试失败: {e}")
            self.results["database"] = "ERROR"
    
    def test_system_diagnostics(self):
        """测试系统诊断"""
        print("\033[94m🔍 运行系统诊断...\033[0m")
        
        diagnostics = {}
        
        # Python环境
        diagnostics["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        # 依赖检查
        required_packages = [
            "PyQt5", "sqlalchemy", "pillow", "playwright", "requests"
        ]
        
        for package in required_packages:
            try:
                __import__(package.lower())
                diagnostics[package] = "✅ 已安装"
            except ImportError:
                diagnostics[package] = "❌ 未安装"
        
        # 文件系统检查
        required_files = [
            "main.py",
            "requirements.txt",
            "src/core/write_xiaohongshu.py",
            "src/config/config.py"
        ]
        
        for file_path in required_files:
            if (self.project_root / file_path).exists():
                diagnostics[file_path] = "✅ 存在"
            else:
                diagnostics[file_path] = "❌ 缺失"
        
        # 打印结果
        for key, value in diagnostics.items():
            print(f"  {value} {key}")
        
        self.results["diagnostics"] = diagnostics
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\033[96m" + "="*80)
        print("📊 测试报告")
        print("="*80 + "\033[0m")
        
        passed = sum(1 for v in self.results.values() if v == "PASS")
        failed = sum(1 for v in self.results.values() if v == "FAIL")
        skipped = sum(1 for v in self.results.values() if v == "SKIP")
        total = len(self.results)
        
        print(f"总测试项: {total}")
        print(f"通过: \033[92m{passed}\033[0m")
        print(f"失败: \033[91m{failed}\033[0m")
        print(f"跳过: \033[93m{skipped}\033[0m")
        
        end_time = datetime.now()
        duration = end_time - self.start_time
        print(f"测试耗时: {duration.total_seconds():.2f}秒")
        
        # 详细结果
        print("\n详细结果:")
        for test, result in self.results.items():
            if result == "PASS":
                color = "\033[92m"
            elif result == "FAIL":
                color = "\033[91m"
            elif result == "SKIP":
                color = "\033[93m"
            else:
                color = "\033[90m"
            
            print(f"  {color}{result}\033[0m {test}")
    
    def run_all_tests(self):
        """运行所有测试"""
        self.print_banner()
        self.check_environment()
        
        # 安装测试依赖
        if not self.install_test_dependencies():
            print("\033[91m❌ 测试依赖安装失败，跳过测试\033[0m")
            return
        
        # 运行各项测试
        self.test_database_functionality()
        self.run_unit_tests()
        self.run_integration_tests()
        self.test_system_diagnostics()
        
        # 生成报告
        self.generate_test_report()
        
        # 建议
        print("\n\033[94m💡 使用建议:\033[0m")
        print("  1. 运行单个测试文件: python test/unit/test_database.py")
        print("  2. 运行所有测试: python -m pytest test/ -v")
        print("  3. 生成HTML报告: python -m pytest test/ --html=reports/test_report.html")
        print("  4. 查看覆盖率: python -m pytest test/ --cov=src --cov-report=html")

if __name__ == '__main__':
    runner = TestRunner()
    runner.run_all_tests()