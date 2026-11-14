# -*- coding: utf-8 -*-
"""系统托盘：点击直接打开手动输入 / 图片识别，另有设置、关于作者、退出。

菜单不含任何勾选开关；功能项点击即执行。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .. import branding


def make_icon(enabled: bool) -> QIcon:
    # 统一使用设计定稿的新 icon（与安装包 / exe / 快捷方式同一真源）；
    # 停用态用 Qt 的 Disabled 渲染出灰版，不再单独手绘一套图形。
    from ..icon import app_icon_path
    path = app_icon_path()
    if path.is_file():
        icon = QIcon(str(path))
        if enabled:
            return icon
        return QIcon(icon.pixmap(64, 64, QIcon.Mode.Disabled))
    # 极端情况（ico 未随包分发）回退到手绘，保证托盘始终可见。
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#c8402f" if enabled else "#a99a96"))
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)
    font = QFont()
    font.setPointSize(30)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "π")
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setIcon(make_icon(True))
        self.setToolTip(f"{branding.APP_NAME} · {branding.OFFLINE_SLOGAN}")

        menu = QMenu()
        # 用户定稿：托盘不再提供「截图监听」勾选开关，也不给功能项加勾选状态。
        # 鼠标点击即直接执行——打开对应窗口 / 直接开始框选，不做任何开关切换。
        act_w3 = QAction(f"手动输入翻译（{controller.store.settings.hotkey_w3}）", menu)
        act_w3.triggered.connect(controller.open_w3)
        menu.addAction(act_w3)

        act_capture = QAction(f"图片识别翻译（{controller.store.settings.hotkey_ocr}）", menu)
        act_capture.triggered.connect(controller.start_ocr_capture)
        menu.addAction(act_capture)
        menu.addSeparator()
        act_settings = QAction("设置", menu)
        act_settings.triggered.connect(controller.open_settings)
        menu.addAction(act_settings)
        act_about = QAction("关于", menu)
        act_about.triggered.connect(controller.show_about)
        menu.addAction(act_about)
        menu.addSeparator()
        act_quit = QAction("退出", menu)
        act_quit.triggered.connect(controller.quit_app)
        menu.addAction(act_quit)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)
        self.refresh()

    def refresh(self) -> None:
        # 菜单已无固定勾选状态；图标与提示保持常态，不再表达「开 / 关」。
        self.setIcon(make_icon(True))
        self.setToolTip(f"{branding.APP_NAME} · {branding.OFFLINE_SLOGAN}\n"
                        f"{branding.AUTHOR_CONTACT}")

    def notify(self, title: str, message: str) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable() and self.isVisible():
            self.showMessage(title, message, QSystemTrayIcon.Information, 2200)

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self.controller.toggle_w3()
