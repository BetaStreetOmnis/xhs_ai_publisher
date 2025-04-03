import logging
import os
import signal
import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow,
                             QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from src.config.config import Config
from src.core.browser import BrowserThread
from src.core.pages.home import HomePage
from src.core.pages.setting import SettingsPage
from src.core.pages.tools import ToolsPage
from src.logger.logger import Logger

# 设置日志文件路径
log_path = os.path.expanduser('~/Desktop/xhsai_error.log')
logging.basicConfig(filename=log_path, level=logging.DEBUG)


class XiaohongshuUI(QMainWindow):
    def __init__(self):
        super().__init__()

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

        # 添加工具箱按钮
        tools_btn = QPushButton("🧰")
        tools_btn.setCheckable(True)
        tools_btn.clicked.connect(lambda: self.switch_page(1))

        settings_btn = QPushButton("⚙️")
        settings_btn.setCheckable(True)
        settings_btn.clicked.connect(lambda: self.switch_page(2))

        sidebar_layout.addWidget(home_btn)
        sidebar_layout.addWidget(tools_btn)
        sidebar_layout.addWidget(settings_btn)
        sidebar_layout.addStretch()

        # 添加侧边栏到主布局
        main_layout.addWidget(sidebar)

        # 创建堆叠窗口部件
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # 创建并添加三个页面
        self.home_page = HomePage(self)
        self.tools_page = ToolsPage(self)
        self.settings_page = SettingsPage(self)

        # 将页面添加到堆叠窗口
        self.stack.addWidget(self.home_page)
        self.stack.insertWidget(1, self.tools_page)
        self.stack.addWidget(self.settings_page)

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
        # 切换页面
        self.stack.setCurrentIndex(index)

        # 更新按钮状态
        sidebar = self.findChild(QWidget, "sidebar")
        if sidebar:
            buttons = [btn for btn in sidebar.findChildren(QPushButton)]
            for i, btn in enumerate(buttons):
                btn.setChecked(i == index)

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

            # 关闭浏览器
            if hasattr(self, 'browser_thread') and self.browser_thread.poster:
                try:
                    self.browser_thread.poster.close(force=True)
                except:
                    pass  # 忽略关闭浏览器时的错误

            # 清理资源
            self.images = []
            self.image_list = []
            self.current_image_index = 0

            # 调用父类的closeEvent
            super().closeEvent(event)

        except Exception as e:
            print(f"关闭应用程序时出错: {str(e)}")
            # 即使出错也强制关闭
            event.accept()


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
