# -*- coding: utf-8 -*-
"""原生窗口通用组件：无边框、可拖动、置顶、圆角阴影、标题栏按钮。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QRect, QRectF, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QMouseEvent, QPainter, QPainterPath, QRegion
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QSizeGrip,
    QSizePolicy, QVBoxLayout, QWidget,
)

from .. import branding
from ..icon import app_icon_path
from ..win_topmost import apply_topmost as _win_apply_topmost
from .theme import (BRAND_RED, FONT_BODY_PX, FONT_CONTROL_PX,
                    FONT_SUBTITLE_PX, FONT_TITLE_PX, palette)


def set_cls(widget: QWidget, value: str) -> None:
    """设置 Qt 动态属性后重新 polish，保证 QSS 属性选择器立即生效。"""
    widget.setProperty("cls", value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def brand_red() -> str:
    return BRAND_RED


class CornerTag(QWidget):
    """左上角品牌标签：朱红半角圆角矩形，只显示右边 + 底边（左上被窗体圆角裁掉）。

    —— 与 UI 重设计预览（ui_redesign.html）一致：色块只比文字略大，承载窗体名与一句副标题。
    父窗口 root 做了圆角 mask，本标签以负偏移贴住左上角，于是它的左上角被窗体圆角裁掉，
    视觉上只剩右边与底边的圆角，呈「折角标签」效果。
    """

    def __init__(self, title: str, subtitle: str = "", fold_corner: bool = True,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("cornerTag")
        # 普通 QWidget 默认不绘制样式表背景，必须开启 WA_StyledBackground 才能画出朱红底。
        self.setAttribute(Qt.WA_StyledBackground, True)
        # 纯文字标签位于标题栏左上角；让鼠标事件穿透到下方 TitleBar，
        # 否则用户按住左上角拖动时窗口不会移动。
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._title = title
        self._subtitle = subtitle
        self._fold = fold_corner
        self._build()

    def _build(self) -> None:
        # 严格复刻 ui_layout_draft_v0.2.html 的折角标签：
        #   .tag{top:-14px;left:-14px;border-radius:16px}
        #   .win{overflow:hidden;border-radius:14px}
        # 标签左上角被父窗圆角「圆弧」裁掉，视觉上只保留右边 + 底边。
        # Qt 没有 overflow:hidden 的圆角裁剪，故在 paintEvent 里直接画交集形状：
        # 标签圆角矩形 减去 {左上 28x28 方块内、以(28,28)为圆心 r=14 的圆以外部分}。
        # 文字按等效位置摆放（CSS padding 24/18 减去 14 偏移 -> 10/4）。
        # 用户定稿：左上角不使用任何装饰性底色，只保留核心汉字名称；
        # 注释词统一为灰色小字解释说明。
        self.setStyleSheet("background:transparent")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 8, 12, 2)
        lay.setSpacing(2)
        self._t = QLabel(self._title)
        self._t.setStyleSheet(f"color:#241a18;font-weight:700;font-size:{FONT_TITLE_PX}px;background:transparent")
        self._s = QLabel(self._subtitle)
        self._s.setStyleSheet(f"color:#6b5d59;font-size:{FONT_SUBTITLE_PX}px;background:transparent")
        lay.addWidget(self._t)
        lay.addWidget(self._s)
        self._sync_size()

    # 不重写 paintEvent：不再绘制朱红折角色块 / 圆角背景，保持纯文字。

    def _sync_size(self) -> None:
        # 纯文字标签：宽度随核心名称自适应，副标题过长时也不会撑破窗口。
        tw = self._t.fontMetrics().horizontalAdvance(self._title)
        sw = self._s.fontMetrics().horizontalAdvance(self._subtitle)
        self.setFixedSize(min(max(tw, sw) + 32, 210), 42)

    def set_subtitle(self, text: str) -> None:
        self._subtitle = text
        self._s.setText(text)
        # 副标题变化后重新量宽，避免「已置顶 · 常显」被截断。
        self._sync_size()


class AuthorSignature(QWidget):
    """作者签名：与普通提示同级（灰字），可点击复制微信号，附低调的「点击复制」。

    去掉了粗体、色块与独立「复制微信号」按钮——签名回到提示文字级别，不再抢眼；
    点击整行即复制，无需任何单独按钮。
    """

    def __init__(self, copy_callback: Callable[[], None] | None = None,
                 compact: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._copy = copy_callback
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("authorSignature")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        if compact:
            # 窄窗底栏（手动输入翻译窗）只保留微信号，避免与右侧主按钮争宽度被硬裁。
            text = f"{branding.AUTHOR_CONTACT_TYPE}：{branding.AUTHOR_WECHAT}"
        else:
            text = f"{branding.AUTHOR_LABEL} · {branding.AUTHOR_CONTACT_TYPE}：{branding.AUTHOR_WECHAT}"
        self._full = text
        self._label = QLabel(text)
        self._label.setStyleSheet(f"color:#6b5d59;font-size:{FONT_CONTROL_PX}px;background:transparent")
        self._ck = QLabel("· 点击复制")
        self._ck.setStyleSheet(f"color:#bcaea9;font-size:{FONT_SUBTITLE_PX}px;background:transparent")
        lay.addWidget(self._label)
        lay.addWidget(self._ck)
        self.setToolTip(f"{text} · 点击复制")

    def set_copy_callback(self, cb: Callable[[], None]) -> None:
        self._copy = cb

    def text(self) -> str:
        return self._full

    def mousePressEvent(self, _event) -> None:
        if self._copy is not None:
            self._copy()


class Hint(QWidget):
    """统一的提示词风格：红点（或金 / 青点）+ 灰字。与 ui_redesign.html 的 .hint 一致。"""

    _DOT = {"default": BRAND_RED, "gold": "#b9760f", "teal": "#0f9b8e"}

    def __init__(self, text: str, variant: str = "default", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("hintWidget")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        dot = QLabel()
        dot.setFixedSize(6, 6)
        color = self._DOT.get(variant, BRAND_RED)
        dot.setStyleSheet(f"background:{color};border-radius:3px")
        self._label = QLabel(text)
        self._label.setStyleSheet(
            f"color:{color if variant != 'default' else '#6b5d59'};font-size:{FONT_CONTROL_PX}px;background:transparent")
        lay.addWidget(dot)
        lay.addWidget(self._label)

    def set_text(self, text: str) -> None:
        self._label.setText(text)

    def text(self) -> str:
        return self._label.text()


class IconButton(QPushButton):
    def __init__(self, text: str, tooltip: str = "", checkable: bool = False,
                 cls: str = "icon", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setToolTip(tooltip)
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        set_cls(self, cls)
        self.setFocusPolicy(Qt.NoFocus)


class ToggleSwitch(QWidget):
    """原型同款开关：38×21 圆角轨道 + 白色圆钮，开启时轨道变蓝、圆钮右移。

    用法与 QCheckBox 一致：``setChecked / isChecked / toggled``。
    """

    toggled = Signal(bool)

    def __init__(self, text: str = "", checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._checked = bool(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setFixedHeight(21)
        # 不被布局拉伸：否则轨道与文字之间会出现大段空白（窄窗工具栏里尤其明显）。
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(9)

        self._track = QLabel(self)
        self._track.setFixedSize(38, 21)
        self._track.setStyleSheet(self._track_style())
        lay.addWidget(self._track)

        self._thumb = QLabel(self._track)
        self._thumb.setGeometry(2, 2, 17, 17)
        self._thumb.setStyleSheet("border-radius:9px;background:#ffffff")

        if text:
            self._label = QLabel(text, self)
            self._label.setStyleSheet(f"font-size:{FONT_BODY_PX}px")
            lay.addWidget(self._label)

        self._anim = QPropertyAnimation(self._thumb, b"geometry")
        self._anim.setDuration(160)

    def _track_style(self) -> str:
        on = palette()["red"]
        off = "#d8cdc9"
        return f"border-radius:11px;background:{on if self._checked else off}"

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        value = bool(value)
        if value == self._checked:
            return
        self._checked = value
        self._apply(animated=True)
        self.toggled.emit(self._checked)

    def setText(self, text: str) -> None:
        if getattr(self, "_label", None) is not None:
            self._label.setText(text)

    def _apply(self, animated: bool) -> None:
        self._track.setStyleSheet(self._track_style())
        target = QRect(19 if self._checked else 2, 2, 17, 17)
        if animated:
            self._anim.stop()
            self._anim.setStartValue(self._thumb.geometry())
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._thumb.setGeometry(target)

    def mousePressEvent(self, event) -> None:
        self.setChecked(not self._checked)
        super().mousePressEvent(event)


class TitleBar(QWidget):
    """可拖动标题栏（仅承载右侧操作按钮与拖拽；窗体名改由左上角 CornerTag 展示）。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("titlebar")
        self.setFixedHeight(44)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 10, 0)
        lay.setSpacing(6)
        lay.addStretch(1)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(4)
        lay.addLayout(self.actions)
        self._drag_origin: QPoint | None = None
        self._window_origin: QPoint | None = None

    def add_action(self, text: str, tooltip: str = "",
                   checkable: bool = False, cls: str = "icon",
                   callback: Callable[[], None] | None = None) -> QPushButton:
        button = IconButton(text, tooltip, checkable, cls, self)
        self.actions.addWidget(button)
        if callback is not None:
            button.clicked.connect(lambda: callback())  # type: ignore[arg-type]
        return button

    # ------------------------------------------------------------ 拖动
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() is Qt.LeftButton:
            win = self.window()
            if win.isMaximized():
                return
            self._drag_origin = event.globalPosition().toPoint()
            self._window_origin = win.frameGeometry().topLeft()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        # 只有按住左键时才跟随移动；避免鼠标划过标题栏导致窗口乱跑。
        if (self._drag_origin is not None and self._window_origin is not None
                and bool(event.buttons() & Qt.LeftButton)):
            delta = event.globalPosition().toPoint() - self._drag_origin
            self.window().move(self._window_origin + delta)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_origin = None
        self._window_origin = None
        self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)


class FramelessWindow(QWidget):
    """所有悬浮窗的基类：圆角卡片 + 阴影 + 标题栏 + 内容区 + 缩放把手。"""

    closed = Signal(object)
    pin_toggled = Signal(object, bool)

    def __init__(self, title: str, badge_cls: str | None = None,
                 on_top: bool = True, resizable: bool = True,
                 min_size: tuple[int, int] = (280, 150)):
        flags = Qt.FramelessWindowHint | Qt.Tool
        # 置顶完全交给 win_topmost（Win32 SetWindowPos），不再设置 Qt 的
        # WindowStaysOnTopHint：Qt flag 会与 Win32 z 序状态打架，且运行期切换
        # setWindowFlag 会重建原生窗口 → hide/show → 用户看到「闪一下」。
        # 默认置顶由 showEvent 里的 apply_topmost() 保证，两者都默认开启。
        super().__init__(None, flags)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(str(app_icon_path())))
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(*min_size)
        self._pinned = False
        self._on_top = on_top
        self._topmost = bool(on_top)
        self._top_guard: QTimer | None = None
        self._corner_radius = 14

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(0)
        self.root = QWidget(self)
        self.root.setObjectName("root")
        outer.addWidget(self.root)
        shadow = QGraphicsDropShadowEffect(self.root)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(120, 70, 60, 95))
        self.root.setGraphicsEffect(shadow)
        self._apply_root_mask()

        self.root_layout = QVBoxLayout(self.root)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        self.titlebar = TitleBar(self.root)
        self.root_layout.addWidget(self.titlebar)

        self.body = QWidget(self.root)
        self.body_layout = QVBoxLayout(self.body)
        # 纯文字标签高 42px，位于标题栏左侧留白区；内容区从 54px 起，
        # 所有窗体统一相对布局，最大化时不错位。
        self.body_layout.setContentsMargins(16, 10, 16, 12)
        self.body_layout.setSpacing(8)
        self.root_layout.addWidget(self.body, 1)

        self.footer = QWidget(self.root)
        self.footer.setObjectName("footer")
        self.footer_layout = QHBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(12, 7, 12, 7)
        self.footer_layout.setSpacing(6)
        self.root_layout.addWidget(self.footer)

        # 左上角折角品牌标签：方角贴住 root 左上角，由 root 圆角 mask 切出「只显右边 + 底边」。
        self.corner_tag = CornerTag(title, "", True, self.root)
        # 贴住窗体左上角 (0,0)：标签自身左上圆角 14px 与窗体圆角同心，
        # 视觉上只剩右边+底边的圆弧。不用负偏移，避免遮罩被阴影效果压制时红块溢出卡片。
        self.corner_tag.move(0, 0)
        self.corner_tag.raise_()

        if resizable:
            grip_lay = QHBoxLayout()
            grip_lay.setContentsMargins(0, 0, 4, 2)
            grip_lay.addStretch(1)
            grip_lay.addWidget(QSizeGrip(self.root))
            self.root_layout.addLayout(grip_lay)

        # 所有悬浮窗默认置顶：可见期间每 1.5s 重申一次 z 序，
        # 避免被 WPS / 全屏程序 / 其它 topmost 窗口压到下层。
        self.enable_topmost_guard()

    # ------------------------------------------------------------ 圆角遮罩
    def _apply_root_mask(self) -> None:
        r = self._corner_radius
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.root.width(), self.root.height()), r, r)
        self.root.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def resizeEvent(self, event) -> None:
        self._apply_root_mask()
        super().resizeEvent(event)

    # ------------------------------------------------------------ 通用能力
    def add_footer_text(self, text: str) -> QLabel:
        label = QLabel(text)
        set_cls(label, "sub")
        label.setStyleSheet(f"font-size:{FONT_SUBTITLE_PX}px")
        self.footer_layout.addWidget(label)
        return label

    def add_footer_hint(self, text: str, variant: str = "default") -> Hint:
        hint = Hint(text, variant)
        self.footer_layout.addWidget(hint)
        return hint

    def add_footer_signature(self, copy_callback: Callable[[], None],
                             compact: bool = False) -> AuthorSignature:
        sig = AuthorSignature(copy_callback, compact)
        self.footer_layout.addWidget(sig)
        return sig

    def set_corner_subtitle(self, text: str) -> None:
        self.corner_tag.set_subtitle(text)

    def add_footer_stretch(self) -> None:
        self.footer_layout.addStretch(1)

    def add_footer_button(self, text: str, callback: Callable[[], None],
                          primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        set_cls(button, "primary" if primary else "btn")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda: callback())  # type: ignore[arg-type]
        self.footer_layout.addWidget(button)
        return button

    def add_footer_copy(self, callback: Callable[[], None],
                        text: str = "复制译文") -> QPushButton:
        """统一的右下角复制按钮：柔和胶囊 + hover 过渡 + 点击「已复制」1.4s 反馈。"""
        button = QPushButton(text)
        set_cls(button, "copy")
        button.setCursor(Qt.PointingHandCursor)

        def restore() -> None:
            button.setText(text)
            button.setProperty("done", False)
            button.style().unpolish(button)
            button.style().polish(button)

        def on_click() -> None:
            callback()
            button.setText("已复制")
            button.setProperty("done", True)
            button.style().unpolish(button)
            button.style().polish(button)
            QTimer.singleShot(1400, restore)

        button.clicked.connect(on_click)
        self.footer_layout.addWidget(button)
        return button

    def add_footer_status_and_copy(self, hint_text: str, copy_callback: Callable[[], None],
                                   button_text: str = "复制译文") -> tuple[Hint, QPushButton]:
        """两个翻译窗共用的底栏结构：左侧状态提示 + 弹性留白 + 右下角复制译文。

        手动输入窗与图片识别窗都调用本方法，因此提示语样式、按钮样式与
        「已复制」反馈状态逐元素一致；底栏本身也统一为透明无背景色块。
        """
        # 只切换 objectName，样式交给全局 QSS 的 #footerPlain 规则。
        # ⚠️ 不能在 footer 上写裸声明 setStyleSheet("border:0")：Qt 样式表会传播到
        # 所有子控件，把「复制译文」的按钮边框一起抹掉（曾导致底栏按钮无边框）。
        self.footer.setObjectName("footerPlain")
        hint = self.add_footer_hint(hint_text, "teal")
        self.add_footer_stretch()
        button = self.add_footer_copy(copy_callback, button_text)
        return hint, button

    # ------------------------------------------------------------ 置顶
    def apply_topmost(self) -> None:
        """Windows 下重申 TOPMOST；不抢焦点，也不改变位置与尺寸。"""
        if self._topmost:
            _win_apply_topmost(self.hwnd(), True)

    def enable_topmost_guard(self, interval_ms: int = 1500) -> None:
        """悬浮窗可见期间定时重申 z 序，防止被其它置顶软件压到下层。"""
        if self._top_guard is None:
            self._top_guard = QTimer(self)
            self._top_guard.setInterval(interval_ms)
            self._top_guard.timeout.connect(self.apply_topmost)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # 窗口显示即重申 z 序：两个翻译窗默认置顶、始终显示在桌面最上层。
        self.apply_topmost()
        if self._top_guard is not None and not self._top_guard.isActive():
            self._top_guard.start()

    def hideEvent(self, event) -> None:
        if self._top_guard is not None:
            self._top_guard.stop()
        super().hideEvent(event)

    def set_on_top(self, enabled: bool) -> None:
        """切换置顶：只改 Win32 z 序，绝不重建窗口 —— 点击图钉零闪烁。

        历史问题：setWindowFlag() 会重建原生窗口并把窗口隐藏，先 hide 后 show
        会让用户看到「窗口闪一下、消失再出现」。现在不碰 Qt 窗口标志、不调用
        show()/hide()，窗口句柄、可见性、几何与最大化状态全程不变。
        """
        self._on_top = bool(enabled)
        self._topmost = bool(enabled)
        _win_apply_topmost(self.hwnd(), self._topmost)

    @property
    def pinned(self) -> bool:
        return self._pinned

    def set_pinned(self, value: bool) -> None:
        self._pinned = bool(value)

    def hwnd(self) -> int:
        try:
            return int(self.winId())
        except Exception:
            return 0

    def closeEvent(self, event) -> None:
        self.closed.emit(self)
        super().closeEvent(event)
