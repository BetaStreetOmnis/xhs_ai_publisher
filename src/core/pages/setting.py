import sys

from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.config.constants import VERSION


class SettingsPage(QWidget):
    """设置页面类"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setObjectName("settingsPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # 添加版本信息
        version_label = QLabel(f"版本号: v{VERSION}")
        version_label.setStyleSheet("""
            font-family: """ + ("Menlo" if sys.platform == "darwin" else "Consolas") + """;
            font-size: 14pt;
            color: #2c3e50;
            font-weight: bold;
            border:none;
        """)
        layout.addWidget(version_label)
        layout.addStretch()
