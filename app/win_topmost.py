# -*- coding: utf-8 -*-
"""Windows 窗口置顶：强制 HWND_TOPMOST，且绝不抢键盘焦点。

作者联系方式 · 微信号：TheSun_Also_Rises

背景：Qt 的 WindowStaysOnTopHint / raise_() 只保证「同级 topmost 之间」的顺序，
当用户切换到另一个同样置顶的程序、或某些软件（WPS / 全屏演示 / 输入法候选窗）
重新声明自己的 z 序时，翻译悬浮窗会被压到下层和看不见。Windows 上更可靠的做法是
显式调用 SetWindowPos(HWND_TOPMOST)，并用 SWP_NOACTIVATE 保证不激活窗口、不抢焦点。

本模块是纯逻辑层，非 Windows 平台一律安全返回 False，便于单测与跨平台。
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
# 只改 z 序：不移动、不改尺寸、不激活，避免闪烁与抢焦点。
TOPMOST_FLAGS = SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE


def is_windows() -> bool:
    return hasattr(ctypes, "windll")


def apply_topmost(hwnd: int, enabled: bool = True) -> bool:
    """把窗口设为最顶层（或恢复为普通窗口）。失败返回 False，绝不抛异常。"""
    if not is_windows() or not hwnd:
        return False
    try:
        user32 = ctypes.windll.user32
        user32.SetWindowPos.argtypes = [
            wintypes.HWND, wintypes.HWND,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.UINT,
        ]
        user32.SetWindowPos.restype = wintypes.BOOL
        insert_after = HWND_TOPMOST if enabled else HWND_NOTOPMOST
        return bool(user32.SetWindowPos(
            wintypes.HWND(int(hwnd)), wintypes.HWND(insert_after),
            0, 0, 0, 0, TOPMOST_FLAGS))
    except (AttributeError, OSError, TypeError, ValueError):
        return False
