# -*- coding: utf-8 -*-
"""Qt 标准控件中文化（输入框右键菜单 / 标准对话框）。

作者联系方式 · 微信号：TheSun_Also_Rises

PySide6 自带 qtbase_zh_CN.qm / qt_zh_CN.qm，PyInstaller 会一并分发到
_internal/PySide6/translations/。加载后 QPlainTextEdit / QLineEdit 的
Undo / Redo / Cut / Copy / Paste / Delete / Select All 等标准上下文菜单
自动变为中文，无需逐个控件改写，也不影响本程序自己的中文文案。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTranslator

# QTranslator 必须保持引用，否则会被 GC 回收导致翻译失效。
_INSTALLED: list[QTranslator] = []


def translations_dir() -> Path:
    """定位 Qt 翻译目录，兼容开发态（.vendor）与冻结态（_internal）。"""
    import PySide6
    return Path(PySide6.__file__).resolve().parent / "translations"


def install_chinese_translator(qapp) -> bool:
    """安装 Qt 官方简体中文翻译（幂等）。返回是否至少加载成功一个。"""
    if _INSTALLED:
        return True
    folder = translations_dir()
    # Qt 按「后安装先查询」的顺序查找；qtbase 含实际译文，放在最后安装以优先命中。
    for name in ("qt_zh_CN.qm", "qtbase_zh_CN.qm"):
        path = folder / name
        if not path.is_file():
            continue
        translator = QTranslator(qapp)
        if translator.load(str(path)):
            qapp.installTranslator(translator)
            _INSTALLED.append(translator)
    return bool(_INSTALLED)
