# -*- coding: utf-8 -*-
"""悬浮窗默认置顶回归。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import unittest

from app.win_topmost import apply_topmost, is_windows


class TopmostTest(unittest.TestCase):
    def test_invalid_hwnd_is_safe(self):
        self.assertFalse(apply_topmost(0, True))
        self.assertFalse(apply_topmost(-1, False))

    @unittest.skipUnless(is_windows(), "仅 Windows 有 SetWindowPos")
    def test_real_window_can_be_set_topmost(self):
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        u.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID,
        ]
        u.CreateWindowExW.restype = wintypes.HWND
        hwnd = u.CreateWindowExW(0, "Static", "pilingo-topmost-check", 0,
                                 0, 0, 1, 1, None, None, None, None)
        if not hwnd:
            self.skipTest("当前会话无法创建 Win32 窗口")
        try:
            self.assertTrue(apply_topmost(int(hwnd), True))
            self.assertTrue(apply_topmost(int(hwnd), False))
        finally:
            u.DestroyWindow(wintypes.HWND(hwnd))


if __name__ == "__main__":
    unittest.main()
