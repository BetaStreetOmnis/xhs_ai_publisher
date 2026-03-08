import shutil
import time

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QColor, QPixmap, QDesktopServices
from PyQt5.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTextEdit, QVBoxLayout, QWidget, QMessageBox, QComboBox, QFileDialog, QInputDialog)

import os
from src.core.alert import TipWindow
from src.core.pages.scheduled_publish_dialog import ScheduledPublishDialog
from src.core.processor.content import ContentGeneratorThread
from src.core.processor.img import ImageProcessorThread
from src.core.processor.chrome_session_import import ChromeSessionImportThread
from src.core.processor.wechat_import import WechatArticleImportThread
from src.core.services.chrome_profile_service import detect_chrome_profiles
from src.core.ui.qt_font import get_ui_text_font_family_css

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
        self.wechat_import_thread = None
        # 创建占位图
        self.placeholder_photo = QPixmap(360, 480)
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
        login_frame.setStyleSheet(f"""
            QFrame {{
                padding: 8px;
                background-color: white;
            }}
            QLabel {{
                font-family: {get_ui_text_font_family_css()};
                font-size: 12pt;
                border: none;
                background: transparent;
            }}
            QLineEdit {{
                font-family: {get_ui_text_font_family_css()};
                font-size: 12pt;
            }}
            QPushButton {{
                font-family: {get_ui_text_font_family_css()};
                font-size: 12pt;
            }}
        """)
        login_layout = QVBoxLayout(login_frame)
        login_layout.setContentsMargins(8, 8, 8, 8)
        login_layout.setSpacing(8)

        # 创建水平布局用于登录控件
        login_controls = QHBoxLayout()
        login_controls.setSpacing(8)

        # 手机号输入
        login_controls.addWidget(QLabel("📱 手机号:"))
        self.country_code_combo = QComboBox()
        self.country_code_combo.setFixedWidth(118)
        for code, label in [
            ("+86", "+86 中国大陆"),
            ("+852", "+852 中国香港"),
            ("+853", "+853 中国澳门"),
            ("+886", "+886 中国台湾"),
            ("+1", "+1 US/CA"),
            ("+44", "+44 UK"),
            ("+81", "+81 日本"),
            ("+82", "+82 韩国"),
            ("+65", "+65 新加坡"),
        ]:
            self.country_code_combo.addItem(label, code)
        saved_country_code = str(self.parent.config.get_country_code_config() or "+86").strip() or "+86"
        country_index = self.country_code_combo.findData(saved_country_code)
        self.country_code_combo.setCurrentIndex(country_index if country_index >= 0 else 0)
        self.country_code_combo.currentIndexChanged.connect(self.update_country_code_config)
        login_controls.addWidget(self.country_code_combo)

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

        # 一键导入系统 Chrome 登录态（用于风控/扫码登录后复用）
        self.chrome_import_btn = QPushButton("🧩 导入登录态")
        self.chrome_import_btn.setFixedWidth(120)
        self.chrome_import_btn.clicked.connect(self.import_chrome_session)
        login_controls.addWidget(self.chrome_import_btn)

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

        # 登录/导入状态提示
        self.login_status_label = QLabel("")
        self.login_status_label.setStyleSheet(
            "color: #7f8c8d; font-size: 10.5pt; padding-left: 2px;"
        )
        self.login_status_label.setText("支持国家区号选择；如遇扫码/滑块风控，可点取消后在浏览器中手动完成登录。")
        login_layout.addWidget(self.login_status_label)
        parent_layout.addWidget(login_frame)

    def create_left_section(self, parent_layout):
        """创建左侧区域"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(8)

        # 标题编辑区域
        title_frame = QFrame()
        title_frame.setStyleSheet(f"""
            QFrame {{
                padding: 12px;
                background-color: white;
            }}
            QLabel {{
                font-family: {get_ui_text_font_family_css()};
                font-size: 11pt;
                color: #2c3e50;
                border: none;
                background: transparent;
            }}
            QLineEdit {{
                font-family: {get_ui_text_font_family_css()};
                padding: 4px;
                margin-bottom: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                max-height: 24px;
                min-width: 200px;
            }}
            QLabel#section_title {{
                font-family: {get_ui_text_font_family_css()};
                font-size: 12pt;
                font-weight: bold;
                margin-bottom: 8px;
            }}
        """)
        title_layout = QVBoxLayout(title_frame)
        title_layout.setSpacing(0)
        title_layout.setContentsMargins(12, 12, 12, 12)

        # 添加标题标签
        header_label = QLabel("📝 标题编辑")
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
        input_frame.setStyleSheet(f"""
            QFrame {{
                padding: 12px;
                background-color: white;
                margin-top: 8px;
            }}
            QLabel {{
                font-family: {get_ui_text_font_family_css()};
                font-size: 12pt;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 8px;
                border: none;
                background: transparent;
            }}
            QTextEdit {{
                font-family: {get_ui_text_font_family_css()};
                font-size: 11pt;
                line-height: 1.5;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }}
            QPushButton {{
                font-family: {get_ui_text_font_family_css()};
                padding: 6px 10px;
                font-weight: bold;
                margin-top: 0px;
            }}
            QPushButton#generate_btn {{
                min-width: 200px;
                padding: 8px 16px;
                margin-top: 10px;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 10px;
            }}
            QPushButton#generate_btn:hover {{
                background-color: #357abd;
            }}
            QPushButton#mini_btn {{
                min-width: 0px;
                padding: 6px 10px;
                margin-top: 0px;
                background-color: #f3f4f6;
                color: #111827;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                font-weight: 600;
            }}
            QPushButton#mini_btn:hover {{
                background-color: #e5e7eb;
            }}
            QPushButton#mini_primary_btn {{
                min-width: 0px;
                padding: 6px 12px;
                margin-top: 0px;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 700;
            }}
            QPushButton#mini_primary_btn:hover {{
                background-color: #357abd;
            }}
        """)
        input_layout = QVBoxLayout(input_frame)
        input_layout.setSpacing(0)
        input_layout.setContentsMargins(12, 12, 12, 12)

        input_label = QLabel("📝 内容输入")
        input_layout.addWidget(input_label)

        # 创建一个水平布局来包含输入框和按钮
        input_container = QWidget()
        input_container_layout = QVBoxLayout(input_container)
        input_container_layout.setContentsMargins(0, 0, 0, 0)
        input_container_layout.setSpacing(0)

        # 热点选择（来自数据中心缓存 / 一键跳转数据中心）
        hotspot_row = QHBoxLayout()
        hotspot_row.setContentsMargins(0, 0, 0, 8)
        hotspot_row.setSpacing(8)

        hotspot_label = QLabel("🔥 热点:")
        hotspot_label.setFixedWidth(90)
        hotspot_row.addWidget(hotspot_label)
        self.hotspot_combo = QComboBox()
        self.hotspot_combo.setMinimumWidth(260)
        self.hotspot_combo.currentIndexChanged.connect(self.on_hotspot_selected)
        hotspot_row.addWidget(self.hotspot_combo, 1)

        open_hot_btn = QPushButton("📊 热榜")
        open_hot_btn.setObjectName("mini_btn")
        open_hot_btn.setToolTip("打开数据中心查看热榜（刷新请在数据中心进行）")
        open_hot_btn.setFixedHeight(32)
        open_hot_btn.clicked.connect(self.open_data_center)
        hotspot_row.addWidget(open_hot_btn)

        input_container_layout.addLayout(hotspot_row)

        # 链接导入（解析标题/正文/图片，自动填充到小红书草稿）
        wechat_row = QHBoxLayout()
        wechat_row.setContentsMargins(0, 0, 0, 8)
        wechat_row.setSpacing(8)
        wechat_label = QLabel("🔗 导入:")
        wechat_label.setFixedWidth(90)
        wechat_row.addWidget(wechat_label)

        self.wechat_url_input = QLineEdit()
        self.wechat_url_input.setPlaceholderText("粘贴网页链接（支持公众号/通用网页，效果视站点而定）")
        try:
            self.wechat_url_input.setClearButtonEnabled(True)
        except Exception:
            pass
        wechat_row.addWidget(self.wechat_url_input, 1)

        self.wechat_import_btn = QPushButton("📥 导入")
        self.wechat_import_btn.setObjectName("mini_primary_btn")
        self.wechat_import_btn.setToolTip("从链接导入标题/正文/图片（公众号/通用网页）")
        self.wechat_import_btn.setFixedHeight(32)
        self.wechat_import_btn.clicked.connect(self.import_wechat_article)
        wechat_row.addWidget(self.wechat_import_btn)

        input_container_layout.addLayout(wechat_row)

        self.wechat_status_label = QLabel("")
        self.wechat_status_label.setStyleSheet("color: #6b7280; font-size: 10.5pt; font-weight: normal;")
        input_container_layout.addWidget(self.wechat_status_label)

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
        self.generate_btn.setObjectName("generate_btn")
        self.generate_btn.clicked.connect(self.generate_content)
        button_layout.addWidget(self.generate_btn)

        input_container_layout.addLayout(button_layout)

        # 避免生成中（按钮文案变长/高DPI）出现文字被截断：按“最长状态文案”的 sizeHint 动态设定最小宽度
        try:
            from PyQt5.QtWidgets import QSizePolicy

            self.generate_btn.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        except Exception:
            pass

        try:
            self.generate_btn.ensurePolished()
            candidates = [
                "✨ 生成内容",
                "⏳ 接口生成中...",
                "🤖 AI生成中...",
                "⏳ 本地生成中...",
                "🪧 生成营销海报中...",
                "⏳ 重试中(99/99)...",
            ]
            original_text = self.generate_btn.text()
            max_w = 0
            for t in candidates:
                self.generate_btn.setText(t)
                max_w = max(max_w, int(self.generate_btn.sizeHint().width() or 0))
            self.generate_btn.setText(original_text)

            if max_w > 0:
                self.generate_btn.setMinimumWidth(max(200, max_w + 8))
        except Exception:
            try:
                self.generate_btn.setMinimumWidth(240)
            except Exception:
                pass

        input_layout.addWidget(input_container)

        # 初次加载热点（不阻塞网络：只读取缓存；刷新请去数据中心）
        try:
            self.refresh_hotspot_options()
        except Exception:
            pass

        # 添加到主布局
        left_layout.addWidget(title_frame)
        left_layout.addWidget(input_frame)
        parent_layout.addWidget(left_widget)

    def create_preview_section(self, parent_layout):
        """创建预览区域"""
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                padding: 15px;
                background-color: white;
                border: 1px solid #e1e4e8;
                border-radius: 8px;
            }}
            QLabel {{
                font-family: {get_ui_text_font_family_css()};
                font-size: 11pt;
                color: #2c3e50;
                border: none;
                background: transparent;
            }}
            QWidget#image_container {{
                background-color: white;
            }}
            QPushButton {{
                font-family: {get_ui_text_font_family_css()};
                padding: 15px;
                font-weight: bold;
                border-radius: 20px;
                background-color: rgba(74, 144, 226, 0.1);
                color: #4a90e2;
            }}
            QPushButton:hover {{
                background-color: rgba(74, 144, 226, 0.2);
            }}
            QPushButton:disabled {{
                background-color: #f5f5f5;
                color: #aaa;
            }}
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

        # 跳转到封面模板库
        template_btn = QPushButton("🧩 封面模板")
        template_btn.setToolTip("打开封面中心的模板库")
        template_btn.setFixedHeight(32)
        template_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 10px;
                border-radius: 10px;
                background-color: #f3f4f6;
                color: #111827;
                font-size: 10.5pt;
            }
            QPushButton:hover { background-color: #e5e7eb; }
        """)
        template_btn.clicked.connect(self.open_cover_template_library)
        header_layout.addWidget(template_btn)

        # 图片下载
        download_btn = QPushButton("📥 下载图片")
        download_btn.setToolTip("将封面和内容图片保存到本地")
        download_btn.setFixedHeight(32)
        download_btn.setStyleSheet(template_btn.styleSheet())
        download_btn.clicked.connect(self.download_images)
        header_layout.addWidget(download_btn)
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
        image_container.setFixedSize(380, 520)
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
        self.image_label.setMinimumSize(360, 480)
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

        # 添加定时发布按钮
        self.schedule_btn = QPushButton("⏰ 定时发布")
        self.schedule_btn.setObjectName("schedule_btn")
        self.schedule_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                font-size: 12pt;
                background-color: #FF2442;
                color: white;
                border: none;
                border-radius: 15px;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #E91E63;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.schedule_btn.setToolTip("创建定时发布任务（支持固定内容/跟随热点）")
        self.schedule_btn.clicked.connect(self.schedule_publish)
        self.schedule_btn.setEnabled(True)
        preview_layout.addWidget(self.schedule_btn, alignment=Qt.AlignCenter)

        # 初始化时禁用按钮
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

        parent_layout.addWidget(preview_frame)

    def open_cover_template_library(self):
        """从首页跳转到封面模板库。"""
        try:
            if not self.parent:
                return

            # 切换到“封面中心”页面（main.py 中固定为 index=4）
            if hasattr(self.parent, "switch_page"):
                self.parent.switch_page(4)

            cover_page = getattr(self.parent, "cover_page", None)
            if cover_page and hasattr(cover_page, "show_template_library"):
                cover_page.show_template_library()
        except Exception as e:
            TipWindow(self.parent, f"❌ 打开模板库失败: {str(e)}").show()

    def download_images(self):
        """将当前生成的封面/内容图片导出到本地目录。"""
        try:
            if not getattr(self, "images", None):
                TipWindow(self.parent, "❌ 暂无图片可下载，请先生成内容").show()
                return

            desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.isdir(desktop_dir):
                desktop_dir = os.path.expanduser("~")

            base_dir = QFileDialog.getExistingDirectory(self, "选择保存目录", desktop_dir)
            if not base_dir:
                return

            ts = time.strftime("%Y%m%d_%H%M%S")
            out_dir = os.path.join(base_dir, f"xhs_images_{ts}")
            os.makedirs(out_dir, exist_ok=True)

            saved = 0
            for idx, src in enumerate(self.images):
                if not src or not os.path.isfile(src):
                    continue
                ext = os.path.splitext(src)[1].lower() or ".jpg"
                if idx == 0:
                    name = f"cover{ext}"
                else:
                    name = f"content_{idx}{ext}"
                dst = os.path.join(out_dir, name)
                shutil.copy2(src, dst)
                saved += 1

            if saved <= 0:
                TipWindow(self.parent, "❌ 保存失败：未找到可用图片文件").show()
                return

            # 打开目录方便用户查看
            try:
                QDesktopServices.openUrl(QUrl.fromLocalFile(out_dir))
            except Exception:
                pass

            TipWindow(self.parent, f"✅ 已保存 {saved} 张图片到：{out_dir}").show()
        except Exception as e:
            TipWindow(self.parent, f"❌ 下载图片失败: {str(e)}").show()

    def open_data_center(self):
        """从首页跳转到数据中心（热榜）。"""
        try:
            if not self.parent:
                return
            if hasattr(self.parent, "switch_page"):
                self.parent.switch_page(5)

            data_page = getattr(self.parent, "data_center_page", None)
            if data_page and hasattr(data_page, "refresh"):
                # 静默刷新，避免频繁弹窗
                data_page.refresh(silent=True)
        except Exception as e:
            TipWindow(self.parent, f"❌ 打开数据中心失败: {str(e)}").show()

    def refresh_hotspot_options(self):
        """从缓存加载热点到下拉框（不主动联网）。"""
        if not hasattr(self, "hotspot_combo") or self.hotspot_combo is None:
            return

        titles = []
        try:
            from src.core.services.hotspot_service import hotspot_service

            cached = hotspot_service.load_cache()
            data = (cached or {}).get("data") if isinstance(cached, dict) else {}
            if not isinstance(data, dict):
                data = {}

            seen = set()
            for sid, _name in hotspot_service.available_sources().items():
                raw_items = data.get(sid) or []
                if not isinstance(raw_items, list):
                    continue
                for it in raw_items[:10]:
                    if not isinstance(it, dict):
                        continue
                    t = str(it.get("title") or "").strip()
                    if not t:
                        continue
                    if t in seen:
                        continue
                    seen.add(t)
                    titles.append(t)
                    if len(titles) >= 30:
                        break
                if len(titles) >= 30:
                    break
        except Exception:
            titles = []

        self.hotspot_combo.blockSignals(True)
        self.hotspot_combo.clear()
        if titles:
            self.hotspot_combo.addItem("（选择热点填入主题）", "")
            for t in titles:
                self.hotspot_combo.addItem(t, t)
        else:
            self.hotspot_combo.addItem("（暂无热点：去📊数据中心刷新）", "")
        self.hotspot_combo.setCurrentIndex(0)
        self.hotspot_combo.blockSignals(False)

    def on_hotspot_selected(self, _index: int):
        """将选中的热点填入内容输入框。"""
        try:
            if not hasattr(self, "hotspot_combo") or self.hotspot_combo is None:
                return
            value = self.hotspot_combo.currentData()
            title = str(value or "").strip()
            if not title:
                return
            if hasattr(self, "input_text") and self.input_text is not None:
                self.input_text.setPlainText(title)
        except Exception:
            pass

    def import_wechat_article(self):
        """从链接导入标题/正文/图片。"""
        try:
            if not hasattr(self, "wechat_url_input") or self.wechat_url_input is None:
                return

            url = str(self.wechat_url_input.text() or "").strip()
            if not url:
                TipWindow(self.parent, "❌ 请输入网页链接").show()
                return

            # 按钮与状态提示
            if hasattr(self, "wechat_import_btn") and self.wechat_import_btn is not None:
                self.wechat_import_btn.setEnabled(False)
                self.wechat_import_btn.setText("⏳ 导入中")
            if hasattr(self, "wechat_status_label") and self.wechat_status_label is not None:
                self.wechat_status_label.setText("⏳ 准备导入...")

            self.wechat_import_thread = WechatArticleImportThread(url, max_images=9)
            self.wechat_import_thread.progress.connect(self.handle_wechat_import_progress)
            self.wechat_import_thread.finished.connect(self.handle_wechat_import_finished)
            self.wechat_import_thread.error.connect(self.handle_wechat_import_error)
            self.wechat_import_thread.start()

        except Exception as e:
            TipWindow(self.parent, f"❌ 导入失败: {str(e)}").show()
            try:
                if hasattr(self, "wechat_import_btn") and self.wechat_import_btn is not None:
                    self.wechat_import_btn.setEnabled(True)
                    self.wechat_import_btn.setText("📥 导入")
            except Exception:
                pass

    def handle_wechat_import_progress(self, msg: str):
        try:
            if hasattr(self, "wechat_status_label") and self.wechat_status_label is not None:
                self.wechat_status_label.setText(str(msg or "").strip())
        except Exception:
            pass

    def handle_wechat_import_finished(self, data: dict):
        try:
            # 恢复按钮
            if hasattr(self, "wechat_import_btn") and self.wechat_import_btn is not None:
                self.wechat_import_btn.setEnabled(True)
                self.wechat_import_btn.setText("📥 导入")

            title = str((data or {}).get("title") or "").strip()
            content = str((data or {}).get("content") or "").strip()
            author = str((data or {}).get("author") or "").strip()
            image_urls = (data or {}).get("image_urls") or []

            # 简单截断：避免超长内容导致发布页输入异常（用户仍可手动编辑）
            max_len = 1000
            if content and len(content) > max_len:
                content = content[:max_len].rstrip() + "\n\n（已自动截断，原文更长）"

            if title:
                self.title_input.setText(title)
            if content:
                self.subtitle_input.setText(content)
            if author and hasattr(self, "author_input") and self.author_input is not None:
                # 仅在作者输入框为空时填充，避免覆盖用户自定义
                if not str(self.author_input.text() or "").strip():
                    self.author_input.setText(author)

            # 主题输入框也填一下，便于后续继续生成/改写
            try:
                if hasattr(self, "input_text") and self.input_text is not None:
                    self.input_text.setPlainText(title or "")
            except Exception:
                pass

            if hasattr(self, "wechat_status_label") and self.wechat_status_label is not None:
                img_count = len(image_urls) if isinstance(image_urls, (list, tuple)) else 0
                self.wechat_status_label.setText(f"✅ 导入完成（图片 {img_count} 张）")

            # 没图时不启动预览加载（小红书图文发布需要图片）
            if not isinstance(image_urls, (list, tuple)) or not image_urls:
                self.images = []
                self.image_list = []
                self.current_image_index = 0
                self.image_label.setPixmap(self.placeholder_photo)
                self.image_title.setText("未解析到图片，请手动选择图片或改用模板生成")
                self.parent.update_preview_button("🎯 预览发布", False)
                TipWindow(self.parent, "⚠️ 未解析到图片（小红书图文发布需要图片）").show()
                return

            cover_image_url = str(image_urls[0] or "").strip()
            content_image_urls = [str(u or "").strip() for u in list(image_urls[1:]) if str(u or "").strip()]
            referer_url = str((data or {}).get("url") or "").strip()

            # 启动图片处理线程（下载+预览）
            self.parent.image_processor = ImageProcessorThread(
                cover_image_url,
                content_image_urls,
                referer_url=referer_url,
            )
            self.parent.image_processor.finished.connect(self.handle_image_processing_result)
            self.parent.image_processor.error.connect(self.handle_image_processing_error)
            self.parent.image_processor.start()

            # 清空旧图片列表并显示占位图
            self.images = []
            self.image_list = []
            self.current_image_index = 0
            self.image_label.setPixmap(self.placeholder_photo)
            self.image_title.setText("正在加载图片...")
            self.parent.update_preview_button("🎯 预览发布", False)

        except Exception as e:
            self.handle_wechat_import_error(str(e))

    def handle_wechat_import_error(self, error_msg: str):
        try:
            if hasattr(self, "wechat_import_btn") and self.wechat_import_btn is not None:
                self.wechat_import_btn.setEnabled(True)
                self.wechat_import_btn.setText("📥 导入")
            if hasattr(self, "wechat_status_label") and self.wechat_status_label is not None:
                self.wechat_status_label.setText("")
        except Exception:
            pass
        TipWindow(self.parent, f"❌ 链接导入失败: {str(error_msg or '').strip()}").show()

    def import_chrome_session(self):
        """一键导入系统 Chrome 中的小红书登录态（cookies + localStorage）。"""
        try:
            phone = (self.phone_input.text() or "").strip()
            if not phone:
                TipWindow(self.parent, "❌ 请输入手机号（用于绑定到当前用户数据目录）").show()
                return

            # 提示用户退出 Chrome，避免 Profile lock
            ret = QMessageBox.question(
                self,
                "导入系统 Chrome 登录态",
                "导入会临时打开你的系统 Chrome Profile 读取登录态。\n\n"
                "注意：请先完全退出 Chrome（macOS：Cmd+Q），否则可能导入失败。\n\n"
                "导入完成后，本项目会保存一份仅包含 xiaohongshu.com 的登录态文件。\n\n"
                "继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ret != QMessageBox.StandardButton.Yes:
                return

            detected = detect_chrome_profiles()
            if not detected or not detected.profiles:
                TipWindow(
                    self.parent,
                    "❌ 未检测到系统 Chrome Profile。\n"
                    "请确认已安装 Chrome，或在项目根目录 .env 设置：\n"
                    "  XHS_CHROME_USER_DATA_DIR=...（Chrome User Data 目录）\n"
                    "  XHS_CHROME_PROFILE_DIRECTORY=Default/Profile 1 ...",
                ).show()
                return

            profile_dir = (detected.default_profile_directory or "Default").strip() or "Default"
            if len(detected.profiles) > 1:
                items = []
                mapping = {}
                for p in detected.profiles:
                    label = f"{(p.name or p.directory).strip()} ({p.directory})"
                    items.append(label)
                    mapping[label] = p.directory
                try:
                    current_index = items.index(next(i for i in items if mapping.get(i) == profile_dir))
                except Exception:
                    current_index = 0

                selected, ok = QInputDialog.getItem(
                    self,
                    "选择 Chrome Profile",
                    "请选择要导入的 Chrome 配置文件：",
                    items,
                    current_index,
                    False,
                )
                if not ok:
                    return
                profile_dir = mapping.get(selected, profile_dir)

            # UI 状态
            try:
                if hasattr(self, "chrome_import_btn") and self.chrome_import_btn is not None:
                    self.chrome_import_btn.setEnabled(False)
                    self.chrome_import_btn.setText("⏳ 导入中...")
                if hasattr(self, "login_status_label") and self.login_status_label is not None:
                    self.login_status_label.setText("⏳ 正在导入系统 Chrome 登录态...")
                self.parent.update_login_button("🚀 登录", False)
            except Exception:
                pass

            # 启动线程
            self.chrome_import_thread = ChromeSessionImportThread(
                phone=phone,
                chrome_user_data_dir=detected.user_data_dir,
                chrome_profile_directory=profile_dir,
                timeout_s=300,
            )
            self.chrome_import_thread.progress.connect(self._on_chrome_import_progress)
            self.chrome_import_thread.finished.connect(self._on_chrome_import_finished)
            self.chrome_import_thread.error.connect(self._on_chrome_import_error)
            self.chrome_import_thread.start()
        except Exception as e:
            TipWindow(self.parent, f"❌ 导入失败: {str(e)}").show()

    def _on_chrome_import_progress(self, msg: str):
        try:
            if hasattr(self, "login_status_label") and self.login_status_label is not None:
                self.login_status_label.setText(str(msg or "").strip())
        except Exception:
            pass

    def _on_chrome_import_finished(self, result: dict):
        try:
            if hasattr(self, "chrome_import_btn") and self.chrome_import_btn is not None:
                self.chrome_import_btn.setEnabled(True)
                self.chrome_import_btn.setText("🧩 导入登录态")
            self.parent.update_login_button("🚀 登录", True)

            if hasattr(self, "login_status_label") and self.login_status_label is not None:
                self.login_status_label.setText("✅ 已导入登录态：现在点“登录”尝试复用（如仍触发风控，请按页面提示完成）。")
        except Exception:
            pass
        TipWindow(self.parent, "✅ 已导入系统 Chrome 登录态，下一步点“登录”尝试复用").show()

    def _on_chrome_import_error(self, err: str):
        try:
            if hasattr(self, "chrome_import_btn") and self.chrome_import_btn is not None:
                self.chrome_import_btn.setEnabled(True)
                self.chrome_import_btn.setText("🧩 导入登录态")
            self.parent.update_login_button("🚀 登录", True)

            if hasattr(self, "login_status_label") and self.login_status_label is not None:
                self.login_status_label.setText(f"❌ 导入失败：{str(err or '').strip()}")
        except Exception:
            pass
        try:
            print(f"❌ Chrome 登录态导入失败: {str(err or '').strip()}")
        except Exception:
            pass
        try:
            QMessageBox.critical(self, "导入失败", str(err or "").strip() or "未知错误")
        except Exception:
            pass
        TipWindow(self.parent, f"❌ 导入失败: {str(err or '').strip()}").show()

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
                'phone': phone,
                'country_code': self.get_country_code(),
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
        try:
            info_reason = (result or {}).get("info_reason") if isinstance(result, dict) else ""
            if info_reason:
                TipWindow(self.parent, f"ℹ️ {info_reason}").show()
        except Exception:
            pass

        self.update_ui_after_generate(
            result['title'],
            result['content'],
            result['cover_image'],
            result['content_images'],
            result['input_text'],
            result.get('content_pages') if isinstance(result, dict) else None,
        )

    def handle_generation_error(self, error_message):
        """处理生成错误，提供用户友好的错误信息和解决建议"""
        print(f"错误信息: {error_message}")

        # 根据错误类型提供具体的用户友好提示
        if "模型配置不可用" in error_message or "LLMServiceError" in error_message:
            user_message = (
                "⚠️ 大模型未配置或不可用\n\n"
                "请在「模型设置」里填写模型端点与模型名称（本地模型可不填 key）。\n\n"
                "你也可以先用「本地备用生成」继续生成。\n"
            )
        elif "本地备用生成器" in error_message and "失败" in error_message:
            user_message = (
                "⚠️ 本地生成失败\n\n"
                "本地备用生成器遇到问题。\n\n"
                "可能的解决方案：\n"
                "• 重启应用程序\n"
                "• 尝试简化输入内容\n"
                "• 检查磁盘权限（~/.xhs_system 是否可写）\n"
            )
        elif "主API和备用生成器都失败了" in error_message:
            user_message = (
                "❌ 内容生成失败\n\n"
                "主API服务和本地备用生成器都遇到了问题。\n\n"
                "可能的解决方案：\n"
                "• 检查网络连接是否正常\n"
                "• 稍后再试，服务可能临时不可用\n"
                "• 尝试简化输入内容\n"
                "• 重启应用程序"
            )
        elif "JSON解析失败" in error_message:
            user_message = (
                "📊 数据解析错误\n\n"
                "模型返回的数据格式异常。\n\n"
                "解决方案：\n"
                "• 重试操作\n"
                "• 尝试更换提示词模板\n"
            )
        else:
            user_message = (
                "❓ 生成失败\n\n"
                "内容生成过程中遇到未知错误。\n\n"
                "解决方案：\n"
                "• 检查输入内容格式\n"
                "• 重试操作\n"
                "• 如果问题持续，请联系技术支持\n"
            )

        # 附加错误详情（避免“回退生成”导致误判）
        try:
            detail = str(error_message or "").strip()
            if len(detail) > 600:
                detail = detail[:600] + "..."
            if detail:
                user_message = user_message.rstrip() + "\n\n错误详情：\n" + detail
        except Exception:
            pass
        
        # 显示用户友好的错误消息
        QMessageBox.warning(self, "内容生成失败", user_message)

    def update_ui_after_generate(self, title, content, cover_image_url, content_image_urls, input_text, content_pages=None):
        try:
            # 优先使用系统模板生成封面 + 内容页（观感更统一）；如用户在“封面模板库”选择了模板，则使用该背景
            try:
                from src.config.config import Config
                from src.core.services.system_image_template_service import system_image_template_service

                tpl_id = (Config().get_templates_config().get("selected_cover_template_id") or "").strip()
                bg_path = ""
                if tpl_id and tpl_id != "showcase_marketing_poster":
                    showcase_dir = system_image_template_service.resolve_showcase_dir()
                    if showcase_dir:
                        candidate = showcase_dir / f"{tpl_id}.png"
                        if candidate.exists():
                            bg_path = str(candidate)

                # 页数优先取文案分页（大模型/默认服务返回 list / content_pages）
                page_count = 3
                if isinstance(content_pages, (list, tuple)) and content_pages:
                    page_count = max(1, len(content_pages))

                generated = None
                if bg_path and os.path.exists(bg_path):
                    # 仅将“封面模板库”背景用于封面；内容页仍使用系统内容模板包，
                    # 避免用封面背景渲染内容页导致文字不可读/像空白。
                    generated = system_image_template_service.generate_post_images(
                        title=title or "",
                        content=content or "",
                        content_pages=content_pages if isinstance(content_pages, (list, tuple)) else None,
                        page_count=page_count,
                        cover_bg_image_path=bg_path,
                    )

                # 未选择封面背景或生成失败：使用系统默认内容模板包生成（比远程图片更“卡片化”）
                if not generated:
                    generated = system_image_template_service.generate_post_images(
                        title=title or "",
                        content=content or "",
                        content_pages=content_pages if isinstance(content_pages, (list, tuple)) else None,
                        page_count=page_count,
                    )

                if generated:
                    new_cover, new_contents = generated
                    new_cover = str(new_cover or "").strip()
                    new_contents = [str(x or "").strip() for x in (new_contents or []) if str(x or "").strip()]
                    # 避免用“空内容页”覆盖掉已有图片（会导致只剩封面，看起来像内容页空白）
                    if new_cover and new_contents:
                        cover_image_url, content_image_urls = new_cover, new_contents
            except Exception as e:
                print(f"⚠️ 使用封面模板生成封面失败，已回退原封面: {e}")

            # 创建并启动图片处理线程
            self.parent.image_processor = ImageProcessorThread(cover_image_url, content_image_urls)
            self.parent.image_processor.finished.connect(self.handle_image_processing_result)
            self.parent.image_processor.error.connect(self.handle_image_processing_error)
            self.parent.image_processor.start()

            # 更新标题和内容
            self.title_input.setText(title if title else "")
            self.subtitle_input.setText(content if content else "")

            # 安全地更新文本编辑器内容
            if input_text:
                self.input_text.clear()
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

    def schedule_publish(self):
        """创建定时发布任务（无人值守自动发布）。"""
        try:
            # 只允许选择“已登录”的用户（无人值守避免验证码）
            try:
                from src.core.services.user_service import user_service

                current_user = user_service.get_current_user()
                users = [u for u in user_service.list_users(active_only=True) if getattr(u, "is_logged_in", False)]
            except Exception:
                users = []
                current_user = None

            if not users:
                TipWindow(self.parent, "❌ 没有已登录用户，请先登录后再创建定时任务").show()
                return

            default_user_id = getattr(current_user, "id", None) if current_user else getattr(users[0], "id", None)

            # 默认重复间隔取后台配置的 interval_hours
            default_interval_hours = 2
            try:
                default_interval_hours = int(self.parent.config.get_schedule_config().get("interval_hours", 2) or 2)
            except Exception:
                default_interval_hours = 2

            dialog = ScheduledPublishDialog(
                self,
                users=users,
                default_user_id=default_user_id,
                default_interval_hours=default_interval_hours,
                initial_title=(self.title_input.text() or "").strip(),
                initial_content=(self.subtitle_input.toPlainText() or "").strip(),
                initial_images=list(getattr(self, "images", None) or []),
            )
            if dialog.exec() != dialog.DialogCode.Accepted:
                return

            user_id = dialog.get_user_id()
            schedule_time = dialog.get_schedule_time()
            if not user_id:
                TipWindow(self.parent, "❌ 请选择发布账号").show()
                return

            if not hasattr(schedule_time, "isoformat"):
                TipWindow(self.parent, "❌ 发布时间无效").show()
                return

            from src.core.scheduler.schedule_manager import schedule_manager

            task_type = dialog.get_task_type()

            if task_type == "hotspot":
                source = dialog.get_hotspot_source()
                rank = dialog.get_hotspot_rank()
                interval_hours = dialog.get_interval_hours()
                use_ctx = dialog.get_use_hotspot_context()

                # 保存当前选择的封面模板（用于生成图片风格）；若为空则用占位图
                cover_template_id = ""
                try:
                    cover_template_id = str(self.parent.config.get_templates_config().get("selected_cover_template_id") or "").strip()
                except Exception:
                    cover_template_id = ""

                task_id = schedule_manager.add_task(
                    content="",
                    schedule_time=schedule_time,
                    title=f"热点({source}) #{rank}",
                    images=[],
                    user_id=int(user_id),
                    task_type="hotspot",
                    interval_hours=int(interval_hours),
                    hotspot_source=str(source),
                    hotspot_rank=int(rank),
                    use_hotspot_context=bool(use_ctx),
                    cover_template_id=cover_template_id,
                    page_count=3,
                )
            else:
                title = dialog.get_fixed_title()
                content = dialog.get_fixed_content()
                images = dialog.get_fixed_images()

                if not title and not content:
                    TipWindow(self.parent, "❌ 请输入标题或正文").show()
                    return

                cover_template_id = ""
                try:
                    cover_template_id = str(self.parent.config.get_templates_config().get("selected_cover_template_id") or "").strip()
                except Exception:
                    cover_template_id = ""

                task_id = schedule_manager.add_task(
                    content=content,
                    schedule_time=schedule_time,
                    title=title,
                    images=images,
                    user_id=int(user_id),
                    task_type="fixed",
                    cover_template_id=cover_template_id,
                    page_count=3,
                )

            try:
                ts = schedule_time.strftime("%Y-%m-%d %H:%M")
            except Exception:
                ts = str(schedule_time)

            TipWindow(self.parent, f"✅ 已创建定时任务：{ts}\n任务ID: {task_id}").show()

            # 若配置页存在任务列表，尽量刷新
            try:
                if hasattr(self.parent, "backend_config_page") and hasattr(self.parent.backend_config_page, "refresh_schedule_tasks"):
                    self.parent.backend_config_page.refresh_schedule_tasks()
            except Exception:
                pass

        except Exception as e:
            TipWindow(self.parent, f"❌ 创建定时任务失败: {str(e)}").show()

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

    def update_country_code_config(self):
        """更新国家区号配置"""
        try:
            self.parent.config.update_country_code_config(self.get_country_code())
        except Exception as e:
            self.parent.logger.error(f"更新国家区号配置失败: {str(e)}")

    def get_country_code(self) -> str:
        try:
            if hasattr(self, 'country_code_combo') and self.country_code_combo is not None:
                return str(self.country_code_combo.currentData() or "+86").strip() or "+86"
        except Exception:
            pass
        return "+86"

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

