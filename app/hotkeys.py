# -*- coding: utf-8 -*-
"""全局快捷键：纯逻辑解析 + Windows 平台注册层（延迟导入，可跨平台测试）。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import ctypes
import threading
from dataclasses import dataclass
from typing import Callable

# Windows RegisterHotKey 修饰键
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

_MODIFIERS = {
    "ctrl": MOD_CONTROL, "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN, "meta": MOD_WIN, "super": MOD_WIN,
}

_NAMED_KEYS = {
    "enter": 0x0D, "return": 0x0D, "space": 0x20, "tab": 0x09,
    "esc": 0x1B, "escape": 0x1B, "ins": 0x2D, "insert": 0x2D,
    "del": 0x2E, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "pgup": 0x21, "pageup": 0x21, "pgdn": 0x22, "pagedown": 0x22,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "backspace": 0x08,
}
for _i in range(1, 13):
    _NAMED_KEYS[f"f{_i}"] = 0x70 + _i - 1


class HotkeyError(ValueError):
    """快捷键字符串非法。"""


@dataclass(frozen=True)
class Hotkey:
    modifiers: int
    vk: int
    display: str

    @property
    def win_modifiers(self) -> int:
        return self.modifiers | MOD_NOREPEAT


def parse_hotkey(spec: str) -> Hotkey:
    """把 ``Ctrl+Shift+T`` 解析成平台无关的热键对象。

    规则：至少一个修饰键；最后一个 token 为按键；字母 / 数字 / F1-F12 / 命名键。
    """
    if not isinstance(spec, str):
        raise HotkeyError("快捷键必须是字符串")
    parts = [p.strip() for p in spec.split("+") if p.strip()]
    if len(parts) < 2:
        raise HotkeyError("全局快捷键必须包含至少一个修饰键")
    *mods, key = parts
    modifiers = 0
    for mod in mods:
        flag = _MODIFIERS.get(mod.lower())
        if flag is None:
            raise HotkeyError(f"未知修饰键：{mod}")
        modifiers |= flag
    if modifiers == 0:
        raise HotkeyError("全局快捷键必须包含至少一个修饰键")

    low = key.lower()
    if low in _MODIFIERS:
        raise HotkeyError("缺少主键")
    if len(key) == 1 and (key.isalpha() or key.isdigit()):
        vk = ord(key.upper())
    elif low in _NAMED_KEYS:
        vk = _NAMED_KEYS[low]
    else:
        raise HotkeyError(f"未知主键：{key}")

    canonical_mods = []
    for name, flag in (("Ctrl", MOD_CONTROL), ("Alt", MOD_ALT),
                       ("Shift", MOD_SHIFT), ("Win", MOD_WIN)):
        if modifiers & flag:
            canonical_mods.append(name)
    display_key = key.upper() if len(key) == 1 else key.title()
    return Hotkey(modifiers, vk, "+".join(canonical_mods + [display_key]))


def is_valid_hotkey(spec: str) -> bool:
    try:
        parse_hotkey(spec)
        return True
    except HotkeyError:
        return False


class GlobalHotkeyManager:
    """Windows 全局热键注册（独立消息循环线程）。

    非 Windows 平台或注册失败时优雅降级：``start()`` 返回 False，
    并通过 ``errors`` 暴露原因，绝不抛异常中断主程序。
    """

    def __init__(self, on_trigger: Callable[[str], None] | None = None):
        self._on_trigger = on_trigger or (lambda action: None)
        self._specs: dict[str, str] = {}
        self._ids: dict[int, str] = {}
        self._thread: threading.Thread | None = None
        self._running = False
        self._thread_id: int | None = None
        self._ready = threading.Event()
        self.errors: list[str] = []
        self.registered: list[str] = []

    @property
    def available(self) -> bool:
        return ctypes.windll is not None if hasattr(ctypes, "windll") else False

    def set_bindings(self, bindings: dict[str, str]) -> None:
        """action -> hotkey spec，例如 ``{"w3": "Ctrl+Shift+I"}``。"""
        clean: dict[str, str] = {}
        for action, spec in bindings.items():
            try:
                hk = parse_hotkey(spec)
            except HotkeyError as exc:
                self.errors.append(f"{action}: {exc}")
                continue
            clean[action] = hk.display
        self._specs = clean

    def start(self) -> bool:
        if self._thread is not None:
            return self._running
        if not hasattr(ctypes, "windll"):
            self.errors.append("当前平台不是 Windows，全局热键不可用（应用内快捷键仍可用）")
            return False
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="pilingo-hotkeys", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=2.0)
        return bool(self.registered)

    def stop(self) -> None:
        self._running = False
        if self._thread_id and hasattr(ctypes, "windll"):
            try:
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
            except Exception:
                pass
        self._thread = None

    def trigger(self, action: str) -> None:
        """供测试 / 应用内快捷键直接复用动作分发。"""
        self._on_trigger(action)

    # ------------------------------------------------------------ 平台实现
    def _loop(self) -> None:
        from ctypes import wintypes  # 延迟：非 Windows 不导入

        user32 = ctypes.windll.user32
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        id_to_action: dict[int, str] = {}
        registered_ids: list[int] = []

        for idx, (action, _) in enumerate(self._specs.items(), start=1):
            try:
                hk = parse_hotkey(self._specs[action])
                ok = user32.RegisterHotKey(None, idx, hk.win_modifiers, hk.vk)
                if ok:
                    id_to_action[idx] = action
                    registered_ids.append(idx)
                    self.registered.append(action)
                else:
                    self.errors.append(f"{action}: 热键已被其它程序占用")
            except Exception as exc:  # pragma: no cover - 平台相关
                self.errors.append(f"{action}: 注册失败 {exc}")
        self._ids = id_to_action
        self._ready.set()

        msg = wintypes.MSG()
        while self._running:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret in (0, -1):
                break
            if msg.message == 0x0312:  # WM_HOTKEY
                action = id_to_action.get(int(msg.wParam))
                if action:
                    try:
                        self._on_trigger(action)
                    except Exception:
                        pass
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        for rid in registered_ids:
            try:
                user32.UnregisterHotKey(None, rid)
            except Exception:
                pass
        self._running = False
