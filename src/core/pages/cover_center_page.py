#!/usr/bin/env python3
"""
封面中心页面：封面模板库（仅选择）

- 模板库：展示系统封面模板（showcase_*.png）
- 选择后：保存为“首页生成封面”的默认模板
"""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QUrl, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QFileDialog,
    QComboBox,
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QScrollArea,
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

        # 营销海报素材选择（仅当选择 showcase_marketing_poster 时显示）
        self.marketing_asset_box = QWidget()
        asset_layout = QVBoxLayout(self.marketing_asset_box)
        asset_layout.setContentsMargins(0, 0, 0, 0)
        asset_layout.setSpacing(6)

        self.poster_layout = QComboBox()
        self.poster_layout.addItem('原有图文排版', '')
        self.poster_layout.addItem('截图为主：大图与短说明', 'screenshot_story')
        self.poster_layout.addItem('橙白立体：黑色大标题', 'orange_paper')
        saved_layout = Config().get_templates_config().get('poster_layout') or ''
        self.poster_layout.setCurrentIndex(max(0, self.poster_layout.findData(saved_layout)))
        self.poster_layout.currentIndexChanged.connect(self._save_poster_layout)
        asset_layout.addWidget(self.poster_layout)

        asset_title = QLabel("封面图片（可选）")
        asset_title.setStyleSheet("color: #111827; font-size: 13px; font-weight: bold;")
        asset_layout.addWidget(asset_title)

        asset_row = QHBoxLayout()
        asset_row.setSpacing(10)

        self.asset_thumb = QLabel("PNG")
        self.asset_thumb.setFixedSize(56, 56)
        self.asset_thumb.setAlignment(Qt.AlignCenter)
        self.asset_thumb.setStyleSheet(
            "QLabel { background: #ffffff; border: 1px dashed #e5e7eb; border-radius: 10px; color: #6b7280; }"
        )
        asset_row.addWidget(self.asset_thumb)

        self.asset_path_label = QLabel("未选择")
        self.asset_path_label.setWordWrap(True)
        self.asset_path_label.setStyleSheet("color: #374151; font-size: 12px;")
        asset_row.addWidget(self.asset_path_label, 1)

        self.select_asset_btn = QPushButton("选择素材")
        self.select_asset_btn.clicked.connect(self.select_marketing_asset)
        asset_row.addWidget(self.select_asset_btn)

        self.clear_asset_btn = QPushButton("清除")
        self.clear_asset_btn.clicked.connect(self.clear_marketing_asset)
        asset_row.addWidget(self.clear_asset_btn)

        asset_layout.addLayout(asset_row)
        self.marketing_asset_box.setVisible(False)
        right_layout.addWidget(self.marketing_asset_box)

        page_assets_title = QLabel('正文配图（可选）')
        page_assets_title.setStyleSheet('color: #111827; font-size: 13px; font-weight: bold;')
        right_layout.addWidget(page_assets_title)
        page_assets_hint = QLabel('按正文段顺序配图，可拖动排序。长文续页不重复配图；生成后请检查图文是否对应。')
        page_assets_hint.setWordWrap(True)
        page_assets_hint.setStyleSheet('color: #374151; font-size: 12px;')
        right_layout.addWidget(page_assets_hint)
        self.page_assets_list = QListWidget()
        self.page_assets_list.setIconSize(QSize(34,34))
        self.page_assets_list.setMaximumHeight(110)
        self.page_assets_list.setMinimumHeight(65)
        self.page_assets_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.page_assets_list.model().rowsMoved.connect(lambda *_: self._save_page_assets())
        right_layout.addWidget(self.page_assets_list)
        page_buttons = QHBoxLayout()
        for label, handler in [('添加图片',self.select_page_assets),('留空一段',self.add_empty_page_asset),('移除选中',self.remove_page_asset)]:
            button = QPushButton(label)
            button.clicked.connect(handler)
            page_buttons.addWidget(button)
        right_layout.addLayout(page_buttons)
        self._sync_page_assets_ui()

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

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QScrollArea.NoFrame)
        right_scroll.setWidget(right)
        splitter.addWidget(right_scroll)
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
        from src.core.services.poster_catalog import resolve_template_selection
        config = Config()
        settings = dict(config.get_templates_config())
        available = {t['id']:t for t in templates}
        replacement = resolve_template_selection(selected_id,settings.get('poster_layout') or '')
        if selected_id not in available and replacement in available:
            settings['selected_cover_template_id'] = replacement
            settings['selected_cover_template_display'] = available[replacement].get('display') or replacement
            config.update_templates_config(settings)
            selected_id = replacement
        if not templates:
            empty = QListWidgetItem("（未发现系统模板）")
            empty.setFlags(Qt.NoItemFlags)
            self.template_list.addItem(empty)
            return

        # 默认：不选封面模板，使用内置/系统模板生成封面与内容图
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
        screenshot_layout = str(data.get('id') or '') == 'showcase_marketing_poster'
        self.poster_layout.setVisible(screenshot_layout)
        is_marketing = str(data.get("id") or "").strip().startswith('showcase_') or bool(data.get('is_default'))
        try:
            self.marketing_asset_box.setVisible(is_marketing)
        except Exception:
            pass
        if is_marketing:
            self._sync_marketing_asset_ui()
        meta = data.get("display") or data.get("id") or "模板"
        category = data.get("category") or ""
        suffix = f" · {category}" if category else ""
        self.meta_label.setText(f"{meta}{suffix} · 预览文字仅作排版示例，生成时替换为你的内容")

        layout_id = self.poster_layout.currentData()
        if screenshot_layout and layout_id in ('screenshot_story', 'orange_paper'):
            filename = 'poster_orange_preview.png' if layout_id == 'orange_paper' else 'poster_screenshot_preview.png'
            preview = Path(__file__).resolve().parents[3] / 'assets' / filename
            if preview.exists():
                pixmap = QPixmap(str(preview))
                self.preview_label.setPixmap(pixmap.scaled(420, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.preview_label.setText('')
                self.meta_label.setText('橙白立体 · 大标题与立体素材，生成时使用你的正文和配图' if layout_id == 'orange_paper' else '截图图文 · 图中为办公小镇演示素材，生成时使用你提供的文字和图片')
                return

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

    @staticmethod
    def _marketing_asset_dir() -> Path:
        return Path(os.path.expanduser("~")) / ".xhs_system" / "marketing_poster_assets"

    def _sync_page_assets_ui(self):
        paths = Config().get_templates_config().get('poster_page_asset_paths') or []
        if not isinstance(paths,list):
            paths = []
        self.page_assets_list.clear()
        for path in paths:
            item = QListWidgetItem(QIcon(str(path)),Path(path).name if path else '不配图')
            item.setData(Qt.UserRole,str(path))
            item.setToolTip(str(path))
            self.page_assets_list.addItem(item)

    def _save_page_assets(self):
        paths = [self.page_assets_list.item(i).data(Qt.UserRole) or '' for i in range(self.page_assets_list.count())]
        config = Config()
        settings = config.get_templates_config()
        settings['poster_page_asset_paths'] = paths
        config.update_templates_config(settings)

    def select_page_assets(self):
        paths,_ = QFileDialog.getOpenFileNames(self,'选择正文图片',str(self._marketing_asset_dir()),'图片 (*.png *.jpg *.jpeg *.webp)')
        if not paths:
            return
        from PIL import Image
        copied = []
        try:
            directory = self._marketing_asset_dir()
            directory.mkdir(parents=True,exist_ok=True)
            for path in paths:
                with Image.open(path) as image:
                    image.verify()
                target = directory/f'page_{uuid.uuid4().hex[:8]}{Path(path).suffix.lower()}'
                shutil.copy2(path,target)
                copied.append(target)
        except Exception as exc:
            for target in copied:
                target.unlink(missing_ok=True)
            QMessageBox.warning(self,'图片未添加',f'无法读取或保存图片：{exc}')
            return
        for target in copied:
            item = QListWidgetItem(QIcon(str(target)),target.name)
            item.setData(Qt.UserRole,str(target))
            item.setToolTip(str(target))
            self.page_assets_list.addItem(item)
        self._save_page_assets()

    def add_empty_page_asset(self):
        item = QListWidgetItem('不配图')
        item.setData(Qt.UserRole,'')
        self.page_assets_list.addItem(item)
        self._save_page_assets()

    def remove_page_asset(self):
        row = self.page_assets_list.currentRow()
        if row >= 0:
            self.page_assets_list.takeItem(row)
            self._save_page_assets()

    def _save_poster_layout(self):
        config = Config()
        settings = dict(config.get_templates_config())
        settings['poster_layout'] = self.poster_layout.currentData() or ''
        config.update_templates_config(settings)
        self.on_template_changed(self.template_list.currentItem(), None)

    def _load_marketing_asset_path(self) -> str:
        try:
            path = str(Config().get_templates_config().get("marketing_poster_asset_path") or "").strip()
        except Exception:
            path = ""
        path = os.path.expanduser(path) if path else ""
        if path and os.path.exists(path):
            return path
        return ""

    def _sync_marketing_asset_ui(self) -> None:
        path = self._load_marketing_asset_path()
        if path:
            basename = os.path.basename(path)
            self.asset_path_label.setText(basename)
            self.asset_path_label.setToolTip(path)
            self.clear_asset_btn.setEnabled(True)
            try:
                pixmap = QPixmap(path)
                scaled = pixmap.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.asset_thumb.setPixmap(scaled)
                self.asset_thumb.setText("")
            except Exception:
                self.asset_thumb.setPixmap(QPixmap())
                self.asset_thumb.setText("PNG")
        else:
            self.asset_path_label.setText("未选择（透明底 PNG）")
            self.asset_path_label.setToolTip("")
            self.clear_asset_btn.setEnabled(False)
            self.asset_thumb.setPixmap(QPixmap())
            self.asset_thumb.setText("PNG")

    def select_marketing_asset(self) -> None:
        """选择营销海报素材（透明底 PNG），并保存到配置。"""
        current = self._load_marketing_asset_path()
        initial_dir = os.path.dirname(current) if current else str(self._marketing_asset_dir())

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择海报素材（PNG）",
            initial_dir,
            "PNG 图片 (*.png);;所有文件 (*)",
        )
        file_path = str(file_path or "").strip()
        if not file_path:
            return
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "提示", "选择的文件不存在")
            return

        asset_dir = self._marketing_asset_dir()
        try:
            asset_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.warning(self, "提示", f"创建素材目录失败: {e}")
            return

        suffix = Path(file_path).suffix.lower() or ".png"
        if suffix != ".png":
            suffix = ".png"
        target = asset_dir / f"asset_{uuid.uuid4().hex[:8]}{suffix}"

        try:
            shutil.copy2(file_path, target)
        except Exception as e:
            QMessageBox.warning(self, "提示", f"复制素材失败: {e}")
            return

        try:
            cfg = Config()
            templates_cfg = cfg.get_templates_config()
            templates_cfg["marketing_poster_asset_path"] = str(target)
            cfg.update_templates_config(templates_cfg)
        except Exception as e:
            QMessageBox.warning(self, "提示", f"保存素材选择失败: {e}")
            return

        self._sync_marketing_asset_ui()
        try:
            TipWindow(self.parent() if self.parent() else self, "✅ 已选择营销海报素材").show()
        except Exception:
            pass

    def clear_marketing_asset(self) -> None:
        """清除营销海报素材选择。"""
        try:
            cfg = Config()
            templates_cfg = cfg.get_templates_config()
            templates_cfg["marketing_poster_asset_path"] = ""
            cfg.update_templates_config(templates_cfg)
        except Exception:
            pass
        self._sync_marketing_asset_ui()

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
