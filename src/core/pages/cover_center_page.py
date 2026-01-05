#!/usr/bin/env python3
"""
封面中心页面：封面模板库（仅选择）

- 模板库：展示系统封面模板（showcase_*.png）
- 选择后：保存为“首页生成封面”的默认模板
"""

from __future__ import annotations

import os
from typing import Optional

from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtGui import QDesktopServices

from src.config.config import Config
from src.core.alert import TipWindow
from src.core.services.system_image_template_service import system_image_template_service
from src.core.ui.qt_font import get_ui_font_family


class CoverTemplateLibraryTab(QWidget):
    """封面模板库（系统模板）"""

    template_chosen = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_template: Optional[dict] = None
        self._setup_ui()
        self.refresh_templates()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("🧩 封面模板库")
        title.setFont(QFont(get_ui_font_family(), 16, QFont.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)

        # 顶部操作区
        top_row = QHBoxLayout()
        self.dir_label = QLabel()
        self.dir_label.setWordWrap(True)
        self.dir_label.setStyleSheet("color: #666; font-size: 12px;")
        top_row.addWidget(self.dir_label, 1)

        open_btn = QPushButton("📂 打开目录")
        open_btn.clicked.connect(self.open_templates_dir)
        top_row.addWidget(open_btn)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_templates)
        top_row.addWidget(refresh_btn)

        layout.addLayout(top_row)

        splitter = QSplitter(Qt.Horizontal)

        # 左侧列表
        self.template_list = QListWidget()
        self.template_list.setMinimumWidth(280)
        self.template_list.currentItemChanged.connect(self.on_template_changed)
        splitter.addWidget(self.template_list)

        # 右侧预览
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.preview_label = QLabel("选择一个模板查看预览")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(420, 420)
        self.preview_label.setStyleSheet(
            "QLabel { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px; }"
        )
        right_layout.addWidget(self.preview_label, 1)

        self.meta_label = QLabel("—")
        self.meta_label.setWordWrap(True)
        self.meta_label.setStyleSheet("color: #374151; font-size: 13px;")
        right_layout.addWidget(self.meta_label)

        apply_btn = QPushButton("✅ 应用到首页")
        apply_btn.setStyleSheet(
            "QPushButton { background-color: #FF2442; color: white; border: none; padding: 10px 14px; border-radius: 8px; font-weight: bold; }"
            "QPushButton:hover { background-color: #E91E63; }"
        )
        apply_btn.clicked.connect(self.apply_current_template)
        right_layout.addWidget(apply_btn)

        clear_btn = QPushButton("🧹 恢复默认")
        clear_btn.setStyleSheet(
            "QPushButton { background-color: #f3f4f6; color: #111827; border: 1px solid #e5e7eb; padding: 10px 14px; border-radius: 8px; font-weight: bold; }"
            "QPushButton:hover { background-color: #e5e7eb; }"
        )
        clear_btn.clicked.connect(self.clear_selection)
        right_layout.addWidget(clear_btn)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter, 1)

    def open_templates_dir(self):
        showcase_dir = system_image_template_service.resolve_showcase_dir()
        if showcase_dir and showcase_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(showcase_dir)))
            return

        templates_dir = system_image_template_service.resolve_templates_dir()
        if not templates_dir or not templates_dir.exists():
            QMessageBox.warning(self, "提示", "未找到系统模板目录（请确认 x-auto-publisher 路径）")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(templates_dir)))

    def refresh_templates(self):
        self.template_list.clear()

        showcase_dir = system_image_template_service.resolve_showcase_dir()
        self.dir_label.setText(f"模板目录：{showcase_dir or '未检测到'}")

        try:
            selected_id = (Config().get_templates_config().get("selected_cover_template_id") or "").strip()
        except Exception:
            selected_id = ""

        templates = system_image_template_service.list_showcase_templates()
        if not templates:
            empty = QListWidgetItem("（未发现系统模板）")
            empty.setFlags(Qt.NoItemFlags)
            self.template_list.addItem(empty)
            return

        # 默认：不选封面模板，走远程接口生成封面/内容图
        default_tpl = {
            "id": "",
            "display": "默认",
            "category": "",
            "name": "默认",
            "path": "",
            "is_default": True,
        }
        default_item = QListWidgetItem("（默认）")
        default_item.setData(Qt.UserRole, default_tpl)
        self.template_list.addItem(default_item)

        for tpl in templates:
            display = tpl.get("display") or tpl.get("id") or "cover"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, tpl)
            self.template_list.addItem(item)

        # 优先定位到已选择的模板
        if selected_id:
            for i in range(self.template_list.count()):
                data = (self.template_list.item(i).data(Qt.UserRole) or {}) if self.template_list.item(i) else {}
                if isinstance(data, dict) and data.get("id") == selected_id:
                    self.template_list.setCurrentRow(i)
                    return

        self.template_list.setCurrentRow(0)

    def on_template_changed(self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]):
        if not current:
            return
        data = current.data(Qt.UserRole) or {}
        if not isinstance(data, dict):
            return

        self._current_template = data
        meta = data.get("display") or data.get("id") or "模板"
        category = data.get("category") or ""
        suffix = f" · {category}" if category else ""
        self.meta_label.setText(f"{meta}{suffix}")

        # 默认模式：不展示图片预览
        if data.get("is_default") or not data.get("path"):
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("默认模式：生成时使用系统默认封面样式")
            return

        bg_path = data.get("path")
        if not bg_path:
            return

        # 直接展示模板原图；生成效果在“生成内容”中预览更准确
        if os.path.exists(bg_path):
            pixmap = QPixmap(bg_path)
            scaled = pixmap.scaled(420, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
            self.preview_label.setText("")
        else:
            self.preview_label.setText("模板文件不存在")

    def apply_current_template(self):
        if not self._current_template:
            QMessageBox.information(self, "提示", "请先选择一个模板")
            return
        self.template_chosen.emit(self._current_template)

    def clear_selection(self):
        """清除封面模板选择，恢复默认。"""
        try:
            self.template_chosen.emit({"id": "", "display": "默认", "is_default": True})
        except Exception:
            pass


class CoverCenterPage(QWidget):
    """封面中心页（独立菜单入口）"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.parent = parent
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.template_tab = CoverTemplateLibraryTab(self)
        self.template_tab.template_chosen.connect(self.on_template_chosen)
        layout.addWidget(self.template_tab)

    def on_template_chosen(self, template: dict):
        try:
            template_id = str((template or {}).get("id") or "").strip()
            display = str((template or {}).get("display") or (template or {}).get("id") or "默认").strip()

            cfg = Config()
            templates_cfg = cfg.get_templates_config()
            templates_cfg["selected_cover_template_id"] = template_id
            templates_cfg["selected_cover_template_display"] = display if template_id else ""
            cfg.update_templates_config(templates_cfg)

            if template_id:
                TipWindow(self.parent, f"✅ 已设为首页封面模板：{display}").show()
            else:
                TipWindow(self.parent, "✅ 已恢复默认封面样式").show()

            # 选择后直接回到首页，让用户一键生成内容
            if self.parent and hasattr(self.parent, "switch_page"):
                self.parent.switch_page(0)
        except Exception as e:
            QMessageBox.warning(self, "提示", f"保存模板选择失败: {e}")

    def show_template_library(self):
        """供首页跳转使用：刷新模板库。"""
        try:
            if hasattr(self, "template_tab") and hasattr(self.template_tab, "refresh_templates"):
                self.template_tab.refresh_templates()
        except Exception:
            pass
