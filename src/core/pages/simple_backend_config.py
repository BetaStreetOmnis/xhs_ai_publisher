#!/usr/bin/env python3
"""
简化的后台配置页面
解决按钮点击问题
"""

import json
import os
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QLineEdit, QComboBox, QTextEdit, 
                           QSpinBox, QCheckBox, QDateTimeEdit, QTabWidget, 
                           QFormLayout, QMessageBox, QScrollArea, QFrame, QGroupBox)

from src.config.config import Config

class SimpleBackendConfigPage(QWidget):
    """简化的后台配置页面"""
    
    config_saved = pyqtSignal()
    
    # 提供商端点映射
    PROVIDER_ENDPOINTS = {
        "OpenAI GPT-4": "https://api.openai.com/v1/chat/completions",
        "OpenAI GPT-3.5": "https://api.openai.com/v1/chat/completions",
        "Claude 3.5": "https://api.anthropic.com/v1/messages",
        "Qwen3": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "Kimi2": "https://api.moonshot.cn/v1/chat/completions",
        "本地模型": "http://localhost:1234/v1/chat/completions"
    }
    
    # 默认模型名称映射
    PROVIDER_MODELS = {
        "OpenAI GPT-4": "gpt-4",
        "OpenAI GPT-3.5": "gpt-3.5-turbo",
        "Claude 3.5": "claude-3-5-sonnet-20241022",
        "Qwen3": "qwen3-72b-instruct",
        "Kimi2": "kimi2-latest",
        "本地模型": "local-model"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.config = Config()
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """设置优化界面"""
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
            }
            QPushButton {
                font-size: 16px;
                font-family: "PingFang SC", "Microsoft YaHei";
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 500;
            }
            QLabel {
                font-size: 15px;
                font-family: "PingFang SC", "Microsoft YaHei";
                font-weight: 500;
                color: #2c3e50;
            }
            QLineEdit, QTextEdit, QComboBox {
                font-size: 15px;
                font-family: "PingFang SC", "Microsoft YaHei";
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
            }
            QGroupBox {
                font-size: 16px;
                font-family: "PingFang SC", "Microsoft YaHei";
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                background-color: white;
            }
            QTabBar::tab {
                font-size: 13px;
                font-family: "PingFang SC", "Microsoft YaHei";
                padding: 8px 16px;
                margin-right: 2px;
                background-color: #f1f3f4;
                border-radius: 8px 8px 0 0;
                color: #5f6368;
                min-width: 100px;
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
        """)
        
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
        title.setFont(QFont("PingFang SC", 24, QFont.Bold))
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("管理您的定时发布、AI模型和API配置")
        subtitle.setFont(QFont("PingFang SC", 16))
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
        title.setFont(QFont("PingFang SC", 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 启用开关
        self.schedule_enabled = QCheckBox("✅ 启用定时发布功能")
        self.schedule_enabled.setFont(QFont("PingFang SC", 16))
        layout.addWidget(self.schedule_enabled)
        
        # 创建分组
        group = QGroupBox("发布设置")
        group_layout = QFormLayout(group)
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(20, 20, 20, 20)
        
        self.schedule_time = QDateTimeEdit()
        self.schedule_time.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.schedule_time.setMinimumDateTime(datetime.now())
        self.schedule_time.setFont(QFont("PingFang SC", 14))
        
        self.interval_hours = QSpinBox()
        self.interval_hours.setRange(1, 24)
        self.interval_hours.setSuffix(" 小时")
        self.interval_hours.setFont(QFont("PingFang SC", 14))
        
        self.max_posts = QSpinBox()
        self.max_posts.setRange(1, 50)
        self.max_posts.setSuffix(" 条")
        self.max_posts.setFont(QFont("PingFang SC", 14))
        
        group_layout.addRow("🕐 发布时间：", self.schedule_time)
        group_layout.addRow("📅 发布间隔：", self.interval_hours)
        group_layout.addRow("📊 每日限制：", self.max_posts)
        
        layout.addWidget(group)
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
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
        title.setFont(QFont("PingFang SC", 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 创建分组
        group = QGroupBox("模型设置")
        group_layout = QFormLayout(group)
        group_layout.setSpacing(15)
        group_layout.setContentsMargins(20, 20, 20, 20)
        
        self.model_provider = QComboBox()
        self.model_provider.addItems([
            "OpenAI GPT-4", "OpenAI GPT-3.5", "Claude 3.5", 
            "Qwen3", "Kimi2", "本地模型"
        ])
        self.model_provider.setFont(QFont("PingFang SC", 14))
        self.model_provider.currentTextChanged.connect(self.on_provider_changed)
        
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setFont(QFont("PingFang SC", 14))
        self.api_key.setPlaceholderText("请输入您的API密钥")
        
        self.api_endpoint = QLineEdit()
        self.api_endpoint.setFont(QFont("PingFang SC", 14))
        self.api_endpoint.setPlaceholderText("例如：https://api.openai.com/v1/chat/completions")
        
        self.model_name = QLineEdit()
        self.model_name.setFont(QFont("PingFang SC", 14))
        self.model_name.setPlaceholderText("例如：gpt-3.5-turbo")
        
        self.system_prompt = QTextEdit()
        self.system_prompt.setMaximumHeight(120)
        self.system_prompt.setFont(QFont("PingFang SC", 14))
        self.system_prompt.setPlaceholderText("请输入自定义系统提示词，这将影响AI生成内容的方式...")
        
        group_layout.addRow("🤖 提供商：", self.model_provider)
        group_layout.addRow("🔑 API密钥：", self.api_key)
        group_layout.addRow("🔗 API端点：", self.api_endpoint)
        group_layout.addRow("⚙️ 模型名称：", self.model_name)
        group_layout.addRow("💬 系统提示：", self.system_prompt)
        
        layout.addWidget(group)
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    def on_provider_changed(self, provider):
        """当提供商改变时自动更新端点和模型名称"""
        # 自动更新端点和模型名称
        self.api_endpoint.setText(self.PROVIDER_ENDPOINTS.get(provider, ''))
        self.model_name.setText(self.PROVIDER_MODELS.get(provider, ''))
    
    def create_api_tab(self):
        """创建API配置标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # 标题
        title = QLabel("🔑 API管理配置")
        title.setFont(QFont("PingFang SC", 20, QFont.Bold))
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 小红书API分组
        xhs_group = QGroupBox("📱 小红书API配置")
        xhs_layout = QFormLayout(xhs_group)
        xhs_layout.setSpacing(15)
        xhs_layout.setContentsMargins(20, 20, 20, 20)
        
        self.xhs_api_key = QLineEdit()
        self.xhs_api_key.setEchoMode(QLineEdit.Password)
        self.xhs_api_key.setFont(QFont("PingFang SC", 14))
        self.xhs_api_key.setPlaceholderText("请输入小红书API密钥")
        
        self.xhs_api_secret = QLineEdit()
        self.xhs_api_secret.setEchoMode(QLineEdit.Password)
        self.xhs_api_secret.setFont(QFont("PingFang SC", 14))
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
        self.image_provider.setFont(QFont("PingFang SC", 14))
        
        self.image_endpoint = QLineEdit()
        self.image_endpoint.setFont(QFont("PingFang SC", 14))
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
            
            # 获取当前提供商
            current_provider = self.model_provider.currentText()
            
            # 设置API密钥
            self.api_key.setText(model_config.get('api_key', ''))
            
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
            
            # 保存模型配置
            model_config = {
                'provider': self.model_provider.currentText(),
                'api_key': self.api_key.text(),
                'api_endpoint': self.api_endpoint.text(),
                'model_name': self.model_name.text(),
                'system_prompt': self.system_prompt.toPlainText(),
                'advanced': {
                    'temperature': 0.7,
                    'max_tokens': 1000,
                    'timeout': 30
                }
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