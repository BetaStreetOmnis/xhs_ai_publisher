"""Widget checks run separately from legacy QCoreApplication-only tests."""
import os
import subprocess
import sys
from pathlib import Path


_WIDGET_CHECK = r"""import os, tempfile
os.environ["XHS_DATA_DIR"] = tempfile.mkdtemp(prefix="xhs-ui-test-")
os.environ["XHS_APP_DATA_DIR"] = os.environ["XHS_DATA_DIR"]
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt5.QtWidgets import QApplication
application = QApplication([])

def test_review_dialog_requires_facts_rights_and_ai_disclosure():
    from src.core.pages.publication_review_dialog import PublicationReviewDialog
    dialog = PublicationReviewDialog()
    assert not dialog.continue_button.isEnabled()
    dialog.facts_check.setChecked(True)
    dialog.rights_check.setChecked(True)
    dialog.ai_usage.setCurrentIndex(2)
    assert not dialog.continue_button.isEnabled()
    dialog.accept()
    assert dialog.result() == 0
    dialog.disclosure_check.setChecked(True)
    assert dialog.continue_button.isEnabled()
    dialog.accept()
    assert dialog.result() == dialog.Accepted
    dialog.close()


def test_task_dialog_accepts_reminder_without_any_account():
    from src.core.pages.scheduled_publish_dialog import ScheduledPublishDialog
    dialog = ScheduledPublishDialog(users=[], initial_content="本人核实后的内容")
    assert dialog.get_user_id() is None
    assert dialog.get_interval_hours() == 0
    assert "提醒" in dialog.mode_combo.currentText()
    dialog.accept()
    assert dialog.result() == dialog.Accepted
    dialog.mode_combo.setCurrentIndex(1)
    assert "草稿" in dialog.mode_combo.currentText()
    assert dialog.get_interval_hours() == 0
    dialog.close()

test_review_dialog_requires_facts_rights_and_ai_disclosure()
test_task_dialog_accepts_reminder_without_any_account()
from src.core.pages.home import HomePage
from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPushButton
from PyQt5.QtGui import QPixmap
from types import SimpleNamespace
from pathlib import Path
image = Path(os.environ["XHS_DATA_DIR"]) / "draft.png"
pixmap = QPixmap(50, 50)
pixmap.fill()
assert pixmap.save(str(image))
button = QPushButton()
editor = SimpleNamespace(title_input=QLineEdit(), subtitle_input=QTextEdit(), images=[],
                         show_current_image=lambda: None, findChild=lambda *args: button)
task = SimpleNamespace(title="待核实标题", content="草稿正文", images=[str(image)])
assert HomePage.load_local_draft(editor, task)
assert editor.title_input.text() == task.title
assert editor.subtitle_input.toPlainText() == task.content
assert editor.images == task.images
assert button.isEnabled()
import shutil
shutil.rmtree(os.environ["XHS_DATA_DIR"])
"""


def test_publication_widgets_and_saved_draft_loading():
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [sys.executable, "-c", _WIDGET_CHECK], cwd=Path(__file__).resolve().parents[2],
        env=environment, timeout=30, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
