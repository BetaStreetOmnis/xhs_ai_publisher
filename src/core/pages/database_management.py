#!/usr/bin/env python3
"""
数据库管理工具页面
提供数据库健康检查、修复、备份等功能
"""

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QGroupBox, QProgressBar,
                             QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem)

import json
from datetime import datetime


class DatabaseWorker(QThread):
    """数据库操作工作线程"""
    
    progress_updated = pyqtSignal(str)  # 进度更新信号
    operation_completed = pyqtSignal(bool, str)  # 操作完成信号
    
    def __init__(self, operation, *args, **kwargs):
        super().__init__()
        self.operation = operation
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            from ..database_manager import database_manager
            
            if self.operation == "health_check":
                self.progress_updated.emit("🔍 正在检查数据库健康状态...")
                result = database_manager.check_database_health()
                self.operation_completed.emit(True, json.dumps(result, ensure_ascii=False, indent=2))
                
            elif self.operation == "fix_database":
                self.progress_updated.emit("🔧 正在修复数据库...")
                success = database_manager.fix_database()
                self.operation_completed.emit(success, "数据库修复完成" if success else "数据库修复失败")
                
            elif self.operation == "init_database":
                self.progress_updated.emit("🚀 正在初始化数据库...")
                success = database_manager.init_database(force_recreate=self.kwargs.get('force', False))
                self.operation_completed.emit(success, "数据库初始化完成" if success else "数据库初始化失败")
                
            elif self.operation == "get_info":
                self.progress_updated.emit("📊 正在获取数据库信息...")
                info = database_manager.get_database_info()
                self.operation_completed.emit(True, json.dumps(info, ensure_ascii=False, indent=2, default=str))
                
        except Exception as e:
            self.operation_completed.emit(False, f"操作失败：{str(e)}")


class DatabaseManagementPage(QWidget):
    """数据库管理页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.init_ui()
        self.auto_check_timer = QTimer()
        self.auto_check_timer.timeout.connect(self.auto_health_check)
        
        # 启动后自动检查一次
        QTimer.singleShot(1000, self.auto_health_check)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("🛠️ 数据库管理工具")
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 健康检查选项卡
        self.health_tab = self.create_health_tab()
        tab_widget.addTab(self.health_tab, "🏥 健康检查")
        
        # 数据库修复选项卡
        self.repair_tab = self.create_repair_tab()
        tab_widget.addTab(self.repair_tab, "🔧 数据库修复")
        
        # 数据库信息选项卡
        self.info_tab = self.create_info_tab()
        tab_widget.addTab(self.info_tab, "📊 数据库信息")
        
        layout.addWidget(tab_widget)
    
    def create_health_tab(self):
        """创建健康检查选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # 状态显示区域
        status_group = QGroupBox("📋 数据库健康状态")
        status_layout = QVBoxLayout(status_group)
        
        self.health_status_label = QLabel("🔄 正在检查...")
        self.health_status_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        status_layout.addWidget(self.health_status_label)
        
        self.health_details = QTextEdit()
        self.health_details.setMaximumHeight(200)
        self.health_details.setFont(QFont("Consolas", 10))
        status_layout.addWidget(self.health_details)
        
        layout.addWidget(status_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.check_health_btn = QPushButton("🔍 立即检查")
        self.check_health_btn.clicked.connect(self.check_health)
        button_layout.addWidget(self.check_health_btn)
        
        self.auto_check_btn = QPushButton("⏰ 开启自动检查")
        self.auto_check_btn.clicked.connect(self.toggle_auto_check)
        button_layout.addWidget(self.auto_check_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        return tab
    
    def create_repair_tab(self):
        """创建数据库修复选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # 修复操作区域
        repair_group = QGroupBox("🔧 数据库修复操作")
        repair_layout = QVBoxLayout(repair_group)
        
        # 修复说明
        info_label = QLabel("""
<b>修复功能说明：</b><br>
• <b>快速修复</b>：清理损坏数据，修复引用关系<br>
• <b>重建数据库</b>：完全重新创建数据库（会丢失所有数据）<br>
• <b>强制初始化</b>：备份原数据后重新初始化
        """)
        info_label.setStyleSheet("color: #555; background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        repair_layout.addWidget(info_label)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.quick_fix_btn = QPushButton("🚀 快速修复")
        self.quick_fix_btn.clicked.connect(self.quick_fix)
        button_layout.addWidget(self.quick_fix_btn)
        
        self.force_init_btn = QPushButton("🔄 强制初始化")
        self.force_init_btn.clicked.connect(self.force_init)
        button_layout.addWidget(self.force_init_btn)
        
        button_layout.addStretch()
        repair_layout.addLayout(button_layout)
        
        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        repair_layout.addWidget(self.progress_bar)
        
        self.operation_log = QTextEdit()
        self.operation_log.setMaximumHeight(250)
        self.operation_log.setFont(QFont("Consolas", 10))
        repair_layout.addWidget(self.operation_log)
        
        layout.addWidget(repair_group)
        
        return tab
    
    def create_info_tab(self):
        """创建数据库信息选项卡"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # 基本信息
        info_group = QGroupBox("📊 数据库基本信息")
        info_layout = QVBoxLayout(info_group)
        
        self.db_info_display = QTextEdit()
        self.db_info_display.setFont(QFont("Consolas", 10))
        info_layout.addWidget(self.db_info_display)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新信息")
        refresh_btn.clicked.connect(self.refresh_db_info)
        info_layout.addWidget(refresh_btn)
        
        layout.addWidget(info_group)
        
        # 表统计信息
        tables_group = QGroupBox("📋 数据表统计")
        tables_layout = QVBoxLayout(tables_group)
        
        self.tables_table = QTableWidget()
        self.tables_table.setColumnCount(2)
        self.tables_table.setHorizontalHeaderLabels(["表名", "记录数"])
        tables_layout.addWidget(self.tables_table)
        
        layout.addWidget(tables_group)
        
        return tab
    
    def check_health(self):
        """手动健康检查"""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "操作进行中", "请等待当前操作完成")
            return
        
        self.health_status_label.setText("🔄 正在检查健康状态...")
        self.health_details.clear()
        self.check_health_btn.setEnabled(False)
        
        self.worker = DatabaseWorker("health_check")
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.operation_completed.connect(self.health_check_completed)
        self.worker.start()
    
    def health_check_completed(self, success, result):
        """健康检查完成"""
        self.check_health_btn.setEnabled(True)
        
        if success:
            try:
                health_data = json.loads(result)
                
                # 更新状态标签
                if health_data.get('healthy', False):
                    self.health_status_label.setText("💚 数据库状态良好")
                    self.health_status_label.setStyleSheet("color: green;")
                else:
                    self.health_status_label.setText("🟡 数据库存在问题")
                    self.health_status_label.setStyleSheet("color: orange;")
                
                # 更新详细信息
                details = []
                details.append(f"健康状态: {'✅ 良好' if health_data.get('healthy') else '⚠️ 有问题'}")
                
                if health_data.get('issues'):
                    details.append("\n发现的问题:")
                    for issue in health_data['issues']:
                        details.append(f"  • {issue}")
                
                if health_data.get('recommendations'):
                    details.append("\n建议操作:")
                    for rec in health_data['recommendations']:
                        details.append(f"  • {rec}")
                
                if health_data.get('stats'):
                    details.append("\n数据统计:")
                    for table, count in health_data['stats'].items():
                        details.append(f"  • {table}: {count} 条记录")
                
                self.health_details.setText('\n'.join(details))
                
            except Exception as e:
                self.health_details.setText(f"解析健康检查结果失败: {e}")
        else:
            self.health_status_label.setText("❌ 健康检查失败")
            self.health_status_label.setStyleSheet("color: red;")
            self.health_details.setText(result)
    
    def auto_health_check(self):
        """自动健康检查（静默）"""
        if self.worker and self.worker.isRunning():
            return
        
        self.worker = DatabaseWorker("health_check")
        self.worker.operation_completed.connect(self.auto_health_check_completed)
        self.worker.start()
    
    def auto_health_check_completed(self, success, result):
        """自动健康检查完成（静默处理）"""
        if success:
            try:
                health_data = json.loads(result)
                if health_data.get('healthy', False):
                    self.health_status_label.setText("💚 数据库状态良好")
                    self.health_status_label.setStyleSheet("color: green;")
                else:
                    self.health_status_label.setText("🟡 发现问题，建议检查")
                    self.health_status_label.setStyleSheet("color: orange;")
            except:
                pass
    
    def toggle_auto_check(self):
        """切换自动检查"""
        if self.auto_check_timer.isActive():
            self.auto_check_timer.stop()
            self.auto_check_btn.setText("⏰ 开启自动检查")
        else:
            self.auto_check_timer.start(30000)  # 30秒检查一次
            self.auto_check_btn.setText("⏸️ 停止自动检查")
    
    def quick_fix(self):
        """快速修复"""
        reply = QMessageBox.question(
            self, "确认修复", 
            "确定要执行快速修复吗？\n\n这将：\n• 清理损坏的数据\n• 修复数据关系\n• 备份原数据",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.start_operation("fix_database", "🔧 正在执行快速修复...")
    
    def force_init(self):
        """强制初始化"""
        reply = QMessageBox.question(
            self, "确认重新初始化", 
            "⚠️ 警告：强制初始化将会：\n\n• 备份当前数据库\n• 完全重建数据库结构\n• 创建默认数据\n\n确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.start_operation("init_database", "🚀 正在强制初始化数据库...", force=True)
    
    def start_operation(self, operation, message, **kwargs):
        """开始数据库操作"""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "操作进行中", "请等待当前操作完成")
            return
        
        self.operation_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        
        # 禁用按钮
        self.quick_fix_btn.setEnabled(False)
        self.force_init_btn.setEnabled(False)
        
        self.worker = DatabaseWorker(operation, **kwargs)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.operation_completed.connect(self.operation_completed)
        self.worker.start()
    
    def operation_completed(self, success, result):
        """操作完成"""
        self.progress_bar.setVisible(False)
        
        # 重新启用按钮
        self.quick_fix_btn.setEnabled(True)
        self.force_init_btn.setEnabled(True)
        
        # 记录结果
        status = "✅ 成功" if success else "❌ 失败"
        self.operation_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {status}: {result}")
        
        # 显示结果
        if success:
            QMessageBox.information(self, "操作完成", result)
            # 重新检查健康状态
            QTimer.singleShot(1000, self.auto_health_check)
        else:
            QMessageBox.warning(self, "操作失败", result)
    
    def update_progress(self, message):
        """更新进度"""
        self.operation_log.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
        
        # 自动滚动到底部
        cursor = self.operation_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.operation_log.setTextCursor(cursor)
    
    def refresh_db_info(self):
        """刷新数据库信息"""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "操作进行中", "请等待当前操作完成")
            return
        
        self.worker = DatabaseWorker("get_info")
        self.worker.operation_completed.connect(self.db_info_completed)
        self.worker.start()
    
    def db_info_completed(self, success, result):
        """数据库信息获取完成"""
        if success:
            try:
                info_data = json.loads(result)
                
                # 更新基本信息
                info_text = []
                info_text.append(f"数据库路径: {info_data.get('db_path', 'N/A')}")
                info_text.append(f"备份目录: {info_data.get('backup_dir', 'N/A')}")
                info_text.append(f"文件存在: {'是' if info_data.get('exists') else '否'}")
                info_text.append(f"文件大小: {info_data.get('size', 0)} 字节")
                
                self.db_info_display.setText('\n'.join(info_text))
                
                # 更新表统计
                tables = info_data.get('tables', [])
                health = info_data.get('health', {})
                stats = health.get('stats', {})
                
                self.tables_table.setRowCount(len(tables))
                for row, table in enumerate(tables):
                    self.tables_table.setItem(row, 0, QTableWidgetItem(table))
                    count = stats.get(table, 0)
                    self.tables_table.setItem(row, 1, QTableWidgetItem(str(count)))
                
                self.tables_table.resizeColumnsToContents()
                
            except Exception as e:
                self.db_info_display.setText(f"解析数据库信息失败: {e}")
        else:
            self.db_info_display.setText(f"获取数据库信息失败: {result}")
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.auto_check_timer.isActive():
            self.auto_check_timer.stop()
        
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        
        event.accept()