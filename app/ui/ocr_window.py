# -*- coding: utf-8 -*-
"""OCR 图片翻译窗 + 屏幕框选遮罩。

作者联系方式 · 微信号：TheSun_Also_Rises

位图只在内存中传递（QPixmap → PNG bytes → numpy），不落盘、不上传。
"""
from __future__ import annotations

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QMouseEvent, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout,
)

from .. import branding
from .widgets import FramelessWindow, Hint, set_cls


class ScreenCaptureDialog(QDialog):
    """半透明全屏遮罩，拖动框选屏幕区域；Esc 取消。"""

    captured = Signal(bytes, QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)
        geo = QApplication.primaryScreen().geometry()
        self.setGeometry(geo)
        self._origin = QPoint()
        self._current = QPoint()
        self._selecting = False
        QShortcut(QKeySequence(Qt.Key_Escape), self).activated.connect(self.reject)

    @staticmethod
    def normalized(a: QPoint, b: QPoint) -> QRect:
        return QRect(min(a.x(), b.x()), min(a.y(), b.y()),
                     abs(a.x() - b.x()), abs(a.y() - b.y()))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(20, 35, 60, 95))
        if self._selecting:
            rect = self.normalized(self._origin, self._current)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(QColor(37, 99, 235))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(rect)
            # 四角控制点：提示用户边界可继续拖动调整
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#ffffff"))
            for cx, cy in ((rect.left(), rect.top()), (rect.right(), rect.top()),
                           (rect.left(), rect.bottom()), (rect.right(), rect.bottom())):
                painter.drawRect(QRect(cx - 3, cy - 3, 7, 7))
            # 选区尺寸标签（贴右上角内侧，超出屏幕则回落到左下）
            self._draw_badge(painter, f"{rect.width()} × {rect.height()}",
                             rect.right() - 8, rect.top() + 8, anchor_right=True)
        else:
            # 未框选时给出操作提示，避免用户不知道下一步该做什么
            self._draw_badge(painter, "拖动鼠标框选要识别的区域　·　Esc 取消",
                             self.width() // 2, 72, center=True)
        painter.end()

    def _draw_badge(self, painter: QPainter, text: str, x: int, y: int,
                    center: bool = False, anchor_right: bool = False) -> None:
        """画一枚深色圆角提示条（尺寸标签 / 操作提示共用）。"""
        fm = painter.fontMetrics()
        w = fm.horizontalAdvance(text) + 24
        h = fm.height() + 14
        if center:
            box = QRect(x - w // 2, y, w, h)
        elif anchor_right:
            box = QRect(x - w, y, w, h)
        else:
            box = QRect(x, y, w, h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(24, 20, 18, 225))
        painter.drawRoundedRect(box, 9, 9)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(box, Qt.AlignCenter, text)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.LeftButton:
            self._origin = event.position().toPoint()
            self._current = self._origin
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._selecting:
            self._current = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if not self._selecting:
            return
        self._selecting = False
        rect = self.normalized(self._origin, event.position().toPoint())
        self.hide()
        if rect.width() < 8 or rect.height() < 8:
            self.reject()
            return
        screen = QApplication.primaryScreen()
        pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        self.captured.emit(bytes(buffer.data().data()), rect)
        self.accept()


class OCRWindow(FramelessWindow):
    """识别原文 ↔ 中文译文左右两栏对照，保留原文供人工核对。"""

    def __init__(self, controller):
        super().__init__("图片识别翻译", "badge-teal",
                         on_top=controller.store.settings.ocr_window_always_on_top,
                         resizable=True, min_size=(480, 420))
        self.controller = controller
        self.set_corner_subtitle("截图框选")
        # 用户定稿：与手动输入翻译窗采用同一套「置顶常驻」策略（可切换、可记忆），
        # 另加「设置」直接打开设置页；「选择新的截图区域」按钮继续保留。
        self.pin_btn = self.titlebar.add_action("📌", "置顶常驻", True, "pin")
        self.pin_btn.setChecked(controller.store.settings.ocr_window_always_on_top)
        self.pin_btn.clicked.connect(self._on_pin_clicked)
        # 用户定稿：翻译窗右上角不再保留「设置」按钮（设置仍可从托盘菜单进入）。
        self.titlebar.add_action("◎", "选择新的截图区域", False, "icon",
                                 self.controller.start_ocr_capture)
        self.titlebar.add_action("✕", "关闭", False, "icon", self.hide)

        head = QHBoxLayout()
        note = Hint(f"{branding.OCR_ENGINE} · 位图仅存内存，不落盘、不上传", "teal")
        head.addWidget(note, 1)
        self.body_layout.addLayout(head)

        self.thumb = QLabel("框选区域预览")
        self.thumb.setFixedHeight(88)
        self.thumb.setAlignment(Qt.AlignCenter)
        set_cls(self.thumb, "sub")
        self.thumb.setStyleSheet("font-size:11px;border:1px dashed #d9b6ae;"
                                 "border-radius:8px;background:#fff8f6")
        self.body_layout.addWidget(self.thumb)

        cols = QHBoxLayout()
        self.src_view = QPlainTextEdit()
        self.src_view.setReadOnly(True)
        self.src_view.setPlaceholderText("识别到的原文（按行）")
        self.dst_view = QPlainTextEdit()
        self.dst_view.setReadOnly(True)
        set_cls(self.dst_view, "output")
        self.dst_view.setPlaceholderText("中文译文")
        left = QVBoxLayout()
        lbl_l = QLabel("识别原文（RapidOCR）")
        set_cls(lbl_l, "lang")
        left.addWidget(lbl_l)
        left.addWidget(self.src_view, 1)
        right = QVBoxLayout()
        lbl_r = QLabel("中文译文（Hy-MT2）")
        set_cls(lbl_r, "lang")
        right.addWidget(lbl_r)
        right.addWidget(self.dst_view, 1)
        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        self.body_layout.addLayout(cols, 1)

        # 与手动输入窗调用同一个 helper：底栏结构、提示样式、按钮外观与反馈状态完全一致。
        self.status_hint, self.copy_btn = self.add_footer_status_and_copy(
            "本地离线 · 识别结果可复制", self._copy_translation)

    def set_thumbnail(self, data: bytes) -> None:
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.thumb.setPixmap(pixmap.scaled(self.thumb.width() - 10, 78,
                                               Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.thumb.setText("")
        else:
            self.thumb.setText("框选区域预览（位图仅存内存）")

    def set_result(self, recognized: str, translated: str, message: str = "") -> None:
        self.src_view.setPlainText(recognized)
        # 出错时把提示完整显示在译文大区，并以品牌朱红错误样式突出，而不是只缩在底部。
        is_error = bool(message) and any(k in message for k in
                                        ("失败", "错误", "未", "Error", "error"))
        if is_error:
            self.dst_view.setPlainText(message)
            set_cls(self.dst_view, "error")
        else:
            self.dst_view.setPlainText(translated)
            set_cls(self.dst_view, "output")
        # 底栏提示保持短文案：过长会挤压右侧「复制译文」按钮，破坏两窗一致性。
        brief = message or "识别与翻译完成 · 本地离线"
        self.status_hint.set_text(brief if len(brief) <= 28 else brief[:27] + "…")

    def _on_pin_clicked(self, _checked: bool = False) -> None:
        """与手动输入翻译窗一致：图钉切换 TOPMOST 并写入配置，下次打开仍生效。"""
        enabled = self.pin_btn.isChecked()
        self.set_on_top(enabled)
        self.controller.store.update(ocr_window_always_on_top=enabled)
        self.controller.notify("窗口已置顶" if enabled else "已取消置顶")

    def _copy_translation(self, _checked: bool = False) -> None:
        text = self.dst_view.toPlainText()
        if text.strip():
            self.controller.copy_to_clipboard(text)
