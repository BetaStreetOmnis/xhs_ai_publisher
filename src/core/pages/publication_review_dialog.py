"""Human review before filling a third-party publication form."""
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout,
)

from src.core.services.publication_policy import PUBLICATION_REVIEW_NOTICE


class PublicationReviewDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("填写前核对")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        notice = QLabel(PUBLICATION_REVIEW_NOTICE)
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.facts_check = QCheckBox("已核对事实和亲身经历，没有编造亲测、数据或引语")
        self.rights_check = QCheckBox("文字、照片和其他素材为本人所有，或已获授权")
        self.ai_usage = QComboBox()
        self.ai_usage.addItem("请选择内容是否使用了 AI", "unspecified")
        self.ai_usage.addItem("未使用 AI", "none")
        self.ai_usage.addItem("使用了 AI 生成或润色", "assisted")
        self.disclosure_check = QCheckBox("将在小红书发布页按平台要求如实声明 AI 使用情况")
        for widget in (self.facts_check, self.rights_check, self.ai_usage, self.disclosure_check):
            layout.addWidget(widget)
        note = QLabel("下一步只填写发布页。请再次检查目标账号和页面内容，最终发布由你手动完成。")
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.rejected.connect(self.reject)
        self.continue_button = buttons.addButton("继续填写发布页", QDialogButtonBox.AcceptRole)
        self.continue_button.clicked.connect(self.accept)
        layout.addWidget(buttons)
        for check in (self.facts_check, self.rights_check, self.disclosure_check):
            check.toggled.connect(self._update_state)
        self.ai_usage.currentIndexChanged.connect(self._update_state)
        self._update_state()

    def _update_state(self, *_args):
        assisted = self.ai_usage.currentData() == "assisted"
        self.disclosure_check.setVisible(assisted)
        self.continue_button.setEnabled(
            self.facts_check.isChecked() and self.rights_check.isChecked()
            and self.ai_usage.currentData() != "unspecified"
            and (not assisted or self.disclosure_check.isChecked())
        )

    def accept(self):
        if self.continue_button.isEnabled():
            super().accept()
