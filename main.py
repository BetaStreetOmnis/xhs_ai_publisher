import logging
import os
import signal
import sys
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QMainWindow,
                             QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from src.config.config import Config
from src.core.browser import BrowserThread
from src.core.pages.home import HomePage
from src.core.pages.setting import SettingsPage
from src.core.pages.tools import ToolsPage
from src.core.pages.user_management import UserManagementPage
from src.logger.logger import Logger

# 设置日志文件路径
log_path = os.path.expanduser('~/Desktop/xhsai_error.log')
logging.basicConfig(filename=log_path, level=logging.DEBUG)

def init_database_on_startup():
    """应用启动时初始化数据库"""
    try:
        print("🚀 应用启动时检查和初始化数据库...")
        
        # 导入数据库管理器
        from src.core.database_manager import database_manager
        
        # 确保数据库已准备就绪（包含自动修复功能）
        success = database_manager.ensure_database_ready()
        
        if success:
            print("✅ 数据库已准备就绪")
            
            # 显示数据库信息
            db_info = database_manager.get_database_info()
            print(f"📁 数据库路径: {db_info['db_path']}")
            print(f"📊 数据库大小: {db_info['size']} 字节")
            print(f"📋 数据表数量: {len(db_info['tables'])}")
            
            # 显示健康状态
            health = db_info['health']
            if health['healthy']:
                print("💚 数据库健康状态: 良好")
            else:
                print("🟡 数据库健康状态: 存在问题")
                for issue in health['issues']:
                    print(f"  ⚠️ {issue}")
        else:
            print("❌ 数据库初始化失败，用户管理功能可能不可用")
            print("💡 请尝试手动运行数据库修复或联系技术支持")
            
        return success
    except Exception as e:
        print(f"❌ 数据库初始化出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

class XiaohongshuUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # 在创建UI之前先初始化数据库
        init_database_on_startup()

        self.config = Config()

        # 设置应用图标
        icon_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'build/icon.png')
        self.app_icon = QIcon(icon_path)
        QApplication.setWindowIcon(self.app_icon)
        self.setWindowIcon(self.app_icon)

        # 加载logger
        app_config = self.config.get_app_config()
        self.logger = Logger(is_console=app_config)

        self.logger.success("小红书发文助手启动")

        self.setWindowTitle("✨ 小红书发文助手")

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: #f8f9fa;
            }}
            QLabel {{
                font-family: {("Menlo" if sys.platform == "darwin" else "Consolas")};
                color: #34495e;
                font-size: 11pt;
                border: none;
                background: transparent;
            }}
            QPushButton {{
                font-family: {("Menlo" if sys.platform == "darwin" else "Consolas")};
                font-size: 11pt;
                font-weight: bold;
                padding: 6px;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #357abd;
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
            }}
            QLineEdit, QTextEdit, QComboBox {{
                font-family: {("Menlo" if sys.platform == "darwin" else "Consolas")};
                font-size: 11pt;
                padding: 4px;
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }}
            QFrame {{
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 6px;
            }}
            QScrollArea {{
                border: none;
            }}
            #sidebar {{
                background-color: #2c3e50;
                min-width: 60px;
                max-width: 60px;
                padding: 20px 0;
            }}
            #sidebar QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 0;
                color: #ecf0f1;
                padding: 15px 0;
                margin: 5px 0;
                font-size: 20px;
            }}
            #sidebar QPushButton:hover {{
                background-color: #34495e;
            }}
            #sidebar QPushButton:checked {{
                background-color: #34495e;
            }}
            #settingsPage {{
                background-color: white;
                padding: 20px;
            }}
        """)

        self.setMinimumSize(1000, 600)
        self.center()

        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 创建水平布局
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建侧边栏
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # 创建侧边栏按钮
        home_btn = QPushButton("🏠")
        home_btn.setCheckable(True)
        home_btn.setChecked(True)
        home_btn.clicked.connect(lambda: self.switch_page(0))

        # 添加用户管理按钮
        user_btn = QPushButton("👤")
        user_btn.setCheckable(True)
        user_btn.clicked.connect(lambda: self.switch_page(1))

        # 添加工具箱按钮
        tools_btn = QPushButton("🧰")
        tools_btn.setCheckable(True)
        tools_btn.clicked.connect(lambda: self.switch_page(2))

        settings_btn = QPushButton("⚙️")
        settings_btn.setCheckable(True)
        settings_btn.clicked.connect(lambda: self.switch_page(3))

        sidebar_layout.addWidget(home_btn)
        sidebar_layout.addWidget(user_btn)
        sidebar_layout.addWidget(tools_btn)
        sidebar_layout.addWidget(settings_btn)
        sidebar_layout.addStretch()

        # 存储按钮引用以便切换状态
        self.sidebar_buttons = [home_btn, user_btn, tools_btn, settings_btn]

        # 添加侧边栏到主布局
        main_layout.addWidget(sidebar)

        # 创建堆叠窗口部件
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # 创建并添加页面
        self.home_page = HomePage(self)
        self.user_management_page = UserManagementPage(self)
        self.tools_page = ToolsPage(self)
        self.settings_page = SettingsPage(self)

        # 将页面添加到堆叠窗口
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.user_management_page)
        self.stack.addWidget(self.tools_page)
        self.stack.addWidget(self.settings_page)

        # 连接用户管理页面的信号
        self.user_management_page.user_switched.connect(self.on_user_switched)

        # 创建浏览器线程
        self.browser_thread = BrowserThread()
        # 连接信号
        self.browser_thread.login_status_changed.connect(
            self.update_login_button)
        self.browser_thread.preview_status_changed.connect(
            self.update_preview_button)
        self.browser_thread.login_success.connect(
            self.home_page.handle_poster_ready)
        self.browser_thread.login_error.connect(
            self.home_page.handle_login_error)
        self.browser_thread.preview_success.connect(
            self.home_page.handle_preview_result)
        self.browser_thread.preview_error.connect(
            self.home_page.handle_preview_error)
        self.browser_thread.start()
        
        # 启动下载器线程
        self.start_downloader_thread()

    def center(self):
        """将窗口移动到屏幕中央"""
        # 获取屏幕几何信息
        screen = QApplication.primaryScreen().geometry()
        # 获取窗口几何信息
        size = self.geometry()
        # 计算居中位置
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        # 移动窗口
        self.move(x, y)

    def update_login_button(self, text, enabled):
        """更新登录按钮状态"""
        login_btn = self.findChild(QPushButton, "login_btn")
        if login_btn:
            login_btn.setText(text)
            login_btn.setEnabled(enabled)

    def update_preview_button(self, text, enabled):
        """更新预览按钮状态"""
        preview_btn = self.findChild(QPushButton, "preview_btn")
        if preview_btn:
            preview_btn.setText(text)
            preview_btn.setEnabled(enabled)

    def switch_page(self, index):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        
        # 更新按钮状态
        for i, btn in enumerate(self.sidebar_buttons):
            btn.setChecked(i == index)
    
    def on_user_switched(self, user_id):
        """处理用户切换事件"""
        try:
            self.logger.info(f"用户已切换到ID: {user_id}")
            # 这里可以添加用户切换后的其他处理逻辑
            # 比如重新加载用户相关的配置、重置浏览器状态等
        except Exception as e:
            self.logger.error(f"处理用户切换失败: {str(e)}")

    def closeEvent(self, event):
        print("关闭应用")
        try:
            # 停止所有线程
            if hasattr(self, 'browser_thread'):
                self.browser_thread.stop()
                self.browser_thread.wait(1000)  # 等待最多1秒
                if self.browser_thread.isRunning():
                    self.browser_thread.terminate()  # 强制终止
                    self.browser_thread.wait()  # 等待终止完成

            if hasattr(self, 'generator_thread') and self.generator_thread.isRunning():
                self.generator_thread.terminate()
                self.generator_thread.wait()

            if hasattr(self, 'image_processor') and self.image_processor.isRunning():
                self.image_processor.terminate()
                self.image_processor.wait()

            # 清理资源
            self.images = []
            self.image_list = []
            self.current_image_index = 0
            # 关闭本机8000端口
            self.stop_downloader()
            # 调用父类的closeEvent
            super().closeEvent(event)

        except Exception as e:
            print(f"关闭应用程序时出错: {str(e)}")
            # 即使出错也强制关闭
            event.accept()
            
    def start_downloader_thread(self):
        """启动Chrome下载器线程"""
        try:
            import threading
            
            def download_chrome():
                """使用Playwright下载Chrome浏览器"""
                try:
                    self.logger.info("🔍 检查Chrome浏览器...")
                    
                    # 尝试导入playwright
                    try:
                        from playwright.sync_api import sync_playwright
                        self.logger.info("✅ Playwright已安装")
                    except ImportError:
                        self.logger.error("❌ Playwright未安装，请运行: pip install playwright")
                        self.logger.info("💡 浏览器功能将不可用，但不影响其他功能的正常使用")
                        return
                    
                    # 检查Chrome是否已安装
                    with sync_playwright() as p:
                        try:
                            # 尝试启动Chrome来检查是否已安装
                            browser = p.chromium.launch(headless=True)
                            browser.close()
                            self.logger.success("✅ Chrome浏览器已可用")
                            return
                        except Exception as e:
                            if "Executable doesn't exist" in str(e) or "找不到" in str(e):
                                self.logger.info("🔄 Chrome浏览器未安装，正在下载...")
                                
                                # 下载Chrome浏览器
                                import subprocess
                                import sys
                                
                                # 使用playwright install命令下载Chrome
                                try:
                                    self.logger.info("📥 正在下载Chrome浏览器，请稍候...")
                                    result = subprocess.run(
                                        [sys.executable, "-m", "playwright", "install", "chromium"],
                                        capture_output=True,
                                        text=True,
                                        timeout=300  # 5分钟超时
                                    )
                                    
                                    if result.returncode == 0:
                                        self.logger.success("✅ Chrome浏览器下载完成")
                                        
                                        # 再次验证安装
                                        with sync_playwright() as p2:
                                            try:
                                                browser = p2.chromium.launch(headless=True)
                                                browser.close()
                                                self.logger.success("✅ Chrome浏览器验证成功")
                                            except Exception as verify_error:
                                                self.logger.error(f"❌ Chrome浏览器验证失败: {str(verify_error)}")
                                    else:
                                        self.logger.error(f"❌ Chrome浏览器下载失败: {result.stderr}")
                                        self.logger.info("💡 您可以手动运行: python -m playwright install chromium")
                                        
                                except subprocess.TimeoutExpired:
                                    self.logger.error("❌ Chrome浏览器下载超时")
                                    self.logger.info("💡 请检查网络连接，或手动运行: python -m playwright install chromium")
                                except Exception as download_error:
                                    self.logger.error(f"❌ Chrome浏览器下载出错: {str(download_error)}")
                                    self.logger.info("💡 请手动运行: python -m playwright install chromium")
                            else:
                                self.logger.error(f"❌ Chrome浏览器检查失败: {str(e)}")
                                
                except Exception as e:
                    self.logger.error(f"❌ Chrome下载器出错: {str(e)}")
                    self.logger.info("💡 浏览器功能将不可用，但不影响其他功能的正常使用")
                    
            # 创建并启动线程
            self.downloader_thread = threading.Thread(target=download_chrome, daemon=True)
            self.downloader_thread.start()
            
        except Exception as e:
            self.logger.error(f"❌ 启动Chrome下载器线程时出错: {str(e)}")
            
    def stop_downloader(self):
        """停止下载器（现在主要是清理资源）"""
        try:
            # 由于我们不再启动服务器进程，这里主要是清理资源
            self.logger.info("ℹ️ 清理浏览器资源")
            
            # 如果有正在运行的下载线程，等待其完成
            if hasattr(self, 'downloader_thread') and self.downloader_thread.is_alive():
                self.logger.info("ℹ️ 等待Chrome下载完成...")
                # 不强制终止下载线程，让它自然完成
                
        except Exception as e:
            self.logger.warning(f"⚠️ 清理浏览器资源时出现问题: {str(e)}")


if __name__ == "__main__":
    try:
        # 设置信号处理
        def signal_handler(signum, frame):
            print("\n正在退出程序...")
            QApplication.quit()
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)

        app = QApplication(sys.argv)

        # 允许 CTRL+C 中断
        timer = QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(100)

        window = XiaohongshuUI()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.exception("程序运行出错：")
        raise
