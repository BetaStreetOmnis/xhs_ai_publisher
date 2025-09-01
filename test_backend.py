#!/usr/bin/env python3
"""
测试后台配置页面按钮功能
"""

import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                             QLabel, QMessageBox, QTabWidget)
from PyQt5.QtCore import Qt

class TestBackendPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("测试后台配置")
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 添加标题
        title = QLabel("测试后台配置页面")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 简单的测试页面
        test_page = QWidget()
        test_layout = QVBoxLayout(test_page)
        
        # 测试按钮
        test_btn = QPushButton("测试保存配置")
        test_btn.clicked.connect(self.test_save)
        test_layout.addWidget(test_btn)
        
        test_btn2 = QPushButton("测试重置配置")
        test_btn2.clicked.connect(self.test_reset)
        test_layout.addWidget(test_btn2)
        
        test_layout.addStretch()
        
        tab_widget.addTab(test_page, "测试")
        layout.addWidget(tab_widget)
        
    def test_save(self):
        print("保存按钮被点击了！")
        QMessageBox.information(self, "测试", "保存按钮正常工作！")
        
    def test_reset(self):
        print("重置按钮被点击了！")
        QMessageBox.information(self, "测试", "重置按钮正常工作！")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestBackendPage()
    window.show()
    sys.exit(app.exec_())