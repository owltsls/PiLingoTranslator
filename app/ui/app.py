# -*- coding: utf-8 -*-
"""应用控制器：把配置 / 翻译 / OCR 接到原生 Qt 窗口。

作者联系方式 · 微信号：TheSun_Also_Rises

划词取词、剪贴板监听与悬浮气泡模块已整体删除；现在只有两类功能入口：
手动输入翻译、截图 OCR 图片识别翻译。无浏览器、无 HTML 前端、无 HTTP 路由、
无端口监听、无任何后台文本读取。
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QDialog


def _qt_alive(widget) -> bool:
    """判断 Qt 对象（C++ 侧）是否仍存活，避免后台回调访问已销毁窗口导致闪退。"""
    try:
        widget.objectName()
        return True
    except (RuntimeError, AttributeError):
        return False


from .. import branding, offline_guard  # noqa: E402
from ..config import ConfigStore, resolve_model_path  # noqa: E402
from ..hotkeys import GlobalHotkeyManager  # noqa: E402
from ..ocr import NullOCRProvider, OCRPipeline, OCRResult, RapidOCRProvider  # noqa: E402
from ..state_machine import AppState, FocusOwner  # noqa: E402
from ..translator import (DemoBackend, LlamaCppBackend,  # noqa: E402
                          UnavailableBackend, get_translator)
from .dialogs import AboutDialog, SettingsDialog  # noqa: E402
from .manual_window import ManualWindow  # noqa: E402
from .ocr_window import OCRWindow, ScreenCaptureDialog  # noqa: E402
from .theme import stylesheet  # noqa: E402
from .tray import TrayIcon  # noqa: E402

# 冻结运行（PyInstaller）时以 exe 所在目录为安装根；开发态以工程目录为根。
APP_ROOT = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent.parent.parent)


class SignalBridge(QObject):
    """全局热键线程 → 主线程的安全分发。"""
    action = Signal(str)


class OCRWorker(QObject):
    finished = Signal(object)

    def __init__(self, pipeline: OCRPipeline, image: bytes):
        super().__init__()
        self.pipeline = pipeline
        self.image = image

    def run(self) -> None:
        try:
            result = self.pipeline.process(self.image)
        except Exception as exc:  # noqa: BLE001
            result = OCRResult("", "", [], False,
                               f"OCR 处理异常：{type(exc).__name__}: {exc}",
                               getattr(self.pipeline, "name", ""))
        self.finished.emit(result)


class TranslatorApp:
    def __init__(self, qapp: QApplication, demo: bool = False,
                 enable_hotkeys: bool = True, enable_tray: bool = True):
        self.qapp = qapp
        # 在构造任何窗口之前装好 Qt 中文翻译，输入框右键菜单即为中文。
        from ..qt_i18n import install_chinese_translator
        install_chinese_translator(qapp)
        qapp.setApplicationName(branding.APP_NAME_ASCII)
        qapp.setApplicationDisplayName(branding.APP_NAME)
        qapp.setOrganizationName(branding.APP_ID)
        qapp.setQuitOnLastWindowClosed(False)
        self.store = ConfigStore()
        self.store.load()
        self.settings = self.store.settings

        if self.settings.network_guard:
            offline_guard.enable()

        self.state = AppState(self.settings)
        self._active_threads: list[tuple[QObject, QObject]] = []
        # 兼容属性：本版本不再注册剪贴板监听，恒为 False。
        self._clipboard_connected = False

        self.translator = get_translator(
            backend=self._make_backend(demo),
            max_block_chars=self.settings.max_block_chars,
        )
        provider = RapidOCRProvider(self.settings.ocr_model_dir or None)
        if not provider.available()[0]:
            provider = NullOCRProvider(provider.available()[1])
        self.ocr_pipeline = OCRPipeline(self.translator, provider,
                                        self.settings.ocr_min_confidence)

        self.qapp.setStyleSheet(stylesheet(self.settings.theme))
        font = QFont()
        font.setPointSize(self.settings.font_size)
        self.qapp.setFont(font)
        self._apply_window_icon()

        self.w3 = ManualWindow(self)
        self.ocr_window = OCRWindow(self)
        self.state.register_self_window(self.w3.hwnd())
        self.state.register_self_window(self.ocr_window.hwnd())

        self._bridge = SignalBridge()
        self._bridge.action.connect(self._on_hotkey_action)
        self.hotkeys = GlobalHotkeyManager(on_trigger=lambda action: self._bridge.action.emit(action))
        self._rebind_hotkeys(enable_hotkeys)

        self.tray = TrayIcon(self)
        if enable_tray and QApplication.instance() is not None:
            self.tray.show()

        if self.settings.w3_visible:
            self.w3.show_window()
        self.tray.refresh()

    def _apply_window_icon(self) -> None:
        from ..icon import app_icon_path
        self.qapp.setWindowIcon(QIcon(str(app_icon_path())))

    # ------------------------------------------------------------ 引擎
    def _make_backend(self, demo: bool):
        if demo:
            return DemoBackend()
        path, reason = resolve_model_path(APP_ROOT, self.settings)
        if path is None:
            return UnavailableBackend(reason)
        backend = LlamaCppBackend(path)
        ok, why = backend.available()
        return backend if ok else UnavailableBackend(why)

    def engine_status(self) -> str:
        ok, reason = self.translator.ready()
        return ("已就绪" if ok else "未就绪") + f"：{reason}"

    def _sync_hooks(self) -> None:
        """保留接口；当前没有任何后台监听钩子需要注册。"""
        return None

    # ------------------------------------------------------------ 开关与窗口
    def set_ocr(self, enabled: bool) -> None:
        self.store.update(ocr_enabled=bool(enabled))
        self.tray.refresh()

    # 托盘与旧调用点兼容：「截图监听」开关等同于 OCR 开关。
    def set_listen(self, enabled: bool) -> None:
        self.set_ocr(enabled)
        self.notify("截图监听已开启" if enabled else "截图监听已停用")

    def set_w3_visible(self, enabled: bool) -> None:
        if enabled:
            self.w3.show_window()
        else:
            self.w3.hide_window()
        self.store.update(w3_visible=bool(enabled))
        self.tray.refresh()

    def open_w3(self, _checked: bool = False) -> None:
        """托盘菜单／图片识别窗：点击即打开手动输入翻译窗，不做开关切换。"""
        self.w3.show_window()
        self.store.update(w3_visible=True)
        self.tray.refresh()

    def toggle_w3(self) -> None:
        self.set_w3_visible(not self.w3.isVisible())

    def w3_is_visible(self) -> bool:
        return self.w3.isVisible()

    def on_w3_hidden(self) -> None:
        self.store.update(w3_visible=False)
        self.tray.refresh()

    def set_focus(self, owner: FocusOwner) -> None:
        self.state.set_focus(owner)

    def save_w3_geometry(self, geometry: dict | None, maximized: bool) -> None:
        values: dict = {"w3_maximized": bool(maximized)}
        if geometry is not None:
            values["w3_geometry"] = geometry
        self.store.update(**values)

    def copy_to_clipboard(self, text: str) -> None:
        self.qapp.clipboard().setText(text)
        self.notify("内容已复制到剪贴板")

    def notify(self, message: str, title: str | None = None) -> None:
        self.tray.notify(title or branding.APP_NAME, message)

    # ------------------------------------------------------------ OCR
    def start_ocr_capture(self, _checked: bool = False) -> None:
        if not self.state.screenshot_enabled:
            self.notify("截图识别已停用，请在设置里重新开启")
            return
        dialog = ScreenCaptureDialog()
        dialog.captured.connect(self._on_captured_image)
        dialog.exec()

    def _on_captured_image(self, data: bytes, rect) -> None:
        self.ocr_window.set_thumbnail(data)
        self.ocr_window.set_result("", "识别中…（本地 OCR + 本地翻译）",
                                   "位图仅存内存 · 不落盘、不上传")
        self.ocr_window.show()
        self.ocr_window.raise_()
        from PySide6.QtCore import QThread
        thread = QThread()
        worker = OCRWorker(self.ocr_pipeline, data)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_ocr_done)
        worker.finished.connect(thread.quit)
        thread.finished.connect(lambda: self._drop_thread(thread))
        self._active_threads.append((thread, worker))
        thread.start()

    def _on_ocr_done(self, result: OCRResult) -> None:
        message = result.message or "识别与翻译完成 · 本地离线"
        self.ocr_window.set_result(result.recognized_text, result.translated_text, message)

    def _drop_thread(self, thread) -> None:
        self._active_threads = [(t, w) for t, w in self._active_threads if t is not thread]

    # ------------------------------------------------------------ 设置 / 关于
    def open_settings(self, _checked: bool = False) -> None:
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            if dialog.result_warnings:
                self.notify("部分设置已自动修正：" + "；".join(dialog.result_warnings[:3]))
            else:
                self.notify("设置已保存（全程本地，不联网）")

    def show_about(self, _checked: bool = False) -> None:
        AboutDialog(self).exec()

    def apply_settings(self, values: dict) -> list[str]:
        warnings = self.store.update(**values)
        self.qapp.setStyleSheet(stylesheet(self.settings.theme))
        font = QFont()
        font.setPointSize(self.settings.font_size)
        self.qapp.setFont(font)
        self._apply_window_icon()
        self.translator.max_block_chars = self.settings.max_block_chars
        self.w3.pin_btn.setChecked(self.settings.w3_always_on_top)
        self.w3.set_on_top(self.settings.w3_always_on_top)
        self.ocr_window.pin_btn.setChecked(self.settings.ocr_window_always_on_top)
        self.ocr_window.set_on_top(self.settings.ocr_window_always_on_top)
        if self.settings.network_guard:
            offline_guard.enable()
        else:
            offline_guard.disable()
        self._rebind_hotkeys(True)
        self.tray.refresh()
        return warnings

    def _rebind_hotkeys(self, enabled: bool) -> None:
        s = self.settings
        self.hotkeys.set_bindings({
            "w3": s.hotkey_w3,
            "ocr": s.hotkey_ocr,
        })
        if enabled and s.global_hotkeys:
            self.hotkeys.start()

    def _on_hotkey_action(self, action: str) -> None:
        if action == "w3":
            self.toggle_w3()
        elif action == "ocr":
            self.start_ocr_capture()

    # ------------------------------------------------------------ 生命周期
    def run(self) -> int:
        return self.qapp.exec()

    def shutdown(self) -> None:
        """清理全部资源但不退出 Qt 事件循环（测试与嵌入式调用用）。"""
        self.hotkeys.stop()
        self.w3.save_geometry()
        self.w3.force_close()
        self.ocr_window.close()
        self.tray.hide()
        offline_guard.disable()

    def quit_app(self, _checked: bool = False) -> None:
        self.shutdown()
        self.qapp.quit()
