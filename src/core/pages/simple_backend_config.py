#!/usr/bin/env python3
"""
简化的后台配置页面
解决按钮点击问题
"""

import json
import os
from pathlib import Path
from datetime import datetime
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QFont, QDesktopServices, QPixmap
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QLineEdit, QComboBox, QTextEdit, 
                           QSpinBox, QCheckBox, QDateTimeEdit, QTabWidget, 
                           QFormLayout, QMessageBox, QScrollArea, QFrame, QGroupBox,
                           QListWidget, QListWidgetItem, QPlainTextEdit, QFileDialog)

from src.config.config import Config
from src.core.services.llm_service import llm_service
from src.core.services.chinese_writing_editor import ChineseWritingEditor
from src.core.ai_integration.api_key_manager import api_key_manager
from src.core.services.system_image_template_service import system_image_template_service
from src.core.ui.qt_font import get_ui_font_family

class SimpleBackendConfigPage(QWidget):
    """简化的后台配置页面"""
    
    config_saved = pyqtSignal()
    
    # 提供商端点映射
    PROVIDER_ENDPOINTS = {
        "OpenAI": "https://api.openai.com/v1/chat/completions",
        "智谱（GLM）": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "Anthropic（Claude）": "https://api.anthropic.com/v1/messages",
        "阿里云（通义千问）": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "月之暗面（Kimi）": "https://api.moonshot.cn/v1/chat/completions",
        "Kimi Code（会员套餐）": "https://api.kimi.com/coding/v1/chat/completions",
        "字节跳动（豆包）": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "腾讯（混元）": "https://api.lkeap.cloud.tencent.com/v1/chat/completions",
        "本地模型": "http://localhost:1234/v1/chat/completions"
    }
    
    # 默认模型名称映射
    PROVIDER_MODELS = {
        "OpenAI": "gpt-3.5-turbo",
        "智谱（GLM）": "glm-4.5-air",
        "Anthropic（Claude）": "claude-3-5-sonnet-20241022",
        "阿里云（通义千问）": "qwen3-72b-instruct",
        "月之暗面（Kimi）": "kimi-k3",
        "Kimi Code（会员套餐）": "k3-256k",
        "字节跳动（豆包）": "doubao-pro-32k",
        "腾讯（混元）": "hunyuan-turbo",
        "本地模型": "local-model"
    }

    # 兼容旧版本 provider 文本
    PROVIDER_ALIASES = {
        "OpenAI GPT-4": "OpenAI",
        "OpenAI GPT-3.5": "OpenAI",
        "Claude 3.5": "Anthropic（Claude）",
        "Qwen3": "阿里云（通义千问）",
        "Kimi2": "月之暗面（Kimi）",
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.config = Config()
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """设置优化界面"""
        font_family = get_ui_font_family()
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
            }
            QPushButton {
                font-size: 16px;
                font-family: "__UI_FONT_FAMILY__";
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 500;
            }
            QLabel {
                font-size: 15px;
                font-family: "__UI_FONT_FAMILY__";
                font-weight: 500;
                color: #2c3e50;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateTimeEdit {
                font-size: 15px;
                font-family: "__UI_FONT_FAMILY__";
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
                color: #1f2937;
                selection-background-color: #1a73e8;
                selection-color: white;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #1f2937;
                selection-background-color: #e8f0fe;
                selection-color: #1a73e8;
            }
            QGroupBox {
                font-size: 16px;
                font-family: "__UI_FONT_FAMILY__";
                font-weight: bold;
                color: #1f2937;
                background-color: white;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                margin-top: 14px;
                padding: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #1a73e8;
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                background-color: white;
            }
            QTabBar::tab {
                font-size: 14px;
                font-family: "__UI_FONT_FAMILY__";
                padding: 8px 16px;
                margin-right: 2px;
                background-color: #f1f3f4;
                border-radius: 8px 8px 0 0;
                color: #5f6368;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #1a73e8;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #e8f0fe;
                color: #1a73e8;
            }
            QCheckBox {
                font-size: 14px;
                font-family: "__UI_FONT_FAMILY__";
                color: #1f2937;
                padding: 4px;
            }
        """.replace("__UI_FONT_FAMILY__", font_family))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题区域
        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4285f4, stop:1 #34a853);
                border-radius: 15px;
                padding: 25px;
            }
        """)
        
        title_layout = QVBoxLayout(title_frame)
        title = QLabel("后台配置中心")
        title.setFont(QFont(get_ui_font_family(), 24, QFont.Bold))
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("管理您的定时发布、AI模型和API配置")
        subtitle.setFont(QFont(get_ui_font_family(), 16))
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        subtitle.setAlignment(Qt.AlignCenter)
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        
        layout.addWidget(title_frame)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 定时发布配置
        tab_widget.addTab(self.create_schedule_tab(), "定时发布")
        tab_widget.addTab(self.create_model_tab(), "模型配置")
        tab_widget.addTab(self.create_template_tab(), "模板库")
        tab_widget.addTab(self.create_api_tab(), "API管理")
        tab_widget.addTab(self.create_save_tab(), "保存配置")
        
        layout.addWidget(tab_widget)
    
    def create_schedule_tab(self):
        """创建定时发布标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # 标题
        title = QLabel("⏰ 定时发布配置")
        title.setFont(QFont(get_ui_font_family(), 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 启用开关
        self.schedule_enabled = QCheckBox("✅ 启用定时发布功能")
        self.schedule_enabled.setFont(QFont(get_ui_font_family(), 16))
        self.schedule_enabled.stateChanged.connect(self.on_schedule_enabled_changed)
        layout.addWidget(self.schedule_enabled)
        
        # 创建分组
        group = QGroupBox("发布设置")
        group_layout = QFormLayout(group)
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(20, 20, 20, 20)
        
        self.schedule_time = QDateTimeEdit()
        self.schedule_time.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.schedule_time.setMinimumDateTime(datetime.now())
        self.schedule_time.setFont(QFont(get_ui_font_family(), 14))
        
        self.interval_hours = QSpinBox()
        self.interval_hours.setRange(1, 24)
        self.interval_hours.setSuffix(" 小时")
        self.interval_hours.setFont(QFont(get_ui_font_family(), 14))
        
        self.max_posts = QSpinBox()
        self.max_posts.setRange(1, 50)
        self.max_posts.setSuffix(" 条")
        self.max_posts.setFont(QFont(get_ui_font_family(), 14))
        
        group_layout.addRow("🕐 发布时间：", self.schedule_time)
        group_layout.addRow("📅 发布间隔：", self.interval_hours)
        group_layout.addRow("📊 每日限制：", self.max_posts)
        
        layout.addWidget(group)

        # 任务列表
        tasks_group = QGroupBox("任务列表")
        tasks_layout = QVBoxLayout(tasks_group)
        tasks_layout.setContentsMargins(16, 16, 16, 16)
        tasks_layout.setSpacing(10)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        create_btn = QPushButton("➕ 创建任务")
        create_btn.clicked.connect(self.create_schedule_task)
        action_row.addWidget(create_btn)

        refresh_btn = QPushButton("🔄 刷新任务")
        refresh_btn.clicked.connect(self.refresh_schedule_tasks)
        action_row.addWidget(refresh_btn)

        delete_btn = QPushButton("🗑️ 删除所选")
        delete_btn.clicked.connect(self.delete_selected_schedule_task)
        action_row.addWidget(delete_btn)

        clear_btn = QPushButton("🧹 清理已完成")
        clear_btn.clicked.connect(self.clear_completed_schedule_tasks)
        action_row.addWidget(clear_btn)

        open_btn = QPushButton("📂 打开任务目录")
        open_btn.clicked.connect(self.open_schedule_tasks_dir)
        action_row.addWidget(open_btn)

        action_row.addStretch()
        tasks_layout.addLayout(action_row)

        self.schedule_tasks_list = QListWidget()
        self.schedule_tasks_list.setMinimumHeight(240)
        tasks_layout.addWidget(self.schedule_tasks_list)

        layout.addWidget(tasks_group)
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll

    def create_schedule_task(self):
        """创建一个新的定时发布任务（手动输入内容/选择热点）。"""
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
                QMessageBox.information(self, "提示", "没有已登录用户，请先登录后再创建定时任务。")
                return

            default_user_id = getattr(current_user, "id", None) if current_user else getattr(users[0], "id", None)

            default_interval_hours = 2
            try:
                default_interval_hours = int(self.config.get_schedule_config().get("interval_hours", 2) or 2)
            except Exception:
                default_interval_hours = 2

            from src.core.pages.scheduled_publish_dialog import ScheduledPublishDialog

            dialog = ScheduledPublishDialog(
                self,
                users=users,
                default_user_id=default_user_id,
                default_interval_hours=default_interval_hours,
                initial_title="",
                initial_content="",
                initial_images=[],
                default_task_type="fixed",
            )
            if dialog.exec() != dialog.DialogCode.Accepted:
                return

            user_id = dialog.get_user_id()
            schedule_time = dialog.get_schedule_time()
            if not user_id:
                QMessageBox.warning(self, "失败", "请选择发布账号。")
                return
            if not hasattr(schedule_time, "isoformat"):
                QMessageBox.warning(self, "失败", "发布时间无效。")
                return

            from src.core.scheduler.schedule_manager import schedule_manager

            task_type = dialog.get_task_type()
            if task_type == "hotspot":
                source = dialog.get_hotspot_source()
                rank = dialog.get_hotspot_rank()
                interval_hours = dialog.get_interval_hours()
                use_ctx = dialog.get_use_hotspot_context()

                cover_template_id = ""
                try:
                    cover_template_id = str(self.config.get_templates_config().get("selected_cover_template_id") or "").strip()
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
                    QMessageBox.warning(self, "失败", "请输入标题或正文。")
                    return

                cover_template_id = ""
                try:
                    cover_template_id = str(self.config.get_templates_config().get("selected_cover_template_id") or "").strip()
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

            QMessageBox.information(self, "成功", f"已创建定时任务：{task_id}")
            try:
                self.refresh_schedule_tasks()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.warning(self, "失败", f"创建任务失败：{str(e)}")

    def on_schedule_enabled_changed(self, state: int):
        """启用/停用定时调度器（应用需保持开启）。"""
        try:
            from src.core.scheduler.schedule_manager import schedule_manager

            enabled = bool(state)
            if enabled:
                schedule_manager.start_scheduler()
            else:
                schedule_manager.stop_scheduler()
        except Exception:
            pass

    def refresh_schedule_tasks(self):
        """刷新定时任务列表。"""
        try:
            if not hasattr(self, "schedule_tasks_list"):
                return

            from src.core.scheduler.schedule_manager import schedule_manager

            # 读取用户映射
            user_map = {}
            try:
                from src.core.services.user_service import user_service

                for u in user_service.list_users(active_only=False):
                    user_map[int(u.id)] = u
            except Exception:
                user_map = {}

            self.schedule_tasks_list.clear()
            tasks = schedule_manager.get_tasks()
            tasks = sorted(tasks, key=lambda t: getattr(t, "schedule_time", datetime.now()))

            status_icon = {
                "pending": "🕒",
                "running": "⏳",
                "completed": "✅",
                "failed": "❌",
                "needs_review": "⚠️",
                "submitted": "📤",
                "under_review": "🔎",
            }

            for t in tasks:
                try:
                    uid = getattr(t, "user_id", None)
                    user_obj = user_map.get(int(uid)) if uid is not None else None
                    user_label = ""
                    if user_obj:
                        name = (user_obj.display_name or user_obj.username or user_obj.phone or f"用户{user_obj.id}").strip()
                        login_tag = "✅" if getattr(user_obj, "is_logged_in", False) else "❌"
                        user_label = f"{name} {login_tag}"
                    else:
                        user_label = "当前用户" if uid is None else f"用户{uid}"

                    st = getattr(t, "status", "pending")
                    icon = status_icon.get(st, "•")
                    label = {"needs_review": "待核验", "submitted": "已提交", "under_review": "审核中"}.get(st, st)
                    title = (getattr(t, "title", "") or "").strip() or "（无标题）"
                    try:
                        ts = getattr(t, "schedule_time").strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        ts = str(getattr(t, "schedule_time", ""))

                    retry = f"{getattr(t, 'retry_count', 0)}/{getattr(t, 'max_retries', 0)}"
                    text = f"{icon} {ts} ｜ {user_label} ｜ {title} ｜ {label} ｜ 失败次数 {retry}"

                    item = QListWidgetItem(text)
                    item.setData(Qt.UserRole, str(getattr(t, "task_id", "")))

                    tooltip_lines = [
                        f"任务ID: {getattr(t, 'task_id', '')}",
                        f"账号: {user_label}",
                        f"时间: {ts}",
                        f"状态: {st}",
                    ]
                    err = (getattr(t, "error_message", "") or "").strip()
                    if err:
                        tooltip_lines.append(f"错误: {err}")
                    item.setToolTip("\n".join(tooltip_lines))

                    self.schedule_tasks_list.addItem(item)
                except Exception:
                    continue

            if self.schedule_tasks_list.count() == 0:
                self.schedule_tasks_list.addItem(QListWidgetItem("（暂无任务）"))
        except Exception:
            pass

    def delete_selected_schedule_task(self):
        try:
            if not hasattr(self, "schedule_tasks_list"):
                return

            items = self.schedule_tasks_list.selectedItems()
            if not items:
                QMessageBox.information(self, "提示", "请先选择一个任务")
                return

            task_id = items[0].data(Qt.UserRole)
            if not task_id:
                return

            reply = QMessageBox.question(self, "确认删除", f"确定要删除任务 {task_id} 吗？", QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return

            from src.core.scheduler.schedule_manager import schedule_manager

            schedule_manager.remove_task(str(task_id))
            self.refresh_schedule_tasks()
        except Exception as e:
            QMessageBox.warning(self, "失败", f"删除任务失败：{str(e)}")

    def clear_completed_schedule_tasks(self):
        try:
            from src.core.scheduler.schedule_manager import schedule_manager

            schedule_manager.clear_completed_tasks()
            self.refresh_schedule_tasks()
        except Exception as e:
            QMessageBox.warning(self, "失败", f"清理失败：{str(e)}")

    def open_schedule_tasks_dir(self):
        """打开定时任务目录（tasks.json + 任务图片）。"""
        try:
            base_dir = os.path.join(os.path.expanduser("~"), ".xhs_system")
            QDesktopServices.openUrl(QUrl.fromLocalFile(base_dir))
        except Exception:
            pass
    
    def create_model_tab(self):
        """创建模型配置标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # 标题
        title = QLabel("🤖 AI模型配置")
        title.setFont(QFont(get_ui_font_family(), 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 创建分组
        group = QGroupBox("模型设置")
        group_layout = QFormLayout(group)
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(20, 20, 20, 20)
        
        self.model_provider = QComboBox()
        self.model_provider.addItems(
            [
                "OpenAI",
                "智谱（GLM）",
                "Anthropic（Claude）",
                "阿里云（通义千问）",
                "月之暗面（Kimi）",
                "Kimi Code（会员套餐）",
                "字节跳动（豆包）",
                "腾讯（混元）",
                "本地模型",
            ]
        )
        self.model_provider.setFont(QFont(get_ui_font_family(), 14))
        self.model_provider.currentTextChanged.connect(self.on_provider_changed)
        
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setFont(QFont(get_ui_font_family(), 14))
        self.api_key.setPlaceholderText("请输入您的API密钥")

        self.show_api_key = QCheckBox("显示")
        self.show_api_key.setChecked(False)
        self.show_api_key.stateChanged.connect(
            lambda state: self.api_key.setEchoMode(QLineEdit.Normal if state else QLineEdit.Password)
        )

        api_key_row = QWidget()
        api_key_row_layout = QHBoxLayout(api_key_row)
        api_key_row_layout.setContentsMargins(0, 0, 0, 0)
        api_key_row_layout.setSpacing(10)
        api_key_row_layout.addWidget(self.api_key, 1)
        api_key_row_layout.addWidget(self.show_api_key, 0)

        self.api_key_hint = QLabel("")
        self.api_key_hint.setWordWrap(True)
        self.api_key_hint.setStyleSheet(
            "color: #374151; font-size: 13px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px;"
        )
        
        self.api_endpoint = QLineEdit()
        self.api_endpoint.setFont(QFont(get_ui_font_family(), 14))
        self.api_endpoint.setPlaceholderText("例如：https://api.openai.com/v1/chat/completions")
        self.api_endpoint.setMinimumWidth(520)
        
        self.model_name = QLineEdit()
        self.model_name.setFont(QFont(get_ui_font_family(), 14))
        self.model_name.setPlaceholderText("例如：gpt-3.5-turbo")
        self.model_name.setMinimumWidth(520)

        # 文案模板选择
        self.prompt_template = QComboBox()
        self.prompt_template.setFont(QFont(get_ui_font_family(), 14))
        self._load_prompt_templates()
        self.prompt_template.currentIndexChanged.connect(self.on_prompt_template_changed)

        self.prompt_template_desc = QLabel("")
        self.prompt_template_desc.setWordWrap(True)
        self.prompt_template_desc.setStyleSheet(
            "color: #374151; font-size: 13px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px;"
        )

        self.system_prompt = QTextEdit()
        self.system_prompt.setMinimumHeight(140)
        self.system_prompt.setFont(QFont(get_ui_font_family(), 14))
        self.system_prompt.setPlaceholderText("请输入自定义系统提示词，这将影响AI生成内容的方式...")

        self.chinese_editor_enabled = QCheckBox("生成后单独改一遍文案")
        self.chinese_editor_enabled.setChecked(True)
        self.writing_sample = QTextEdit()
        self.writing_sample.setMinimumHeight(110)
        self.writing_sample.setPlaceholderText("贴一小段你自己写的文字。留空时沿用本次原稿的语气。")
        self.writing_sample.setFont(QFont(get_ui_font_family(), 14))
        self.chinese_editor_enabled.toggled.connect(self.writing_sample.setEnabled)
        writing_hint = QLabel("普通笔记和海报共用。开启后生成时间会增加，最多多调用模型两次。样本只参考写法。")
        writing_hint.setWordWrap(True)
        writing_hint.setStyleSheet("color: #6b7280; font-size: 13px;")
        
        group_layout.addRow("🤖 提供商：", self.model_provider)
        group_layout.addRow("🔑 API密钥：", api_key_row)
        group_layout.addRow("", self.api_key_hint)
        group_layout.addRow("🔗 API端点：", self.api_endpoint)
        group_layout.addRow("⚙️ 模型名称：", self.model_name)
        group_layout.addRow("🧩 文案模板：", self.prompt_template)
        group_layout.addRow("", self.prompt_template_desc)
        group_layout.addRow("💬 系统提示：", self.system_prompt)
        group_layout.addRow("中文审稿：", self.chinese_editor_enabled)
        group_layout.addRow("参考语气（可选）：", self.writing_sample)
        group_layout.addRow("", writing_hint)
        
        layout.addWidget(group)
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll

    def create_template_tab(self):
        """创建模板库标签页（文案模板）。"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("🧩 模板库")
        title.setFont(QFont(get_ui_font_family(), 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title)

        template_dir = str(llm_service.get_prompt_templates_dir())
        dir_row = QWidget()
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.setSpacing(10)

        dir_label = QLabel(f"模板目录：{template_dir}")
        dir_label.setStyleSheet("color: #374151; font-size: 13px;")
        dir_layout.addWidget(dir_label, 1)

        open_btn = QPushButton("📂 打开目录")
        open_btn.setStyleSheet(
            "QPushButton { background-color: #1a73e8; color: white; border: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; }"
            "QPushButton:hover { background-color: #1669d6; }"
        )
        open_btn.clicked.connect(self.open_prompt_templates_dir)
        dir_layout.addWidget(open_btn, 0)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet(
            "QPushButton { background-color: #34a853; color: white; border: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; }"
            "QPushButton:hover { background-color: #2f974b; }"
        )
        refresh_btn.clicked.connect(self.refresh_prompt_templates_library)
        dir_layout.addWidget(refresh_btn, 0)

        layout.addWidget(dir_row)

        group = QGroupBox("文案模板（Prompts）")
        group_layout = QHBoxLayout(group)
        group_layout.setSpacing(16)
        group_layout.setContentsMargins(16, 20, 16, 16)

        self.template_list = QListWidget()
        self.template_list.setMinimumWidth(260)
        self.template_list.setStyleSheet(
            "QListWidget { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 8px; }"
            "QListWidget::item { padding: 10px; border-radius: 8px; }"
            "QListWidget::item:selected { background: #e8f0fe; color: #1a73e8; }"
        )
        self.template_list.currentItemChanged.connect(self.on_template_item_changed)

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(10)

        self.template_meta = QLabel("请选择一个模板查看详情")
        self.template_meta.setWordWrap(True)
        self.template_meta.setStyleSheet(
            "color: #374151; font-size: 13px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px;"
        )
        detail_layout.addWidget(self.template_meta)

        self.template_prompt_view = QPlainTextEdit()
        self.template_prompt_view.setReadOnly(True)
        self.template_prompt_view.setPlaceholderText("这里会显示模板的 user_prompt 内容")
        self.template_prompt_view.setStyleSheet(
            "QPlainTextEdit { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px; font-size: 13px; }"
        )
        self.template_prompt_view.setMinimumHeight(260)
        detail_layout.addWidget(self.template_prompt_view, 1)

        group_layout.addWidget(self.template_list, 0)
        group_layout.addWidget(detail, 1)
        layout.addWidget(group)

        # 初次加载
        self.refresh_prompt_templates_library()

        # 系统图片模板（x-auto-publisher）
        img_group = QGroupBox("系统模板图片（来自 x-auto-publisher，可导入本地）")
        img_layout = QVBoxLayout(img_group)
        img_layout.setSpacing(12)
        img_layout.setContentsMargins(16, 20, 16, 16)

        img_dir_row = QWidget()
        img_dir_layout = QHBoxLayout(img_dir_row)
        img_dir_layout.setContentsMargins(0, 0, 0, 0)
        img_dir_layout.setSpacing(10)

        self.system_templates_dir_label = QLabel("")
        self.system_templates_dir_label.setWordWrap(True)
        self.system_templates_dir_label.setStyleSheet("color: #374151; font-size: 13px;")
        img_dir_layout.addWidget(self.system_templates_dir_label, 1)

        choose_btn = QPushButton("🗂 选择目录")
        choose_btn.setStyleSheet(
            "QPushButton { background-color: #1a73e8; color: white; border: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; }"
            "QPushButton:hover { background-color: #1669d6; }"
        )
        choose_btn.clicked.connect(self.choose_system_templates_dir)
        img_dir_layout.addWidget(choose_btn, 0)

        import_btn = QPushButton("📥 导入本地")
        import_btn.setStyleSheet(
            "QPushButton { background-color: #ff9500; color: white; border: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; }"
            "QPushButton:hover { background-color: #e88600; }"
        )
        import_btn.clicked.connect(self.import_system_templates)
        img_dir_layout.addWidget(import_btn, 0)

        refresh_btn2 = QPushButton("🔄 刷新列表")
        refresh_btn2.setStyleSheet(
            "QPushButton { background-color: #34a853; color: white; border: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; }"
            "QPushButton:hover { background-color: #2f974b; }"
        )
        refresh_btn2.clicked.connect(self.refresh_system_templates_library)
        img_dir_layout.addWidget(refresh_btn2, 0)

        open_btn2 = QPushButton("📂 打开目录")
        open_btn2.setStyleSheet(
            "QPushButton { background-color: #6b7280; color: white; border: none; padding: 8px 14px; border-radius: 8px; font-size: 13px; }"
            "QPushButton:hover { background-color: #4b5563; }"
        )
        open_btn2.clicked.connect(self.open_system_templates_dir)
        img_dir_layout.addWidget(open_btn2, 0)

        img_layout.addWidget(img_dir_row)

        img_split = QWidget()
        img_split_layout = QHBoxLayout(img_split)
        img_split_layout.setContentsMargins(0, 0, 0, 0)
        img_split_layout.setSpacing(16)

        self.system_pack_list = QListWidget()
        self.system_pack_list.setMinimumWidth(260)
        self.system_pack_list.setStyleSheet(
            "QListWidget { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 8px; }"
            "QListWidget::item { padding: 10px; border-radius: 8px; }"
            "QListWidget::item:selected { background: #e8f0fe; color: #1a73e8; }"
        )
        self.system_pack_list.currentItemChanged.connect(self.on_system_pack_changed)
        img_split_layout.addWidget(self.system_pack_list, 0)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.system_pack_meta = QLabel("选择一个模板包查看预览")
        self.system_pack_meta.setWordWrap(True)
        self.system_pack_meta.setStyleSheet(
            "color: #374151; font-size: 13px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px;"
        )
        right_layout.addWidget(self.system_pack_meta)

        self.system_pack_preview = QLabel()
        self.system_pack_preview.setMinimumHeight(260)
        self.system_pack_preview.setAlignment(Qt.AlignCenter)
        self.system_pack_preview.setStyleSheet(
            "QLabel { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px; }"
        )
        self.system_pack_preview.setText("预览图")
        right_layout.addWidget(self.system_pack_preview, 1)

        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        set_default_btn = QPushButton("⭐ 设为默认（生成时使用）")
        set_default_btn.setStyleSheet(
            "QPushButton { background-color: #1a73e8; color: white; border: none; padding: 10px 14px; border-radius: 10px; font-size: 13px; }"
            "QPushButton:hover { background-color: #1669d6; }"
        )
        set_default_btn.clicked.connect(self.set_default_system_pack)
        btn_layout.addWidget(set_default_btn, 0)

        btn_layout.addStretch()
        right_layout.addWidget(btn_row)

        img_split_layout.addWidget(right_panel, 1)
        img_layout.addWidget(img_split)
        layout.addWidget(img_group)

        self.refresh_system_templates_library()

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def open_prompt_templates_dir(self):
        try:
            path = str(llm_service.get_prompt_templates_dir())
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开目录失败: {e}")

    def refresh_prompt_templates_library(self):
        """刷新模板库列表，并同步刷新模型配置里的下拉框。"""
        try:
            templates = llm_service.list_prompt_templates()
        except Exception as e:
            templates = []
            QMessageBox.warning(self, "错误", f"加载模板失败: {e}")

        # 列表
        if hasattr(self, "template_list") and self.template_list is not None:
            self.template_list.clear()
            if not templates:
                item = QListWidgetItem("（未找到模板）")
                item.setData(Qt.UserRole, "")
                self.template_list.addItem(item)
            else:
                for tpl in templates:
                    item = QListWidgetItem(tpl.name)
                    item.setData(Qt.UserRole, tpl.id)
                    self.template_list.addItem(item)
                self.template_list.setCurrentRow(0)

        # 同步模型页下拉框（保持当前选择）
        try:
            selected_id = None
            if hasattr(self, "prompt_template") and self.prompt_template is not None:
                selected_id = self.prompt_template.currentData()
                self._load_prompt_templates()
                if selected_id:
                    idx = self.prompt_template.findData(selected_id)
                    if idx >= 0:
                        self.prompt_template.setCurrentIndex(idx)
                self.on_prompt_template_changed(self.prompt_template.currentIndex())
        except Exception:
            pass

    def _update_system_templates_dir_label(self):
        base_dir = system_image_template_service.resolve_templates_dir()
        if base_dir:
            self.system_templates_dir_label.setText(f"当前模板目录：{base_dir}")
        else:
            self.system_templates_dir_label.setText(
                "当前模板目录：未发现（可选择 x-auto-publisher 目录，或导入到本地 ~/.xhs_system/system_templates）"
            )

    def refresh_system_templates_library(self):
        self._update_system_templates_dir_label()
        packs = system_image_template_service.list_content_packs()

        self.system_pack_list.clear()
        if not packs:
            item = QListWidgetItem("（未找到 content_*_page*.png 模板包）")
            item.setData(Qt.UserRole, "")
            self.system_pack_list.addItem(item)
            self.system_pack_meta.setText("未发现可用模板包。你可以点击“选择目录”指向 x-auto-publisher，或点击“导入本地”。")
            self.system_pack_preview.setText("预览图")
            self.system_pack_preview.setPixmap(QPixmap())
            return

        for pack in packs:
            show = pack.id.replace("content_", "")
            page_count = len(pack.pages)
            item = QListWidgetItem(f"{show}  ({page_count}页)")
            item.setData(Qt.UserRole, pack.id)
            item.setData(Qt.UserRole + 1, [str(p) for p in pack.pages])
            self.system_pack_list.addItem(item)

        # 选中默认项
        default_id = system_image_template_service.get_selected_pack_id()
        target_row = 0
        if default_id:
            for i in range(self.system_pack_list.count()):
                it = self.system_pack_list.item(i)
                if it and it.data(Qt.UserRole) == default_id:
                    target_row = i
                    break
        self.system_pack_list.setCurrentRow(target_row)

    def on_system_pack_changed(self, current: QListWidgetItem, _previous: QListWidgetItem):
        try:
            if not current:
                return
            pack_id = str(current.data(Qt.UserRole) or "")
            pages = current.data(Qt.UserRole + 1) or []
            if not pack_id or not pages:
                self.system_pack_meta.setText("未找到可用模板包。")
                self.system_pack_preview.setText("预览图")
                self.system_pack_preview.setPixmap(QPixmap())
                return

            self.system_pack_meta.setText(f"模板包：{pack_id}\n页数：{len(pages)}")

            preview_path = pages[0]
            if preview_path and os.path.exists(preview_path):
                pix = QPixmap(preview_path)
                if not pix.isNull():
                    self.system_pack_preview.setPixmap(pix.scaled(360, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    return
            self.system_pack_preview.setText("预览图加载失败")
            self.system_pack_preview.setPixmap(QPixmap())
        except Exception as e:
            self.system_pack_meta.setText(f"预览失败: {e}")
            self.system_pack_preview.setText("预览图")
            self.system_pack_preview.setPixmap(QPixmap())

    def choose_system_templates_dir(self):
        try:
            start_dir = str(system_image_template_service.resolve_templates_dir() or Path.home())
            chosen = QFileDialog.getExistingDirectory(self, "选择系统模板目录（x-auto-publisher 或其 templates 目录）", start_dir)
            if not chosen:
                return
            cfg = self.config.get_templates_config()
            cfg["system_templates_dir"] = chosen
            self.config.update_templates_config(cfg)
            self.refresh_system_templates_library()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"选择目录失败: {e}")

    def import_system_templates(self):
        try:
            start_dir = str(system_image_template_service.resolve_templates_dir() or Path.home())
            chosen = QFileDialog.getExistingDirectory(self, "选择要导入的模板目录（建议选择 x-auto-publisher 根目录）", start_dir)
            if not chosen:
                return
            ok, msg = system_image_template_service.import_from_source(chosen)
            if ok:
                QMessageBox.information(self, "成功", msg)
            else:
                QMessageBox.warning(self, "失败", msg)
            self.refresh_system_templates_library()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导入失败: {e}")

    def open_system_templates_dir(self):
        try:
            path = system_image_template_service.resolve_templates_dir()
            if not path:
                QMessageBox.information(self, "提示", "未发现模板目录，请先选择或导入。")
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开目录失败: {e}")

    def set_default_system_pack(self):
        try:
            current = self.system_pack_list.currentItem()
            if not current:
                return
            pack_id = str(current.data(Qt.UserRole) or "").strip()
            if not pack_id:
                return
            cfg = self.config.get_templates_config()
            cfg["default_content_pack"] = pack_id
            # 同时保存当前目录（便于跨平台一致）
            base_dir = system_image_template_service.resolve_templates_dir()
            if base_dir:
                cfg["system_templates_dir"] = str(base_dir)
            self.config.update_templates_config(cfg)
            QMessageBox.information(self, "成功", f"已设置默认模板包：{pack_id}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"设置失败: {e}")

    def on_template_item_changed(self, current: QListWidgetItem, _previous: QListWidgetItem):
        try:
            template_id = current.data(Qt.UserRole) if current else ""
            if not template_id:
                self.template_meta.setText("未找到可用模板文件。请将模板 JSON 放入 templates/prompts 目录后点击“刷新”。")
                self.template_prompt_view.setPlainText("")
                return

            tpl = llm_service.get_prompt_template(str(template_id))
            if not tpl:
                self.template_meta.setText("模板读取失败，请点击“刷新”重试。")
                self.template_prompt_view.setPlainText("")
                return

            meta = f"ID：{tpl.id}\n名称：{tpl.name}\n描述：{tpl.description or '（无）'}"
            self.template_meta.setText(meta)
            self.template_prompt_view.setPlainText(tpl.user_prompt or "")
        except Exception as e:
            self.template_meta.setText(f"模板显示失败: {e}")
            self.template_prompt_view.setPlainText("")

    def _load_prompt_templates(self):
        """加载文案模板列表。"""
        try:
            self.prompt_template.clear()
            templates = llm_service.list_prompt_templates()
            if not templates:
                self.prompt_template.addItem("（未找到模板，使用默认内置）", "builtin")
                return

            for tpl in templates:
                self.prompt_template.addItem(tpl.name, tpl.id)

        except Exception:
            self.prompt_template.clear()
            self.prompt_template.addItem("（模板加载失败，使用默认内置）", "builtin")

    def on_prompt_template_changed(self, _index: int = 0):
        """模板切换时更新描述。"""
        try:
            template_id = self.prompt_template.currentData()
            tpl = llm_service.get_prompt_template(template_id)
            self.prompt_template_desc.setText(tpl.description if tpl else "")
        except Exception:
            self.prompt_template_desc.setText("")
    
    def on_provider_changed(self, provider):
        """当提供商改变时自动更新端点和模型名称"""
        # 自动更新端点和模型名称
        self.api_endpoint.setText(self.PROVIDER_ENDPOINTS.get(provider, ''))
        self.model_name.setText(self.PROVIDER_MODELS.get(provider, ''))
    
    def create_api_tab(self):
        """创建API配置标签页"""
        ui_font_family = get_ui_font_family()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # 标题
        title = QLabel("🔑 API管理配置")
        title.setFont(QFont(ui_font_family, 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 小红书API分组
        xhs_group = QGroupBox("📱 小红书API配置")
        xhs_layout = QFormLayout(xhs_group)
        xhs_layout.setSpacing(15)
        xhs_layout.setContentsMargins(20, 20, 20, 20)
        
        self.xhs_api_key = QLineEdit()
        self.xhs_api_key.setEchoMode(QLineEdit.Password)
        self.xhs_api_key.setFont(QFont(ui_font_family, 14))
        self.xhs_api_key.setPlaceholderText("请输入小红书API密钥")
        
        self.xhs_api_secret = QLineEdit()
        self.xhs_api_secret.setEchoMode(QLineEdit.Password)
        self.xhs_api_secret.setFont(QFont(ui_font_family, 14))
        self.xhs_api_secret.setPlaceholderText("请输入小红书API密钥密文")
        
        xhs_layout.addRow("🔑 API密钥：", self.xhs_api_key)
        xhs_layout.addRow("🔐 API密钥密文：", self.xhs_api_secret)
        
        # 图片存储分组
        storage_group = QGroupBox("🖼️ 图片存储配置")
        storage_layout = QFormLayout(storage_group)
        storage_layout.setSpacing(15)
        storage_layout.setContentsMargins(20, 20, 20, 20)
        
        self.image_provider = QComboBox()
        self.image_provider.addItems(["本地存储", "阿里云OSS", "腾讯云COS"])
        self.image_provider.setFont(QFont(ui_font_family, 14))
        
        self.image_endpoint = QLineEdit()
        self.image_endpoint.setFont(QFont(ui_font_family, 14))
        self.image_endpoint.setPlaceholderText("例如：https://your-bucket.oss-region.aliyuncs.com")
        
        storage_layout.addRow("☁️ 存储提供商：", self.image_provider)
        storage_layout.addRow("🔗 存储端点：", self.image_endpoint)
        
        layout.addWidget(xhs_group)
        layout.addWidget(storage_group)
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    def create_save_tab(self):
        """创建保存配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 保存按钮
        save_btn = QPushButton("💾 保存配置")
        save_btn.clicked.connect(self.save_config)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 25px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                min-width: 130px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #388e3c;
            }
        """)
        
        reset_btn = QPushButton("🔄 重置配置")
        reset_btn.clicked.connect(self.load_config)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 12px 25px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
                min-width: 130px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        
        layout.addWidget(save_btn)
        layout.addWidget(reset_btn)
        layout.addStretch()
        
        return widget
    
    def load_config(self):
        """加载配置"""
        try:
            self._api_key_placeholder_active = False
            self._api_key_name = ""

            # 定时发布配置
            schedule_config = self.config.get_schedule_config()
            self.schedule_enabled.setChecked(schedule_config.get('enabled', False))
            self.interval_hours.setValue(schedule_config.get('interval_hours', 2))
            self.max_posts.setValue(schedule_config.get('max_posts', 10))
            try:
                self.refresh_schedule_tasks()
            except Exception:
                pass
            
            # 模型配置
            model_config = self.config.get_model_config()

            saved_provider_raw = (model_config.get('provider', '') or '').strip() or 'OpenAI'
            saved_provider = self.PROVIDER_ALIASES.get(saved_provider_raw, saved_provider_raw)

            provider_index = self.model_provider.findText(saved_provider)
            if provider_index >= 0:
                self.model_provider.setCurrentIndex(provider_index)
            
            # 获取当前提供商
            current_provider = self.model_provider.currentText()
            
            # 设置API密钥（优先显示 settings.json 里的明文；否则使用本地加密存储）
            api_key_plain = (model_config.get('api_key', '') or '').strip()
            api_key_name = (model_config.get('api_key_name', '') or '').strip() or 'default'
            key_from_store = api_key_manager.get_key(current_provider, api_key_name) if api_key_name else None
            if not key_from_store and saved_provider_raw and saved_provider_raw != current_provider:
                legacy_key = api_key_manager.get_key(saved_provider_raw, api_key_name)
                if legacy_key:
                    key_from_store = legacy_key
                    # 自动迁移旧 provider 下的 key，避免保存后丢失
                    try:
                        api_key_manager.add_key(current_provider, api_key_name, legacy_key)
                    except Exception:
                        pass

            if api_key_plain:
                self.api_key.setText(api_key_plain)
                self.api_key.setPlaceholderText("请输入您的API密钥")
                self._api_key_placeholder_active = False
                self._api_key_name = api_key_name
                self.api_key_hint.setText("提示：已从 settings.json 读取 API Key。保存后会默认写入本地加密存储。")
            elif key_from_store:
                self.api_key.setText("")
                self.api_key.setPlaceholderText(f"已配置（加密存储：{api_key_name}），留空则保持不变")
                self._api_key_placeholder_active = True
                self._api_key_name = api_key_name
                self.api_key_hint.setText(f"提示：API Key 已加密保存（{api_key_name}）。如需更新，直接在此处粘贴新 Key 并保存。")
            else:
                self.api_key.setText("")
                self.api_key.setPlaceholderText("请输入您的API密钥")
                self._api_key_placeholder_active = False
                self._api_key_name = api_key_name
                self.api_key_hint.setText("提示：本地模型/localhost 一般无需 Key；公网模型通常需要 Key。")
            
            # 根据提供商自动设置默认端点和模型名称（保持向后兼容）
            saved_endpoint = model_config.get('api_endpoint', '')
            saved_model = model_config.get('model_name', '')
            
            # 如果用户已自定义端点或模型名称，保持用户设置
            if saved_endpoint and saved_endpoint != self.PROVIDER_ENDPOINTS.get(current_provider, ''):
                self.api_endpoint.setText(saved_endpoint)
            else:
                # 自动设置默认端点
                self.api_endpoint.setText(self.PROVIDER_ENDPOINTS.get(current_provider, ''))
                
            if saved_model and saved_model != self.PROVIDER_MODELS.get(current_provider, ''):
                self.model_name.setText(saved_model)
            else:
                # 自动设置默认模型名称
                self.model_name.setText(self.PROVIDER_MODELS.get(current_provider, ''))
            
            # 如果端点和模型名称为空，使用默认设置
            if not self.api_endpoint.text():
                self.api_endpoint.setText(self.PROVIDER_ENDPOINTS.get(current_provider, ''))
            if not self.model_name.text():
                self.model_name.setText(self.PROVIDER_MODELS.get(current_provider, ''))
                
            self.system_prompt.setPlainText(model_config.get('system_prompt', ''))
            editor = ChineseWritingEditor.from_config(model_config)
            self.chinese_editor_enabled.setChecked(editor.enabled)
            self.writing_sample.setPlainText(editor.writing_sample)
            self.writing_sample.setEnabled(editor.enabled)

            # 文案模板
            template_id = (model_config.get('prompt_template') or 'xiaohongshu_default')
            tpl_index = self.prompt_template.findData(template_id)
            if tpl_index >= 0:
                self.prompt_template.setCurrentIndex(tpl_index)
            else:
                # 找不到就保持默认第一个
                self.prompt_template.setCurrentIndex(0)
            self.on_prompt_template_changed(self.prompt_template.currentIndex())
            
            # API配置
            api_config = self.config.get_api_config()
            self.xhs_api_key.setText(api_config.get('xhs_api_key', ''))
            self.xhs_api_secret.setText(api_config.get('xhs_api_secret', ''))
            self.image_endpoint.setText(api_config.get('image_endpoint', ''))
            
            provider_index = self.image_provider.findText(api_config.get('image_provider', '本地存储'))
            if provider_index >= 0:
                self.image_provider.setCurrentIndex(provider_index)
                
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
    
    def save_config(self):
        """保存配置"""
        try:
            print("开始保存配置...")
            
            # 保存定时发布配置
            schedule_config = {
                'enabled': self.schedule_enabled.isChecked(),
                'schedule_time': self.schedule_time.dateTime().toString("yyyy-MM-dd HH:mm"),
                'interval_hours': self.interval_hours.value(),
                'max_posts': self.max_posts.value()
            }
            self.config.update_schedule_config(schedule_config)
            
            # 保存模型配置（API Key 默认加密存储到 ~/.xhs_system/keys.enc）
            provider = self.model_provider.currentText()
            api_key_name = (getattr(self, "_api_key_name", "") or "default").strip() or "default"
            api_key_plain = (self.api_key.text() or "").strip()

            stored_in_keychain = False
            if api_key_plain:
                try:
                    stored_in_keychain = bool(api_key_manager.add_key(provider, api_key_name, api_key_plain))
                except Exception:
                    stored_in_keychain = False

            if stored_in_keychain:
                api_key_to_save = ""
            else:
                # 用户手动输入但存储失败，则保底写入 settings.json，保证可用
                api_key_to_save = api_key_plain

            if not api_key_plain and getattr(self, "_api_key_placeholder_active", False):
                # 留空表示保持加密存储中的 key，不改动
                api_key_to_save = ""

            previous_model = self.config.get_model_config()
            advanced = dict(previous_model.get('advanced') or {
                'temperature': 0.7, 'max_tokens': 1000, 'timeout': 30
            })
            if llm_service._is_kimi_k3(self.api_endpoint.text(), self.model_name.text()):
                if previous_model.get('model_name') != self.model_name.text():
                    advanced.update(max_tokens=8192, timeout=180, reasoning_effort='high')
                else:
                    advanced.setdefault('reasoning_effort', 'high')
            model_config = {
                'provider': provider,
                'api_key': api_key_to_save,
                'api_key_name': api_key_name,
                'api_endpoint': self.api_endpoint.text(),
                'model_name': self.model_name.text(),
                'prompt_template': self.prompt_template.currentData(),
                'system_prompt': self.system_prompt.toPlainText(),
                'chinese_editor_enabled': self.chinese_editor_enabled.isChecked(),
                'writing_sample': self.writing_sample.toPlainText(),
                'advanced': advanced
            }
            self.config.update_model_config(model_config)
            
            # 保存API配置
            api_config = {
                'xhs_api_key': self.xhs_api_key.text(),
                'xhs_api_secret': self.xhs_api_secret.text(),
                'image_provider': self.image_provider.currentText(),
                'image_endpoint': self.image_endpoint.text(),
                'image_access_key': '',
                'image_secret_key': ''
            }
            self.config.update_api_config(api_config)
            
            print("配置保存完成")
            QMessageBox.information(self, "成功", "配置已保存！")
            
        except Exception as e:
            print(f"保存配置失败: {e}")
            QMessageBox.warning(self, "错误", f"保存配置失败: {str(e)}")

# 更新主程序引用
class BackendConfigPage(SimpleBackendConfigPage):
    pass
