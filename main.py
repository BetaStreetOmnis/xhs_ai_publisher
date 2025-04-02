import logging
import sys
import signal
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit, QFrame,
                             QStackedWidget, QScrollArea)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QColor, QIcon
import os
from src.core.processor.content import ContentGeneratorThread
from src.core.processor.img import ImageProcessorThread
from src.core.browser import BrowserThread
from src.config.config import Config
from src.logger.logger import Logger

from src.core.alert import TipWindow

from src.config.constants import VERSION

import requests
import base64
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

import uvicorn

# 设置日志文件路径
log_path = os.path.expanduser('~/Desktop/xhsai_error.log')
logging.basicConfig(filename=log_path, level=logging.DEBUG)

class HomePage(QWidget):
    """主页类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        # 初始化变量
        self.images = []
        self.image_list = []
        self.current_image_index = 0
        # 创建占位图
        self.placeholder_photo = QPixmap(200, 200)
        self.placeholder_photo.fill(QColor('#f8f9fa'))

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)

        # 创建登录区域
        self.create_login_section(layout)

        # 创建内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        layout.addLayout(content_layout)

        # 创建左侧区域
        self.create_left_section(content_layout)

        # 创建右侧预览区域
        self.create_preview_section(content_layout)

    def create_login_section(self, parent_layout):
        """创建登录区域"""
        login_frame = QFrame()
        login_frame.setStyleSheet("""
            QFrame {
                padding: 8px;
                background-color: white;
            }
            QLabel {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                font-size: 12pt;
                border: none;
                background: transparent;
            }
            QLineEdit {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                font-size: 12pt;
            }
            QPushButton {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                font-size: 12pt;
            }
        """)
        login_layout = QVBoxLayout(login_frame)
        login_layout.setContentsMargins(8, 8, 8, 8)
        login_layout.setSpacing(8)

        # 创建水平布局用于登录控件
        login_controls = QHBoxLayout()
        login_controls.setSpacing(8)

        # 手机号输入
        login_controls.addWidget(QLabel("📱 手机号:"))
        self.phone_input = QLineEdit()
        self.phone_input.setFixedWidth(180)
        self.phone_input.setText("15239851762")
        login_controls.addWidget(self.phone_input)

        # 登录按钮
        login_btn = QPushButton("🚀 登录")
        login_btn.setObjectName("login_btn")
        login_btn.setFixedWidth(100)
        login_btn.clicked.connect(self.login)
        login_controls.addWidget(login_btn)

        # 添加免责声明
        disclaimer_label = QLabel("⚠️ 仅限于学习,请勿用于其他用途,否则后果自负")
        disclaimer_label.setStyleSheet("""
            color: #e74c3c;
            font-size: 11pt;
            font-weight: bold;
        """)
        login_controls.addWidget(disclaimer_label)

        login_controls.addStretch()
        login_layout.addLayout(login_controls)
        parent_layout.addWidget(login_frame)

    def create_left_section(self, parent_layout):
        """创建左侧区域"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(8)

        # 标题编辑区域
        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                padding: 12px;
                background-color: white;
            }
            QLabel {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                font-size: 11pt;
                color: #2c3e50;
                border: none;
                background: transparent;
            }
            QLineEdit {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                padding: 4px;
                margin-bottom: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                max-height: 24px;
                min-width: 200px;
            }
            QLabel#section_title {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                font-size: 12pt;
                font-weight: bold;
                margin-bottom: 8px;
            }
        """)
        title_layout = QVBoxLayout(title_frame)
        title_layout.setSpacing(0)
        title_layout.setContentsMargins(12, 12, 12, 12)

        # 添加标题标签
        header_label = QLabel("✏️ 标题编辑")
        header_label.setObjectName("section_title")
        title_layout.addWidget(header_label)

        # 眉头标题输入框
        header_input_layout = QHBoxLayout()
        header_input_layout.setSpacing(8)
        header_label = QLabel("🏷️ 眉头标题")
        header_label.setFixedWidth(100)
        header_input_layout.addWidget(header_label)
        self.header_input = QLineEdit(self.parent.config.get_title_config()['title'])
        self.header_input.setMinimumWidth(250)
        self.header_input.textChanged.connect(self.update_title_config)
        header_input_layout.addWidget(self.header_input)
        title_layout.addLayout(header_input_layout)

        # 作者输入框
        author_input_layout = QHBoxLayout()
        author_input_layout.setSpacing(8)
        author_label = QLabel("👤 作者")
        author_label.setFixedWidth(100)
        author_input_layout.addWidget(author_label)
        self.author_input = QLineEdit(self.parent.config.get_title_config()['author'])
        self.author_input.setMinimumWidth(250)
        self.author_input.textChanged.connect(self.update_author_config)
        author_input_layout.addWidget(self.author_input)
        title_layout.addLayout(author_input_layout)

        # 标题输入框
        title_input_layout = QHBoxLayout()
        title_input_layout.setSpacing(8)
        title_label = QLabel("📌 标题")
        title_label.setFixedWidth(100)
        title_input_layout.addWidget(title_label)
        self.title_input = QLineEdit()
        title_input_layout.addWidget(self.title_input)
        title_layout.addLayout(title_input_layout)

        # 内容输入框
        content_input_layout = QHBoxLayout()
        content_input_layout.setSpacing(8)
        content_label = QLabel("📄 内容")
        content_label.setFixedWidth(100)
        content_input_layout.addWidget(content_label)
        self.subtitle_input = QTextEdit()
        self.subtitle_input.setMinimumHeight(120)
        self.subtitle_input.setStyleSheet("""
            QTextEdit {
                font-size: 11pt;
                line-height: 1.5;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
        """)
        content_input_layout.addWidget(self.subtitle_input)
        title_layout.addLayout(content_input_layout)

        # 添加垂直间距
        title_layout.addSpacing(25)

        # 内容输入区域
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                padding: 12px;
                background-color: white;
                margin-top: 8px;
            }
            QLabel {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                font-size: 12pt;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }
            QTextEdit {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                font-size: 11pt;
                line-height: 1.5;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QPushButton {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                min-width: 100px;
                padding: 8px 15px;
                font-weight: bold;
                margin-top: 10px;
            }
        """)
        input_layout = QVBoxLayout(input_frame)
        input_layout.setSpacing(0)
        input_layout.setContentsMargins(12, 12, 12, 12)

        input_label = QLabel("✏️ 内容输入")
        input_layout.addWidget(input_label)

        # 创建一个水平布局来包含输入框和按钮
        input_container = QWidget()
        input_container_layout = QVBoxLayout(input_container)
        input_container_layout.setContentsMargins(0, 0, 0, 0)
        input_container_layout.setSpacing(0)

        # 添加输入框
        self.input_text = QTextEdit()
        self.input_text.setMinimumHeight(120)
        self.input_text.setPlainText("中医的好处")
        input_container_layout.addWidget(self.input_text)

        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        button_layout.addStretch()

        # 将生成按钮保存为类属性
        self.generate_btn = QPushButton("✨ 生成内容")
        self.generate_btn.clicked.connect(self.generate_content)
        button_layout.addWidget(self.generate_btn)

        input_container_layout.addLayout(button_layout)
        input_layout.addWidget(input_container)

        # 添加到主布局
        left_layout.addWidget(title_frame)
        left_layout.addWidget(input_frame)
        parent_layout.addWidget(left_widget)

    def create_preview_section(self, parent_layout):
        """创建预览区域"""
        preview_frame = QFrame()
        preview_frame.setStyleSheet("""
            QFrame {
                padding: 15px;
                background-color: white;
                border: 1px solid #e1e4e8;
                border-radius: 8px;
            }
            QLabel {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                font-size: 11pt;
                color: #2c3e50;
                border: none;
                background: transparent;
            }
            QWidget#image_container {
                background-color: white;
            }
            QPushButton {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                padding: 15px;
                font-weight: bold;
                border-radius: 20px;
                background-color: rgba(74, 144, 226, 0.1);
                color: #4a90e2;
            }
            QPushButton:hover {
                background-color: rgba(74, 144, 226, 0.2);
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #aaa;
            }
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setSpacing(15)
        preview_layout.setContentsMargins(15, 15, 15, 15)

        # 添加标题标签
        header_layout = QHBoxLayout()
        title_label = QLabel("🖼️ 图片预览")
        title_label.setStyleSheet(
            "font-size: 13pt; font-weight: bold; color: #2c3e50; padding-bottom: 5px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        preview_layout.addLayout(header_layout)

        # 图片预览区域（包含左右按钮）
        image_preview_layout = QHBoxLayout()
        image_preview_layout.setSpacing(10)
        image_preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 左侧按钮
        self.prev_btn = QPushButton("<")
        self.prev_btn.setFixedSize(40, 40)
        self.prev_btn.clicked.connect(self.prev_image)
        image_preview_layout.addWidget(self.prev_btn)

        # 图片容器
        image_container = QWidget()
        image_container.setFixedSize(380, 380)
        image_container.setStyleSheet("""
            background-color: white;
            border: 2px solid #e1e4e8;
            border-radius: 8px;
        """)
        image_container_layout = QVBoxLayout(image_container)
        image_container_layout.setContentsMargins(5, 5, 5, 5)
        image_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 图片标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(360, 360)
        self.image_label.setStyleSheet("border: none;")
        image_container_layout.addWidget(self.image_label)

        image_preview_layout.addWidget(image_container)

        # 右侧按钮
        self.next_btn = QPushButton(">")
        self.next_btn.setFixedSize(40, 40)
        self.next_btn.clicked.connect(self.next_image)
        image_preview_layout.addWidget(self.next_btn)

        preview_layout.addLayout(image_preview_layout)

        # 图片标题
        self.image_title = QLabel("暂无图片")
        self.image_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_title.setStyleSheet("""
            font-weight: bold;
            color: #2c3e50;
            font-size: 12pt;
            padding: 10px 0;
        """)
        preview_layout.addWidget(self.image_title)

        # 添加预览发布按钮
        preview_btn = QPushButton("🎯 预览发布")
        preview_btn.setObjectName("preview_btn")
        preview_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                font-size: 12pt;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 15px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        preview_btn.clicked.connect(self.preview_post)
        preview_btn.setEnabled(False)
        preview_layout.addWidget(
            preview_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # 初始化时禁用按钮
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

        parent_layout.addWidget(preview_frame)

    def login(self):
        try:
            phone = self.phone_input.text()

            if not phone:
                TipWindow(self.parent, "❌ 请输入手机号").show()
                return

            # 更新登录按钮状态
            self.parent.update_login_button("⏳ 登录中...", False)

            # 添加登录任务到浏览器线程
            self.parent.browser_thread.action_queue.append({
                'type': 'login',
                'phone': phone
            })

        except Exception as e:
            TipWindow(self.parent, f"❌ 登录失败: {str(e)}").show()

    def handle_login_error(self, error_msg):
        # 恢复登录按钮状态
        self.parent.update_login_button("🚀 登录", True)
        TipWindow(self.parent, f"❌ 登录失败: {error_msg}").show()

    def handle_poster_ready(self, poster):
        """处理登录成功后的poster对象"""
        self.parent.poster = poster
        # 更新登录按钮状态
        self.parent.update_login_button("✅ 已登录", False)
        TipWindow(self.parent, "✅ 登录成功").show()

    def generate_content(self):
        try:
            input_text = self.input_text.toPlainText().strip()
            if not input_text:
                TipWindow(self.parent, "❌ 请输入内容").show()
                return

            # 创建并启动生成线程
            self.parent.generator_thread = ContentGeneratorThread(
                input_text,
                self.header_input.text(),
                self.author_input.text(),
                self.generate_btn  # 传递按钮引用
            )
            self.parent.generator_thread.finished.connect(
                self.handle_generation_result)
            self.parent.generator_thread.error.connect(self.handle_generation_error)
            self.parent.generator_thread.start()

        except Exception as e:
            self.generate_btn.setText("✨ 生成内容")  # 恢复按钮文字
            self.generate_btn.setEnabled(True)  # 恢复按钮可点击状态
            TipWindow(self.parent, f"❌ 生成内容失败: {str(e)}").show()

    def handle_generation_result(self, result):
        self.update_ui_after_generate(
            result['title'],
            result['content'],
            result['cover_image'],
            result['content_images'],
            result['input_text']
        )

    def handle_generation_error(self, error_msg):
        TipWindow(self.parent, f"❌ 生成内容失败: {error_msg}").show()

    def update_ui_after_generate(self, title, content, cover_image_url, content_image_urls, input_text):
        try:
            # 创建并启动图片处理线程
            self.parent.image_processor = ImageProcessorThread(
                cover_image_url, content_image_urls)
            self.parent.image_processor.finished.connect(
                self.handle_image_processing_result)
            self.parent.image_processor.error.connect(
                self.handle_image_processing_error)
            self.parent.image_processor.start()

            # 更新标题和内容
            self.title_input.setText(title if title else "")
            self.subtitle_input.setText(content if content else "")

            # 安全地更新文本编辑器内容
            if input_text:
                self.input_text.clear()  # 先清空内容
                # 使用setPlainText而不是setText
                self.input_text.setPlainText(input_text)
            else:
                self.input_text.clear()

            # 清空之前的图片列表
            self.images = []
            self.image_list = []
            self.current_image_index = 0

            # 显示占位图
            self.image_label.setPixmap(self.placeholder_photo)
            self.image_title.setText("正在加载图片...")

        except Exception as e:
            print(f"更新UI时出错: {str(e)}")
            TipWindow(self.parent, f"❌ 更新内容失败: {str(e)}").show()

    def handle_image_processing_result(self, images, image_list):
        try:
            self.images = images
            self.image_list = image_list

            # 打印调试信息
            print(f"收到图片处理结果: {len(images)} 张图片")

            if self.image_list:
                # 确保当前索引有效
                self.current_image_index = 0
                # 显示第一张图片
                current_image = self.image_list[self.current_image_index]
                if current_image and 'pixmap' in current_image:
                    self.image_label.setPixmap(current_image['pixmap'])
                    self.image_title.setText(current_image['title'])
                    # 更新按钮状态
                    self.prev_btn.setEnabled(len(self.image_list) > 1)
                    self.next_btn.setEnabled(len(self.image_list) > 1)
                    # 启用预览发布按钮
                    self.parent.update_preview_button("🎯 预览发布", True)
                else:
                    raise Exception("图片数据无效")
            else:
                raise Exception("没有可显示的图片")

        except Exception as e:
            print(f"处理图片结果时出错: {str(e)}")
            self.image_label.setPixmap(self.placeholder_photo)
            self.image_title.setText("图片加载失败")
            # 禁用预览发布按钮
            self.parent.update_preview_button("🎯 预览发布", False)
            TipWindow(self.parent, f"❌ 图片加载失败: {str(e)}").show()

    def handle_image_processing_error(self, error_msg):
        self.image_label.setPixmap(self.placeholder_photo)
        self.image_title.setText("图片加载失败")
        # 禁用预览发布按钮
        self.parent.update_preview_button("🎯 预览发布", False)
        TipWindow(self.parent, f"❌ 图片处理失败: {error_msg}").show()

    def show_current_image(self):
        if not self.image_list:
            self.image_label.setPixmap(self.placeholder_photo)
            self.image_title.setText("暂无图片")
            self.update_button_states()
            return

        current_image = self.image_list[self.current_image_index]
        self.image_label.setPixmap(current_image['pixmap'])
        self.image_title.setText(current_image['title'])
        self.update_button_states()

    def update_button_states(self):
        has_images = bool(self.image_list)
        self.prev_btn.setEnabled(has_images)
        self.next_btn.setEnabled(has_images)

    def prev_image(self):
        if self.image_list:
            self.current_image_index = (
                self.current_image_index - 1) % len(self.image_list)
            self.show_current_image()

    def next_image(self):
        if self.image_list:
            self.current_image_index = (
                self.current_image_index + 1) % len(self.image_list)
            self.show_current_image()

    def preview_post(self):
        try:
            if not self.parent.browser_thread.poster:
                TipWindow(self.parent, "❌ 请先登录").show()
                return

            title = self.title_input.text()
            content = self.subtitle_input.toPlainText()

            # 更新预览按钮状态
            self.parent.update_preview_button("⏳ 发布中...", False)

            # 添加预览任务到浏览器线程
            self.parent.browser_thread.action_queue.append({
                'type': 'preview',
                'title': title,
                'content': content,
                'images': self.images
            })

        except Exception as e:
            TipWindow(self.parent, f"❌ 预览发布失败: {str(e)}").show()

    def handle_preview_result(self):
        # 恢复预览按钮状态
        self.parent.update_preview_button("🎯 预览发布", True)
        TipWindow(self.parent, "🎉 文章已准备好，请在浏览器中检查并发布").show()

    def handle_preview_error(self, error_msg):
        # 恢复预览按钮状态
        self.parent.update_preview_button("🎯 预览发布", True)
        TipWindow(self.parent, f"❌ 预览发布失败: {error_msg}").show()

    def update_title_config(self):
        """更新标题配置"""
        try:
            title_config = self.parent.config.get_title_config()
            title_config['title'] = self.header_input.text()
            self.parent.config.update_title_config(title_config['title'])
        except Exception as e:
            self.parent.logger.error(f"更新标题配置失败: {str(e)}")

    def update_author_config(self):
        """更新作者配置"""
        try:
            title_config = self.parent.config.get_title_config()
            title_config['author'] = self.author_input.text()
            self.parent.config.update_author_config(title_config['author'])
        except Exception as e:
            self.parent.logger.error(f"更新作者配置失败: {str(e)}")

class ToolsPage(QWidget):
    """工具箱页面类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        self.media_cache = {}  # 用于缓存已下载的媒体文件

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #f1f1f1;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #888;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical {
                height: 0px;
            }
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # 创建内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 10, 15, 10)
        content_layout.setSpacing(8)

        # 创建视频去水印工具区域
        watermark_frame = QFrame()
        watermark_frame.setStyleSheet("""
            QFrame {
                padding: 15px;
                background-color: white;
                border: 1px solid #e1e4e8;
                border-radius: 8px;
            }
            QLabel {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                font-size: 12pt;
                color: #2c3e50;
            }
            QLineEdit {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                padding: 8px;
                font-size: 12pt;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QPushButton {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                padding: 10px;
                font-size: 14pt;
                font-weight: bold;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        watermark_layout = QVBoxLayout(watermark_frame)
        
        # 添加标题
        title_label = QLabel("⚡ 视频平台水印去除工具")
        title_label.setStyleSheet("""
            font-size: 16pt;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
        """)
        watermark_layout.addWidget(title_label)
        
        # URL输入框
        url_label = QLabel("* 请输入 URL 地址")
        url_label.setStyleSheet("color: #e74c3c; font-size: 12pt;")
        watermark_layout.addWidget(url_label)
        
        url_input = QLineEdit()
        url_input.setPlaceholderText("请输入平台对应的 URL 地址 ~")
        url_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                font-size: 12pt;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
        """)
        watermark_layout.addWidget(url_input)
        
        # 支持平台说明
        platform_label = QLabel("支持平台列表如下: (可点击图标进行测试)")
        platform_label.setStyleSheet("color: #7f8c8d; margin-top: 15px;")
        watermark_layout.addWidget(platform_label)
        
        # 平台图标列表
        platform_widget = QWidget()
        platform_layout = QHBoxLayout(platform_widget)
        platform_layout.setSpacing(20)
        
        platforms = [
            ("快手", "ks.png", "https://v.kuaishou.com/xxxxx"),
            ("皮皮虾", "ppx.png", "https://h5.pipix.com/item/xxxxx"), 
            ("抖音", "dy.png", "https://v.douyin.com/xxxxx"),
            ("微视", "ws.png", "https://h5.weibo.cn/xxxxx"),
            ("小红书", "xhs.png", "https://www.xiaohongshu.com/explore/xxxxx"),
            ("最右", "zy.png", "https://share.izuiyou.com/xxxxx")
        ]
        
        for name, icon, example_url in platforms:
            btn = QPushButton()
            btn.setIcon(QIcon(f"icons/{icon}"))
            btn.setFixedSize(50, 50)
            btn.setToolTip(f"点击填充{name}示例链接")
            btn.clicked.connect(lambda checked, url=example_url: self.fill_example_url(url))
            platform_layout.addWidget(btn)
        
        watermark_layout.addWidget(platform_widget)
        
        # 处理按钮
        process_btn = QPushButton("⚡ 开始处理")
        process_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                font-size: 14pt;
                font-weight: bold;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        # 保存url_input为类属性以便在其他方法中访问
        self.url_input = url_input
        # 连接点击事件到处理函数
        process_btn.clicked.connect(self.process_video)
        watermark_layout.addWidget(process_btn)
        
        # 创建结果展示区域
        result_frame = QFrame()
        result_frame.setStyleSheet("""
            QFrame {
                margin-top: 20px;
                padding: 20px;
                background-color: white;
                border: 1px solid #e1e4e8;
                border-radius: 12px;
            }
            QLabel {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                color: #2c3e50;
            }
            QTextEdit {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                font-size: 11pt;
                line-height: 1.6;
                padding: 15px;
                background-color: white;
                border: none;
                border-radius: 8px;
            }
            QLabel#section_header {
                font-size: 14pt;
                font-weight: bold;
                color: #1a1a1a;
                padding: 5px 0;
                margin-top: 10px;
            }
            QLabel#section_content {
                font-size: 12pt;
                color: #666666;
                padding: 3px 0;
            }
            QLabel#section_divider {
                background-color: #f5f5f5;
                min-height: 1px;
                margin: 10px 0;
            }
            QLabel#download_link {
                color: #4a90e2;
                text-decoration: underline;
                cursor: pointer;
            }
        """)
        result_layout = QVBoxLayout(result_frame)
        result_layout.setSpacing(0)
        result_layout.setContentsMargins(0, 0, 0, 0)

        # 添加结果标题
        result_title = QLabel("📋 解析结果")
        result_title.setStyleSheet("""
            font-size: 16pt;
            font-weight: bold;
            color: #1a1a1a;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        """)
        result_layout.addWidget(result_title)

        # 创建结果文本展示区
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit {
                font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
                font-size: 11pt;
                line-height: 1.6;
                padding: 15px;
                background-color: white;
                border: none;
            }
        """)
        self.result_text.setMinimumHeight(400)
        result_layout.addWidget(self.result_text)

        # 将结果区域添加到水印工具布局中
        watermark_layout.addWidget(result_frame)

        # 将水印工具添加到内容布局
        content_layout.addWidget(watermark_frame)
        content_layout.addStretch()

        # 设置滚动区域的内容
        scroll_area.setWidget(content_widget)

        # 将滚动区域添加到工具箱页面
        layout.addWidget(scroll_area)

    def process_video(self):
        try:
            url = self.url_input.text().strip()
            if not url:
                TipWindow(self.parent, "❌ 请输入视频URL").show()
                return
            
            # 调用API
            server = "http://127.0.0.1:8000/xhs/"
            data = {
                "url": url,
                "download": True,
                "index": [3, 6, 9]
            }
            
            # 发送请求并处理结果
            response = requests.post(server, json=data)
            result = response.json()
            
            # 格式化显示结果
            if 'data' in result:
                data = result['data']
                # 创建预览区域的HTML
                preview_html = self.create_media_preview_html(data.get('下载地址', []))
                
                formatted_result = f"""
<h2 style='color: #1a1a1a; margin-bottom: 20px;'>🎥 作品信息</h2>

<div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;'>
    <div style='font-size: 14pt; font-weight: bold; color: #1a1a1a; margin-bottom: 10px;'>{data.get('作品标题', 'N/A')}</div>
    <div style='color: #666666; margin-bottom: 5px;'>📝 {data.get('作品描述', 'N/A')}</div>
    <div style='color: #999999; font-size: 10pt;'>
        {data.get('作品类型', 'N/A')} · {data.get('发布时间', 'N/A')}
    </div>
</div>

<h3 style='color: #1a1a1a; margin: 15px 0;'>👤 创作者信息</h3>
<div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;'>
    <div style='font-weight: bold; color: #1a1a1a;'>{data.get('作者昵称', 'N/A')}</div>
    <div style='color: #666666;'>ID: {data.get('作者ID', 'N/A')}</div>
</div>

<h3 style='color: #1a1a1a; margin: 15px 0;'>📊 数据统计</h3>
<div style='display: flex; align-items: center; background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;'>
    <div style='flex: 1; text-align: center; position: relative;'>
        <div style='display: flex; align-items: center; justify-content: center; gap: 8px;'>
            <span style='font-size: 16pt; font-weight: bold; color: #1a1a1a;'>{data.get('点赞数量', 'N/A')}</span>
            <span style='color: #666666;'>👍 点赞</span>
        </div>
    </div>
    <div style='width: 1px; height: 24px; background-color: #e1e4e8;'></div>
    <div style='flex: 1; text-align: center; position: relative;'>
        <div style='display: flex; align-items: center; justify-content: center; gap: 8px;'>
            <span style='font-size: 16pt; font-weight: bold; color: #1a1a1a;'>{data.get('收藏数量', 'N/A')}</span>
            <span style='color: #666666;'>⭐ 收藏</span>
        </div>
    </div>
    <div style='width: 1px; height: 24px; background-color: #e1e4e8;'></div>
    <div style='flex: 1; text-align: center; position: relative;'>
        <div style='display: flex; align-items: center; justify-content: center; gap: 8px;'>
            <span style='font-size: 16pt; font-weight: bold; color: #1a1a1a;'>{data.get('评论数量', 'N/A')}</span>
            <span style='color: #666666;'>💬 评论</span>
        </div>
    </div>
    <div style='width: 1px; height: 24px; background-color: #e1e4e8;'></div>
    <div style='flex: 1; text-align: center; position: relative;'>
        <div style='display: flex; align-items: center; justify-content: center; gap: 8px;'>
            <span style='font-size: 16pt; font-weight: bold; color: #1a1a1a;'>{data.get('分享数量', 'N/A')}</span>
            <span style='color: #666666;'>🔄 分享</span>
        </div>
    </div>
</div>

<h3 style='color: #1a1a1a; margin: 15px 0;'>🏷️ 标签</h3>
<div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;'>
    <div style='color: #4a90e2;'>{data.get('作品标签', 'N/A')}</div>
</div>

<h3 style='color: #1a1a1a; margin: 15px 0;'>🔗 链接</h3>
<div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;'>
    <div style='margin-bottom: 5px;'><span style='color: #666666;'>作品链接：</span><a href='{data.get('作品链接', '#')}' style='color: #4a90e2;'>{data.get('作品链接', 'N/A')}</a></div>
    <div><span style='color: #666666;'>作者主页：</span><a href='{data.get('作者链接', '#')}' style='color: #4a90e2;'>{data.get('作者链接', 'N/A')}</a></div>
</div>

<h3 style='color: #1a1a1a; margin: 15px 0;'>📥 媒体预览</h3>
{preview_html}
"""
                # 更新结果显示
                self.result_text.setHtml(formatted_result)
                
                # 显示成功提示
                TipWindow(self.parent, "✅ 解析成功").show()
            else:
                error_message = f"""
<div style='background-color: #fee2e2; padding: 15px; border-radius: 8px; margin: 10px 0;'>
    <div style='color: #dc2626; font-weight: bold;'>❌ 解析失败</div>
    <div style='color: #7f1d1d; margin-top: 5px;'>{result.get('message', '未知错误')}</div>
</div>
"""
                self.result_text.setHtml(error_message)
                TipWindow(self.parent, "❌ 解析失败").show()
            
        except Exception as e:
            print("处理视频时出错:", str(e))
            error_message = f"""
<div style='background-color: #fee2e2; padding: 15px; border-radius: 8px; margin: 10px 0;'>
    <div style='color: #dc2626; font-weight: bold;'>❌ 处理出错</div>
    <div style='color: #7f1d1d; margin-top: 5px;'>{str(e)}</div>
</div>
"""
            self.result_text.setHtml(error_message)
            TipWindow(self.parent, f"❌ 处理失败: {str(e)}").show()

    def create_media_preview_html(self, urls):
        """创建媒体预览的HTML"""
        if not urls:
            return "<div style='color: #666666;'>暂无可下载的媒体文件</div>"

        preview_html = "<div style='display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;'>"
        
        # 创建线程池
        with ThreadPoolExecutor(max_workers=5) as executor:
            # 提交所有图片加载任务
            future_to_url = {executor.submit(self.load_image, url): url for url in urls}
            
            # 处理完成的任务
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result['success']:
                        preview_html += f"""
                        <div style='background-color: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center;'>
                            <img src="{result['data']}" style='width: 100%; max-width: 300px; border-radius: 4px; object-fit: cover;' loading="lazy">
                            <div style='margin-top: 8px;'>
                                <a href="{url}" style='color: #4a90e2; text-decoration: none;' target="_blank">下载图片</a>
                            </div>
                        </div>
                        """
                    else:
                        preview_html += f"""
                        <div style='background-color: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center;'>
                            <div style='color: #666666; margin-bottom: 8px;'>图片加载失败</div>
                            <a href="{url}" style='color: #4a90e2; text-decoration: none;' target="_blank">下载图片</a>
                        </div>
                        """
                except Exception as e:
                    print(f"处理图片结果时出错: {str(e)}")
                    preview_html += f"""
                    <div style='background-color: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center;'>
                        <div style='color: #666666; margin-bottom: 8px;'>处理图片时出错</div>
                        <a href="{url}" style='color: #4a90e2; text-decoration: none;' target="_blank">下载图片</a>
                    </div>
                    """
        
        preview_html += "</div>"
        return preview_html

    def fill_example_url(self, url):
        """填充示例URL"""
        self.url_input.setText(url)
        TipWindow(self.parent, "已填充示例链接，请替换为实际链接").show()

    def load_image(self, url):
        """加载单个图片"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.xiaohongshu.com/'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            content_type = response.headers.get('content-type', 'image/jpeg')
            image_data = base64.b64encode(response.content).decode('utf-8')
            return {
                'success': True,
                'url': url,
                'data': f"data:{content_type};base64,{image_data}"
            }
        except Exception as e:
            print(f"加载图片失败: {str(e)}")
            return {
                'success': False,
                'url': url,
                'error': str(e)
            }

class SettingsPage(QWidget):
    """设置页面类"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setObjectName("settingsPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # 添加版本信息
        version_label = QLabel(f"版本号: v{VERSION}")
        version_label.setStyleSheet("""
            font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
            font-size: 14pt;
            color: #2c3e50;
            font-weight: bold;
        """)
        layout.addWidget(version_label)
        layout.addStretch()

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
        self.browser_thread.login_success.connect(self.home_page.handle_poster_ready)
        self.browser_thread.login_error.connect(self.home_page.handle_login_error)
        self.browser_thread.preview_success.connect(self.home_page.handle_preview_result)
        self.browser_thread.preview_error.connect(self.home_page.handle_preview_error)
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
