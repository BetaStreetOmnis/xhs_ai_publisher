import logging
import os
import signal
import sys
from src.version import __version__
from src.core.services.runtime_paths import get_logs_dir, init_runtime_env

init_runtime_env()

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QMainWindow,
                             QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from src.config.config import Config
from src.core.browser import BrowserThread
from src.core.pages.home import HomePage
from src.core.pages.tools import ToolsPage
from src.core.pages.browser_environment_page import BrowserEnvironmentPage
from src.core.pages.user_management_page import UserManagementPage
from src.core.pages.simple_backend_config import BackendConfigPage
from src.core.pages.cover_center_page import CoverCenterPage
from src.core.pages.data_center_page import DataCenterPage
from src.core.alert import TipWindow
from src.logger.logger import Logger
from src.core.ui.qt_font import (
    get_emoji_font_family,
    get_emoji_font_family_css,
    get_ui_text_font_family_css,
    ui_font,
)

# 设置日志文件路径
log_path = str(get_logs_dir() / "xhsai_error.log")
logging.basicConfig(filename=log_path, level=logging.DEBUG, encoding="utf-8")

def load_env_file():
    """加载项目根目录的 .env（不覆盖已有环境变量）。"""
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    try:
        project_root = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(project_root, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)
    except Exception:
        pass


def init_playwright_env():
    """统一 Playwright 浏览器缓存目录，提升 Windows 稳定性。"""
    try:
        init_runtime_env()
        browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
        if sys.platform == "win32":
            os.environ.setdefault("PLAYWRIGHT_DOWNLOAD_HOST", "https://npmmirror.com/mirrors/playwright")
        if browsers_path:
            os.makedirs(browsers_path, exist_ok=True)
    except Exception:
        pass

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
            print("❌ 数据库初始化失败")
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
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "icon.png")
        if os.path.exists(icon_path):
            self.app_icon = QIcon(icon_path)
            QApplication.setWindowIcon(self.app_icon)
            self.setWindowIcon(self.app_icon)

        # 加载logger
        app_config = self.config.get_app_config()
        self.logger = Logger(is_console=app_config)

        self.logger.success("小红书发文助手启动")

        self.setWindowTitle(f"✨ 小红书发文助手 {__version__}")

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: #f8f9fa;
            }}
            QLabel {{
                font-family: {get_ui_text_font_family_css()};
                color: #34495e;
                font-size: 11pt;
                border: none;
                background: transparent;
            }}
            QPushButton {{
                font-family: {get_ui_text_font_family_css()};
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
                font-family: {get_ui_text_font_family_css()};
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
                font-family: {get_emoji_font_family_css()};
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

        self.setMinimumSize(1200, 780)  # 增大主窗口最小尺寸，提升纵向显示空间
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
        home_btn.setToolTip("主页")

        # 添加用户管理按钮
        user_btn = QPushButton("👥")
        user_btn.setCheckable(True)
        user_btn.clicked.connect(lambda: self.switch_page(1))
        user_btn.setToolTip("用户管理")

        # 添加浏览器环境按钮
        browser_env_btn = QPushButton("🌐")
        browser_env_btn.setCheckable(True)
        browser_env_btn.clicked.connect(lambda: self.switch_page(2))
        browser_env_btn.setToolTip("浏览器环境")

        # 添加后台配置按钮
        backend_btn = QPushButton("⚙️")
        backend_btn.setCheckable(True)
        backend_btn.clicked.connect(lambda: self.switch_page(3))
        backend_btn.setToolTip("后台配置")

        # 添加封面生成按钮
        cover_btn = QPushButton("🖼️")
        cover_btn.setCheckable(True)
        cover_btn.clicked.connect(lambda: self.switch_page(4))
        cover_btn.setToolTip("封面中心")

        # 数据中心
        data_center_btn = QPushButton("📊")
        data_center_btn.setCheckable(True)
        data_center_btn.clicked.connect(lambda: self.switch_page(5))
        data_center_btn.setToolTip("数据中心")

        # 添加工具箱按钮
        tools_btn = QPushButton("🧰")
        tools_btn.setCheckable(True)
        tools_btn.clicked.connect(lambda: self.switch_page(6))
        tools_btn.setToolTip("工具箱")

        emoji_font = get_emoji_font_family()
        if emoji_font:
            sidebar_font_css = f"font-family: '{emoji_font}';"
            for btn in [
                home_btn,
                user_btn,
                browser_env_btn,
                backend_btn,
                cover_btn,
                data_center_btn,
                tools_btn,
            ]:
                btn.setStyleSheet(sidebar_font_css)

        sidebar_layout.addWidget(home_btn)
        sidebar_layout.addWidget(user_btn)
        sidebar_layout.addWidget(browser_env_btn)
        sidebar_layout.addWidget(backend_btn)
        sidebar_layout.addWidget(cover_btn)
        sidebar_layout.addWidget(data_center_btn)
        sidebar_layout.addWidget(tools_btn)
        sidebar_layout.addStretch()

        # 存储按钮引用以便切换状态
        self.sidebar_buttons = [home_btn, user_btn, browser_env_btn, backend_btn, cover_btn, data_center_btn, tools_btn]

        # 添加侧边栏到主布局
        main_layout.addWidget(sidebar)

        # 创建堆叠窗口部件
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # 创建并添加页面
        self.home_page = HomePage(self)
        self.user_management_page = UserManagementPage(self)
        self.browser_environment_page = BrowserEnvironmentPage(self)
        self.backend_config_page = BackendConfigPage(self)
        self.cover_page = CoverCenterPage(self)
        self.data_center_page = DataCenterPage(self)
        self.tools_page = ToolsPage(self)

# 将页面添加到堆叠窗口
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.user_management_page)
        self.stack.addWidget(self.browser_environment_page)
        self.stack.addWidget(self.backend_config_page)
        self.stack.addWidget(self.cover_page)
        self.stack.addWidget(self.data_center_page)
        self.stack.addWidget(self.tools_page)

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
        
        # 启动定时发布调度器
        from src.core.scheduler.schedule_manager import schedule_manager
        self.schedule_manager = schedule_manager
        try:
            # 任务到期：派发给浏览器线程执行
            self.schedule_manager.task_execute_requested.connect(self.enqueue_scheduled_task)
            # 浏览器线程回传执行结果：更新任务状态（跨线程安全）
            self.browser_thread.scheduled_task_result.connect(self.schedule_manager.handle_task_result)

            # 可选：提示执行状态
            self.schedule_manager.task_started.connect(self.on_scheduled_task_started)
            self.schedule_manager.task_completed.connect(self.on_scheduled_task_completed)
            self.schedule_manager.task_failed.connect(self.on_scheduled_task_failed)
        except Exception as e:
            print(f"⚠️ 定时发布信号连接失败: {e}")
        
        # 启动下载器线程
        self.start_downloader_thread()

        # 启动后同步一次当前用户到UI
        self.sync_current_user_to_ui()

    def sync_current_user_to_ui(self):
        """将当前用户手机号同步到主页手机号输入框。"""
        try:
            from src.core.services.user_service import user_service

            current_user = user_service.get_current_user()
            if not current_user:
                return

            if hasattr(self, "home_page") and hasattr(self.home_page, "phone_input"):
                self.home_page.phone_input.blockSignals(True)
                self.home_page.phone_input.setText(current_user.phone or "")
                self.home_page.phone_input.blockSignals(False)
        except Exception:
            pass

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

    def enqueue_scheduled_task(self, task: object):
        """接收调度器的到期任务，并加入浏览器线程队列执行。"""
        try:
            data = task if isinstance(task, dict) else {}
            self.browser_thread.action_queue.append(
                {
                    "type": "scheduled_publish",
                    "task_id": data.get("task_id"),
                    "user_id": data.get("user_id"),
                    "title": data.get("title"),
                    "content": data.get("content"),
                    "images": data.get("images"),
                    # 热点任务相关字段（用于到点重新生成内容/图片）
                    "task_type": data.get("task_type"),
                    "interval_hours": data.get("interval_hours"),
                    "hotspot_source": data.get("hotspot_source"),
                    "hotspot_rank": data.get("hotspot_rank"),
                    "use_hotspot_context": data.get("use_hotspot_context"),
                    "cover_template_id": data.get("cover_template_id"),
                    "page_count": data.get("page_count"),
                    "platform": data.get("platform"),
                    "engine": data.get("engine"),
                }
            )
        except Exception as e:
            task_id = ""
            try:
                task_id = str((task or {}).get("task_id") or "")
            except Exception:
                task_id = ""
            try:
                if getattr(self, "schedule_manager", None) and task_id:
                    self.schedule_manager.handle_task_result(task_id, False, str(e))
            except Exception:
                pass

    def on_scheduled_task_started(self, task_id: str):
        try:
            TipWindow(self, f"⏰ 定时任务开始执行：{task_id}").show()
        except Exception:
            pass

    def on_scheduled_task_completed(self, task_id: str):
        try:
            TipWindow(self, f"📤 定时任务已执行，请核验平台结果：{task_id}").show()
        except Exception:
            pass

    def on_scheduled_task_failed(self, task_id: str, reason: str):
        try:
            msg = f"⚠️ 定时任务已暂停，等待核验：{task_id}"
            if reason:
                msg += f"\n{reason}"
            TipWindow(self, msg).show()
        except Exception:
            pass

    def switch_page(self, index):
        """切换页面"""
        self.stack.setCurrentIndex(index)
        
        # 更新按钮状态
        for i, btn in enumerate(self.sidebar_buttons):
            btn.setChecked(i == index)
    


    def closeEvent(self, event):
        print("关闭应用")
        try:
            # 停止定时发布调度器
            from src.core.scheduler.schedule_manager import schedule_manager
            schedule_manager.stop_scheduler()
            
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
                            # 优先检查 Playwright 自带 Chromium
                            browser = p.chromium.launch(headless=True, timeout=30_000)
                            browser.close()
                            self.logger.success("✅ Playwright Chromium 已可用")
                            return
                        except Exception as e:
                            if "Executable doesn't exist" in str(e) or "找不到" in str(e):
                                # 尝试系统浏览器通道（避免因 Playwright 缓存缺失而强制下载）
                                for channel in ("chrome", "msedge"):
                                    try:
                                        browser = p.chromium.launch(channel=channel, headless=True, timeout=30_000)
                                        browser.close()
                                        self.logger.success(f"✅ 系统浏览器可用（{channel}），无需下载 Playwright Chromium")
                                        return
                                    except Exception:
                                        continue

                                self.logger.info("🔄 Chrome浏览器未安装，正在下载...")
                                
                                # 下载Chrome浏览器
                                import subprocess
                                import sys

                                # 打包版 exe 无法通过 `sys.executable -m playwright ...` 在线安装浏览器
                                if getattr(sys, "frozen", False):
                                    self.logger.error("❌ 检测到浏览器缺失，但当前为打包版本，无法自动下载 Playwright Chromium。")
                                    self.logger.info("💡 可能原因：杀毒软件误删了浏览器文件；请将程序目录加入白名单并重新解压完整包。")
                                    return
                                
                                # 使用playwright install命令下载Chrome
                                try:
                                    self.logger.info("📥 正在下载Chrome浏览器，请稍候...")
                                    env = os.environ.copy()
                                    env.setdefault(
                                        "PLAYWRIGHT_BROWSERS_PATH",
                                        os.path.join(os.path.expanduser("~"), ".xhs_system", "ms-playwright"),
                                    )
                                    if sys.platform == "win32":
                                        env.setdefault("PLAYWRIGHT_DOWNLOAD_HOST", "https://npmmirror.com/mirrors/playwright")

                                    result = subprocess.run(
                                        [sys.executable, "-m", "playwright", "install", "chromium"],
                                        capture_output=True,
                                        text=True,
                                        env=env,
                                        timeout=1200  # 20分钟超时（部分网络较慢）
                                    )
                                    
                                    if result.returncode == 0:
                                        self.logger.success("✅ Chrome浏览器下载完成")
                                        
                                        # Reuse the active context; nesting sync contexts fails.
                                        try:
                                            browser = p.chromium.launch(headless=True)
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
    if "--smoke-test" in sys.argv:
        from src.core.services.release_smoke import run_release_smoke
        run_release_smoke()
        sys.exit(0)
    try:
        load_env_file()
        init_playwright_env()

        # 设置信号处理
        def signal_handler(signum, frame):
            print("\n正在退出程序...")
            QApplication.quit()
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)

        app = QApplication(sys.argv)
        app.setApplicationVersion(__version__)
        # Prefer a UI font that supports CJK, and let monospace be opt-in per widget.
        app.setFont(ui_font(12))

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
