#!/usr/bin/env python3
"""
用户管理页面
提供多账户创建/切换/编辑/删除
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QDialog,
    QLineEdit,
    QMessageBox,
)

from src.core.ui.qt_font import get_ui_font_family


class UserDialog(QDialog):
    """用户编辑/创建对话框"""

    def __init__(self, parent=None, title: str = "用户信息"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(520, 260)
        self.default_font = QFont(get_ui_font_family(), 11)
        self.setFont(self.default_font)

        self.username_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.display_name_input = QLineEdit()

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title_label = QLabel("👥 用户信息")
        title_label.setFont(QFont(get_ui_font_family(), 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        def row(label_text: str, widget: QWidget):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)
            label = QLabel(label_text)
            label.setFixedWidth(110)
            row_layout.addWidget(label)
            row_layout.addWidget(widget)
            return row_layout

        layout.addLayout(row("用户名:", self.username_input))
        layout.addLayout(row("手机号:", self.phone_input))
        layout.addLayout(row("显示名称:", self.display_name_input))

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("保存")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

    def set_data(self, username: str, phone: str, display_name: str):
        self.username_input.setText(username or "")
        self.phone_input.setText(phone or "")
        self.display_name_input.setText(display_name or "")

    def get_data(self):
        return {
            "username": self.username_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "display_name": self.display_name_input.text().strip(),
        }


class UserManagementPage(QWidget):
    """用户管理页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_service = None
        self._init_services()
        self._init_ui()
        self.load_users()

    def _init_services(self):
        try:
            from ..services.user_service import user_service

            self.user_service = user_service
            self._services_ready = True
        except Exception as e:
            print(f"⚠️ 用户服务不可用: {e}")
            self._services_ready = False

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 顶部状态栏
        status_layout = QHBoxLayout()
        if self._services_ready:
            status_label = QLabel("💚 用户服务已连接")
            status_label.setStyleSheet("color: green; font-weight: bold; font-size: 12px;")
        else:
            status_label = QLabel("🟡 用户服务不可用（仅展示）")
            status_label.setStyleSheet("color: orange; font-weight: bold; font-size: 12px;")
        status_layout.addWidget(status_label)
        status_layout.addStretch()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setFont(QFont(get_ui_font_family(), 11))
        refresh_btn.clicked.connect(self.load_users)
        status_layout.addWidget(refresh_btn)
        layout.addLayout(status_layout)

        title = QLabel("👥 用户管理")
        title.setFont(QFont(get_ui_font_family(), 26, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 用户表
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(7)
        self.users_table.setHorizontalHeaderLabels(["ID", "用户名", "手机号", "显示名称", "当前", "登录状态", "操作"])
        self.users_table.setFont(QFont(get_ui_font_family(), 11))
        self.users_table.horizontalHeader().setFont(QFont(get_ui_font_family(), 12, QFont.Bold))
        self.users_table.verticalHeader().setDefaultSectionSize(35)
        self.users_table.setColumnWidth(0, 60)
        self.users_table.setColumnWidth(1, 140)
        self.users_table.setColumnWidth(2, 160)
        self.users_table.setColumnWidth(3, 160)
        self.users_table.setColumnWidth(4, 80)
        self.users_table.setColumnWidth(5, 120)
        self.users_table.setColumnWidth(6, 220)
        layout.addWidget(self.users_table)

        # 操作按钮
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 添加用户")
        add_btn.setFont(QFont(get_ui_font_family(), 12))
        add_btn.setMinimumHeight(40)
        add_btn.clicked.connect(self.add_user)
        btn_layout.addWidget(add_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def load_users(self):
        if not self._services_ready:
            self.users_table.setRowCount(0)
            return

        try:
            users = self.user_service.list_users(active_only=False)
            self.users_table.setRowCount(len(users))

            for row, user in enumerate(users):
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
                self.users_table.setItem(row, 1, QTableWidgetItem(user.username or ""))
                self.users_table.setItem(row, 2, QTableWidgetItem(user.phone or ""))
                self.users_table.setItem(row, 3, QTableWidgetItem(user.display_name or ""))
                self.users_table.setItem(row, 4, QTableWidgetItem("⭐" if user.is_current else ""))
                self.users_table.setItem(row, 5, QTableWidgetItem("✅ 已登录" if user.is_logged_in else "❌ 未登录"))

                # 操作按钮
                op_layout = QHBoxLayout()
                op_layout.setSpacing(6)

                switch_btn = QPushButton("设为当前")
                switch_btn.setFont(QFont(get_ui_font_family(), 10))
                switch_btn.setMinimumHeight(28)
                switch_btn.clicked.connect(lambda checked, uid=user.id: self.switch_user(uid))
                op_layout.addWidget(switch_btn)

                edit_btn = QPushButton("编辑")
                edit_btn.setFont(QFont(get_ui_font_family(), 10))
                edit_btn.setMinimumHeight(28)
                edit_btn.clicked.connect(lambda checked, u=user: self.edit_user(u))
                op_layout.addWidget(edit_btn)

                del_btn = QPushButton("删除")
                del_btn.setFont(QFont(get_ui_font_family(), 10))
                del_btn.setMinimumHeight(28)
                del_btn.clicked.connect(lambda checked, uid=user.id: self.delete_user(uid))
                op_layout.addWidget(del_btn)

                op_widget = QWidget()
                op_widget.setLayout(op_layout)
                self.users_table.setCellWidget(row, 6, op_widget)

        except Exception as e:
            print(f"❌ 加载用户失败: {e}")
            QMessageBox.warning(self, "加载失败", f"加载用户数据时出错：{str(e)}")

    def add_user(self):
        if not self._services_ready:
            QMessageBox.warning(self, "不可用", "用户服务不可用")
            return

        dialog = UserDialog(self, title="添加用户")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.user_service.create_user(
                    username=data["username"],
                    phone=data["phone"],
                    display_name=data["display_name"] or None,
                    set_current=True,
                )
                self._sync_current_user_to_main()
                self.load_users()
                QMessageBox.information(self, "成功", "用户创建成功")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"创建用户失败：{str(e)}")

    def edit_user(self, user):
        if not self._services_ready:
            QMessageBox.warning(self, "不可用", "用户服务不可用")
            return

        dialog = UserDialog(self, title="编辑用户")
        dialog.set_data(user.username, user.phone, user.display_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                self.user_service.update_user(
                    user_id=user.id,
                    username=data["username"],
                    phone=data["phone"],
                    display_name=data["display_name"] or None,
                )
                self.load_users()
                QMessageBox.information(self, "成功", "用户更新成功")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"更新用户失败：{str(e)}")

    def delete_user(self, user_id: int):
        if not self._services_ready:
            QMessageBox.warning(self, "不可用", "用户服务不可用")
            return

        reply = QMessageBox.question(self, "确认删除", "确定要删除该用户吗？", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        try:
            self.user_service.delete_user(user_id)
            self._sync_current_user_to_main()
            self.load_users()
            QMessageBox.information(self, "成功", "用户删除成功")
        except Exception as e:
            QMessageBox.warning(self, "失败", f"删除用户失败：{str(e)}")

    def switch_user(self, user_id: int):
        if not self._services_ready:
            QMessageBox.warning(self, "不可用", "用户服务不可用")
            return

        try:
            self.user_service.switch_user(user_id)
            self._sync_current_user_to_main()
            self.load_users()
            QMessageBox.information(self, "成功", "已切换当前用户")
        except Exception as e:
            QMessageBox.warning(self, "失败", f"切换用户失败：{str(e)}")

    def _sync_current_user_to_main(self):
        """切换用户后，同步到主界面（手机号输入框 + 环境页）。"""
        try:
            parent = self.parent()
            if not parent:
                return

            if hasattr(parent, "sync_current_user_to_ui"):
                parent.sync_current_user_to_ui()
            else:
                # 兼容旧主窗口：尽量刷新手机号
                current = self.user_service.get_current_user()
                if current and hasattr(parent, "home_page") and hasattr(parent.home_page, "phone_input"):
                    parent.home_page.phone_input.setText(current.phone or "")

            if hasattr(parent, "browser_environment_page") and hasattr(parent.browser_environment_page, "load_data"):
                parent.browser_environment_page.load_data()
        except Exception:
            pass
