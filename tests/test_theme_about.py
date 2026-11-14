# -*- coding: utf-8 -*-
"""统一按钮 / 字号规范与「关于」页文案回归。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import os
import re
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app import branding  # noqa: E402
from app.ui.theme import (FONT_BODY_PX, FONT_CONTROL_PX,  # noqa: E402
                          FONT_SUBTITLE_PX, FONT_TITLE_PX, stylesheet)


class ThemeUnifyTest(unittest.TestCase):
    def setUp(self):
        self.qss = stylesheet("light")

    def test_copy_button_no_longer_uses_faint_capsule(self):
        self.assertNotIn("qlineargradient", self.qss)
        self.assertNotIn("border-radius: 13px", self.qss)
        self.assertNotIn("border: 1px solid #f0d3cd", self.qss)

    def test_all_buttons_share_one_visible_border(self):
        self.assertIn("QPushButton { background: #ffffff; color: #241a18; "
                      "border: 1px solid #d9bcb5;", self.qss)
        self.assertIn('QPushButton[cls="copy"] { padding: 5px 13px; }', self.qss)
        # 图标按钮也用同一条边框，两个翻译窗里的按钮完全一致。
        self.assertIn("QPushButton[cls=\"icon\"] { background: #ffffff; "
                      "border: 1px solid #d9bcb5;", self.qss)

    def test_font_sizes_come_from_one_constant_set(self):
        values = set(re.findall(r"font-size:\s*([\d.]+)px", self.qss))
        allowed = {str(FONT_TITLE_PX), str(FONT_SUBTITLE_PX),
                   str(FONT_BODY_PX), str(FONT_CONTROL_PX)}
        self.assertTrue(values, "QSS 必须显式声明字号")
        self.assertTrue(values <= allowed, f"出现规范外字号：{values - allowed}")

    def test_dialog_controls_use_smaller_control_font(self):
        self.assertIn(f"QDialog QLabel, QDialog QCheckBox, QDialog QGroupBox "
                      f"{{ font-size: {FONT_BODY_PX}px; }}", self.qss)
        self.assertIn("QDialog QLineEdit, QDialog QComboBox, QDialog QSpinBox {",
                      self.qss)
        self.assertIn(f"QDialog QLabel[cls=\"sub\"] {{ font-size: {FONT_CONTROL_PX}px; }}",
                      self.qss)


class AboutTextTest(unittest.TestCase):
    def test_lazy_loading_mistranslation_is_gone(self):
        text = "\n".join(branding.about_lines())
        for bad in ("懒加载", "偷懒", "lazy", "单例", "离线守卫", "架构："):
            self.assertNotIn(bad, text)

    def test_only_model_and_license_info_remains(self):
        text = "\n".join(branding.about_lines())
        for needed in ("Hy-MT2", "Apache-2.0", "MIT", "LGPL", "licenses/"):
            self.assertIn(needed, text)

    def test_about_body_is_professional_and_comprehensive(self):
        lines = branding.about_lines()
        self.assertGreaterEqual(len(lines), 20, "技术说明应写全、把窗口铺满")
        text = "\n".join(lines)
        for detail in ("n_ctx = 2048", "temperature = 0.0", "top_p = 0.9",
                       "repeat_penalty = 1.05", "n_gpu_layers = 0",
                       "use_mmap = True", "max_tokens", "Q4_K_M",
                       "PP-OCRv5", "ONNX Runtime", "det / rec / cls",
                       "【推理配置】", "【离线与隐私】"):
            self.assertIn(detail, text)

    def test_detail_lines_are_indented_for_hierarchy(self):
        lines = list(branding.about_lines())
        titles = [x for x in lines if x.startswith("【")]
        details = [x for x in lines if x and not x.startswith("【")]
        self.assertEqual(len(titles), 5)
        self.assertGreaterEqual(len(details), 20)
        # 分区标题顶格；每条明细首行缩进 2 个全角空格。
        self.assertTrue(all(x.startswith("　　") for x in details))
        self.assertTrue(all(not x.startswith("　") for x in titles))

    def test_author_block_is_short(self):
        block = branding.signature_block()
        self.assertEqual(len(block), 2)
        self.assertIn(branding.AUTHOR_WECHAT, block[-1])
        joined = "\n".join(block)
        self.assertNotIn("商务", joined)
        self.assertNotIn("如需定制", joined)

    def test_about_body_has_no_author_contact_footer_still_has_it(self):
        from PySide6.QtWidgets import QApplication, QLabel

        from app.ui.app import TranslatorApp
        from app.ui.dialogs import AboutDialog
        from app.ui.widgets import AuthorSignature
        from tests import cleanup_tmp, make_tmp

        tmp = make_tmp()
        prev = os.environ.get("PILINGO_CONFIG_DIR")
        os.environ["PILINGO_CONFIG_DIR"] = str(tmp)
        try:
            app = QApplication.instance() or QApplication([])
            ctrl = TranslatorApp(app, demo=True, enable_hotkeys=False,
                                 enable_tray=False)
            dlg = AboutDialog(ctrl)
            bodies = [w for w in dlg.findChildren(QLabel)
                      if w.wordWrap() and w.textInteractionFlags()]
            self.assertTrue(bodies)
            body = max(bodies, key=lambda w: len(w.text()))
            text = body.text()
            self.assertNotIn(branding.AUTHOR_WECHAT, text)
            self.assertNotIn("作者联系方式", text)
            self.assertNotIn("微信号", text)
            sig = dlg.findChild(AuthorSignature)
            self.assertIsNotNone(sig)
            self.assertIn(branding.AUTHOR_WECHAT, sig.text())
            dlg.close()
            ctrl.shutdown()
        finally:
            if prev is None:
                os.environ.pop("PILINGO_CONFIG_DIR", None)
            else:
                os.environ["PILINGO_CONFIG_DIR"] = prev
            cleanup_tmp(tmp)


if __name__ == "__main__":
    unittest.main()
