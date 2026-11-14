# -*- coding: utf-8 -*-
"""交付资产校验：作者签名全覆盖、打包元数据、离线口径、CLI 输出。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import subprocess
import sys
import unittest

from app import branding
from tests import WORKSPACE

CONTACT = "TheSun_Also_Rises"


def read(rel: str) -> str:
    return (WORKSPACE / rel).read_text(encoding="utf-8")


class AuthorSignatureTest(unittest.TestCase):
    def test_every_source_file_carries_the_signature(self):
        files = sorted((WORKSPACE / "app").rglob("*.py")) + [
            WORKSPACE / "main.py", WORKSPACE / "build" / "build_installer.py",
            WORKSPACE / "build" / "PiLingoTranslator.spec",
        ]
        missing = [p.name for p in files if CONTACT not in p.read_text(encoding="utf-8")]
        self.assertEqual(missing, [], f"以下源码缺少作者签名：{missing}")
        self.assertGreater(len(files), 10)

    def test_packaging_metadata_carries_the_signature(self):
        for rel in ("build/setup.iss", "build/version_info.txt"):
            with self.subTest(rel=rel):
                self.assertIn(CONTACT, read(rel))

    def test_docs_carry_the_signature(self):
        for rel in ("README.md", "requirements.txt", "licenses/README.md",
                    "licenses/LICENSE_NOTICE.txt", "resources/models/README.md"):
            with self.subTest(rel=rel):
                self.assertIn(CONTACT, read(rel))

    def test_installer_metadata_fields(self):
        iss = read("build/setup.iss")
        self.assertIn("#define MyAppName", iss)
        self.assertIn("#define MyAppPublisher", iss)
        self.assertIn("AppId={{8F6A2D14-9C3E-4B7A-91D2-6C1E4A0B7F31}}", iss)
        self.assertIn("Hy-MT2-1.8B-Q4_K_M.gguf", iss)
        version = read("build/version_info.txt")
        self.assertIn("LegalCopyright", version)
        self.assertIn("CompanyName", version)
        self.assertIn(CONTACT, version)

    def test_new_icon_wired_to_every_surface(self):
        """icon 9 处接入的静态回归：真源 / 安装包 / 向导 / 快捷方式 / 运行时。"""
        import struct
        ico = WORKSPACE / "resources" / "PiLingo.ico"
        self.assertTrue(ico.is_file())
        raw = ico.read_bytes()
        self.assertEqual(raw[:4], b"\x00\x00\x01\x00", "不是合法 ICO")
        frames = struct.unpack_from("<H", raw, 4)[0]
        self.assertGreaterEqual(frames, 5, "icon 缺少多分辨率帧")
        for name in ("wizard_large.png", "wizard_small.png"):
            self.assertTrue((WORKSPACE / "resources" / name).is_file(), name)
        iss = read("build/setup.iss")
        for token in ("SetupIconFile", "WizardImageFile", "WizardSmallImageFile"):
            self.assertIn(token, iss)
        self.assertGreaterEqual(iss.count("IconFilename"), 4, "快捷方式未全部指定新 icon")
        spec = read("build/PiLingoTranslator.spec")
        self.assertIn('PiLingo.ico"), "resources"', spec, "冻结态读不到 icon 文件")
        app_py = read("app/ui/app.py")
        self.assertIn("setWindowIcon", app_py)
        tray_py = read("app/ui/tray.py")
        self.assertIn("app_icon_path", tray_py)

    def test_spec_defines_inprocess_engine_and_version_resource(self):
        spec = read("build/PiLingoTranslator.spec")
        self.assertIn("app.ui.app", spec)
        self.assertIn("version_info.txt", spec)
        self.assertIn("HIDDEN", spec)

    def test_build_installer_static_check_passes(self):
        result = subprocess.run(
            [sys.executable, "build/build_installer.py", "--check"],
            cwd=str(WORKSPACE), capture_output=True, text=True, encoding="utf-8",
            timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("静态自检通过", result.stdout)

    def test_cli_version_and_self_test(self):
        version = subprocess.run(
            [sys.executable, "main.py", "--version"],
            cwd=str(WORKSPACE), capture_output=True, text=True, encoding="utf-8",
            timeout=30)
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertIn(CONTACT, version.stdout)
        self.assertIn(f"v{branding.APP_VERSION}", version.stdout)

        check = subprocess.run(
            [sys.executable, "main.py", "--self-test"],
            cwd=str(WORKSPACE), capture_output=True, text=True, encoding="utf-8",
            timeout=60)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        # 不硬编码项数：自检会随验收项扩充，只要「全部通过」即可。
        import re
        m = re.search(r"逻辑自检：(\d+)/(\d+) 通过", check.stdout)
        self.assertIsNotNone(m, check.stdout)
        self.assertEqual(m.group(1), m.group(2), check.stdout)

    def test_no_web_ui_in_runtime_sources(self):
        runtime = sorted((WORKSPACE / "app").rglob("*.py"))
        offenders = []
        for path in runtime:
            # offline_guard.py 自身保存了禁用词正则，跳过（与其静态扫描逻辑一致）
            if path.name == "offline_guard.py":
                continue
            text = path.read_text(encoding="utf-8")
            for token in ("QWebEngineView", "webbrowser.open", "http.server",
                          "localhost:8911", "QWebEnginePage"):
                if token in text:
                    offenders.append(f"{path.name}: {token}")
        self.assertEqual(offenders, [], "运行时源码出现 Web 端架构：" + str(offenders))


if __name__ == "__main__":
    unittest.main()
