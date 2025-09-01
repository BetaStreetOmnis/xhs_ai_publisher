#!/usr/bin/env python3
"""
AI封面生成页面
支持AI文字生成和动态贴图到模板
"""

import os
import json
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QGridLayout, 
                             QComboBox, QLineEdit, QTextEdit, QMessageBox, 
                             QFileDialog, QProgressBar, QTabWidget, QSplitter,
                             QListWidget, QListWidgetItem, QGroupBox)

# 导入增强版服务
from src.core.services.enhanced_cover_service import enhanced_cover_service
from src.core.generation.cover_text_generator import CoverTextGenerator


class AICoverGeneratorThread(QThread):
    """AI封面生成线程"""
    finished = pyqtSignal(dict)  # 生成完成，返回结果
    error = pyqtSignal(str)
    
    def __init__(self, content, template_type, platform="xiaohongshu", bg_image_path=None):
        super().__init__()
        self.content = content
        self.template_type = template_type
        self.platform = platform
        self.bg_image_path = bg_image_path
    
    def run(self):
        try:
            result = enhanced_cover_service.generate_ai_cover(
                content=self.content,
                template_type=self.template_type,
                platform=self.platform,
                bg_image_path=self.bg_image_path
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class BatchAICoverThread(QThread):
    """批量AI封面生成线程"""
    progress = pyqtSignal(int, int)  # 当前进度，总数
    finished = pyqtSignal(list)      # 所有结果
    error = pyqtSignal(str)
    
    def __init__(self, content, template_types, platform="xiaohongshu"):
        super().__init__()
        self.content = content
        self.template_types = template_types
        self.platform = platform
    
    def run(self):
        try:
            results = []
            for i, template_type in enumerate(self.template_types):
                result = enhanced_cover_service.generate_ai_cover(
                    content=self.content,
                    template_type=template_type,
                    platform=self.platform
                )
                results.append(result)
                self.progress.emit(i + 1, len(self.template_types))
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class AICoverPreviewWidget(QWidget):
    """AI封面预览组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_preview = None
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 预览图片
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 400)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 10px;
                background-color: #f8f9fa;
            }
        """)
        self.preview_label.setText("封面预览")
        layout.addWidget(self.preview_label)
        
        # 文字信息
        self.text_info_group = QGroupBox("封面文字")
        text_layout = QVBoxLayout(self.text_info_group)
        
        self.title_label = QLabel("主标题: -")
        self.title_label.setFont(QFont("Microsoft YaHei", 11))
        text_layout.addWidget(self.title_label)
        
        self.subtitle_label = QLabel("副标题: -")
        self.subtitle_label.setFont(QFont("Microsoft YaHei", 10))
        text_layout.addWidget(self.subtitle_label)
        
        self.tags_label = QLabel("标签: -")
        self.tags_label.setFont(QFont("Microsoft YaHei", 9))
        text_layout.addWidget(self.tags_label)
        
        layout.addWidget(self.text_info_group)
    
    def update_preview(self, cover_path: str, cover_text: dict):
        """更新预览"""
        self.current_preview = cover_path
        
        # 更新图片
        if os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            scaled_pixmap = pixmap.scaled(380, 380, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
            self.preview_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #4a90e2;
                    border-radius: 10px;
                }
            """)
        
        # 更新文字信息
        self.title_label.setText(f"主标题: {cover_text.get('main_title', '')}")
        self.subtitle_label.setText(f"副标题: {cover_text.get('subtitle', '')}")
        tags_str = ' '.join(cover_text.get('tags', []))
        self.tags_label.setText(f"标签: {tags_str}")


class AICoverPage(QWidget):
    """AI封面生成页面"""
    
    cover_generated = pyqtSignal(str)  # 封面生成完成
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.current_results = []
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title = QLabel("🎨 AI智能封面生成")
        title.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 主区域 - 使用QSplitter
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧控制面板
        self.create_control_panel(main_splitter)
        
        # 右侧预览区域
        self.create_preview_area(main_splitter)
        
        main_splitter.setStretchFactor(0, 1)  # 左侧占1份
        main_splitter.setStretchFactor(1, 2)  # 右侧占2份
        main_splitter.setSizes([400, 800])
        
        layout.addWidget(main_splitter)
    
    def create_control_panel(self, parent):
        """创建控制面板"""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setSpacing(15)
        
        # 内容输入
        content_group = QGroupBox("📄 内容输入")
        content_layout = QVBoxLayout(content_group)
        
        self.content_text = QTextEdit()
        self.content_text.setPlaceholderText("输入您要发布的内容，AI将为您生成适合的封面文字...")
        self.content_text.setMaximumHeight(150)
        content_layout.addWidget(self.content_text)
        
        # 快速生成按钮
        quick_gen_btn = QPushButton("✨ AI一键生成")
        quick_gen_btn.clicked.connect(self.quick_generate)
        quick_gen_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF2442;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #E91E63;
            }
        """)
        content_layout.addWidget(quick_gen_btn)
        
        control_layout.addWidget(content_group)
        
        # 高级设置
        settings_group = QGroupBox("⚙️ 高级设置")
        settings_layout = QVBoxLayout(settings_group)
        
        # 平台选择
        platform_layout = QHBoxLayout()
        platform_layout.addWidget(QLabel("平台:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItems([
            "xiaohongshu",
            "douyin", 
            "weibo",
            "instagram"
        ])
        platform_layout.addWidget(self.platform_combo)
        settings_layout.addLayout(platform_layout)
        
        # 模板选择
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("模板:"))
        self.template_combo = QComboBox()
        self.template_combo.addItems([
            "时尚模板",
            "生活模板", 
            "美妆模板",
            "美食模板",
            "旅行模板"
        ])
        template_layout.addWidget(self.template_combo)
        settings_layout.addLayout(template_layout)
        
        # 背景图片选择
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel("背景:"))
        self.bg_path_label = QLabel("使用默认背景")
        self.bg_path_label.setStyleSheet("color: #666; font-size: 11px;")
        bg_layout.addWidget(self.bg_path_label)
        
        select_bg_btn = QPushButton("选择")
        select_bg_btn.setFixedWidth(60)
        select_bg_btn.clicked.connect(self.select_background)
        bg_layout.addWidget(select_bg_btn)
        settings_layout.addLayout(bg_layout)
        
        control_layout.addWidget(settings_group)
        
        # 生成按钮组
        button_group = QGroupBox("🚀 生成选项")
        button_layout = QVBoxLayout(button_group)
        
        self.generate_single_btn = QPushButton("生成单张封面")
        self.generate_single_btn.clicked.connect(self.generate_single)
        button_layout.addWidget(self.generate_single_btn)
        
        self.generate_batch_btn = QPushButton("批量生成多个")
        self.generate_batch_btn.clicked.connect(self.generate_batch)
        button_layout.addWidget(self.generate_batch_btn)
        
        control_layout.addWidget(button_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        control_layout.addStretch()
        
        parent.addWidget(control_widget)
    
    def create_preview_area(self, parent):
        """创建预览区域"""
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # 单张预览标签页
        self.single_preview = AICoverPreviewWidget()
        self.tab_widget.addTab(self.single_preview, "单张预览")
        
        # 批量结果标签页
        self.batch_widget = QWidget()
        batch_layout = QVBoxLayout(self.batch_widget)
        
        self.batch_list = QListWidget()
        self.batch_list.itemClicked.connect(self.on_batch_item_selected)
        batch_layout.addWidget(self.batch_list)
        
        self.tab_widget.addTab(self.batch_widget, "批量结果")
        
        preview_layout.addWidget(self.tab_widget)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("保存封面")
        self.save_btn.clicked.connect(self.save_current_cover)
        button_layout.addWidget(self.save_btn)
        
        self.use_btn = QPushButton("使用此封面")
        self.use_btn.clicked.connect(self.use_current_cover)
        button_layout.addWidget(self.use_btn)
        
        preview_layout.addLayout(button_layout)
        
        parent.addWidget(preview_widget)
    
    def quick_generate(self):
        """快速生成"""
        content = self.content_text.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请输入内容后再生成")
            return
        
        template_type = self.get_template_type_from_combo()
        platform = self.platform_combo.currentText()
        bg_path = self.get_background_path()
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        # 启动生成线程
        self.generator_thread = AICoverGeneratorThread(
            content=content,
            template_type=template_type,
            platform=platform,
            bg_image_path=bg_path
        )
        self.generator_thread.finished.connect(self.on_single_generated)
        self.generator_thread.error.connect(self.on_generation_error)
        self.generator_thread.start()
    
    def generate_single(self):
        """生成单张封面"""
        self.quick_generate()
    
    def generate_batch(self):
        """批量生成"""
        content = self.content_text.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请输入内容后再生成")
            return
        
        template_types = ["fashion", "lifestyle", "beauty", "food", "travel"]
        platform = self.platform_combo.currentText()
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(template_types))
        
        # 启动批量生成线程
        self.batch_thread = BatchAICoverThread(
            content=content,
            template_types=template_types,
            platform=platform
        )
        self.batch_thread.progress.connect(self.on_batch_progress)
        self.batch_thread.finished.connect(self.on_batch_generated)
        self.batch_thread.error.connect(self.on_generation_error)
        self.batch_thread.start()
    
    def on_single_generated(self, result: dict):
        """单张生成完成"""
        self.progress_bar.setVisible(False)
        self.current_results = [result]
        
        # 更新预览
        self.single_preview.update_preview(
            result['cover_path'],
            result['cover_text']
        )
        
        # 切换到单张预览
        self.tab_widget.setCurrentIndex(0)
    
    def on_batch_generated(self, results: list):
        """批量生成完成"""
        self.progress_bar.setVisible(False)
        self.current_results = results
        
        # 更新批量列表
        self.batch_list.clear()
        for i, result in enumerate(results):
            item = QListWidgetItem(f"方案{i+1}: {result['template_type']}")
            item.setData(Qt.UserRole, result)
            self.batch_list.addItem(item)
        
        # 切换到批量结果
        self.tab_widget.setCurrentIndex(1)
    
    def on_batch_progress(self, current: int, total: int):
        """批量生成进度"""
        self.progress_bar.setValue(current)
        self.progress_bar.setMaximum(total)
    
    def on_generation_error(self, error_msg: str):
        """生成错误"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "生成失败", error_msg)
    
    def on_batch_item_selected(self, item):
        """批量项目选择"""
        result = item.data(Qt.UserRole)
        if result:
            self.single_preview.update_preview(
                result['cover_path'],
                result['cover_text']
            )
            self.tab_widget.setCurrentIndex(0)
    
    def select_background(self):
        """选择背景图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_path:
            filename = os.path.basename(file_path)
            self.bg_path_label.setText(filename[:20] + "..." if len(filename) > 20 else filename)
    
    def get_background_path(self) -> str:
        """获取背景图片路径"""
        text = self.bg_path_label.text()
        return None if text in ["使用默认背景", "未选择"] else text
    
    def get_template_type_from_combo(self) -> str:
        """从下拉框获取模板类型"""
        mapping = {
            "时尚模板": "fashion",
            "生活模板": "lifestyle",
            "美妆模板": "beauty",
            "美食模板": "food",
            "旅行模板": "travel"
        }
        return mapping.get(self.template_combo.currentText(), "lifestyle")
    
    def save_current_cover(self):
        """保存当前封面"""
        if not self.current_results:
            QMessageBox.warning(self, "提示", "请先生成封面")
            return
        
        current_result = self.current_results[0] if len(self.current_results) == 1 else \
                        next((r for r in self.current_results if r == self.current_results[0]), None)
        
        if current_result:
            save_path, _ = QFileDialog.getSaveFileName(
                self, "保存封面", "",
                "PNG图片 (*.png)"
            )
            
            if save_path:
                import shutil
                shutil.copy2(current_result['cover_path'], save_path)
                QMessageBox.information(self, "成功", f"封面已保存到:\n{save_path}")
    
    def use_current_cover(self):
        """使用当前封面"""
        if not self.current_results:
            QMessageBox.warning(self, "提示", "请先生成封面")
            return
        
        current_result = self.current_results[0] if len(self.current_results) == 1 else \
                        next((r for r in self.current_results if r == self.current_results[0]), None)
        
        if current_result:
            self.cover_generated.emit(current_result['cover_path'])
            QMessageBox.information(self, "成功", "封面已应用！")