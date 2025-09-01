#!/usr/bin/env python3
"""
现代化的后台配置页面
采用卡片式设计和直观的交互体验
"""

import json
import os
from datetime import datetime, timedelta
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QPoint, QEasingCurve
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QPalette, QLinearGradient, QPainter
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QGroupBox, QLineEdit, QComboBox, 
                           QTextEdit, QSpinBox, QCheckBox, QDateTimeEdit,
                           QTabWidget, QFormLayout, QMessageBox, QFileDialog,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QFrame, QScrollArea, QSizePolicy, QStackedWidget)

from src.config.config import Config
from src.core.scheduler.schedule_manager import schedule_manager


class CardWidget(QFrame):
    """现代化卡片组件"""
    
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            CardWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 20px;
                margin: 8px;
            }
            CardWidget:hover {
                border: 2px solid #4A90E2;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        if title:
            title_label = QLabel(title)
            title_label.setFont(QFont("PingFang SC", 16, QFont.Bold))
            title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
            self.layout.addWidget(title_label)


class ModernInput(QLineEdit):
    """现代化输入框"""
    
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                background-color: #fafafa;
            }
            QLineEdit:focus {
                border: 2px solid #4A90E2;
                background-color: white;
            }
            QLineEdit:hover {
                border: 2px solid #c0c0c0;
            }
        """)


class ModernTextEdit(QTextEdit):
    """现代化文本编辑框"""
    
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QTextEdit {
                padding: 12px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                font-family: "PingFang SC", "Microsoft YaHei";
                background-color: #fafafa;
                line-height: 1.6;
            }
            QTextEdit:focus {
                border: 2px solid #4A90E2;
                background-color: white;
            }
            QTextEdit:hover {
                border: 2px solid #c0c0c0;
            }
        """)


class ModernButton(QPushButton):
    """现代化按钮"""
    
    def __init__(self, text="", icon="", parent=None):
        super().__init__(text, parent)
        if icon:
            self.setText(f"{icon} {text}")
        
        self.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                background-color: #4A90E2;
                color: white;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2968A3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)


class StatusCard(CardWidget):
    """状态卡片"""
    
    def __init__(self, title, value, color="#4A90E2", parent=None):
        super().__init__()
        self.setFixedSize(200, 120)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        value_label = QLabel(str(value))
        value_label.setFont(QFont("PingFang SC", 24, QFont.Bold))
        value_label.setStyleSheet(f"color: {color};")
        value_label.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("PingFang SC", 12))
        title_label.setStyleSheet("color: #666666;")
        title_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(value_label)
        layout.addWidget(title_label)


class ModernBackendConfigPage(QWidget):
    """现代化的后台配置页面"""
    
    config_saved = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.config = Config()
        self.setup_ui()
        self.load_config()
        self.load_task_stats()
        
    def mousePressEvent(self, event):
        """调试按钮点击问题"""
        print(f"按钮点击事件: {event.pos()}")
        super().mousePressEvent(event)
    
    def setup_ui(self):
        """设置现代化界面""
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: "PingFang SC", "Microsoft YaHei";
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 标题区域
        header = self.create_header()
        layout.addWidget(header)
        
        # 状态概览
        stats = self.create_stats_overview()
        layout.addWidget(stats)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 使用现代化的标签页
        tab_widget.addTab(self.create_schedule_tab(), "⏰ 定时发布")
        tab_widget.addTab(self.create_model_tab(), "🤖 模型配置")
        tab_widget.addTab(self.create_api_tab(), "🔑 API管理")
        tab_widget.addTab(self.create_advanced_tab(), "⚡ 高级设置")
        
        layout.addWidget(tab_widget)
    
    def create_header(self):
        """创建现代化标题区域"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4A90E2, stop:1 #5BA3F5);
                border-radius: 12px;
                padding: 30px;
            }
        """)
        
        layout = QHBoxLayout(header)
        
        # 标题
        title_layout = QVBoxLayout()
        title = QLabel("后台配置中心")
        title.setFont(QFont("PingFang SC", 28, QFont.Bold))
        title.setStyleSheet("color: white;")
        
        subtitle = QLabel("管理您的定时发布、AI模型和API配置")
        subtitle.setFont(QFont("PingFang SC", 14))
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        layout.addLayout(title_layout)
        layout.addStretch()
        
        return header
    
    def create_stats_overview(self):
        """创建状态概览"""
        container = QFrame()
        container.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(container)
        layout.setSpacing(20)
        
        # 获取统计数据
        stats = schedule_manager.get_task_stats()
        
        cards = [
            ("总任务数", stats['total'], "#4A90E2"),
            ("待执行", stats['pending'], "#FF9500"),
            ("已完成", stats['completed'], "#34C759"),
            ("失败", stats['failed'], "#FF3B30")
        ]
        
        for title, value, color in cards:
            card = StatusCard(title, value, color)
            layout.addWidget(card)
        
        return container
    
    def create_schedule_tab(self):
        """创建现代化的定时发布标签页"""
        tab = QScrollArea()
        tab.setWidgetResizable(True)
        tab.setStyleSheet("background: transparent; border: none;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        
        # 快速设置卡片
        quick_setup = CardWidget("📅 快速设置")
        quick_layout = QVBoxLayout()
        
        # 开关按钮
        switch_layout = QHBoxLayout()
        self.schedule_enabled = QCheckBox("启用定时发布")
        self.schedule_enabled.setStyleSheet("""
            QCheckBox {
                font-size: 16px;
                font-weight: 600;
                color: #2c3e50;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid #e0e0e0;
            }
            QCheckBox::indicator:checked {
                background-color: #4A90E2;
                border-color: #4A90E2;
            }
        """)
        switch_layout.addWidget(self.schedule_enabled)
        switch_layout.addStretch()
        quick_layout.addLayout(switch_layout)
        
        # 设置表单
        form_layout = QHBoxLayout()
        
        # 时间选择器
        time_group = QGroupBox("发布时间")
        time_group.setStyleSheet("""
            QGroupBox {
                font-weight: 600;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        time_layout = QVBoxLayout(time_group)
        self.schedule_time = QDateTimeEdit()
        self.schedule_time.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.schedule_time.setMinimumDateTime(datetime.now())
        self.schedule_time.setCalendarPopup(True)
        self.schedule_time.setStyleSheet("""
            QDateTimeEdit {
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
            }
        """)
        time_layout.addWidget(self.schedule_time)
        
        # 间隔设置
        interval_group = QGroupBox("发布间隔")
        interval_layout = QVBoxLayout(interval_group)
        self.interval_hours = QSpinBox()
        self.interval_hours.setRange(1, 168)
        self.interval_hours.setSuffix(" 小时")
        self.interval_hours.setStyleSheet("""
            QSpinBox {
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
            }
        """)
        interval_layout.addWidget(self.interval_hours)
        
        # 数量限制
        limit_group = QGroupBox("每日限制")
        limit_layout = QVBoxLayout(limit_group)
        self.max_posts = QSpinBox()
        self.max_posts.setRange(1, 50)
        self.max_posts.setSuffix(" 条")
        self.max_posts.setStyleSheet("""
            QSpinBox {
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
            }
        """)
        limit_layout.addWidget(self.max_posts)
        
        form_layout.addWidget(time_group)
        form_layout.addWidget(interval_group)
        form_layout.addWidget(limit_group)
        quick_layout.addLayout(form_layout)
        
        quick_setup.setLayout(quick_layout)
        layout.addWidget(quick_setup)
        
        # 任务管理卡片
        task_card = CardWidget("📋 任务管理")
        task_layout = QVBoxLayout()
        
        # 任务表格
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels(["内容", "发布时间", "状态", "创建时间", "操作"])
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.task_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 12px;
                border: none;
                font-weight: 600;
                color: #2c3e50;
            }
        """)
        task_layout.addWidget(self.task_table)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        add_btn = ModernButton("添加任务", "➕")
        add_btn.clicked.connect(self.add_schedule_task)
        
        clear_btn = ModernButton("清空任务", "🗑️")
        clear_btn.setStyleSheet(add_btn.styleSheet().replace("#4A90E2", "#FF3B30"))
        clear_btn.clicked.connect(self.clear_schedule_tasks)
        
        refresh_btn = ModernButton("刷新", "🔄")
        refresh_btn.setStyleSheet(add_btn.styleSheet().replace("#4A90E2", "#34C759"))
        refresh_btn.clicked.connect(self.refresh_task_table)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        task_layout.addLayout(btn_layout)
        
        task_card.setLayout(task_layout)
        layout.addWidget(task_card)
        
        tab.setWidget(content)
        return tab
    
    def create_model_tab(self):
        """创建现代化的模型配置标签页"""
        tab = QScrollArea()
        tab.setWidgetResizable(True)
        tab.setStyleSheet("background: transparent; border: none;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        
        # 模型选择卡片
        model_card = CardWidget("🤖 AI模型配置")
        model_layout = QVBoxLayout()
        
        # 提供商选择
        provider_layout = QHBoxLayout()
        provider_label = QLabel("提供商")
        provider_label.setFont(QFont("PingFang SC", 14, QFont.Bold))
        self.model_provider = QComboBox()
        self.model_provider.addItems([
            "OpenAI GPT-4", 
            "OpenAI GPT-3.5", 
            "Claude 3.5", 
            "Claude 3",
            "本地模型",
            "自定义API"
        ])
        self.model_provider.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
                min-width: 200px;
            }
        """)
        provider_layout.addWidget(provider_label)
        provider_layout.addWidget(self.model_provider)
        provider_layout.addStretch()
        model_layout.addLayout(provider_layout)
        
        # 配置输入
        config_form = QFormLayout()
        config_form.setSpacing(15)
        
        self.api_key = ModernInput("输入API密钥")
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_endpoint = ModernInput("https://api.openai.com/v1/chat/completions")
        self.model_name = ModernInput("gpt-3.5-turbo")
        self.system_prompt = ModernTextEdit("输入自定义系统提示词...")
        self.system_prompt.setMaximumHeight(80)
        
        config_form.addRow("🔑 API密钥:", self.api_key)
        config_form.addRow("🔗 API端点:", self.api_endpoint)
        config_form.addRow("🤖 模型名称:", self.model_name)
        config_form.addRow("💬 系统提示词:", self.system_prompt)
        
        model_layout.addLayout(config_form)
        model_card.setLayout(model_layout)
        layout.addWidget(model_card)
        
        # 高级设置卡片
        advanced_card = CardWidget("⚡ 高级参数")
        advanced_layout = QHBoxLayout()
        
        # 温度设置
        temp_group = QGroupBox("随机度")
        temp_layout = QVBoxLayout()
        self.temperature = QSpinBox()
        self.temperature.setRange(0, 100)
        self.temperature.setValue(70)
        self.temperature.setSuffix("%")
        self.temperature.setStyleSheet("""
            QSpinBox {
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
                width: 100px;
            }
        """)
        temp_layout.addWidget(self.temperature)
        temp_group.setLayout(temp_layout)
        
        # Token限制
        token_group = QGroupBox("最大长度")
        token_layout = QVBoxLayout()
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(100, 4000)
        self.max_tokens.setValue(1000)
        self.max_tokens.setSuffix(" tokens")
        self.max_tokens.setStyleSheet("""
            QSpinBox {
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
                width: 120px;
            }
        """)
        token_layout.addWidget(self.max_tokens)
        token_group.setLayout(token_layout)
        
        # 超时时间
        timeout_group = QGroupBox("超时时间")
        timeout_layout = QVBoxLayout()
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 300)
        self.timeout.setValue(30)
        self.timeout.setSuffix(" 秒")
        self.timeout.setStyleSheet("""
            QSpinBox {
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
                width: 100px;
            }
        """)
        timeout_layout.addWidget(self.timeout)
        timeout_group.setLayout(timeout_layout)
        
        advanced_layout.addWidget(temp_group)
        advanced_layout.addWidget(token_group)
        advanced_layout.addWidget(timeout_group)
        advanced_card.setLayout(advanced_layout)
        layout.addWidget(advanced_card)
        
        tab.setWidget(content)
        return tab
    
    def create_api_tab(self):
        """创建现代化的API配置标签页"""
        tab = QScrollArea()
        tab.setWidgetResizable(True)
        tab.setStyleSheet("background: transparent; border: none;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        
        # 小红书配置
        xhs_card = CardWidget("📱 小红书API配置")
        xhs_layout = QFormLayout()
        xhs_layout.setSpacing(15)
        
        self.xhs_api_key = ModernInput("小红书API密钥")
        self.xhs_api_key.setEchoMode(QLineEdit.Password)
        self.xhs_api_secret = ModernInput("小红书API密钥密文")
        self.xhs_api_secret.setEchoMode(QLineEdit.Password)
        
        xhs_layout.addRow("🔑 API密钥:", self.xhs_api_key)
        xhs_layout.addRow("🔐 API密钥密文:", self.xhs_api_secret)
        
        xhs_card.setLayout(xhs_layout)
        layout.addWidget(xhs_card)
        
        # 图片存储配置
        storage_card = CardWidget("🖼️ 图片存储配置")
        storage_layout = QVBoxLayout()
        
        # 提供商选择
        provider_layout = QHBoxLayout()
        provider_label = QLabel("存储提供商")
        provider_label.setFont(QFont("PingFang SC", 14, QFont.Bold))
        self.image_provider = QComboBox()
        self.image_provider.addItems([
            "本地存储",
            "阿里云OSS",
            "腾讯云COS",
            "七牛云",
            "自定义CDN"
        ])
        self.image_provider.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
                min-width: 200px;
            }
        """)
        provider_layout.addWidget(provider_label)
        provider_layout.addWidget(self.image_provider)
        provider_layout.addStretch()
        storage_layout.addLayout(provider_layout)
        
        # 存储配置
        storage_form = QFormLayout()
        storage_form.setSpacing(15)
        
        self.image_endpoint = ModernInput("https://your-cdn.com")
        self.image_access_key = ModernInput("访问密钥")
        self.image_access_key.setEchoMode(QLineEdit.Password)
        self.image_secret_key = ModernInput("密钥密文")
        self.image_secret_key.setEchoMode(QLineEdit.Password)
        
        storage_form.addRow("🔗 存储端点:", self.image_endpoint)
        storage_form.addRow("🔑 访问密钥:", self.image_access_key)
        storage_form.addRow("🔐 密钥密文:", self.image_secret_key)
        
        storage_layout.addLayout(storage_form)
        storage_card.setLayout(storage_layout)
        layout.addWidget(storage_card)
        
        tab.setWidget(content)
        return tab
    
    def create_advanced_tab(self):
        """创建高级设置标签页"""
        tab = QScrollArea()
        tab.setWidgetResizable(True)
        tab.setStyleSheet("background: transparent; border: none;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        
        # 保存配置卡片
        save_card = CardWidget("💾 配置管理")
        save_layout = QHBoxLayout()
        save_layout.setSpacing(15)
        
        save_btn = ModernButton("保存配置", "💾")
        save_btn.clicked.connect(self.save_config)
        
        reset_btn = ModernButton("重置配置", "🔄")
        reset_btn.setStyleSheet(save_btn.styleSheet().replace("#4A90E2", "#FF9500"))
        reset_btn.clicked.connect(self.reset_config)
        
        export_btn = ModernButton("导出配置", "📤")
        export_btn.setStyleSheet(save_btn.styleSheet().replace("#4A90E2", "#34C759"))
        export_btn.clicked.connect(self.export_config)
        
        import_btn = ModernButton("导入配置", "📥")
        import_btn.setStyleSheet(save_btn.styleSheet().replace("#4A90E2", "#5E5CE6"))
        import_btn.clicked.connect(self.import_config)
        
        save_layout.addWidget(save_btn)
        save_layout.addWidget(reset_btn)
        save_layout.addWidget(export_btn)
        save_layout.addWidget(import_btn)
        save_layout.addStretch()
        
        save_card.setLayout(save_layout)
        layout.addWidget(save_card)
        
        tab.setWidget(content)
        return tab
    
    def load_task_stats(self):
        """加载任务统计"""
        stats = schedule_manager.get_task_stats()
        # 这里可以更新状态卡片
    
    def load_config(self):
        """加载配置"""
        try:
            # 定时发布配置
            schedule_config = self.config.get_schedule_config()
            self.schedule_enabled.setChecked(schedule_config.get('enabled', False))
            self.interval_hours.setValue(schedule_config.get('interval_hours', 2))
            self.max_posts.setValue(schedule_config.get('max_posts', 10))
            
            # 模型配置
            model_config = self.config.get_model_config()
            provider_index = self.model_provider.findText(model_config.get('provider', 'OpenAI GPT-3.5'))
            if provider_index >= 0:
                self.model_provider.setCurrentIndex(provider_index)
            
            self.api_key.setText(model_config.get('api_key', ''))
            self.api_endpoint.setText(model_config.get('api_endpoint', ''))
            self.model_name.setText(model_config.get('model_name', ''))
            self.system_prompt.setPlainText(model_config.get('system_prompt', ''))
            
            # 高级配置
            advanced_config = model_config.get('advanced', {})
            self.temperature.setValue(int(advanced_config.get('temperature', 0.7) * 100))
            self.max_tokens.setValue(advanced_config.get('max_tokens', 1000))
            self.timeout.setValue(advanced_config.get('timeout', 30))
            
            # API配置
            api_config = self.config.get_api_config()
            self.xhs_api_key.setText(api_config.get('xhs_api_key', ''))
            self.xhs_api_secret.setText(api_config.get('xhs_api_secret', ''))
            self.image_endpoint.setText(api_config.get('image_endpoint', ''))
            self.image_access_key.setText(api_config.get('image_access_key', ''))
            self.image_secret_key.setText(api_config.get('image_secret_key', ''))
            
            provider_index = self.image_provider.findText(api_config.get('image_provider', '本地存储'))
            if provider_index >= 0:
                self.image_provider.setCurrentIndex(provider_index)
                
            self.refresh_task_table()
                
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
    
    def refresh_task_table(self):
        """刷新任务表格"""
        tasks = schedule_manager.get_tasks()
        self.task_table.setRowCount(len(tasks))
        
        for row, task in enumerate(tasks):
            self.task_table.setItem(row, 0, QTableWidgetItem(task.content[:50] + "..."))
            self.task_table.setItem(row, 1, QTableWidgetItem(task.schedule_time.strftime("%Y-%m-%d %H:%M")))
            
            status_text = {
                "pending": "待执行",
                "running": "执行中",
                "completed": "已完成",
                "failed": "失败"
            }.get(task.status, task.status)
            
            status_item = QTableWidgetItem(status_text)
            if task.status == "completed":
                status_item.setBackground(QColor("#E8F5E8"))
            elif task.status == "failed":
                status_item.setBackground(QColor("#FFE8E8"))
            
            self.task_table.setItem(row, 2, status_item)
            self.task_table.setItem(row, 3, QTableWidgetItem(task.created_at.strftime("%Y-%m-%d %H:%M")))
    
    def add_schedule_task(self):
        """添加定时任务"""
        # 这里可以添加任务创建对话框
        QMessageBox.information(self, "提示", "任务添加功能将在下一版本提供")
    
    def clear_schedule_tasks(self):
        """清空定时任务"""
        reply = QMessageBox.question(self, "确认", "确定要清空所有任务吗？", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            schedule_manager.clear_completed_tasks()
            self.refresh_task_table()
    
    def save_config(self):
        """保存配置"""
        try:
            print("开始保存配置...")  # 调试信息
            
            # 保存定时发布配置
            schedule_config = {
                'enabled': self.schedule_enabled.isChecked(),
                'schedule_time': self.schedule_time.dateTime().toString("yyyy-MM-dd HH:mm"),
                'interval_hours': self.interval_hours.value(),
                'max_posts': self.max_posts.value()
            }
            self.config.update_schedule_config(schedule_config)
            
            # 保存模型配置
            model_config = {
                'provider': self.model_provider.currentText(),
                'api_key': self.api_key.text(),
                'api_endpoint': self.api_endpoint.text(),
                'model_name': self.model_name.text(),
                'system_prompt': self.system_prompt.toPlainText(),
                'advanced': {
                    'temperature': self.temperature.value() / 100,
                    'max_tokens': self.max_tokens.value(),
                    'timeout': self.timeout.value()
                }
            }
            self.config.update_model_config(model_config)
            
            # 保存API配置
            api_config = {
                'xhs_api_key': self.xhs_api_key.text(),
                'xhs_api_secret': self.xhs_api_secret.text(),
                'image_provider': self.image_provider.currentText(),
                'image_endpoint': self.image_endpoint.text(),
                'image_access_key': self.image_access_key.text(),
                'image_secret_key': self.image_secret_key.text()
            }
            self.config.update_api_config(api_config)
            
            print("配置保存完成")  # 调试信息
            self.config_saved.emit()
            QMessageBox.information(self, "成功", "配置已保存！")
            
        except Exception as e:
            print(f"保存配置失败: {e}")  # 调试信息
            QMessageBox.warning(self, "错误", f"保存配置失败: {str(e)}")
    
    def reset_config(self):
        """重置配置"""
        reply = QMessageBox.question(self, "确认", "确定要重置所有配置吗？", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.load_config()
    
    def export_config(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", "", "JSON文件 (*.json)"
        )
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config.config, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "成功", f"配置已导出到: {file_path}")
    
    def import_config(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", "", "JSON文件 (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.config.config = json.load(f)
                    self.config.save_config()
                self.load_config()
                QMessageBox.information(self, "成功", "配置已导入！")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入配置失败: {str(e)}")


# 更新主程序引用
class BackendConfigPage(ModernBackendConfigPage):
    pass