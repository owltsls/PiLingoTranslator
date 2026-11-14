# -*- coding: utf-8 -*-
"""配置默认值、校验、持久化与模型定位。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from app import branding
from app.config import AUTO_TRANSLATE_DELAY_MS, ConfigStore, Settings, resolve_model_path
from tests import WORKSPACE, cleanup_tmp, make_tmp


class DefaultsTest(unittest.TestCase):
    def test_defaults(self):
        s = Settings()
        self.assertTrue(s.ocr_enabled)
        self.assertTrue(s.network_guard)
        self.assertTrue(s.w3_always_on_top)
        self.assertEqual(s.max_block_chars, 2000)
        self.assertEqual(s.theme, "light")
        self.assertEqual(AUTO_TRANSLATE_DELAY_MS, 1000)

    def test_selection_module_fields_are_gone(self):
        names = {f.name for f in __import__("dataclasses").fields(Settings)}
        for gone in ("listen_enabled", "trigger_mode", "min_selection_chars",
                     "hotkey_toggle", "hotkey_capture", "max_pinned_windows",
                     "w3_auto_translate", "w3_debounce_ms"):
            self.assertNotIn(gone, names)


class ValidationTest(unittest.TestCase):
    def test_type_repair(self):
        s = Settings(ocr_enabled="yes", font_size="big", w3_geometry="oops")  # type: ignore[arg-type]
        w = s.validate_and_fix()
        self.assertIs(s.ocr_enabled, True)
        self.assertEqual(s.font_size, 13)
        self.assertIsInstance(s.w3_geometry, dict)
        self.assertTrue(any("类型非法" in x for x in w))

    def test_enum_and_range_clamp(self):
        s = Settings(theme="neon", source_language="!!!",
                     max_block_chars=1, font_size=99, ocr_min_confidence=5.0)
        s.validate_and_fix()
        self.assertEqual(s.theme, "light")
        self.assertEqual(s.source_language, "auto")
        self.assertEqual(s.max_block_chars, 200)
        self.assertEqual(s.font_size, 24)
        self.assertEqual(s.ocr_min_confidence, 1.0)

    def test_hotkey_normalisation(self):
        s = Settings(hotkey_w3="shift+ctrl+i", hotkey_ocr="bad")
        s.validate_and_fix()
        self.assertEqual(s.hotkey_w3, "Ctrl+Shift+I")
        self.assertEqual(s.hotkey_ocr, "Ctrl+Shift+O")


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = make_tmp()
        self.prev = os.environ.get("PILINGO_CONFIG_DIR")
        os.environ["PILINGO_CONFIG_DIR"] = str(self.tmp)

    def tearDown(self):
        if self.prev is None:
            os.environ.pop("PILINGO_CONFIG_DIR", None)
        else:
            os.environ["PILINGO_CONFIG_DIR"] = self.prev
        cleanup_tmp(self.tmp)

    def test_round_trip(self):
        store = ConfigStore()
        store.load()
        store.update(theme="dark", font_size=15, w3_maximized=True)
        again = ConfigStore()
        again.load()
        self.assertEqual(again.settings.theme, "dark")
        self.assertEqual(again.settings.font_size, 15)
        self.assertTrue(again.settings.w3_maximized)

    def test_legacy_fields_are_ignored(self):
        (self.tmp / "settings.json").write_text(
            '{"listen_enabled": false, "trigger_mode": "select", "theme": "dark"}',
            encoding="utf-8")
        store = ConfigStore()
        store.load()
        self.assertEqual(store.settings.theme, "dark")
        self.assertFalse(hasattr(store.settings, "trigger_mode"))


class ModelPathTest(unittest.TestCase):
    def test_bundled_model_is_located(self):
        path, reason = resolve_model_path(WORKSPACE)
        self.assertIsNotNone(path)
        self.assertTrue(Path(path).is_file(), reason)
        self.assertEqual(Path(path).name, branding.TRANSLATION_MODEL_FILE)


if __name__ == "__main__":
    unittest.main()
