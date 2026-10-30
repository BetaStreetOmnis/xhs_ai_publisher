#!/usr/bin/env python3
"""
提醒与热点草稿弹窗

- 关联账号（可选）
- 选择提醒或生成时间
- 内容到点提醒；热点生成一次本地草稿
"""

from __future__ import annotations

import os
from typing import List, Optional

from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QHBoxLayout,
    QFileDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.ui.qt_font import get_ui_font_family
from src.core.services.hotspot_service import hotspot_service


class ScheduledPublishDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        users: Optional[List[object]] = None,
        default_user_id: Optional[int] = None,
        default_interval_hours: int = 2,
        initial_title: str = "",
        initial_content: str = "",
        initial_images: Optional[List[str]] = None,
        default_task_type: str = "fixed",
    ):
        super().__init__(parent)
        self.setWindowTitle("⏰ 提醒与草稿")
        self.setModal(True)
        self.setFixedSize(660, 720)

        self._users = users or []
        self._default_user_id = default_user_id
        self._default_interval_hours = max(1, int(default_interval_hours or 2))
        self._initial_title = str(initial_title or "")
        self._initial_content = str(initial_content or "")
        self._initial_images = [p for p in (initial_images or []) if isinstance(p, str) and p]
        self._default_task_type = str(default_task_type or "fixed").strip() or "fixed"

        self.user_combo = QComboBox()
        self.datetime_edit = QDateTimeEdit()
        self.mode_combo = QComboBox()
        self.fixed_container = QWidget()
        self.fixed_title_input = QLineEdit()
        self.fixed_content_edit = QTextEdit()
        self.images_list = QListWidget()
        self._fixed_images: List[str] = []
        self.hotspot_container = QWidget()
        self.hotspot_source_combo = QComboBox()
        self.hotspot_rank_spin = QSpinBox()
        self.interval_hours_spin = QSpinBox()
        self.hotspot_context_check = QCheckBox("保存搜索摘要供核对（不是事实核验）")

        self._setup_ui()
        self._load_users()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("⏰ 创建提醒或热点草稿")
        title.setFont(QFont(get_ui_font_family(), 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        hint = QLabel("软件需保持运行。内容任务到点提醒；热点任务仅生成一次本地草稿，之后由你核对。")
        hint.setStyleSheet("color: #6b7280;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 模式选择
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        mode_label = QLabel("任务类型：")
        mode_label.setFixedWidth(90)
        mode_row.addWidget(mode_label)
        self.mode_combo.addItem("内容提醒（保存当前内容）", "fixed")
        self.mode_combo.addItem("热点草稿（到点生成一次）", "hotspot")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo, 1)
        layout.addLayout(mode_row)

        # 用户选择
        user_row = QHBoxLayout()
        user_row.setSpacing(10)
        user_label = QLabel("关联账号：")
        user_label.setFixedWidth(90)
        user_row.addWidget(user_label)
        user_row.addWidget(self.user_combo, 1)
        layout.addLayout(user_row)

        # 时间选择
        time_row = QHBoxLayout()
        time_row.setSpacing(10)
        time_label = QLabel("提醒 / 生成：")
        time_label.setFixedWidth(90)
        time_row.addWidget(time_label)

        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.datetime_edit.setCalendarPopup(True)
        now = QDateTime.currentDateTime()
        self.datetime_edit.setMinimumDateTime(now.addSecs(30))
        self.datetime_edit.setDateTime(now.addSecs(10 * 60))
        time_row.addWidget(self.datetime_edit, 1)
        layout.addLayout(time_row)

        # 固定内容（一次发布时显示）
        fixed_layout = QVBoxLayout(self.fixed_container)
        fixed_layout.setContentsMargins(0, 0, 0, 0)
        fixed_layout.setSpacing(10)

        fixed_title_row = QHBoxLayout()
        fixed_title_row.setSpacing(10)
        fixed_title_label = QLabel("标题：")
        fixed_title_label.setFixedWidth(90)
        fixed_title_row.addWidget(fixed_title_label)
        self.fixed_title_input.setPlaceholderText("可输入标题（建议不超过 20 字）")
        self.fixed_title_input.setText(self._initial_title)
        fixed_title_row.addWidget(self.fixed_title_input, 1)
        fixed_layout.addLayout(fixed_title_row)

        fixed_content_label = QLabel("正文：")
        fixed_content_label.setStyleSheet("color: #111827;")
        fixed_layout.addWidget(fixed_content_label)

        self.fixed_content_edit.setPlaceholderText("可输入正文内容（支持换行）")
        self.fixed_content_edit.setText(self._initial_content)
        self.fixed_content_edit.setMinimumHeight(160)
        fixed_layout.addWidget(self.fixed_content_edit)

        images_title_row = QHBoxLayout()
        images_title_row.setSpacing(10)
        images_label = QLabel("图片：")
        images_label.setFixedWidth(90)
        images_title_row.addWidget(images_label)

        add_btn = QPushButton("选择图片…")
        add_btn.clicked.connect(self._add_images)
        images_title_row.addWidget(add_btn)

        remove_btn = QPushButton("移除所选")
        remove_btn.clicked.connect(self._remove_selected_images)
        images_title_row.addWidget(remove_btn)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear_images)
        images_title_row.addWidget(clear_btn)

        images_title_row.addStretch()
        fixed_layout.addLayout(images_title_row)

        self.images_list.setMinimumHeight(120)
        fixed_layout.addWidget(self.images_list)

        img_hint = QLabel("图片随内容保存。到点只提醒，不生成占位图，也不发布。")
        img_hint.setStyleSheet("color: #6b7280;")
        img_hint.setWordWrap(True)
        fixed_layout.addWidget(img_hint)

        self._set_fixed_images(self._initial_images)
        self.fixed_container.setVisible(True)
        layout.addWidget(self.fixed_container)

        # 热点选项（跟随热点时显示）
        hs_layout = QVBoxLayout(self.hotspot_container)
        hs_layout.setContentsMargins(0, 0, 0, 0)
        hs_layout.setSpacing(10)

        source_row = QHBoxLayout()
        source_row.setSpacing(10)
        source_label = QLabel("热点来源：")
        source_label.setFixedWidth(90)
        source_row.addWidget(source_label)
        for sid, name in hotspot_service.available_sources().items():
            self.hotspot_source_combo.addItem(name, sid)
        source_row.addWidget(self.hotspot_source_combo, 1)
        hs_layout.addLayout(source_row)

        rank_row = QHBoxLayout()
        rank_row.setSpacing(10)
        rank_label = QLabel("热榜排名：")
        rank_label.setFixedWidth(90)
        rank_row.addWidget(rank_label)
        self.hotspot_rank_spin.setRange(1, 50)
        self.hotspot_rank_spin.setValue(1)
        rank_row.addWidget(self.hotspot_rank_spin, 1)
        hs_layout.addLayout(rank_row)

        cost_note = QLabel("热点生成会使用已配置的模型及额度。结果待核实，不会发布，也不会循环生成。")
        cost_note.setWordWrap(True)
        hs_layout.addWidget(cost_note)

        self.hotspot_context_check.setChecked(True)
        hs_layout.addWidget(self.hotspot_context_check)

        self.hotspot_container.setVisible(False)
        layout.addWidget(self.hotspot_container)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("创建任务")
        ok_btn.setStyleSheet(
            "QPushButton { background-color: #FF2442; color: white; border: none; padding: 8px 14px; border-radius: 8px; font-weight: bold; }"
            "QPushButton:hover { background-color: #E91E63; }"
        )
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)

        layout.addStretch()
        layout.addLayout(btn_row)

    def _on_mode_changed(self, _index: int):
        task_type = self.get_task_type()
        self.hotspot_container.setVisible(task_type == "hotspot")
        self.fixed_container.setVisible(task_type != "hotspot")

    def _set_fixed_images(self, paths: List[str]):
        self._fixed_images = []
        for p in paths or []:
            if isinstance(p, str) and p and p not in self._fixed_images:
                self._fixed_images.append(p)
        self._refresh_images_list()

    def _refresh_images_list(self):
        self.images_list.clear()
        for p in self._fixed_images:
            name = os.path.basename(p) or p
            self.images_list.addItem(name)
            try:
                item = self.images_list.item(self.images_list.count() - 1)
                item.setToolTip(p)
            except Exception:
                pass

    def _add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)",
        )
        if not files:
            return
        changed = False
        for p in files:
            if isinstance(p, str) and p and p not in self._fixed_images:
                self._fixed_images.append(p)
                changed = True
        if changed:
            self._refresh_images_list()

    def _remove_selected_images(self):
        rows = sorted({idx.row() for idx in self.images_list.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for r in rows:
            try:
                del self._fixed_images[r]
            except Exception:
                pass
        self._refresh_images_list()

    def _clear_images(self):
        self._fixed_images = []
        self._refresh_images_list()

    def _load_users(self):
        self.user_combo.clear()
        self.user_combo.addItem("暂不关联账号", None)

        selected_index = 0
        for idx, u in enumerate(self._users):
            try:
                user_id = int(getattr(u, "id"))
            except Exception:
                continue

            phone = str(getattr(u, "phone", "") or "").strip()
            username = str(getattr(u, "username", "") or "").strip()
            display_name = str(getattr(u, "display_name", "") or "").strip()
            is_current = bool(getattr(u, "is_current", False))
            is_logged_in = bool(getattr(u, "is_logged_in", False))

            name = display_name or username or phone or f"用户{user_id}"
            current_tag = " ⭐" if is_current else ""
            login_tag = " ✅" if is_logged_in else " ❌"
            label = f"{name}{current_tag}{login_tag}"
            if phone:
                label += f"  ({phone})"

            self.user_combo.addItem(label, user_id)
            if self._default_user_id and user_id == int(self._default_user_id):
                selected_index = self.user_combo.count() - 1

        if self.user_combo.count() > 0:
            self.user_combo.setCurrentIndex(selected_index)

        # 默认任务类型
        try:
            if self._default_task_type == "hotspot":
                idx = self.mode_combo.findData("hotspot")
                if idx >= 0:
                    self.mode_combo.setCurrentIndex(idx)
        except Exception:
            pass
        self._on_mode_changed(self.mode_combo.currentIndex())

    def get_user_id(self) -> Optional[int]:
        try:
            val = self.user_combo.currentData()
            return int(val) if val is not None else None
        except Exception:
            return None

    def get_schedule_time(self):
        dt = self.datetime_edit.dateTime()
        try:
            return dt.toPyDateTime()
        except Exception:
            # 兜底：返回字符串由调用方处理
            return dt.toString("yyyy-MM-dd HH:mm")

    def get_task_type(self) -> str:
        return str(self.mode_combo.currentData() or "fixed")

    def get_hotspot_source(self) -> str:
        return str(self.hotspot_source_combo.currentData() or "")

    def get_hotspot_rank(self) -> int:
        try:
            return int(self.hotspot_rank_spin.value())
        except Exception:
            return 1

    def get_interval_hours(self) -> int:
        return 0

    def get_use_hotspot_context(self) -> bool:
        try:
            return bool(self.hotspot_context_check.isChecked())
        except Exception:
            return True

    def get_fixed_title(self) -> str:
        try:
            return str(self.fixed_title_input.text() or "").strip()
        except Exception:
            return ""

    def get_fixed_content(self) -> str:
        try:
            return str(self.fixed_content_edit.toPlainText() or "").strip()
        except Exception:
            return ""

    def get_fixed_images(self) -> List[str]:
        images = []
        for p in self._fixed_images:
            if isinstance(p, str) and p:
                images.append(p)
        return images

    def accept(self):
        try:
            if self.get_task_type() == "fixed":
                if not self.get_fixed_title() and not self.get_fixed_content():
                    QMessageBox.warning(self, "提示", "请至少输入标题或正文。")
                    return
        except Exception:
            pass
        super().accept()
