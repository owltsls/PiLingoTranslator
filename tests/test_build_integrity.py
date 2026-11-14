# -*- coding: utf-8 -*-
"""构建完整性防呆回归：空文件白名单、哈希同步、关键文件清单。

作者联系方式 · 微信号：TheSun_Also_Rises

针对历史上多次出现的「代码段文件复制为空 / 注入包缺文件仍照样出包」，
本测试直接验证 build_installer.py 里的纯函数，不触发真实编译。
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests import WORKSPACE

_SPEC = importlib.util.spec_from_file_location(
    "build_installer_under_test", WORKSPACE / "build" / "build_installer.py")
assert _SPEC is not None and _SPEC.loader is not None
bi = importlib.util.module_from_spec(_SPEC)
sys.modules["build_installer_under_test"] = bi
_SPEC.loader.exec_module(bi)


class EmptyFileWhitelistTest(unittest.TestCase):
    def test_known_legal_empty_files_are_allowed(self):
        for rel in ("_internal/numpy/py.typed",
                    "_internal/onnxruntime-1.31.1.dist-info/REQUESTED",
                    "_internal/shapely/tests/__init__.py",
                    "_internal/numpy/core/_dtype.pyi",
                    "_internal/numpy/_pyinstaller/__init__.py",
                    "_internal/llama_cpp/server/__init__.py"):
            self.assertTrue(bi._is_legal_empty(Path(rel)), rel)

    def test_business_code_empty_is_rejected(self):
        for rel in ("_internal/app/ui/app.py",
                    "_internal/six.py",
                    "_internal/yaml/__init__.py",
                    "PiLingoTranslator.exe"):
            self.assertFalse(bi._is_legal_empty(Path(rel)), rel)


class SyncTreeVerificationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pilingo_integrity_"))
        self.src = self.tmp / "src"
        self.dst = self.tmp / "dst"
        self.src.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_copy_then_corrupt_target_is_repaired_by_hash_check(self):
        source = self.src / "module.py"
        source.write_text("print('hello')\n", encoding="utf-8")
        bi.sync_tree(self.src, self.dst)
        target = self.dst / "module.py"
        self.assertEqual(target.read_text(encoding="utf-8"), "print('hello')\n")

        # 同长度但内容不同：旧的 size+mtime 判定会漏，哈希校验必须发现并修复。
        target.write_text("print('HELLO')\n", encoding="utf-8")
        bi.sync_tree(self.src, self.dst)
        self.assertEqual(target.read_text(encoding="utf-8"), "print('hello')\n")

    def test_empty_source_business_file_is_detected(self):
        (self.src / "empty.py").write_text("", encoding="utf-8")
        bi.sync_tree(self.src, self.dst)
        issues = bi.verify_tree(self.dst)
        self.assertTrue(any("未登记的空文件" in i for i in issues), issues)

    def test_prune_false_keeps_existing_files(self):
        (self.src / "a.txt").write_text("a", encoding="utf-8")
        self.dst.mkdir()
        (self.dst / "keep.txt").write_text("keep", encoding="utf-8")
        bi.sync_tree(self.src, self.dst, prune=False)
        self.assertTrue((self.dst / "keep.txt").is_file())


class CriticalManifestTest(unittest.TestCase):
    def test_critical_list_covers_runtime_and_icon(self):
        keys = set(bi.CRITICAL_FILES)
        for required in ("PiLingoTranslator.exe", "_internal/six.py",
                         "_internal/yaml/__init__.py",
                         "_internal/rapidocr_onnxruntime/__init__.py",
                         "_internal/resources/PiLingo.ico",
                         "resources/models/bundled/Hy-MT2-1.8B-Q4_K_M.gguf"):
            self.assertIn(required, keys)

    def test_verify_tree_reports_missing_critical_files(self):
        with tempfile.TemporaryDirectory(prefix="pilingo_verify_") as tmp:
            root = Path(tmp)
            issues = bi.verify_tree(root)
            self.assertTrue(any("关键文件缺失" in i for i in issues))
            self.assertTrue(any("PiLingoTranslator.exe" in i for i in issues))

    def test_write_manifest_produces_report(self):
        with tempfile.TemporaryDirectory(prefix="pilingo_manifest_") as tmp:
            root = Path(tmp)
            p = root / "PiLingoTranslator.exe"
            p.write_bytes(b"x" * 1024)
            saved_critical, saved_build = bi.CRITICAL_FILES, bi.BUILD
            bi.CRITICAL_FILES = {"PiLingoTranslator.exe": 100}
            bi.BUILD = root          # 报告写到临时目录，不污染工程
            try:
                report = bi.write_manifest(root)
                import json
                data = json.loads(report.read_text(encoding="utf-8"))
                self.assertEqual(data["total_files"], 1)
                self.assertIn("sha256", data["critical"]["PiLingoTranslator.exe"])
            finally:
                bi.CRITICAL_FILES, bi.BUILD = saved_critical, saved_build


class StaticSourceHealthTest(unittest.TestCase):
    def test_all_runtime_sources_compile(self):
        import py_compile
        bad = []
        for path in (WORKSPACE / "app").rglob("*.py"):
            try:
                py_compile.compile(str(path), doraise=True, cfile=str(
                    Path(tempfile.gettempdir()) / "pilingo_compile_check.pyc"))
            except py_compile.PyCompileError as exc:
                bad.append(f"{path.name}: {exc}")
        self.assertEqual(bad, [], "源码语法错误：" + "; ".join(bad))


if __name__ == "__main__":
    unittest.main()
