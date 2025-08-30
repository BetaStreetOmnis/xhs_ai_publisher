import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTextEdit, QVBoxLayout, QWidget, QMessageBox)

import os
from src.core.alert import TipWindow
from src.core.processor.content import ContentGeneratorThread
from src.core.processor.img import ImageProcessorThread

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
        self.phone_input.setText(self.parent.config.get_phone_config())
        self.phone_input.textChanged.connect(self.update_phone_config)
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
        self.header_input = QLineEdit(
            self.parent.config.get_title_config()['title'])
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
        self.author_input = QLineEdit(
            self.parent.config.get_title_config()['author'])
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
        
        # 添加封面模板按钮
        template_btn = QPushButton("🎨 封面模板")
        template_btn.clicked.connect(self.open_template_library)
        button_layout.addWidget(template_btn)

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
        image_preview_layout.setAlignment(Qt.AlignCenter)

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
        image_container_layout.setAlignment(Qt.AlignCenter)

        # 图片标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
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
        self.image_title.setAlignment(Qt.AlignCenter)
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
            preview_btn, alignment=Qt.AlignCenter)

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
            self.parent.generator_thread.error.connect(
                self.handle_generation_error)
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

    def handle_generation_error(self, error_message):
        """处理生成错误，提供用户友好的错误信息和解决建议"""
        print(f"错误信息: {error_message}")
        
        # 根据错误类型提供具体的用户友好提示
        if "主API和备用生成器都失败了" in error_message:
            user_message = (
                "❌ 内容生成失败\n\n"
                "主API服务和本地备用生成器都遇到了问题。\n\n"
                "可能的解决方案：\n"
                "• 检查网络连接是否正常\n"
                "• 稍后再试，服务可能临时不可用\n"
                "• 尝试简化输入内容\n"
                "• 重启应用程序"
            )
        elif "网络连接失败" in error_message:
            user_message = (
                "🌐 网络连接失败\n\n"
                "无法连接到内容生成服务。\n\n"
                "解决方案：\n"
                "• 检查网络连接是否正常\n"
                "• 确认防火墙设置允许应用访问网络\n"
                "• 尝试切换网络环境\n"
                "• 系统将自动尝试使用备用生成器"
            )
        elif "API请求超时" in error_message:
            user_message = (
                "⏰ 请求超时\n\n"
                "服务器响应时间过长。\n\n"
                "解决方案：\n"
                "• 检查网络速度\n"
                "• 尝试减少输入内容的长度\n"
                "• 稍后重试\n"
                "• 系统将自动尝试使用备用生成器"
            )
        elif "状态码: 404" in error_message:
            user_message = (
                "🔍 服务不可用\n\n"
                "内容生成服务接口不存在或已更改。\n\n"
                "解决方案：\n"
                "• 检查应用是否为最新版本\n"
                "• 联系技术支持获取帮助\n"
                "• 系统将自动尝试使用备用生成器"
            )
        elif "状态码: 500" in error_message:
            user_message = (
                "🔧 服务器错误\n\n"
                "内容生成服务遇到内部错误。\n\n"
                "解决方案：\n"
                "• 稍后重试，问题可能是临时的\n"
                "• 如果问题持续，请联系技术支持\n"
                "• 系统将自动尝试使用备用生成器"
            )
        elif "状态码: 400" in error_message:
            user_message = (
                "📝 请求格式错误\n\n"
                "请求参数可能有误或API格式已更改。\n\n"
                "解决方案：\n"
                "• 检查输入内容是否包含特殊字符\n"
                "• 尝试简化输入内容\n"
                "• 确保应用为最新版本\n"
                "• 系统将自动尝试使用备用生成器"
            )
        elif "JSON解析失败" in error_message:
            user_message = (
                "📊 数据解析错误\n\n"
                "服务器返回的数据格式异常。\n\n"
                "解决方案：\n"
                "• 重试操作\n"
                "• 如果问题持续，请联系技术支持\n"
                "• 系统将自动尝试使用备用生成器"
            )
        elif "备用生成器" in error_message and "失败" in error_message:
            user_message = (
                "⚠️ 备用生成器错误\n\n"
                "本地备用内容生成器遇到问题。\n\n"
                "解决方案：\n"
                "• 重启应用程序\n"
                "• 检查输入内容是否过长或包含特殊字符\n"
                "• 尝试简化输入内容\n"
                "• 联系技术支持获取帮助"
            )
        else:
            user_message = (
                "❓ 生成失败\n\n"
                "内容生成过程中遇到未知错误。\n\n"
                "解决方案：\n"
                "• 检查输入内容格式\n"
                "• 重试操作\n"
                "• 如果问题持续，请联系技术支持\n"
                "• 系统已尝试多种生成方式"
            )
        
        # 显示用户友好的错误消息
        QMessageBox.warning(self, "内容生成失败", user_message)

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
            # 使用用户输入的新标题
            new_title = self.header_input.text()
            self.parent.config.update_title_config(new_title)
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

    def update_phone_config(self):
        """更新手机号配置"""
        try:
            new_phone = self.phone_input.text()
            self.parent.config.update_phone_config(new_phone)
        except Exception as e:
            self.parent.logger.error(f"更新手机号配置失败: {str(e)}")

    def apply_generated_cover(self, cover_path):
        """应用生成的封面图片"""
        try:
            if os.path.exists(cover_path):
                # 清空现有图片列表，将新封面设为第一张图片
                self.images = [cover_path]
                self.image_list = []
                self.current_image_index = 0
                
                # 创建预览图片
                from PIL import Image
                import io
                from PyQt5.QtGui import QImage
                
                # 处理图片预览
                image = Image.open(cover_path)
                max_size = 360
                width, height = image.size
                scale = min(max_size/width, max_size/height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                
                # 缩放图片
                image = image.resize((new_width, new_height), Image.LANCZOS)
                
                # 创建白色背景
                background = Image.new('RGB', (max_size, max_size), 'white')
                offset = ((max_size - new_width) // 2, (max_size - new_height) // 2)
                background.paste(image, offset)
                
                # 转换为QPixmap
                img_bytes = io.BytesIO()
                background.save(img_bytes, format='PNG')
                img_data = img_bytes.getvalue()
                
                qimage = QImage.fromData(img_data)
                pixmap = QPixmap.fromImage(qimage)
                
                if not pixmap.isNull():
                    self.image_list = [{'pixmap': pixmap, 'title': '模板封面'}]
                    # 更新预览显示
                    self.update_image_display()
                    
                    # 显示提示
                    TipWindow(self.parent, "✅ 模板封面已应用").show()
                else:
                    TipWindow(self.parent, "❌ 封面图片加载失败").show()
            else:
                TipWindow(self.parent, "❌ 封面文件不存在").show()
                
        except Exception as e:
            self.parent.logger.error(f"应用生成封面失败: {str(e)}")
            TipWindow(self.parent, f"❌ 应用封面失败: {str(e)}").show()

    def open_template_library(self):
        """打开封面模板库"""
        try:
            # 切换到封面模板页面
            self.parent.switch_page(3)  # 封面模板页面的索引
            
            # 如果有生成的标题，自动填入模板页面
            if hasattr(self, 'title_output') and self.title_output.toPlainText().strip():
                title_text = self.title_output.toPlainText().strip()
                if hasattr(self.parent, 'cover_template_page'):
                    self.parent.cover_template_page.set_title_text(title_text)
            
        except Exception as e:
            self.parent.logger.error(f"打开模板库失败: {str(e)}")
            TipWindow(self.parent, f"❌ 打开模板库失败: {str(e)}").show()
