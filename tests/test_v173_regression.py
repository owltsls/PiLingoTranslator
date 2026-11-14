# -*- coding: utf-8 -*-
"""v1.7.3 回归：零闪置顶、默认置顶、中文右键菜单、托盘文案、版本与关于页层级。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app import branding  # noqa: E402
from tests import WORKSPACE, cleanup_tmp, make_tmp  # noqa: E402


class VersionAndDateTest(unittest.TestCase):
    def test_version_is_173_everywhere(self):
        self.assertEqual(branding.APP_VERSION, "1.7.3")
        self.assertIn("v1.7.3", branding.product_line())
        for rel in ("build/setup.iss", "build/version_info.txt"):
            text = (WORKSPACE / rel).read_text(encoding="utf-8")
            self.assertIn("1.7.3", text, rel)
            self.assertNotIn("0.1.0", text, rel)

    def test_build_date_is_gone(self):
        self.assertFalse(hasattr(branding, "BUILD_DATE"))
        source = (WORKSPACE / "app" / "branding.py").read_text(encoding="utf-8")
        self.assertNotIn("2026-11-12", source)
        dialogs = (WORKSPACE / "app" / "ui" / "dialogs.py").read_text(encoding="utf-8")
        self.assertNotIn("构建 ", dialogs)

    def test_product_line_has_no_date(self):
        self.assertNotIn("2026", branding.product_line())


class UITestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.prev = os.environ.get("PILINGO_CONFIG_DIR")
        cls.tmp = make_tmp()
        os.environ["PILINGO_CONFIG_DIR"] = str(cls.tmp)
        cls.qapp = QApplication.instance() or QApplication([])
        cls.qapp.setQuitOnLastWindowClosed(False)

    @classmethod
    def tearDownClass(cls):
        if cls.prev is None:
            os.environ.pop("PILINGO_CONFIG_DIR", None)
        else:
            os.environ["PILINGO_CONFIG_DIR"] = cls.prev
        cleanup_tmp(cls.tmp)

    def setUp(self):
        from app.ui.app import TranslatorApp
        self.ctrl = TranslatorApp(self.qapp, demo=True,
                                  enable_hotkeys=False, enable_tray=False)

    def tearDown(self):
        self.ctrl.shutdown()


class TopmostTest(UITestBase):
    def test_both_windows_default_to_topmost(self):
        s = self.ctrl.store.settings
        self.assertTrue(s.w3_always_on_top)
        self.assertTrue(s.ocr_window_always_on_top)
        for win in (self.ctrl.w3, self.ctrl.ocr_window):
            self.assertTrue(win._topmost)
            self.assertTrue(win.pin_btn.isChecked())

    def test_pin_never_rebuilds_or_hides_window(self):
        for win in (self.ctrl.w3, self.ctrl.ocr_window):
            win.show()
            self.qapp.processEvents()
            before_hwnd = int(win.winId())
            before_flags = win.windowFlags()
            for state in (False, True):
                win.pin_btn.setChecked(state)
                win._on_pin_clicked()
                self.qapp.processEvents()
                self.assertTrue(win.isVisible(), "切换置顶时窗口不应被隐藏")
                self.assertEqual(int(win.winId()), before_hwnd,
                                 "重建原生窗口会导致闪烁")
                self.assertEqual(win.windowFlags(), before_flags,
                                 "不得调用 setWindowFlag")


class ChineseMenuTest(UITestBase):
    def test_standard_context_menu_is_chinese(self):
        from PySide6.QtWidgets import QPlainTextEdit
        from app.qt_i18n import install_chinese_translator
        self.assertTrue(install_chinese_translator(self.qapp))
        editor = QPlainTextEdit()
        editor.setPlainText("测试文本")
        texts = [a.text().replace("&", "") for a in
                 editor.createStandardContextMenu().actions()
                 if not a.isSeparator()]
        joined = " ".join(texts)
        for word in ("撤消", "重做", "剪切", "复制", "粘贴", "删除", "全选"):
            self.assertIn(word, joined)
        for english in ("Undo", "Redo", "Cut", "Copy", "Paste", "Select All"):
            self.assertNotIn(english, joined)

    def test_translation_files_are_available(self):
        from app.qt_i18n import translations_dir
        self.assertTrue((translations_dir() / "qtbase_zh_CN.qm").is_file())


class TrayAndAboutTest(UITestBase):
    def test_tray_about_label_is_short(self):
        labels = [a.text() for a in self.ctrl.tray.contextMenu().actions()
                  if not a.isSeparator()]
        self.assertIn("关于", labels)
        self.assertFalse(any("关于作者" in x for x in labels))

    def test_tray_settings_has_no_ellipsis(self):
        labels = [a.text() for a in self.ctrl.tray.contextMenu().actions()
                  if not a.isSeparator()]
        self.assertIn("设置", labels)
        self.assertNotIn("设置…", labels)

    def test_about_has_single_title_and_no_date(self):
        from PySide6.QtWidgets import QLabel
        from app.ui.dialogs import AboutDialog
        dlg = AboutDialog(self.ctrl)
        labels = [x.text() for x in dlg.findChildren(QLabel) if x.text()]
        # 左上角「关于」是唯一主标题；不再有红色大标题重复产品名。
        self.assertIn("关于", labels)
        self.assertFalse(any("color:#c8402f" in x.styleSheet() and
                             "font-weight:800" in x.styleSheet()
                             for x in dlg.findChildren(QLabel)))
        self.assertFalse(any("2026-11-12" in x or "构建 " in x for x in labels))
        # 红框内的产品元信息行已整行删除：关于页不再出现版本行与标语。
        self.assertFalse(any(branding.OFFLINE_SLOGAN in x for x in labels))
        self.assertFalse(any(branding.product_line() in x for x in labels))
        bodies = [x for x in dlg.findChildren(QLabel)
                  if x.wordWrap() and x.textInteractionFlags()]
        body = max(bodies, key=lambda w: len(w.text()))
        self.assertNotIn(branding.AUTHOR_WECHAT, body.text())
        dlg.close()


if __name__ == "__main__":
    unittest.main()
