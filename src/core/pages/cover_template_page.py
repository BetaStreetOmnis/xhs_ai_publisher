import sys
import os
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QScrollArea, QFrame, QGridLayout, QComboBox, QLineEdit,
    QTextEdit, QMessageBox, QFileDialog, QProgressBar
)

from src.core.services.cover_template_service import cover_template_service


class CoverGeneratorThread(QThread):
    """封面生成线程"""
    finished = pyqtSignal(str)  # 生成完成，返回文件路径
    error = pyqtSignal(str)
    
    def __init__(self, template_id, title, subtitle="", background_image=None):
        super().__init__()
        self.template_id = template_id
        self.title = title
        self.subtitle = subtitle
        self.background_image = background_image
    
    def run(self):
        try:
            cover_path = cover_template_service.generate_cover(
                self.template_id, self.title, self.subtitle, self.background_image
            )
            if cover_path:
                self.finished.emit(cover_path)
            else:
                self.error.emit("生成封面失败")
        except Exception as e:
            self.error.emit(f"生成封面出错: {str(e)}")


class TemplateCard(QFrame):
    """模板卡片组件"""
    
    template_selected = pyqtSignal(int)  # 模板被选择
    
    def __init__(self, template_data):
        super().__init__()
        self.template_data = template_data
        self.template_id = template_data['id']
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setFixedSize(160, 200)
        self.setStyleSheet("""
            TemplateCard {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
            }
            TemplateCard:hover {
                border-color: #4a90e2;
                background-color: #f8fbff;
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        
        # 缩略图
        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(140, 140)
        thumbnail_label.setAlignment(Qt.AlignCenter)
        thumbnail_label.setStyleSheet("border: 1px solid #ddd; border-radius: 4px;")
        
        # 加载缩略图
        thumbnail_path = self.template_data.get('thumbnail_path')
        if thumbnail_path and os.path.exists(thumbnail_path):
            pixmap = QPixmap(thumbnail_path)
            scaled_pixmap = pixmap.scaled(140, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            thumbnail_label.setPixmap(scaled_pixmap)
        else:
            thumbnail_label.setText("预览图")
            thumbnail_label.setStyleSheet("""
                border: 1px solid #ddd; 
                border-radius: 4px;
                background-color: #f5f5f5;
                color: #999;
            """)
        
        layout.addWidget(thumbnail_label)
        
        # 模板名称
        name_label = QLabel(self.template_data['name'])
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont("Arial", 10, QFont.Bold))
        name_label.setStyleSheet("color: #333; font-weight: bold;")
        layout.addWidget(name_label)
        
        # 分类标签
        category_label = QLabel(self.template_data['category'])
        category_label.setAlignment(Qt.AlignCenter)
        category_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(category_label)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.template_selected.emit(self.template_id)
            # 视觉反馈
            self.setStyleSheet("""
                TemplateCard {
                    background-color: #e3f2fd;
                    border: 2px solid #4a90e2;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)


class CoverTemplatePage(QWidget):
    """封面模板库页面"""
    
    template_applied = pyqtSignal(str)  # 模板应用完成，发送封面路径
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.selected_template_id = None
        self.background_image_path = None
        self.setup_ui()
        self.load_templates()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("🎨 封面模板库")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 工具栏
        self.create_toolbar(layout)
        
        # 模板网格区域
        self.create_template_grid(layout)
        
        # 预览和控制区域
        self.create_preview_section(layout)
    
    def create_toolbar(self, parent_layout):
        """创建工具栏"""
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        
        # 分类筛选
        toolbar_layout.addWidget(QLabel("分类:"))
        self.category_combo = QComboBox()
        self.category_combo.setFixedWidth(120)
        self.category_combo.currentTextChanged.connect(self.filter_templates)
        toolbar_layout.addWidget(self.category_combo)
        
        toolbar_layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_templates)
        toolbar_layout.addWidget(refresh_btn)
        
        parent_layout.addWidget(toolbar_frame)
    
    def create_template_grid(self, parent_layout):
        """创建模板网格"""
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #f8f9fa; }")
        
        # 网格容器
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(15, 15, 15, 15)
        
        scroll_area.setWidget(self.grid_widget)
        parent_layout.addWidget(scroll_area, 1)  # 占用剩余空间
    
    def create_preview_section(self, parent_layout):
        """创建预览区域"""
        preview_frame = QFrame()
        preview_frame.setFixedHeight(200)
        preview_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        preview_layout = QHBoxLayout(preview_frame)
        
        # 左侧控制区
        controls_layout = QVBoxLayout()
        
        # 标题输入
        controls_layout.addWidget(QLabel("📝 封面标题:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("输入封面标题...")
        controls_layout.addWidget(self.title_input)
        
        # 副标题输入
        controls_layout.addWidget(QLabel("📄 副标题:"))
        self.subtitle_input = QLineEdit()
        self.subtitle_input.setPlaceholderText("输入副标题（可选）...")
        controls_layout.addWidget(self.subtitle_input)
        
        # 背景图片选择
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel("🖼️ 背景图:"))
        self.bg_image_label = QLabel("未选择")
        self.bg_image_label.setStyleSheet("color: #666; font-size: 10pt;")
        bg_layout.addWidget(self.bg_image_label)
        
        select_bg_btn = QPushButton("选择")
        select_bg_btn.setFixedWidth(60)
        select_bg_btn.clicked.connect(self.select_background_image)
        bg_layout.addWidget(select_bg_btn)
        
        clear_bg_btn = QPushButton("清除")
        clear_bg_btn.setFixedWidth(60)
        clear_bg_btn.clicked.connect(self.clear_background_image)
        bg_layout.addWidget(clear_bg_btn)
        
        controls_layout.addLayout(bg_layout)
        
        controls_layout.addStretch()
        
        preview_layout.addLayout(controls_layout, 2)
        
        # 右侧预览区
        preview_right_layout = QVBoxLayout()
        
        # 预览图
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(150, 150)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            border: 2px dashed #ccc;
            border-radius: 8px;
            background-color: #f8f9fa;
            color: #999;
        """)
        self.preview_label.setText("封面预览")
        preview_right_layout.addWidget(self.preview_label)
        
        # 生成按钮
        self.generate_btn = QPushButton("🎨 生成封面")
        self.generate_btn.setFixedHeight(40)
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self.generate_cover)
        preview_right_layout.addWidget(self.generate_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        preview_right_layout.addWidget(self.progress_bar)
        
        preview_layout.addLayout(preview_right_layout, 1)
        
        parent_layout.addWidget(preview_frame)
    
    def load_templates(self):
        """加载模板"""
        try:
            # 清空现有模板
            self.clear_grid()
            
            # 获取分类列表
            categories = ['全部'] + cover_template_service.get_categories()
            self.category_combo.clear()
            self.category_combo.addItems(categories)
            
            # 获取模板列表
            templates = cover_template_service.get_templates()
            
            # 显示模板
            self.display_templates(templates)
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载模板失败: {str(e)}")
    
    def clear_grid(self):
        """清空网格"""
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def display_templates(self, templates):
        """显示模板列表"""
        row = 0
        col = 0
        cols_per_row = 5  # 每行5个模板
        
        for template in templates:
            template_card = TemplateCard(template)
            template_card.template_selected.connect(self.on_template_selected)
            
            self.grid_layout.addWidget(template_card, row, col)
            
            col += 1
            if col >= cols_per_row:
                col = 0
                row += 1
        
        # 添加空白占位，确保网格对齐
        for i in range(cols_per_row - col):
            if col + i < cols_per_row:
                spacer = QWidget()
                spacer.setFixedSize(160, 200)
                self.grid_layout.addWidget(spacer, row, col + i)
    
    def filter_templates(self, category):
        """根据分类筛选模板"""
        try:
            self.clear_grid()
            
            if category == "全部":
                templates = cover_template_service.get_templates()
            else:
                templates = cover_template_service.get_templates(category)
            
            self.display_templates(templates)
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"筛选模板失败: {str(e)}")
    
    def on_template_selected(self, template_id):
        """模板被选择"""
        self.selected_template_id = template_id
        self.generate_btn.setEnabled(True)
        
        # 重置其他模板卡片的样式
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, TemplateCard) and widget.template_id != template_id:
                widget.setStyleSheet("""
                    TemplateCard {
                        background-color: white;
                        border: 2px solid #e0e0e0;
                        border-radius: 8px;
                        padding: 8px;
                    }
                    TemplateCard:hover {
                        border-color: #4a90e2;
                        background-color: #f8fbff;
                    }
                """)
    
    def select_background_image(self):
        """选择背景图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "", 
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            self.background_image_path = file_path
            filename = os.path.basename(file_path)
            self.bg_image_label.setText(filename[:20] + "..." if len(filename) > 20 else filename)
            self.bg_image_label.setStyleSheet("color: #4a90e2; font-size: 10pt;")
    
    def clear_background_image(self):
        """清除背景图片"""
        self.background_image_path = None
        self.bg_image_label.setText("未选择")
        self.bg_image_label.setStyleSheet("color: #666; font-size: 10pt;")
    
    def generate_cover(self):
        """生成封面"""
        if not self.selected_template_id:
            QMessageBox.warning(self, "提示", "请先选择一个模板")
            return
        
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "提示", "请输入封面标题")
            return
        
        subtitle = self.subtitle_input.text().strip()
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        self.generate_btn.setEnabled(False)
        
        # 启动生成线程
        self.generator_thread = CoverGeneratorThread(
            self.selected_template_id, title, subtitle, self.background_image_path
        )
        self.generator_thread.finished.connect(self.on_cover_generated)
        self.generator_thread.error.connect(self.on_cover_error)
        self.generator_thread.start()
    
    def on_cover_generated(self, cover_path):
        """封面生成完成"""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        
        # 显示预览
        if os.path.exists(cover_path):
            pixmap = QPixmap(cover_path)
            scaled_pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
            self.preview_label.setStyleSheet("border: 1px solid #4a90e2; border-radius: 8px;")
            
            # 发出信号，通知主程序封面已生成
            self.template_applied.emit(cover_path)
            
            QMessageBox.information(self, "成功", f"封面生成成功！\n保存路径: {cover_path}")
        else:
            QMessageBox.warning(self, "错误", "封面文件未找到")
    
    def on_cover_error(self, error_msg):
        """封面生成失败"""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        QMessageBox.critical(self, "错误", f"生成封面失败: {error_msg}")
    
    def set_title_text(self, title):
        """设置标题文本（外部调用）"""
        self.title_input.setText(title)