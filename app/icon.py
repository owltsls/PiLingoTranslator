# -*- coding: utf-8 -*-
"""新 icon 唯一真源的运行时定位。

作者联系方式 · 微信号：TheSun_Also_Rises

开发态读 ``resources/PiLingo.ico``；冻结态 PyInstaller 把它放在
``_internal/resources/PiLingo.ico``（见 build/PiLingoTranslator.spec 的 datas）。
历史上冻结态 __file__ 指向临时解包目录，所以这里一律以 sys.executable 为基准。
"""
from __future__ import annotations

import sys
from pathlib import Path

ICON_NAME = "PiLingo.ico"


def app_icon_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "_internal" / "resources" / ICON_NAME
    return Path(__file__).resolve().parent.parent / "resources" / ICON_NAME
