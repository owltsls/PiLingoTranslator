# -*- coding: utf-8 -*-
"""离线守卫：运行时阻断外连、端点一律拒绝、源码静态扫描。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import socket
import unittest
from pathlib import Path

from app import offline_guard as guard
from tests import WORKSPACE


class OfflineGuardTest(unittest.TestCase):
    def tearDown(self):
        guard.disable()
        guard.reset_attempts()

    def test_enable_blocks_all_connections(self):
        guard.enable()
        self.assertTrue(guard.is_enabled())
        for address in (("8.8.8.8", 53), ("127.0.0.1", 8080)):
            with self.subTest(address=address):
                with self.assertRaises(guard.NetworkBlockedError):
                    with socket.socket() as sock:
                        sock.connect(address)
        self.assertEqual(len(guard.blocked_attempts()), 2)

    def test_create_connection_blocked(self):
        guard.enable()
        with self.assertRaises(guard.NetworkBlockedError):
            socket.create_connection(("127.0.0.1", 9), timeout=0.1)
        self.assertIn("零出站", guard.BLOCK_REASON)

    def test_disable_restores_original_functions(self):
        original = socket.socket.connect
        guard.enable()
        self.assertIsNot(socket.socket.connect, original)
        guard.disable()
        self.assertIs(socket.socket.connect, original)
        self.assertFalse(guard.is_enabled())

    def test_enable_disable_are_idempotent(self):
        self.assertTrue(guard.enable())
        self.assertFalse(guard.enable())
        self.assertTrue(guard.disable())
        self.assertFalse(guard.disable())

    def test_reset_attempts(self):
        guard.enable()
        try:
            with socket.socket() as sock:
                sock.connect(("1.1.1.1", 80))
        except guard.NetworkBlockedError:
            pass
        self.assertTrue(guard.blocked_attempts())
        guard.reset_attempts()
        self.assertEqual(guard.blocked_attempts(), ())

    def test_every_endpoint_is_rejected_including_loopback(self):
        for url in ("", "http://127.0.0.1:8080/v1", "https://api.example.com/translate",
                    "ws://localhost:9999", "ftp://example.com", "not-a-url"):
            with self.subTest(url=url):
                allowed, reason = guard.validate_endpoint(url)
                self.assertFalse(allowed)
                self.assertTrue(reason)

    def test_source_scan_finds_no_network_calls(self):
        findings = guard.scan_sources_for_network_calls(WORKSPACE / "app")
        self.assertEqual(findings, [], "\n".join(findings))

    def test_source_scan_detects_violations(self):
        from tests import cleanup_tmp, make_tmp
        tmp = make_tmp()
        try:
            (tmp / "bad.py").write_text("import requests\nrequests.get('https://x')\n",
                                        encoding="utf-8")
            (tmp / "good.py").write_text("x = 1\n", encoding="utf-8")
            findings = guard.scan_sources_for_network_calls(tmp)
            self.assertTrue(any("requests" in item for item in findings))
            self.assertEqual(len(findings), 1)
        finally:
            cleanup_tmp(tmp)

    def test_missing_dir_reports_finding(self):
        self.assertTrue(guard.scan_sources_for_network_calls(Path("Z:/no-such-dir")))


if __name__ == "__main__":
    unittest.main()
