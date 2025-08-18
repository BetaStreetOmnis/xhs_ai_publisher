#!/usr/bin/env python3
"""
用户管理页面
"""

import json
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QDialog, QTextEdit, QMessageBox, QTabWidget)

# 导入真实的服务类
try:
    from ..services.user_service import UserService
    from ..services.proxy_service import ProxyService
    from ..services.fingerprint_service import FingerprintService
    
    print("✅ 成功导入真实服务模块")
    USE_REAL_SERVICES = True
    
except ImportError as e:
    print(f"⚠️ 无法导入服务模块: {e}")
    print("💡 使用Mock服务作为备用方案")
    USE_REAL_SERVICES = False
    
    # Mock服务类
    class MockService:
        def __init__(self):
            self.data = []
        
        def get_all(self):
            return [{'id': item.get('id'), **item} for item in self.data if isinstance(item, dict)]
        
        def create(self, **kwargs):
            item = kwargs.copy()
            item['id'] = len(self.data) + 1
            self.data.append(item)
            return item
        
        def update(self, item_id, **kwargs):
            for item in self.data:
                if isinstance(item, dict) and item.get('id') == item_id:
                    item.update(kwargs)
                    return item
            return None
        
        def delete(self, item_id):
            self.data = [item for item in self.data if not (isinstance(item, dict) and item.get('id') == item_id)]
            return True

    class UserService(MockService):
        def get_all(self):
            return [{'id': item.get('id'), 'username': item.get('username', ''), 
                    'phone': item.get('phone', ''), 'display_name': item.get('display_name', '')} 
                   for item in self.data if isinstance(item, dict)]

    class ProxyService(MockService):
        pass

    class FingerprintService(MockService):
        pass


class UserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户信息")
        self.setModal(True)
        self.setFixedSize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_label = QLabel("👤 用户信息")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        info_label = QLabel("请在下方输入JSON格式的用户信息：")
        info_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(info_label)
        
        self.json_edit = QTextEdit()
        self.json_edit.setPlaceholderText('{"username": "用户名", "phone": "手机号", "display_name": "显示名称"}')
        self.json_edit.setFont(QFont("Consolas", 11))
        layout.addWidget(self.json_edit)
        
        button_layout = QHBoxLayout()
        example_btn = QPushButton("📋 插入示例")
        example_btn.clicked.connect(self.insert_example)
        button_layout.addWidget(example_btn)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)

    def insert_example(self):
        example_json = '{"username": "test_user_001", "phone": "13900139000", "display_name": "测试用户001"}'
        self.json_edit.setPlainText(example_json)

    def get_user_data(self):
        try:
            json_text = self.json_edit.toPlainText().strip()
            if not json_text:
                return {}
            data = json.loads(json_text)
            return {
                'username': data.get('username', '').strip(),
                'phone': data.get('phone', '').strip(),
                'display_name': data.get('display_name', '').strip() or None
            }
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON格式错误", f"JSON格式不正确：{str(e)}")
            return {}
        except Exception as e:
            QMessageBox.warning(self, "解析错误", f"解析数据时出错：{str(e)}")
            return {}


class ProxyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("代理配置")
        self.setModal(True)
        self.setFixedSize(550, 450)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_label = QLabel("🌐 代理服务器配置")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        info_label = QLabel("请在下方输入JSON格式的代理配置：")
        info_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(info_label)
        
        self.json_edit = QTextEdit()
        self.json_edit.setPlaceholderText('{"name": "配置名称", "proxy_type": "http", "host": "127.0.0.1", "port": 1080}')
        self.json_edit.setFont(QFont("Consolas", 11))
        layout.addWidget(self.json_edit)
        
        button_layout = QHBoxLayout()
        example_btn = QPushButton("📋 插入示例")
        example_btn.clicked.connect(self.insert_example)
        button_layout.addWidget(example_btn)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)

    def insert_example(self):
        example_json = '{"name": "家庭代理", "proxy_type": "http", "host": "127.0.0.1", "port": 1080, "username": "", "password": ""}'
        self.json_edit.setPlainText(example_json)

    def get_proxy_data(self):
        try:
            json_text = self.json_edit.toPlainText().strip()
            if not json_text:
                return {}
            data = json.loads(json_text)
            return {
                'name': data.get('name', '').strip(),
                'proxy_type': data.get('proxy_type', 'http').lower(),
                'host': data.get('host', '').strip(),
                'port': data.get('port', 1080),
                'username': data.get('username', '').strip() or None,
                'password': data.get('password', '').strip() or None,
            }
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON格式错误", f"JSON格式不正确：{str(e)}")
            return {}
        except Exception as e:
            QMessageBox.warning(self, "解析错误", f"解析数据时出错：{str(e)}")
            return {}


class FingerprintDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("浏览器指纹配置")
        self.setModal(True)
        self.setFixedSize(600, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_label = QLabel("🔍 浏览器指纹配置")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        info_label = QLabel("请在下方输入JSON格式的浏览器指纹配置：")
        info_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(info_label)
        
        self.json_edit = QTextEdit()
        self.json_edit.setPlaceholderText('{"name": "配置名称", "user_agent": "User-Agent字符串", "viewport_width": 1920, "viewport_height": 1080}')
        self.json_edit.setFont(QFont("Consolas", 11))
        layout.addWidget(self.json_edit)
        
        button_layout = QHBoxLayout()
        example_btn = QPushButton("📋 插入示例")
        example_btn.clicked.connect(self.insert_example)
        button_layout.addWidget(example_btn)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)

    def insert_example(self):
        example_json = '{"name": "Windows Chrome 默认", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "viewport_width": 1920, "viewport_height": 1080, "platform": "Win32", "timezone": "Asia/Shanghai"}'
        self.json_edit.setPlainText(example_json)

    def get_fingerprint_data(self):
        try:
            json_text = self.json_edit.toPlainText().strip()
            if not json_text:
                return {}
            data = json.loads(json_text)
            return {
                'name': data.get('name', '').strip(),
                'user_agent': data.get('user_agent', '').strip() or None,
                'viewport_width': data.get('viewport_width', 1920),
                'viewport_height': data.get('viewport_height', 1080),
                'platform': data.get('platform', 'Win32'),
                'timezone': data.get('timezone', 'Asia/Shanghai'),
                'locale': 'zh-CN'
            }
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON格式错误", f"JSON格式不正确：{str(e)}")
            return {}
        except Exception as e:
            QMessageBox.warning(self, "解析错误", f"解析数据时出错：{str(e)}")
            return {}


class UserManagementPage(QWidget):
    user_switched = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化服务
        self.user_service = UserService()
        self.proxy_service = ProxyService()
        self.fingerprint_service = FingerprintService()
        
        # 显示服务状态
        if USE_REAL_SERVICES:
            print("💚 用户管理页面使用真实数据库服务")
        else:
            print("🟡 用户管理页面使用Mock服务（数据将不会持久化）")
        
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 添加服务状态指示器
        status_layout = QHBoxLayout()
        
        if USE_REAL_SERVICES:
            status_label = QLabel("💚 数据库服务已连接")
            status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            status_label = QLabel("🟡 使用临时数据（重启后丢失）")
            status_label.setStyleSheet("color: orange; font-weight: bold;")
        
        status_layout.addWidget(status_label)
        status_layout.addStretch()
        
        # 添加刷新按钮
        refresh_btn = QPushButton("🔄 刷新数据")
        refresh_btn.clicked.connect(self.load_data)
        status_layout.addWidget(refresh_btn)
        
        layout.addLayout(status_layout)
        
        title = QLabel("👥 用户管理中心")
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Microsoft YaHei", 10))
        
        # 用户管理选项卡
        self.users_tab = QWidget()
        self.init_users_tab()
        self.tab_widget.addTab(self.users_tab, "👤 用户管理")
        
        # 代理管理选项卡
        self.proxies_tab = QWidget()
        self.init_proxies_tab()
        self.tab_widget.addTab(self.proxies_tab, "🌐 代理管理")
        
        # 指纹管理选项卡
        self.fingerprints_tab = QWidget()
        self.init_fingerprints_tab()
        self.tab_widget.addTab(self.fingerprints_tab, "🔍 指纹管理")
        
        layout.addWidget(self.tab_widget)

    def init_users_tab(self):
        layout = QVBoxLayout(self.users_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels(["ID", "用户名", "手机号", "显示名称", "操作"])
        layout.addWidget(self.users_table)
        
        button_layout = QHBoxLayout()
        add_user_btn = QPushButton("➕ 添加用户")
        add_user_btn.clicked.connect(self.add_user)
        button_layout.addWidget(add_user_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def init_proxies_tab(self):
        layout = QVBoxLayout(self.proxies_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.proxies_table = QTableWidget()
        self.proxies_table.setColumnCount(7)
        self.proxies_table.setHorizontalHeaderLabels(["ID", "名称", "类型", "主机", "端口", "用户名", "操作"])
        layout.addWidget(self.proxies_table)
        
        button_layout = QHBoxLayout()
        add_proxy_btn = QPushButton("➕ 添加代理")
        add_proxy_btn.clicked.connect(self.add_proxy)
        button_layout.addWidget(add_proxy_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def init_fingerprints_tab(self):
        layout = QVBoxLayout(self.fingerprints_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.fingerprints_table = QTableWidget()
        self.fingerprints_table.setColumnCount(7)
        self.fingerprints_table.setHorizontalHeaderLabels(["ID", "名称", "User-Agent", "分辨率", "平台", "时区", "操作"])
        layout.addWidget(self.fingerprints_table)
        
        button_layout = QHBoxLayout()
        add_fingerprint_btn = QPushButton("➕ 添加指纹")
        add_fingerprint_btn.clicked.connect(self.add_fingerprint)
        button_layout.addWidget(add_fingerprint_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def load_data(self):
        """加载所有数据"""
        try:
            print("🔄 正在刷新用户管理数据...")
            self.load_users()
            self.load_proxies()
            self.load_fingerprints()
            print("✅ 数据刷新完成")
        except Exception as e:
            print(f"❌ 刷新数据失败: {e}")
            QMessageBox.warning(self, "刷新失败", f"刷新数据时出错：{str(e)}")

    def load_users(self):
        try:
            if USE_REAL_SERVICES:
                # 使用真实服务获取数据
                users = self.user_service.get_all_users()
                # 转换为字典格式以兼容原有代码
                users_data = []
                for user in users:
                    users_data.append({
                        'id': user.id,
                        'username': user.username,
                        'phone': user.phone,
                        'display_name': user.display_name
                    })
            else:
                # 使用Mock服务
                users_data = self.user_service.get_all()
            
            self.users_table.setRowCount(len(users_data))
            for row, user in enumerate(users_data):
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user.get('id', ''))))
                self.users_table.setItem(row, 1, QTableWidgetItem(user.get('username', '')))
                self.users_table.setItem(row, 2, QTableWidgetItem(user.get('phone', '')))
                self.users_table.setItem(row, 3, QTableWidgetItem(user.get('display_name', '') or ''))
                
                button_layout = QHBoxLayout()
                edit_btn = QPushButton("编辑")
                edit_btn.clicked.connect(lambda checked, u=user: self.edit_user(u))
                button_layout.addWidget(edit_btn)
                
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, u=user: self.delete_user(u))
                button_layout.addWidget(delete_btn)
                
                button_widget = QWidget()
                button_widget.setLayout(button_layout)
                self.users_table.setCellWidget(row, 4, button_widget)
                
        except Exception as e:
            print(f"❌ 加载用户数据失败: {e}")
            QMessageBox.warning(self, "加载失败", f"加载用户数据时出错：{str(e)}")

    def load_proxies(self):
        try:
            proxies = self.proxy_service.get_all()
            self.proxies_table.setRowCount(len(proxies))
            for row, proxy in enumerate(proxies):
                self.proxies_table.setItem(row, 0, QTableWidgetItem(str(proxy.get('id', ''))))
                self.proxies_table.setItem(row, 1, QTableWidgetItem(proxy.get('name', '')))
                self.proxies_table.setItem(row, 2, QTableWidgetItem(proxy.get('proxy_type', '')))
                self.proxies_table.setItem(row, 3, QTableWidgetItem(proxy.get('host', '')))
                self.proxies_table.setItem(row, 4, QTableWidgetItem(str(proxy.get('port', ''))))
                self.proxies_table.setItem(row, 5, QTableWidgetItem(proxy.get('username', '') or ''))
                
                button_layout = QHBoxLayout()
                edit_btn = QPushButton("编辑")
                edit_btn.clicked.connect(lambda checked, p=proxy: self.edit_proxy(p))
                button_layout.addWidget(edit_btn)
                
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, p=proxy: self.delete_proxy(p))
                button_layout.addWidget(delete_btn)
                
                button_widget = QWidget()
                button_widget.setLayout(button_layout)
                self.proxies_table.setCellWidget(row, 6, button_widget)
        except Exception as e:
            print(f"❌ 加载代理数据失败: {e}")

    def load_fingerprints(self):
        try:
            fingerprints = self.fingerprint_service.get_all()
            self.fingerprints_table.setRowCount(len(fingerprints))
            for row, fingerprint in enumerate(fingerprints):
                self.fingerprints_table.setItem(row, 0, QTableWidgetItem(str(fingerprint.get('id', ''))))
                self.fingerprints_table.setItem(row, 1, QTableWidgetItem(fingerprint.get('name', '')))
                self.fingerprints_table.setItem(row, 2, QTableWidgetItem(fingerprint.get('user_agent', '') or ''))
                self.fingerprints_table.setItem(row, 3, QTableWidgetItem(f"{fingerprint.get('viewport_width', '')}x{fingerprint.get('viewport_height', '')}"))
                self.fingerprints_table.setItem(row, 4, QTableWidgetItem(fingerprint.get('platform', '')))
                self.fingerprints_table.setItem(row, 5, QTableWidgetItem(fingerprint.get('timezone', '')))
                
                button_layout = QHBoxLayout()
                edit_btn = QPushButton("编辑")
                edit_btn.clicked.connect(lambda checked, f=fingerprint: self.edit_fingerprint(f))
                button_layout.addWidget(edit_btn)
                
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, f=fingerprint: self.delete_fingerprint(f))
                button_layout.addWidget(delete_btn)
                
                button_widget = QWidget()
                button_widget.setLayout(button_layout)
                self.fingerprints_table.setCellWidget(row, 6, button_widget)
        except Exception as e:
            print(f"❌ 加载指纹数据失败: {e}")

    def add_user(self):
        dialog = UserDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            user_data = dialog.get_user_data()
            if user_data:
                try:
                    if USE_REAL_SERVICES:
                        # 使用真实服务创建用户
                        user = self.user_service.create_user(**user_data)
                        print(f"✅ 成功创建用户: {user.username}")
                    else:
                        # 使用Mock服务
                        user = self.user_service.create(**user_data)
                        print(f"✅ 成功创建Mock用户: {user.get('username')}")
                    
                    self.load_users()
                    QMessageBox.information(self, "成功", "用户添加成功！")
                except Exception as e:
                    print(f"❌ 添加用户失败: {e}")
                    QMessageBox.warning(self, "错误", f"添加用户失败：{str(e)}")

    def edit_user(self, user):
        dialog = UserDialog(self)
        user_json = {
            "username": user.get('username', ''),
            "phone": user.get('phone', ''),
            "display_name": user.get('display_name', '') or ''
        }
        dialog.json_edit.setPlainText(json.dumps(user_json, ensure_ascii=False, indent=2))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            user_data = dialog.get_user_data()
            if user_data:
                try:
                    if USE_REAL_SERVICES:
                        # 使用真实服务更新用户
                        updated_user = self.user_service.update_user(user['id'], **user_data)
                        print(f"✅ 成功更新用户: {updated_user.username}")
                    else:
                        # 使用Mock服务
                        self.user_service.update(user['id'], **user_data)
                        print(f"✅ 成功更新Mock用户: {user_data.get('username')}")
                    
                    self.load_users()
                    QMessageBox.information(self, "成功", "用户更新成功！")
                except Exception as e:
                    print(f"❌ 更新用户失败: {e}")
                    QMessageBox.warning(self, "错误", f"更新用户失败：{str(e)}")

    def delete_user(self, user):
        reply = QMessageBox.question(self, "确认删除", 
                                   f"确定要删除用户 '{user.get('username', '')}' 吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                if USE_REAL_SERVICES:
                    # 使用真实服务删除用户
                    self.user_service.delete_user(user['id'])
                    print(f"✅ 成功删除用户: {user.get('username')}")
                else:
                    # 使用Mock服务
                    self.user_service.delete(user['id'])
                    print(f"✅ 成功删除Mock用户: {user.get('username')}")
                
                self.load_users()
                QMessageBox.information(self, "成功", "用户删除成功！")
            except Exception as e:
                print(f"❌ 删除用户失败: {e}")
                QMessageBox.warning(self, "错误", f"删除用户失败：{str(e)}")

    def add_proxy(self):
        dialog = ProxyDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            proxy_data = dialog.get_proxy_data()
            if proxy_data:
                try:
                    proxy = self.proxy_service.create(**proxy_data)
                    self.load_proxies()
                    QMessageBox.information(self, "成功", "代理添加成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"添加代理失败：{str(e)}")

    def edit_proxy(self, proxy):
        dialog = ProxyDialog(self)
        proxy_json = {
            "name": proxy.get('name', ''),
            "proxy_type": proxy.get('proxy_type', ''),
            "host": proxy.get('host', ''),
            "port": proxy.get('port', ''),
            "username": proxy.get('username', '') or '',
            "password": proxy.get('password', '') or ''
        }
        dialog.json_edit.setPlainText(json.dumps(proxy_json, ensure_ascii=False, indent=2))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            proxy_data = dialog.get_proxy_data()
            if proxy_data:
                try:
                    self.proxy_service.update(proxy['id'], **proxy_data)
                    self.load_proxies()
                    QMessageBox.information(self, "成功", "代理更新成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"更新代理失败：{str(e)}")

    def delete_proxy(self, proxy):
        reply = QMessageBox.question(self, "确认删除", 
                                   f"确定要删除代理 '{proxy.get('name', '')}' 吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.proxy_service.delete(proxy['id'])
                self.load_proxies()
                QMessageBox.information(self, "成功", "代理删除成功！")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除代理失败：{str(e)}")

    def add_fingerprint(self):
        dialog = FingerprintDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            fingerprint_data = dialog.get_fingerprint_data()
            if fingerprint_data:
                try:
                    fingerprint = self.fingerprint_service.create(**fingerprint_data)
                    self.load_fingerprints()
                    QMessageBox.information(self, "成功", "指纹添加成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"添加指纹失败：{str(e)}")

    def edit_fingerprint(self, fingerprint):
        dialog = FingerprintDialog(self)
        fingerprint_json = {
            "name": fingerprint.get('name', ''),
            "user_agent": fingerprint.get('user_agent', '') or '',
            "viewport_width": fingerprint.get('viewport_width', ''),
            "viewport_height": fingerprint.get('viewport_height', ''),
            "platform": fingerprint.get('platform', ''),
            "timezone": fingerprint.get('timezone', '')
        }
        dialog.json_edit.setPlainText(json.dumps(fingerprint_json, ensure_ascii=False, indent=2))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            fingerprint_data = dialog.get_fingerprint_data()
            if fingerprint_data:
                try:
                    self.fingerprint_service.update(fingerprint['id'], **fingerprint_data)
                    self.load_fingerprints()
                    QMessageBox.information(self, "成功", "指纹更新成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"更新指纹失败：{str(e)}")

    def delete_fingerprint(self, fingerprint):
        reply = QMessageBox.question(self, "确认删除", 
                                   f"确定要删除指纹 '{fingerprint.get('name', '')}' 吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.fingerprint_service.delete(fingerprint['id'])
                self.load_fingerprints()
                QMessageBox.information(self, "成功", "指纹删除成功！")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除指纹失败：{str(e)}")

class UserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户信息")
        self.setModal(True)
        self.setFixedSize(500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_label = QLabel("👤 用户信息")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        info_label = QLabel("请在下方输入JSON格式的用户信息：")
        info_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(info_label)
        
        self.json_edit = QTextEdit()
        self.json_edit.setPlaceholderText('{"username": "用户名", "phone": "手机号", "display_name": "显示名称"}')
        self.json_edit.setFont(QFont("Consolas", 11))
        layout.addWidget(self.json_edit)
        
        button_layout = QHBoxLayout()
        example_btn = QPushButton("📋 插入示例")
        example_btn.clicked.connect(self.insert_example)
        button_layout.addWidget(example_btn)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)

    def insert_example(self):
        example_json = '{"username": "test_user_001", "phone": "13900139000", "display_name": "测试用户001"}'
        self.json_edit.setPlainText(example_json)

    def get_user_data(self):
        try:
            json_text = self.json_edit.toPlainText().strip()
            if not json_text:
                return {}
            data = json.loads(json_text)
            return {
                'username': data.get('username', '').strip(),
                'phone': data.get('phone', '').strip(),
                'display_name': data.get('display_name', '').strip() or None
            }
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON格式错误", f"JSON格式不正确：{str(e)}")
            return {}
        except Exception as e:
            QMessageBox.warning(self, "解析错误", f"解析数据时出错：{str(e)}")
            return {}

class ProxyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("代理配置")
        self.setModal(True)
        self.setFixedSize(550, 450)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_label = QLabel("🌐 代理服务器配置")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        info_label = QLabel("请在下方输入JSON格式的代理配置：")
        info_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(info_label)
        
        self.json_edit = QTextEdit()
        self.json_edit.setPlaceholderText('{"name": "配置名称", "proxy_type": "http", "host": "127.0.0.1", "port": 1080}')
        self.json_edit.setFont(QFont("Consolas", 11))
        layout.addWidget(self.json_edit)
        
        button_layout = QHBoxLayout()
        example_btn = QPushButton("📋 插入示例")
        example_btn.clicked.connect(self.insert_example)
        button_layout.addWidget(example_btn)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)

    def insert_example(self):
        example_json = '{"name": "家庭代理", "proxy_type": "http", "host": "127.0.0.1", "port": 1080, "username": "", "password": ""}'
        self.json_edit.setPlainText(example_json)

    def get_proxy_data(self):
        try:
            json_text = self.json_edit.toPlainText().strip()
            if not json_text:
                return {}
            data = json.loads(json_text)
            return {
                'name': data.get('name', '').strip(),
                'proxy_type': data.get('proxy_type', 'http').lower(),
                'host': data.get('host', '').strip(),
                'port': data.get('port', 1080),
                'username': data.get('username', '').strip() or None,
                'password': data.get('password', '').strip() or None,
            }
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON格式错误", f"JSON格式不正确：{str(e)}")
            return {}
        except Exception as e:
            QMessageBox.warning(self, "解析错误", f"解析数据时出错：{str(e)}")
            return {}

class FingerprintDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("浏览器指纹配置")
        self.setModal(True)
        self.setFixedSize(600, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title_label = QLabel("🔍 浏览器指纹配置")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        info_label = QLabel("请在下方输入JSON格式的浏览器指纹配置：")
        info_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(info_label)
        
        self.json_edit = QTextEdit()
        self.json_edit.setPlaceholderText('{"name": "配置名称", "user_agent": "User-Agent字符串", "viewport_width": 1920, "viewport_height": 1080}')
        self.json_edit.setFont(QFont("Consolas", 11))
        layout.addWidget(self.json_edit)
        
        button_layout = QHBoxLayout()
        example_btn = QPushButton("📋 插入示例")
        example_btn.clicked.connect(self.insert_example)
        button_layout.addWidget(example_btn)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)

    def insert_example(self):
        example_json = '{"name": "Windows Chrome 默认", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "viewport_width": 1920, "viewport_height": 1080, "platform": "Win32", "timezone": "Asia/Shanghai"}'
        self.json_edit.setPlainText(example_json)

    def get_fingerprint_data(self):
        try:
            json_text = self.json_edit.toPlainText().strip()
            if not json_text:
                return {}
            data = json.loads(json_text)
            return {
                'name': data.get('name', '').strip(),
                'user_agent': data.get('user_agent', '').strip() or None,
                'viewport_width': data.get('viewport_width', 1920),
                'viewport_height': data.get('viewport_height', 1080),
                'platform': data.get('platform', 'Win32'),
                'timezone': data.get('timezone', 'Asia/Shanghai'),
                'locale': 'zh-CN'
            }
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON格式错误", f"JSON格式不正确：{str(e)}")
            return {}
        except Exception as e:
            QMessageBox.warning(self, "解析错误", f"解析数据时出错：{str(e)}")
            return {}

class UserManagementPage(QWidget):
    user_switched = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_service = UserService()
        self.proxy_service = ProxyService()
        self.fingerprint_service = FingerprintService()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        title = QLabel("👥 用户管理中心")
        title.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Microsoft YaHei", 10))
        
        # 用户管理选项卡
        self.users_tab = QWidget()
        self.init_users_tab()
        self.tab_widget.addTab(self.users_tab, "👤 用户管理")
        
        # 代理管理选项卡
        self.proxies_tab = QWidget()
        self.init_proxies_tab()
        self.tab_widget.addTab(self.proxies_tab, "🌐 代理管理")
        
        # 指纹管理选项卡
        self.fingerprints_tab = QWidget()
        self.init_fingerprints_tab()
        self.tab_widget.addTab(self.fingerprints_tab, "🔍 指纹管理")
        
        layout.addWidget(self.tab_widget)

    def init_users_tab(self):
        layout = QVBoxLayout(self.users_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels(["ID", "用户名", "手机号", "显示名称", "操作"])
        layout.addWidget(self.users_table)
        
        button_layout = QHBoxLayout()
        add_user_btn = QPushButton("➕ 添加用户")
        add_user_btn.clicked.connect(self.add_user)
        button_layout.addWidget(add_user_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def init_proxies_tab(self):
        layout = QVBoxLayout(self.proxies_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.proxies_table = QTableWidget()
        self.proxies_table.setColumnCount(7)
        self.proxies_table.setHorizontalHeaderLabels(["ID", "名称", "类型", "主机", "端口", "用户名", "操作"])
        layout.addWidget(self.proxies_table)
        
        button_layout = QHBoxLayout()
        add_proxy_btn = QPushButton("➕ 添加代理")
        add_proxy_btn.clicked.connect(self.add_proxy)
        button_layout.addWidget(add_proxy_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def init_fingerprints_tab(self):
        layout = QVBoxLayout(self.fingerprints_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        self.fingerprints_table = QTableWidget()
        self.fingerprints_table.setColumnCount(7)
        self.fingerprints_table.setHorizontalHeaderLabels(["ID", "名称", "User-Agent", "分辨率", "平台", "时区", "操作"])
        layout.addWidget(self.fingerprints_table)
        
        button_layout = QHBoxLayout()
        add_fingerprint_btn = QPushButton("➕ 添加指纹")
        add_fingerprint_btn.clicked.connect(self.add_fingerprint)
        button_layout.addWidget(add_fingerprint_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def load_data(self):
        self.load_users()
        self.load_proxies()
        self.load_fingerprints()

    def load_users(self):
        try:
            users = self.user_service.get_all()
            self.users_table.setRowCount(len(users))
            for row, user in enumerate(users):
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user.get('id', ''))))
                self.users_table.setItem(row, 1, QTableWidgetItem(user.get('username', '')))
                self.users_table.setItem(row, 2, QTableWidgetItem(user.get('phone', '')))
                self.users_table.setItem(row, 3, QTableWidgetItem(user.get('display_name', '') or ''))
                
                button_layout = QHBoxLayout()
                edit_btn = QPushButton("编辑")
                edit_btn.clicked.connect(lambda checked, u=user: self.edit_user(u))
                button_layout.addWidget(edit_btn)
                
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, u=user: self.delete_user(u))
                button_layout.addWidget(delete_btn)
                
                button_widget = QWidget()
                button_widget.setLayout(button_layout)
                self.users_table.setCellWidget(row, 4, button_widget)
        except Exception as e:
            print(f"加载用户数据失败: {e}")

    def load_proxies(self):
        try:
            proxies = self.proxy_service.get_all()
            self.proxies_table.setRowCount(len(proxies))
            for row, proxy in enumerate(proxies):
                self.proxies_table.setItem(row, 0, QTableWidgetItem(str(proxy.get('id', ''))))
                self.proxies_table.setItem(row, 1, QTableWidgetItem(proxy.get('name', '')))
                self.proxies_table.setItem(row, 2, QTableWidgetItem(proxy.get('proxy_type', '')))
                self.proxies_table.setItem(row, 3, QTableWidgetItem(proxy.get('host', '')))
                self.proxies_table.setItem(row, 4, QTableWidgetItem(str(proxy.get('port', ''))))
                self.proxies_table.setItem(row, 5, QTableWidgetItem(proxy.get('username', '') or ''))
                
                button_layout = QHBoxLayout()
                edit_btn = QPushButton("编辑")
                edit_btn.clicked.connect(lambda checked, p=proxy: self.edit_proxy(p))
                button_layout.addWidget(edit_btn)
                
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, p=proxy: self.delete_proxy(p))
                button_layout.addWidget(delete_btn)
                
                button_widget = QWidget()
                button_widget.setLayout(button_layout)
                self.proxies_table.setCellWidget(row, 6, button_widget)
        except Exception as e:
            print(f"加载代理数据失败: {e}")

    def load_fingerprints(self):
        try:
            fingerprints = self.fingerprint_service.get_all()
            self.fingerprints_table.setRowCount(len(fingerprints))
            for row, fingerprint in enumerate(fingerprints):
                self.fingerprints_table.setItem(row, 0, QTableWidgetItem(str(fingerprint.get('id', ''))))
                self.fingerprints_table.setItem(row, 1, QTableWidgetItem(fingerprint.get('name', '')))
                self.fingerprints_table.setItem(row, 2, QTableWidgetItem(fingerprint.get('user_agent', '') or ''))
                self.fingerprints_table.setItem(row, 3, QTableWidgetItem(f"{fingerprint.get('viewport_width', '')}x{fingerprint.get('viewport_height', '')}"))
                self.fingerprints_table.setItem(row, 4, QTableWidgetItem(fingerprint.get('platform', '')))
                self.fingerprints_table.setItem(row, 5, QTableWidgetItem(fingerprint.get('timezone', '')))
                
                button_layout = QHBoxLayout()
                edit_btn = QPushButton("编辑")
                edit_btn.clicked.connect(lambda checked, f=fingerprint: self.edit_fingerprint(f))
                button_layout.addWidget(edit_btn)
                
                delete_btn = QPushButton("删除")
                delete_btn.clicked.connect(lambda checked, f=fingerprint: self.delete_fingerprint(f))
                button_layout.addWidget(delete_btn)
                
                button_widget = QWidget()
                button_widget.setLayout(button_layout)
                self.fingerprints_table.setCellWidget(row, 6, button_widget)
        except Exception as e:
            print(f"加载指纹数据失败: {e}")

    def add_user(self):
        dialog = UserDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            user_data = dialog.get_user_data()
            if user_data:
                try:
                    user = self.user_service.create(**user_data)
                    self.load_users()
                    QMessageBox.information(self, "成功", "用户添加成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"添加用户失败：{str(e)}")

    def edit_user(self, user):
        dialog = UserDialog(self)
        user_json = {
            "username": user.get('username', ''),
            "phone": user.get('phone', ''),
            "display_name": user.get('display_name', '') or ''
        }
        dialog.json_edit.setPlainText(json.dumps(user_json, ensure_ascii=False, indent=2))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            user_data = dialog.get_user_data()
            if user_data:
                try:
                    self.user_service.update(user['id'], **user_data)
                    self.load_users()
                    QMessageBox.information(self, "成功", "用户更新成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"更新用户失败：{str(e)}")

    def delete_user(self, user):
        reply = QMessageBox.question(self, "确认删除", 
                                   f"确定要删除用户 '{user.get('username', '')}' 吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.user_service.delete(user['id'])
                self.load_users()
                QMessageBox.information(self, "成功", "用户删除成功！")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除用户失败：{str(e)}")

    def add_proxy(self):
        dialog = ProxyDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            proxy_data = dialog.get_proxy_data()
            if proxy_data:
                try:
                    proxy = self.proxy_service.create(**proxy_data)
                    self.load_proxies()
                    QMessageBox.information(self, "成功", "代理添加成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"添加代理失败：{str(e)}")

    def edit_proxy(self, proxy):
        dialog = ProxyDialog(self)
        proxy_json = {
            "name": proxy.get('name', ''),
            "proxy_type": proxy.get('proxy_type', ''),
            "host": proxy.get('host', ''),
            "port": proxy.get('port', ''),
            "username": proxy.get('username', '') or '',
            "password": proxy.get('password', '') or ''
        }
        dialog.json_edit.setPlainText(json.dumps(proxy_json, ensure_ascii=False, indent=2))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            proxy_data = dialog.get_proxy_data()
            if proxy_data:
                try:
                    self.proxy_service.update(proxy['id'], **proxy_data)
                    self.load_proxies()
                    QMessageBox.information(self, "成功", "代理更新成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"更新代理失败：{str(e)}")

    def delete_proxy(self, proxy):
        reply = QMessageBox.question(self, "确认删除", 
                                   f"确定要删除代理 '{proxy.get('name', '')}' 吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.proxy_service.delete(proxy['id'])
                self.load_proxies()
                QMessageBox.information(self, "成功", "代理删除成功！")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除代理失败：{str(e)}")

    def add_fingerprint(self):
        dialog = FingerprintDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            fingerprint_data = dialog.get_fingerprint_data()
            if fingerprint_data:
                try:
                    fingerprint = self.fingerprint_service.create(**fingerprint_data)
                    self.load_fingerprints()
                    QMessageBox.information(self, "成功", "指纹添加成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"添加指纹失败：{str(e)}")

    def edit_fingerprint(self, fingerprint):
        dialog = FingerprintDialog(self)
        fingerprint_json = {
            "name": fingerprint.get('name', ''),
            "user_agent": fingerprint.get('user_agent', '') or '',
            "viewport_width": fingerprint.get('viewport_width', ''),
            "viewport_height": fingerprint.get('viewport_height', ''),
            "platform": fingerprint.get('platform', ''),
            "timezone": fingerprint.get('timezone', '')
        }
        dialog.json_edit.setPlainText(json.dumps(fingerprint_json, ensure_ascii=False, indent=2))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            fingerprint_data = dialog.get_fingerprint_data()
            if fingerprint_data:
                try:
                    self.fingerprint_service.update(fingerprint['id'], **fingerprint_data)
                    self.load_fingerprints()
                    QMessageBox.information(self, "成功", "指纹更新成功！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"更新指纹失败：{str(e)}")

    def delete_fingerprint(self, fingerprint):
        reply = QMessageBox.question(self, "确认删除", 
                                   f"确定要删除指纹 '{fingerprint.get('name', '')}' 吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.fingerprint_service.delete(fingerprint['id'])
                self.load_fingerprints()
                QMessageBox.information(self, "成功", "指纹删除成功！")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"删除指纹失败：{str(e)}") 