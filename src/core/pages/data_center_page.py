#!/usr/bin/env python3
"""
数据中心页面：自动采集热点信息

- 支持多平台热榜（微博/百度/头条/B站）
- 支持手动刷新 + 自动刷新
- 支持一键将热点词带回首页生成内容
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal, QUrl
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtGui import QDesktopServices

from src.config.config import Config
from src.core.alert import TipWindow
from src.core.services.hotspot_service import HotspotItem, hotspot_service
from src.core.ui.qt_font import get_ui_font_family


class HotspotFetchThread(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, sources: List[str], limit: int = 50):
        super().__init__()
        self.sources = sources
        self.limit = limit

    def run(self):
        try:
            data = hotspot_service.fetch_many(self.sources, limit=self.limit)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class HotspotContextThread(QThread):
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str, str)

    def __init__(self, query: str, limit: int = 3):
        super().__init__()
        self.query = query
        self.limit = limit

    def run(self):
        try:
            items = hotspot_service.fetch_baidu_search_snippets(self.query, limit=self.limit)
            self.finished.emit(self.query, items)
        except Exception as e:
            self.error.emit(self.query, str(e))


class DataCenterPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.parent = parent
        self._tables: Dict[str, QTableWidget] = {}
        self._last_payload: Dict[str, List[HotspotItem]] = {}
        self._auto_timer = QTimer(self)
        self._auto_timer.timeout.connect(self._auto_refresh_tick)
        self._thread: Optional[HotspotFetchThread] = None
        self._silent_refresh = False
        self._context_thread: Optional[HotspotContextThread] = None
        self._context_cache: Dict[str, str] = {}
        self._pending_context_query: str = ""
        self._context_timer = QTimer(self)
        self._context_timer.setSingleShot(True)
        self._context_timer.timeout.connect(self._maybe_fetch_pending_context)
        self._selected_hotspot: Optional[HotspotItem] = None
        self._setup_ui()
        self._load_cached()
        self._apply_auto_refresh_from_config()
        QTimer.singleShot(800, lambda: self.refresh(silent=True))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("QFrame { background-color: white; border-bottom: 1px solid #e5e7eb; }")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_layout.setSpacing(12)

        title = QLabel("📊 数据中心 · 热点采集")
        title.setFont(QFont(get_ui_font_family(), 16, QFont.Bold))
        title.setStyleSheet("color: #111827;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.source_combo = QComboBox()
        self.source_combo.addItem("全部平台", "__all__")
        for sid, name in hotspot_service.available_sources().items():
            self.source_combo.addItem(name, sid)
        header_layout.addWidget(QLabel("来源:"))
        header_layout.addWidget(self.source_combo)

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(10, 100)
        self.limit_spin.setValue(50)
        self.limit_spin.setSingleStep(10)
        header_layout.addWidget(QLabel("条数:"))
        header_layout.addWidget(self.limit_spin)

        self.auto_check = QCheckBox("自动刷新")
        self.auto_check.stateChanged.connect(self._on_auto_changed)
        header_layout.addWidget(self.auto_check)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(10)
        self.interval_spin.setSuffix(" 分钟")
        self.interval_spin.valueChanged.connect(self._on_interval_changed)
        header_layout.addWidget(self.interval_spin)

        self.last_label = QLabel("上次更新：—")
        self.last_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        header_layout.addWidget(self.last_label)

        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(lambda: self.refresh(silent=False))
        self.refresh_btn.setStyleSheet(
            "QPushButton { padding: 6px 10px; border-radius: 8px; background-color: #f3f4f6; }"
            "QPushButton:hover { background-color: #e5e7eb; }"
        )
        header_layout.addWidget(self.refresh_btn)

        self.use_btn = QPushButton("✍️ 用作首页主题")
        self.use_btn.clicked.connect(self.use_selected_as_topic)
        self.use_btn.setStyleSheet(
            "QPushButton { padding: 6px 10px; border-radius: 8px; background-color: #FF2442; color: white; font-weight: bold; }"
            "QPushButton:hover { background-color: #E91E63; }"
        )
        header_layout.addWidget(self.use_btn)

        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: none; background-color: #f8f9fa; }"
            "QTabBar::tab { background: #e9ecef; color: #495057; padding: 8px 16px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-weight: bold; }"
            "QTabBar::tab:selected { background: white; color: #2c3e50; }"
            "QTabBar::tab:hover { background: #dee2e6; }"
        )

        for sid, name in hotspot_service.available_sources().items():
            tab = self._create_source_tab(sid)
            self.tabs.addTab(tab, name)
        self.tabs.currentChanged.connect(lambda _i: self._sync_selected_hotspot())

        layout.addWidget(self.tabs, 1)

        # 详情面板：展示热点“内容摘要”
        detail = QFrame()
        detail.setStyleSheet("QFrame { background-color: white; border-top: 1px solid #e5e7eb; }")
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(18, 12, 18, 12)
        detail_layout.setSpacing(8)

        detail_top = QHBoxLayout()
        self.detail_title = QLabel("🧾 热点内容：未选择")
        self.detail_title.setFont(QFont(get_ui_font_family(), 12, QFont.Bold))
        self.detail_title.setStyleSheet("color: #111827;")
        detail_top.addWidget(self.detail_title)
        detail_top.addStretch()

        self.auto_content_check = QCheckBox("选中自动抓取内容")
        self.auto_content_check.setChecked(True)
        detail_top.addWidget(self.auto_content_check)

        self.open_link_btn = QPushButton("🔗 打开链接")
        self.open_link_btn.clicked.connect(self.open_selected_link)
        self.open_link_btn.setEnabled(False)
        detail_top.addWidget(self.open_link_btn)

        self.fetch_context_btn = QPushButton("📥 抓取内容")
        self.fetch_context_btn.clicked.connect(lambda: self.fetch_selected_context(silent=False))
        detail_top.addWidget(self.fetch_context_btn)

        detail_layout.addLayout(detail_top)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMinimumHeight(160)
        self.detail_text.setStyleSheet(
            "QTextEdit { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px; color: #111827; }"
        )
        self.detail_text.setText("在榜单中选择一条热点后，可抓取该热点的相关摘要（来自百度移动搜索）。")
        detail_layout.addWidget(self.detail_text)

        layout.addWidget(detail)

    def _create_source_tab(self, source_id: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(["排名", "标题", "热度", "链接"])
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.cellDoubleClicked.connect(self._open_link_from_cell)

        table.setColumnWidth(0, 60)
        table.setColumnWidth(1, 520)
        table.setColumnWidth(2, 120)
        table.itemSelectionChanged.connect(self._on_table_selection_changed)

        self._tables[source_id] = table
        layout.addWidget(table)
        return widget

    def _load_cached(self):
        cached = hotspot_service.load_cache()
        data = (cached or {}).get("data") if isinstance(cached, dict) else {}
        if not isinstance(data, dict):
            return
        for sid in hotspot_service.available_sources().keys():
            raw_items = data.get(sid) or []
            items: List[HotspotItem] = []
            for it in raw_items:
                if not isinstance(it, dict):
                    continue
                items.append(
                    HotspotItem(
                        source=sid,
                        rank=int(it.get("rank") or 0),
                        title=str(it.get("title") or ""),
                        hot=int(it.get("hot")) if str(it.get("hot") or "").isdigit() else None,
                        url=str(it.get("url") or ""),
                    )
                )
            if items:
                self._last_payload[sid] = items
                self._fill_table(sid, items)

    def _apply_auto_refresh_from_config(self):
        try:
            cfg_obj = Config()
            cfg = cfg_obj.config.get("data_center", {}) if isinstance(getattr(cfg_obj, "config", None), dict) else {}
            auto = bool((cfg or {}).get("auto_refresh", True))
            interval = int((cfg or {}).get("interval_minutes", 10) or 10)
        except Exception:
            auto = True
            interval = 10

        self.auto_check.blockSignals(True)
        self.interval_spin.blockSignals(True)
        self.auto_check.setChecked(auto)
        self.interval_spin.setValue(max(1, min(120, interval)))
        self.auto_check.blockSignals(False)
        self.interval_spin.blockSignals(False)

        self._reset_timer()

    def _save_auto_refresh_to_config(self):
        try:
            cfg_obj = Config()
            data_center = cfg_obj.config.get("data_center", {}) if hasattr(cfg_obj, "config") else {}
            if not isinstance(data_center, dict):
                data_center = {}
            data_center["auto_refresh"] = bool(self.auto_check.isChecked())
            data_center["interval_minutes"] = int(self.interval_spin.value())
            cfg_obj.config["data_center"] = data_center
            cfg_obj.save_config()
        except Exception:
            pass

    def _reset_timer(self):
        self._auto_timer.stop()
        if self.auto_check.isChecked():
            interval_ms = int(self.interval_spin.value()) * 60 * 1000
            self._auto_timer.start(max(60_000, interval_ms))

    def _on_auto_changed(self, _state: int):
        self._save_auto_refresh_to_config()
        self._reset_timer()

    def _on_interval_changed(self, _value: int):
        self._save_auto_refresh_to_config()
        self._reset_timer()

    def _auto_refresh_tick(self):
        self.refresh(silent=True)

    def refresh(self, silent: bool = False):
        if self._thread and self._thread.isRunning():
            return

        self._silent_refresh = bool(silent)

        selected = self.source_combo.currentData()
        if selected == "__all__":
            sources = list(hotspot_service.available_sources().keys())
        else:
            sources = [str(selected)] if selected else list(hotspot_service.available_sources().keys())

        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("⏳ 刷新中...")

        self._thread = HotspotFetchThread(sources=sources, limit=int(self.limit_spin.value()))
        self._thread.finished.connect(self._on_fetched)
        self._thread.error.connect(self._on_fetch_error)
        self._thread.start()

    def _on_fetch_error(self, msg: str):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 刷新")
        if self._silent_refresh:
            self.last_label.setText(f"采集失败：{msg[:60]}")
            return
        QMessageBox.warning(self, "提示", f"采集失败：{msg}")

    def _on_fetched(self, payload: dict):
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 刷新")

        now = int(time.time())
        self.last_label.setText(f"上次更新：{time.strftime('%H:%M:%S', time.localtime(now))}")

        errors: List[str] = []
        cache_out: Dict[str, list] = {}
        for sid in hotspot_service.available_sources().keys():
            if sid in payload and isinstance(payload.get(sid), list):
                items = payload.get(sid) or []
                err_items = payload.get(f"{sid}__error") or []
                if not items and err_items and isinstance(err_items, list):
                    msg = str(getattr(err_items[0], "title", "") or "")
                    if msg:
                        errors.append(f"{hotspot_service.available_sources().get(sid, sid)}：{msg}")
                self._last_payload[sid] = items
                self._fill_table(sid, items)
                cache_out[sid] = [
                    {"rank": x.rank, "title": x.title, "hot": x.hot, "url": x.url}
                    for x in items
                    if isinstance(x, HotspotItem)
                ]
            else:
                # 未刷新到的来源保留旧数据（避免全清）
                old = self._last_payload.get(sid) or []
                cache_out[sid] = [{"rank": x.rank, "title": x.title, "hot": x.hot, "url": x.url} for x in old]

        hotspot_service.save_cache(cache_out)
        if self._silent_refresh:
            return

        if errors:
            QMessageBox.warning(self, "部分采集失败", "\n".join(errors[:8]))
            return
        TipWindow(self.parent, "✅ 热点已更新").show()

    def _fill_table(self, source_id: str, items: List[HotspotItem]):
        table = self._tables.get(source_id)
        if not table:
            return
        table.setRowCount(0)
        for it in items:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(str(it.rank)))
            title_item = QTableWidgetItem(it.title)
            title_item.setData(Qt.UserRole, it)
            table.setItem(row, 1, title_item)
            table.setItem(row, 2, QTableWidgetItem(str(it.hot) if it.hot is not None else "—"))
            link_item = QTableWidgetItem(it.url or "")
            link_item.setForeground(Qt.blue)
            table.setItem(row, 3, link_item)

        if items and table.currentRow() < 0:
            table.setCurrentCell(0, 1)

    def _open_link_from_cell(self, row: int, _col: int):
        sid = self._current_source_id()
        table = self._tables.get(sid)
        if not table:
            return
        url = table.item(row, 3).text() if table.item(row, 3) else ""
        if not url:
            return
        QDesktopServices.openUrl(QUrl(url))

    def _on_table_selection_changed(self):
        self._sync_selected_hotspot()

    def _sync_selected_hotspot(self):
        sid = self._current_source_id()
        table = self._tables.get(sid)
        if not table:
            return

        row = table.currentRow()
        if row < 0:
            self._selected_hotspot = None
            self.detail_title.setText("🧾 热点内容：未选择")
            self.open_link_btn.setEnabled(False)
            self.detail_text.setText("在榜单中选择一条热点后，可抓取该热点的相关摘要（来自百度移动搜索）。")
            return

        title_item = table.item(row, 1)
        data = title_item.data(Qt.UserRole) if title_item else None
        if isinstance(data, HotspotItem):
            self._selected_hotspot = data
        else:
            title = title_item.text().strip() if title_item else ""
            url_item = table.item(row, 3)
            url = url_item.text().strip() if url_item else ""
            self._selected_hotspot = HotspotItem(source=sid, rank=row + 1, title=title, hot=None, url=url)

        display = (self._selected_hotspot.title or "").strip()
        if len(display) > 42:
            display = display[:42] + "…"
        self.detail_title.setText(f"🧾 热点内容：{display or '—'}")
        self.open_link_btn.setEnabled(bool((self._selected_hotspot.url or "").strip()))

        q = (self._selected_hotspot.title or "").strip()
        if q and q in self._context_cache:
            self.detail_text.setText(self._context_cache[q])
        else:
            self.detail_text.setText("已选择热点。点击“抓取内容”获取摘要；或双击表格链接打开原网页。")
            if self.auto_content_check.isChecked():
                self._pending_context_query = q
                self._context_timer.start(400)

    def _maybe_fetch_pending_context(self):
        q = (self._pending_context_query or "").strip()
        if not q:
            return
        if q in self._context_cache:
            return
        self.fetch_selected_context(silent=True)

    def fetch_selected_context(self, silent: bool = False):
        hs = self._selected_hotspot
        if not hs or not (hs.title or "").strip():
            if not silent:
                QMessageBox.information(self, "提示", "请先在榜单中选择一条热点")
            return

        query = (hs.title or "").strip()
        if query in self._context_cache:
            self.detail_text.setText(self._context_cache[query])
            return

        if self._context_thread and self._context_thread.isRunning():
            self._pending_context_query = query
            return

        self._pending_context_query = ""
        self.fetch_context_btn.setEnabled(False)
        self.fetch_context_btn.setText("⏳ 抓取中...")

        self._context_thread = HotspotContextThread(query=query, limit=3)
        self._context_thread.finished.connect(self._on_context_fetched)
        self._context_thread.error.connect(self._on_context_error)
        self._context_thread.start()

    def _on_context_error(self, query: str, msg: str):
        self.fetch_context_btn.setEnabled(True)
        self.fetch_context_btn.setText("📥 抓取内容")
        if self._selected_hotspot and (self._selected_hotspot.title or "").strip() == (query or "").strip():
            self.detail_text.setText(f"抓取失败：{msg}\n\n可尝试：\n- 直接双击链接打开\n- 稍后重试")

    def _on_context_fetched(self, query: str, items: object):
        self.fetch_context_btn.setEnabled(True)
        self.fetch_context_btn.setText("📥 抓取内容")

        parts: List[str] = []
        parts.append("【热点相关内容摘要】")
        parts.append(f"关键词：{query}")
        parts.append("")
        parts.append("来源：百度移动搜索（Top 3）")
        parts.append("")

        if isinstance(items, list) and items:
            for i, it in enumerate(items, start=1):
                if not isinstance(it, dict):
                    continue
                t = str(it.get("title") or "").strip()
                s = str(it.get("snippet") or "").strip()
                u = str(it.get("url") or "").strip()
                if not t:
                    continue
                parts.append(f"{i}. {t}")
                if s:
                    parts.append(f"   {s}")
                if u:
                    parts.append(f"   {u}")
                parts.append("")
        else:
            parts.append("未抓到摘要（可能被限制/关键词过新），建议双击链接查看原网页。")

        text = "\n".join(parts).rstrip() + "\n"
        self._context_cache[query] = text

        if self._selected_hotspot and (self._selected_hotspot.title or "").strip() == (query or "").strip():
            self.detail_text.setText(text)

        # 若用户在抓取过程中又切换了选择，则继续抓取下一条
        if self._pending_context_query:
            self._context_timer.start(300)

    def open_selected_link(self):
        hs = self._selected_hotspot
        if not hs:
            return
        url = (hs.url or "").strip()
        if not url:
            return
        QDesktopServices.openUrl(QUrl(url))

    def _current_source_id(self) -> str:
        idx = self.tabs.currentIndex()
        if idx < 0:
            return list(hotspot_service.available_sources().keys())[0]
        return list(hotspot_service.available_sources().keys())[idx]

    def _get_selected_title(self) -> str:
        sid = self._current_source_id()
        table = self._tables.get(sid)
        if not table:
            return ""
        row = table.currentRow()
        if row < 0:
            return ""
        return table.item(row, 1).text().strip() if table.item(row, 1) else ""

    def use_selected_as_topic(self):
        title = self._get_selected_title()
        if not title:
            QMessageBox.information(self, "提示", "请先在榜单中选择一条热点")
            return

        if not self.parent or not hasattr(self.parent, "home_page"):
            QMessageBox.warning(self, "提示", "未找到首页页面，无法填入主题")
            return

        try:
            home = getattr(self.parent, "home_page", None)
            if home and hasattr(home, "input_text"):
                home.input_text.setPlainText(title)
                TipWindow(self.parent, "✅ 已填入首页主题").show()
                if hasattr(self.parent, "switch_page"):
                    self.parent.switch_page(0)
        except Exception as e:
            QMessageBox.warning(self, "提示", f"填入失败: {e}")
