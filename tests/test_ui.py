# -*- coding: utf-8 -*-
"""PySide6 原生窗口离屏冒烟：构造、自动翻译、最大化、拖动、作者签名。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import os
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QPoint, QTimer, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from app import offline_guard  # noqa: E402
from app.config import AUTO_TRANSLATE_DELAY_MS  # noqa: E402
from app.state_machine import W3State  # noqa: E402
from app.ui.dialogs import AboutDialog, SettingsDialog  # noqa: E402
from tests import WORKSPACE, cleanup_tmp, make_tmp  # noqa: E402


class UITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prev_config = os.environ.get("PILINGO_CONFIG_DIR")
        cls.tmp = make_tmp()
        os.environ["PILINGO_CONFIG_DIR"] = str(cls.tmp)
        cls.qapp = QApplication.instance() or QApplication([])
        cls.qapp.setQuitOnLastWindowClosed(False)

    @classmethod
    def tearDownClass(cls):
        if cls.prev_config is None:
            os.environ.pop("PILINGO_CONFIG_DIR", None)
        else:
            os.environ["PILINGO_CONFIG_DIR"] = cls.prev_config
        offline_guard.disable()
        cleanup_tmp(cls.tmp)

    def setUp(self):
        from app.ui.app import TranslatorApp
        self.ctrl = TranslatorApp(self.qapp, demo=True,
                                  enable_hotkeys=False, enable_tray=False)

    def tearDown(self):
        self.ctrl.shutdown()

    def pump_until(self, predicate, timeout_ms: int = 6000) -> bool:
        loop = QEventLoop()
        timer = QTimer()
        timer.setInterval(25)
        started = time.monotonic()

        def tick():
            if predicate() or (time.monotonic() - started) * 1000 > timeout_ms:
                loop.quit()

        timer.timeout.connect(tick)
        timer.start()
        loop.exec()
        timer.stop()
        return bool(predicate())

    # ------------------------------------------------------------ 构造
    def test_all_native_windows_construct(self):
        self.assertIsNotNone(self.ctrl.w3)
        self.assertIsNotNone(self.ctrl.ocr_window)
        about = AboutDialog(self.ctrl)
        settings = SettingsDialog(self.ctrl)
        self.assertTrue(about.windowTitle())
        self.assertTrue(settings.windowTitle())
        about.close(); settings.close()

    def test_engine_status_is_honest_in_demo_mode(self):
        self.assertIn("就绪", self.ctrl.engine_status())

    # ------------------------------------------------------------ 自动翻译定稿
    def test_auto_translate_delay_is_one_second(self):
        self.assertEqual(self.ctrl.w3._debounce.interval(), AUTO_TRANSLATE_DELAY_MS)
        self.assertEqual(AUTO_TRANSLATE_DELAY_MS, 1000)

    def test_no_translate_button_and_no_shortcut(self):
        w3 = self.ctrl.w3
        self.assertFalse(hasattr(w3, "go_btn"))
        self.assertFalse(hasattr(w3, "auto_switch"))
        src = (WORKSPACE / "app" / "ui" / "manual_window.py").read_text(encoding="utf-8")
        self.assertNotIn("Ctrl+Enter", src)
        self.assertNotIn("QShortcut", src)

    def test_typing_arms_auto_translate_timer(self):
        self.ctrl.w3.show_window()
        self.ctrl.w3.input.setPlainText("Offline translation keeps data on this device.")
        self.assertTrue(self.ctrl.w3._debounce.isActive())

    def test_manual_input_end_to_end_translation(self):
        w3 = self.ctrl.w3
        w3.show_window()
        w3.input.setPlainText("Offline translation keeps data on this device.")
        w3.start_translation()
        self.assertTrue(self.pump_until(lambda: w3.state.state is W3State.DONE))
        self.assertTrue(w3.output.toPlainText().strip())

    def test_empty_input_does_not_request_translation(self):
        w3 = self.ctrl.w3
        w3.show_window()
        w3.input.setPlainText("")
        w3.start_translation()
        self.assertIn("空输入", w3.status_hint.text())

    # ------------------------------------------------------------ 窗口交互
    def test_maximize_toggle(self):
        w3 = self.ctrl.w3
        w3.show_window()
        w3.toggle_maximize()
        self.assertTrue(w3.isMaximized())
        w3.toggle_maximize()
        self.assertFalse(w3.isMaximized())

    def test_titlebar_drag_moves_window(self):
        w3 = self.ctrl.w3
        w3.show_window()
        if w3.isMaximized():
            self.skipTest("最大化状态不允许拖动")
        origin = w3.pos()
        bar = w3.titlebar
        press = QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(150, 20),
                            origin + QPoint(150, 20), Qt.LeftButton, Qt.LeftButton,
                            Qt.NoModifier)
        bar.mousePressEvent(press)
        move = QMouseEvent(QMouseEvent.MouseMove, QPoint(190, 45),
                           origin + QPoint(190, 45), Qt.NoButton, Qt.LeftButton,
                           Qt.NoModifier)
        bar.mouseMoveEvent(move)
        release = QMouseEvent(QMouseEvent.MouseButtonRelease, QPoint(190, 45),
                              origin + QPoint(190, 45), Qt.LeftButton, Qt.NoButton,
                              Qt.NoModifier)
        bar.mouseReleaseEvent(release)
        self.assertNotEqual(w3.pos(), origin)

    # ------------------------------------------------------------ 文案与签名
    def test_subtitle_is_input_translate(self):
        self.assertIn("输入即译", self.ctrl.w3.corner_tag._s.text())

    def test_author_contact_in_about_and_settings(self):
        from app.ui.widgets import AuthorSignature
        about = AboutDialog(self.ctrl)
        settings = SettingsDialog(self.ctrl)
        self.assertIn("TheSun_Also_Rises", about.findChild(AuthorSignature).text())
        self.assertIn("微信号", settings.findChild(AuthorSignature).text())
        about.close(); settings.close()

    def test_author_contact_kept_in_tray_only(self):
        from app.ui.widgets import AuthorSignature
        # 用户定稿：手动输入窗底栏删除微信联系方式，托盘 / 关于 / 设置仍保留。
        self.assertIn("TheSun_Also_Rises", self.ctrl.tray.toolTip())
        self.assertEqual(self.ctrl.w3.findChildren(AuthorSignature), [])

    # ------------------------------------------------------------ 本轮 UI 定稿
    def test_splitter_decoration_line_is_transparent(self):
        from app.ui.theme import stylesheet
        self.assertIn("QSplitter::handle { background: transparent; }",
                      stylesheet("light"))

    def test_clear_button_sits_above_input_and_clears(self):
        w3 = self.ctrl.w3
        self.assertEqual(w3.clear_btn.text(), "清空输入")
        w3.input.setPlainText("Offline translation")
        w3.output.setPlainText("离线翻译")
        w3.clear_btn.click()
        self.assertEqual(w3.input.toPlainText(), "")
        self.assertEqual(w3.output.toPlainText(), "")

    def test_footer_only_has_copy_button(self):
        buttons = [b.text() for b in self.ctrl.w3.footer.findChildren(QPushButton)]
        self.assertEqual(buttons, ["复制译文"])
        self.assertEqual(self.ctrl.w3.footer.objectName(), "footerPlain")

    def test_opening_never_restores_maximized(self):
        w3 = self.ctrl.w3
        self.ctrl.store.update(w3_maximized=True)
        w3.show_window()
        self.assertFalse(w3.isMaximized())
        self.assertFalse(self.ctrl.store.settings.w3_maximized)
        w3.hide_window()

    def test_settings_has_no_appearance_engine_group(self):
        from PySide6.QtWidgets import QGroupBox
        from app.ui.dialogs import SettingsDialog
        dlg = SettingsDialog(self.ctrl)
        titles = [g.title() for g in dlg.findChildren(QGroupBox)]
        self.assertNotIn("外观、窗口与本地引擎", titles)
        self.assertFalse(hasattr(dlg, "theme_combo"))
        dlg.close()

    def test_ocr_window_has_pin_and_recapture(self):
        ocr = self.ctrl.ocr_window
        self.assertTrue(ocr.pin_btn.isCheckable())
        tips = [b.toolTip() for b in ocr.titlebar.findChildren(QPushButton)]
        self.assertIn("置顶常驻", tips)
        self.assertIn("选择新的截图区域", tips)
        self.assertNotIn("设置", tips)

    def test_ocr_pin_persists_topmost_choice(self):
        ocr = self.ctrl.ocr_window
        ocr.pin_btn.setChecked(False)
        ocr._on_pin_clicked()
        self.assertFalse(self.ctrl.store.settings.ocr_window_always_on_top)
        ocr.pin_btn.setChecked(True)
        ocr._on_pin_clicked()
        self.assertTrue(self.ctrl.store.settings.ocr_window_always_on_top)

    def test_tray_menu_has_no_toggles(self):
        actions = [a for a in self.ctrl.tray.contextMenu().actions()
                   if not a.isSeparator()]
        self.assertFalse(any(a.isCheckable() for a in actions))
        self.assertFalse(any("截图监听" in a.text() for a in actions))

    # ------------------------------------------------------------ 16:27 一致性 / 图钉
    def test_no_settings_button_on_translation_windows(self):
        for win in (self.ctrl.w3, self.ctrl.ocr_window):
            tips = [b.toolTip() for b in win.titlebar.findChildren(QPushButton)]
            self.assertNotIn("设置", tips)

    def test_footer_style_never_erases_button_border(self):
        # footer 上的裸声明 setStyleSheet("border:0") 会传播到子按钮，
        # 把「复制译文」的边框抹掉；样式必须只靠全局 QSS 的 #footerPlain 规则。
        for win in (self.ctrl.w3, self.ctrl.ocr_window):
            self.assertNotIn("border", win.footer.styleSheet().lower())
            self.assertEqual(win.footer.objectName(), "footerPlain")

    def test_two_windows_have_identical_footer(self):
        from app.ui.widgets import Hint
        w3, ocr = self.ctrl.w3, self.ctrl.ocr_window
        for win in (w3, ocr):
            self.assertEqual(win.footer.objectName(), "footerPlain")
            self.assertEqual([b.text() for b in win.footer.findChildren(QPushButton)],
                             ["复制译文"])
            self.assertEqual(len(win.footer.findChildren(Hint)), 1)
        self.assertEqual(w3.copy_btn.property("cls"), ocr.copy_btn.property("cls"))
        self.assertEqual(w3.clear_btn.property("cls"), w3.copy_btn.property("cls"))
        self.assertEqual(w3.footer.findChildren(Hint)[0]._label.styleSheet(),
                         ocr.footer.findChildren(Hint)[0]._label.styleSheet())

    def test_settings_checkboxes_are_side_by_side(self):
        from app.ui.dialogs import SettingsDialog
        dlg = SettingsDialog(self.ctrl)
        dlg.show()
        self.qapp.processEvents()
        ya = dlg.w3_top.mapTo(dlg, QPoint(0, 0)).y()
        yb = dlg.w3_clear.mapTo(dlg, QPoint(0, 0)).y()
        xa = dlg.w3_top.mapTo(dlg, QPoint(0, 0)).x()
        xb = dlg.w3_clear.mapTo(dlg, QPoint(0, 0)).x()
        self.assertLessEqual(abs(ya - yb), 4, "两个复选框应处于同一行")
        self.assertLess(xa, xb, "应横向并排")
        dlg.close()

    def test_pin_click_never_closes_windows(self):
        w3, ocr = self.ctrl.w3, self.ctrl.ocr_window
        w3.show()
        ocr.show()
        self.qapp.processEvents()
        for btn, handler in ((w3.pin_btn, w3._on_pin_clicked),
                             (ocr.pin_btn, ocr._on_pin_clicked)):
            for state in (False, True):
                btn.setChecked(state)
                handler()
                self.qapp.processEvents()
                self.assertTrue(w3.isVisible(), "点图钉后手动输入窗被关闭")
                self.assertTrue(ocr.isVisible(), "点图钉后图片识别窗被关闭")


class CrashHardeningTest(UITest):
    def test_qt_alive_true_for_live_widget(self):
        from app.ui.app import _qt_alive
        w = QPushButton()
        self.assertTrue(_qt_alive(w))
        w.deleteLater()

    def test_ocr_worker_emits_error_result_on_exception(self):
        from PySide6.QtCore import QThread
        from app.ui.app import OCRWorker

        class BoomPipeline:
            def process(self, image):
                raise RuntimeError("模拟 OCR 推理崩溃")

        captured = {}
        thread = QThread()
        worker = OCRWorker(BoomPipeline(), b"fake")
        worker.moveToThread(thread)
        worker.finished.connect(lambda result: captured.setdefault("r", result))
        worker.finished.connect(thread.quit)
        thread.started.connect(worker.run)
        thread.start()
        loop = QEventLoop()
        QTimer.singleShot(3000, loop.quit)
        thread.finished.connect(loop.quit)
        loop.exec()
        self.assertIsNotNone(captured.get("r"))
        self.assertIn("异常", captured["r"].message)


if __name__ == "__main__":
    unittest.main()
