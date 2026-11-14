# -*- coding: utf-8 -*-
"""回归：安装版（冻结运行）自检不得依赖磁盘 .py 源码。

作者联系方式 · 微信号：TheSun_Also_Rises

历史缺陷：自检里直接 read_text 读取 app/ui/manual_window.py，
在 PyInstaller 产物中该文件不存在，导致安装版 --self-test 崩溃。
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout

import main


class FrozenSelfTestTest(unittest.TestCase):
    def test_self_test_passes_when_frozen(self):
        original = getattr(sys, "frozen", None)
        sys.frozen = True  # type: ignore[attr-defined]
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                failures = main.self_test()
            output = buf.getvalue()
            self.assertEqual(failures, 0, output)
            self.assertIn("通过", output)
            self.assertNotIn("Traceback", output)
        finally:
            if original is None:
                del sys.frozen  # type: ignore[attr-defined]
            else:
                sys.frozen = original  # type: ignore[attr-defined]


if __name__ == "__main__":
    unittest.main()
