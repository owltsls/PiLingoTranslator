# -*- coding: utf-8 -*-
"""测试工具：临时目录一律放在工作区内，逐文件清理，绝不整目录删除。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))
for _vendor in sorted(WORKSPACE.parent.glob(".vendor*")):
    if _vendor.is_dir() and str(_vendor) not in sys.path:
        sys.path.insert(0, str(_vendor))

SANDBOX = WORKSPACE / ".sandbox" / "tests"


def make_tmp() -> Path:
    SANDBOX.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="case-", dir=str(SANDBOX)))


def cleanup_tmp(path: Path) -> None:
    if not path.exists():
        return
    for item in sorted(path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        try:
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                item.rmdir()
        except OSError:
            pass
    try:
        path.rmdir()
    except OSError:
        pass
