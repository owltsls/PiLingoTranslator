# -*- coding: utf-8 -*-
"""手动输入翻译窗：参考固定窗的紧凑骨架，上输入 / 下译文、自动分块、原生最大化。

作者联系方式 · 微信号：TheSun_Also_Rises

产品定稿：输入停止 1 秒自动翻译，界面不提供翻译按钮、不显示任何快捷键；
划词取词模块已整体删除；窗口可拖动、可手动缩放、点右上角按钮用 Windows 原生
最大化，再点一次恢复小窗。
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSplitter,
    QVBoxLayout, QWidget,
)

from ..config import AUTO_TRANSLATE_DELAY_MS
from ..state_machine import FocusOwner, W3State, W3StateMachine
from ..text_logic import long_text_hint
from ..translator import TranslationResult
from .widgets import AuthorSignature, FramelessWindow, Hint, set_cls


class TranslateWorker(QObject):
    """后台线程执行翻译，逐块通过信号回填到主线程 UI。"""

    block_done = Signal(int, int, str)
    finished = Signal(object)

    def __init__(self, translator, text: str, src: str,
                 cancel_event: threading.Event):
        super().__init__()
        self.translator = translator
        self.text = text
        self.src = src
        self.cancel_event = cancel_event

    def run(self) -> None:
        def on_block(index: int, total: int, chunk: str) -> None:
            self.block_done.emit(index, total, chunk)

        result = self.translator.translate(
            self.text, src=self.src, on_block=on_block,
            cancel=self.cancel_event.is_set,
        )
        self.finished.emit(result)


class ManualWindow(FramelessWindow):
    """手动输入翻译：唯一可输入的窗口。"""

    def __init__(self, controller):
        super().__init__("手动输入翻译", "badge-rose",
                         on_top=controller.store.settings.w3_always_on_top,
                         resizable=True, min_size=(420, 520))
        self.controller = controller
        self.state = W3StateMachine()
        self._allow_close = False
        self._thread: QThread | None = None
        self._worker: TranslateWorker | None = None
        self._cancel_event: threading.Event | None = None
        self._pending_text: str | None = None
        # 灰色小字固定为「输入即译」，最大化态也统一，不再切换。
        self.set_corner_subtitle("输入即译")

        # ------------------------------------------------------------ 标题栏按钮
        self.pin_btn = self.titlebar.add_action("📌", "窗口始终置顶", True, "pin")
        self.pin_btn.setChecked(self.controller.store.settings.w3_always_on_top)
        self.pin_btn.clicked.connect(self._on_pin_clicked)
        self.max_btn = self.titlebar.add_action("□", "最大化", False, "icon",
                                                self.toggle_maximize)
        # 用户定稿：翻译窗右上角不再保留「设置」按钮（设置仍可从托盘菜单进入）。
        self.titlebar.add_action("✕", "隐藏（保留译文与位置）", False, "icon", self.hide_window)

        # ------------------------------------------------------------ 状态行 + 清空输入
        # 「清空输入」位于输入文本框上方、与底栏「复制译文」右对齐成同一列；
        # 采用同款柔和胶囊，点击即清空原文与译文，不弹确认框。
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(8)
        self.status_hint = Hint("就绪 · 输入或粘贴后自动翻译")
        status_row.addWidget(self.status_hint, 1)
        self.clear_btn = QPushButton("清空输入")
        set_cls(self.clear_btn, "copy")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setToolTip("清空原文与译文")
        self.clear_btn.clicked.connect(self.clear_all)
        status_row.addWidget(self.clear_btn)
        self.body_layout.addLayout(status_row)

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.body_layout.addWidget(self.splitter, 1)

        # ------------------------------------------------------------ 上栏：原文输入
        top = QWidget()
        top_lay = QVBoxLayout(top)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(6)
        head = QHBoxLayout()
        lbl = QLabel("原文输入")
        set_cls(lbl, "lang")
        head.addWidget(lbl)
        head.addWidget(Hint("可编辑 · 支持长文本自动分块"), 1)
        top_lay.addLayout(head)

        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("在这里手动输入或粘贴任意语言文本…")
        self.input.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.input.setMinimumHeight(90)
        self.input.document().setDocumentMargin(9)
        set_cls(self.input, "input")
        self.input.textChanged.connect(self._on_text_changed)
        self.input.installEventFilter(self)
        top_lay.addWidget(self.input, 1)

        self.count_label = Hint("0 字 · 单块上限 2000 字（超长自动分块，不截断）")
        top_lay.addWidget(self.count_label)
        self.long_hint = Hint("")
        self.long_hint.setVisible(False)
        top_lay.addWidget(self.long_hint)
        top.setMinimumHeight(180)
        self.splitter.addWidget(top)

        # ------------------------------------------------------------ 下栏：译文
        bottom = QWidget()
        bottom_lay = QVBoxLayout(bottom)
        bottom_lay.setContentsMargins(0, 0, 0, 0)
        bottom_lay.setSpacing(6)
        head2 = QHBoxLayout()
        lbl2 = QLabel("中文译文")
        set_cls(lbl2, "lang")
        head2.addWidget(lbl2)
        head2.addWidget(Hint("本地离线 · 逐块回填", "teal"), 1)
        bottom_lay.addLayout(head2)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        set_cls(self.output, "output")
        self.output.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.output.setMinimumHeight(80)
        self.output.document().setDocumentMargin(9)
        self.output.setPlaceholderText("输入内容后，这里显示中文译文")
        bottom_lay.addWidget(self.output, 1)
        bottom.setMinimumHeight(130)
        self.splitter.addWidget(bottom)
        # 按比例分配，拖大 / 缩小时两栏始终等分，不会错位。
        self.splitter.setSizes([1, 1])

        # ------------------------------------------------------------ 底栏
        # 与图片识别窗调用同一个 helper：左侧状态提示 + 右下角「复制译文」，
        # 提示语样式、按钮外观与「已复制」反馈状态逐元素一致，底栏透明无背景色块。
        self.footer_hint, self.copy_btn = self.add_footer_status_and_copy(
            "本地离线 · 译文可复制", self.copy_translation)

        # ------------------------------------------------------------ 自动翻译
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(AUTO_TRANSLATE_DELAY_MS)
        self._debounce.timeout.connect(self.start_translation)
        self._update_count()

    # ------------------------------------------------------------ 焦点（防自触发）
    def eventFilter(self, obj, event) -> bool:
        from PySide6.QtCore import QEvent
        if obj is self.input:
            if event.type() == QEvent.FocusIn:
                self.controller.set_focus(FocusOwner.W3_INPUT)
            elif event.type() == QEvent.FocusOut:
                self.controller.set_focus(FocusOwner.OWN_WINDOW)
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------ 显示 / 隐藏 / 几何
    def show_window(self) -> None:
        self.state.show()
        self.restore_geometry()
        self.show()
        self.raise_()
        self._update_count()

    def hide_window(self) -> None:
        self.save_geometry()
        self.state.hide()
        self.hide()
        self.controller.set_focus(FocusOwner.EXTERNAL)

    def _clamped_geometry(self, geo: dict) -> tuple[int, int, int, int]:
        """把记忆的窗口位置夹到当前屏幕可见区。"""
        x = int(geo.get("x", 120)); y = int(geo.get("y", 120))
        w = max(420, int(geo.get("width", 420))); h = max(480, int(geo.get("height", 500)))
        screen = QApplication.primaryScreen()
        area = screen.availableGeometry() if screen else None
        if area is not None:
            w = min(w, max(420, area.width() - 20))
            h = min(h, max(480, area.height() - 20))
            x = max(area.left() + 5, min(x, area.right() - w - 5))
            y = max(area.top() + 5, min(y, area.bottom() - h - 5))
        return x, y, w, h

    def restore_geometry(self) -> None:
        # 用户定稿：每次打开都回到初始小窗状态，绝不恢复上次的「最大化」。
        # 配置里残留的 w3_maximized=True 会被清零，避免开机自启 / 托盘唤起时被撑满。
        self.showNormal()
        self.setGeometry(*self._clamped_geometry(
            self.controller.store.settings.w3_geometry))
        if self.controller.store.settings.w3_maximized:
            self.controller.save_w3_geometry(None, False)
        self._sync_max_button()

    def save_geometry(self) -> None:
        if self.isMaximized():
            # 最大化只属于本次会话，不写盘；保留关闭前那份小窗几何即可。
            self.controller.save_w3_geometry(None, False)
        else:
            rect = self.geometry()
            self.controller.save_w3_geometry(
                {"x": rect.x(), "y": rect.y(), "width": rect.width(), "height": rect.height()},
                False)

    def _sync_max_button(self) -> None:
        maximized = self.isMaximized()
        self.max_btn.setText("■" if maximized else "□")
        self.max_btn.setToolTip("还原为小窗" if maximized else "最大化")

    def toggle_maximize(self, _checked: bool = False) -> None:
        """一键 Windows 原生最大化；再点一次恢复小窗尺寸。"""
        if self.isMaximized():
            self.showNormal()
            self.setGeometry(*self._clamped_geometry(
                self.controller.store.settings.w3_geometry))
            self.controller.save_w3_geometry(None, False)
        else:
            self.save_geometry()       # 先记住小窗位置
            self.showMaximized()       # 仅本次会话最大化，不持久化
        self._sync_max_button()

    @property
    def is_maximized(self) -> bool:
        return self.isMaximized()

    def closeEvent(self, event) -> None:
        if not self._allow_close:
            event.ignore()
            self.hide_window()
            self.controller.on_w3_hidden()
            return
        self.save_geometry()
        super().closeEvent(event)

    def force_close(self) -> None:
        self._allow_close = True
        self.close()

    # ------------------------------------------------------------ 输入与提示
    def _update_count(self) -> None:
        text = self.input.toPlainText()
        n = len(text)
        max_chars = self.controller.store.settings.max_block_chars
        self.count_label.set_text(f"{n} 字 · 单块上限 {max_chars} 字（超长自动分块，不截断）")
        level, message = long_text_hint(n, max_chars, text)
        self.long_hint.setVisible(bool(message))
        self.long_hint.set_text(message)
        return level

    def _on_text_changed(self) -> None:
        self._update_count()
        if self.state.state in (W3State.EMPTY, W3State.DONE):
            self.state.transition(W3State.TYPING)
        self._debounce.stop()
        if self.input.toPlainText().strip():
            # 固定 1 秒停顿自动翻译；无开关、无按钮、无快捷键。
            self._debounce.start(AUTO_TRANSLATE_DELAY_MS)

    def _on_pin_clicked(self, _checked: bool = False) -> None:
        enabled = self.pin_btn.isChecked()
        self.set_on_top(enabled)
        self.controller.store.update(w3_always_on_top=enabled)
        self.controller.notify("窗口已置顶" if enabled else "已取消置顶")

    # ------------------------------------------------------------ 翻译
    def clear_all(self, _checked: bool = False) -> None:
        self._debounce.stop()
        self.input.setPlainText("")
        self.output.setPlainText("")
        if self.state.state is W3State.DONE or self.state.state is W3State.TYPING:
            self.state.transition(W3State.EMPTY)
        self.status_hint.set_text("已清空")
        self.footer_hint.set_text("已清空 · 本地离线")
        self._update_count()

    def fill_long_sample(self, _checked: bool = False) -> None:
        base = "\n".join([
            "Offline translation keeps every selected phrase on this device.",
            "The local model handles the request without any network call.",
            "Long passages are split into blocks and translated one by one.",
        ])
        self.input.setPlainText("\n\n".join(f"Paragraph {i}\n{base}" for i in range(1, 13)))
        self.controller.notify("已填入长文本：可拖动滚动条，或点右上角最大化按钮")

    def start_translation(self, _checked: bool = False) -> None:
        self._debounce.stop()
        text = self.input.toPlainText()
        if not text.strip():
            self.output.setPlainText("")
            self.status_hint.set_text("空输入，未发起翻译请求")
            self.footer_hint.set_text("空输入 · 本地离线")
            return
        if self._thread is not None and self._thread.isRunning():
            self._pending_text = text
            self.status_hint.set_text("模型忙：已排队，当前翻译结束后自动继续")
            return
        if self.state.state in (W3State.EMPTY, W3State.DONE):
            self.state.transition(W3State.TYPING)
        if self.state.state is W3State.TYPING:
            self.state.transition(W3State.TRANSLATING)
        self.output.setPlainText("")
        self.status_hint.set_text("翻译中…（本机模型推理）")
        self.footer_hint.set_text("翻译中 · 本地离线")

        self._cancel_event = threading.Event()
        self._thread = QThread(self)
        self._worker = TranslateWorker(self.controller.translator, text,
                                       self.controller.store.settings.source_language,
                                       self._cancel_event)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.block_done.connect(self._on_block)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def cancel_translation(self, _checked: bool = False) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()
        self.status_hint.set_text("正在取消…（在块边界停止，已完成译文保留）")

    def _on_block(self, index: int, total: int, chunk: str) -> None:
        current = self.output.toPlainText()
        prefix = "\n" if current and index > 1 and not current.endswith("\n") else ""
        self.output.setPlainText(current + prefix + chunk)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())
        self.status_hint.set_text(f"翻译中… 第 {index}/{total} 块已回填")

    def _on_finished(self, result: TranslationResult) -> None:
        if self.state.state is W3State.TRANSLATING:
            if result.cancelled:
                self.state.cancel_translation()
            else:
                self.state.transition(W3State.DONE)
        if result.cancelled:
            self.status_hint.set_text("已取消 · 已完成译文保留")
            self.footer_hint.set_text("已取消 · 本地离线")
        elif result.error:
            self.output.setPlainText(f"无法翻译：{result.error}\n\n"
                                     "请在「设置 → 本地 GGUF 权重」指定权重。全程本地离线，不会联网。")
            self.status_hint.set_text("翻译失败（本地引擎未就绪）")
            self.footer_hint.set_text("翻译失败 · 本地引擎未就绪")
        else:
            self.status_hint.set_text(
                f"完成 · {result.done_blocks}/{result.total_blocks} 块 · {result.elapsed_ms:.0f} ms · 本地离线")
            self.footer_hint.set_text(
                f"完成 · {result.done_blocks}/{result.total_blocks} 块 · 本地离线")
        if self._pending_text is not None:
            pending, self._pending_text = self._pending_text, None
            self.input.setPlainText(pending)
            QTimer.singleShot(0, self.start_translation)

    def _cleanup_thread(self) -> None:
        self._thread = None
        self._worker = None
        self._cancel_event = None

    def copy_translation(self, _checked: bool = False) -> None:
        text = self.output.toPlainText()
        if text.strip():
            self.controller.copy_to_clipboard(text)
        else:
            self.controller.notify("暂无译文可复制")
