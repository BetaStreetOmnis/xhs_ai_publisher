import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel,  QPushButton, QFrame,
                             QProgressBar, QGraphicsView, QGraphicsScene,
                             QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush
from PyQt5.QtCore import QEvent


class LoadingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 创建遮罩层
        self.mask = QGraphicsView(parent)
        self.mask.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.mask.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.mask.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mask.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mask.setStyleSheet("background: transparent;")
        self.mask.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.mask.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 创建场景
        self.scene = QGraphicsScene()
        self.mask.setScene(self.scene)
        # 创建半透明遮罩矩形
        self.rect_item = self.scene.addRect(0, 0, parent.width(), parent.height(),
                                            QPen(Qt.PenStyle.NoPen),
                                            # 128 = 0.5 * 255
                                            QBrush(QColor(0, 0, 0, 128)))
        self.mask.setGeometry(parent.geometry())
        self.mask.show()
        self.mask.raise_()

        # 设置遮罩层事件过滤器，阻止所有鼠标事件
        self.mask.installEventFilter(self)

        # 连接主窗口的 resize 事件
        if parent:
            parent.resizeEvent = lambda e: self.update_mask_geometry()

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(248, 249, 250, 0.95);
                border-radius: 10px;
                border: 1px solid #ddd;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #2c3e50;
            }
            QProgressBar {
                border: none;
                background-color: #e9ecef;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
                border-radius: 5px;
            }
        """)

        # 设置固定大小
        self.setFixedSize(300, 150)

        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 加载提示文字
        loading_label = QLabel("✨ 正在生成内容...", self)
        loading_label.setStyleSheet(f"""
            font-family: {("Menlo" if sys.platform == "darwin" else "Consolas")};
            font-size: 14pt;
            font-weight: bold;
            color: #2c3e50;
        """)
        loading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(loading_label)

        # 进度条
        self.progress = QProgressBar(self)
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.progress.setStyleSheet("""
            QProgressBar {
                min-height: 8px;
                max-height: 8px;
            }
        """)
        layout.addWidget(self.progress)

        # 提示文字
        tip_label = QLabel("奋力生成中", self)
        tip_label.setStyleSheet(f"""
            font-family: {("Menlo" if sys.platform == "darwin" else "Consolas")};
            font-size: 12pt;
            color: #666;
        """)
        tip_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip_label)

        # 设置初始透明度
        self.setWindowOpacity(0)

        # 淡入动画
        self.animation = QTimer()
        self.animation.timeout.connect(self._fade_step)
        self.opacity = 0.0

    def eventFilter(self, obj, event):
        # 阻止遮罩层的所有鼠标事件
        if obj == self.mask and event.type() in [
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.MouseMove
        ]:
            return True
        return super().eventFilter(obj, event)

    def update_mask_geometry(self):
        if self.parent():
            # 获取主窗口的几何信息
            parent_rect = self.parent().geometry()
            # 更新遮罩层大小和位置
            self.mask.setGeometry(
                0, 0, parent_rect.width(), parent_rect.height())
            # 更新场景大小
            self.scene.setSceneRect(
                0, 0, parent_rect.width(), parent_rect.height())
            # 更新矩形大小
            self.rect_item.setRect(
                0, 0, parent_rect.width(), parent_rect.height())
            self.mask.raise_()
            self.mask.show()

            # 更新加载窗口位置
            x = (parent_rect.width() - self.width()) // 2
            y = (parent_rect.height() - self.height()) // 2
            self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            # 更新遮罩层大小和位置
            self.update_mask_geometry()
            # 确保遮罩层和加载窗口在最上层
            self.mask.raise_()
            self.raise_()
            # 开始淡入动画
            self.animation.start(30)

    def closeEvent(self, event):
        # 关闭遮罩层
        if hasattr(self, 'mask'):
            self.mask.close()
        super().closeEvent(event)

    def _fade_step(self):
        if self.opacity >= 1.0:
            self.animation.stop()
            return
        self.opacity += 0.1
        self.setWindowOpacity(self.opacity)


class TipWindow(QWidget):
    def __init__(self, parent=None, message="", duration=2000):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 创建消息框
        self.msg_frame = QFrame()
        self.msg_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid rgba(0, 0, 0, 0.1);
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        self.msg_frame.setGraphicsEffect(shadow)

        # 消息框布局
        msg_layout = QHBoxLayout(self.msg_frame)
        msg_layout.setContentsMargins(16, 16, 16, 16)
        msg_layout.setSpacing(12)

        # 设置图标和颜色
        if "❌" in message:
            icon = "⚠️"
            color = "#E6A23C"  # 警告色
            text_color = "#606266"  # 文字颜色
            title = "警告"
        elif "✅" in message:
            icon = "✅"
            color = "#67C23A"  # 成功色
            text_color = "#606266"
            title = "成功"
        elif "错误" in message:
            icon = "❌"
            color = "#F56C6C"  # 错误色
            text_color = "#606266"
            title = "错误"
        else:
            icon = "ℹ️"
            color = "#909399"  # 信息色
            text_color = "#606266"
            title = "消息"

        # 清理消息文本
        message = message.replace("❌", "").replace("✅", "").strip()

        # 创建图标标签
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            font-size: 20px;
            color: {color};
            padding: 0;
            margin: 0;
        """)
        msg_layout.addWidget(icon_label)

        # 创建文字容器
        text_container = QVBoxLayout()
        text_container.setSpacing(4)

        # 创建标题标签
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 500;
            color: {color};
            padding: 0;
            margin: 0;
        """)
        text_container.addWidget(title_label)

        # 创建消息标签
        msg_label = QLabel(message)
        msg_label.setStyleSheet(f"""
            font-size: 14px;
            color: {text_color};
            padding: 0;
            margin: 0;
        """)
        msg_label.setWordWrap(True)
        text_container.addWidget(msg_label)

        # 将文字容器添加到主布局
        msg_layout.addLayout(text_container, 1)

        # 创建关闭按钮
        close_btn = QPushButton("×")
        close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                font-size: 18px;
                color: #909399;
                background: transparent;
                padding: 0;
                margin: 0;
            }
            QPushButton:hover {
                color: #606266;
            }
        """)
        close_btn.clicked.connect(self.close)
        msg_layout.addWidget(close_btn)

        # 将消息框添加到主布局
        layout.addWidget(self.msg_frame)

        # 设置固定宽度和调整大小
        self.setFixedWidth(380)
        self.adjustSize()

        # 设置动画效果
        self.setWindowOpacity(0)

        # 设置定时器
        self.fade_in_timer = QTimer(self)
        self.fade_in_timer.timeout.connect(self.fade_in_step)
        self.fade_in_timer.start(20)

        self.fade_out_timer = QTimer(self)
        self.fade_out_timer.timeout.connect(self.fade_out_step)
        QTimer.singleShot(duration, self.fade_out_timer.start)

        self.opacity = 0.0

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            parent_size = self.parent().size()
            x = (parent_size.width() - self.width()) // 2
            y = 30
            self.move(x, y)

    def fade_in_step(self):
        if self.opacity >= 1.0:
            self.fade_in_timer.stop()
            return
        self.opacity += 0.1
        self.setWindowOpacity(self.opacity)

    def fade_out_step(self):
        if self.opacity <= 0.0:
            self.fade_out_timer.stop()
            self.close()
            return
        self.opacity -= 0.1
        self.setWindowOpacity(self.opacity)
