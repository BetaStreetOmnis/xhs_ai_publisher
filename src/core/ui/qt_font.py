from __future__ import annotations

import sys
from typing import Optional

from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QApplication

_cached_ui_font_family: Optional[str] = None


def _candidates() -> list[str]:
    if sys.platform == "win32":
        return [
            "Microsoft YaHei UI",
            "Microsoft YaHei",
            "Segoe UI",
            "Arial",
        ]
    if sys.platform == "darwin":
        return [
            "PingFang SC",
            "Hiragino Sans GB",
            "Heiti SC",
            "Helvetica Neue",
            "Arial",
        ]
    return [
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
        "DejaVu Sans",
        "Arial",
    ]


def get_ui_font_family() -> str:
    """Return a best-effort font family that exists on current OS."""
    global _cached_ui_font_family
    if _cached_ui_font_family:
        return _cached_ui_font_family

    # Avoid caching before QApplication is created.
    if QApplication.instance() is None:
        return QFont().defaultFamily()

    try:
        available = set(QFontDatabase().families())
        for family in _candidates():
            if family in available:
                _cached_ui_font_family = family
                return family
    except Exception:
        pass

    _cached_ui_font_family = QFont().defaultFamily()
    return _cached_ui_font_family


def ui_font(point_size: int = 12, weight: int = -1, italic: bool = False) -> QFont:
    """Convenience helper for a consistent UI font."""
    return QFont(get_ui_font_family(), point_size, weight, italic)
