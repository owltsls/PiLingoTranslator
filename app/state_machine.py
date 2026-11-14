# -*- coding: utf-8 -*-
"""运行状态：手动输入窗状态机与焦点归属。

作者联系方式 · 微信号：TheSun_Also_Rises

划词取词 / 剪贴板监听 / 悬浮气泡模块已按产品决策整体移除。
本模块不再包含任何系统文本读取能力，也不注册任何监听钩子。
"""
from __future__ import annotations

from enum import Enum

from .config import Settings


class FocusOwner(Enum):
    """当前焦点归属，用于手动输入窗防自触发。"""
    EXTERNAL = "external"
    OWN_WINDOW = "own_window"
    W3_INPUT = "w3_input"


class W3State(Enum):
    HIDDEN = "hidden"
    EMPTY = "empty"
    TYPING = "typing"
    TRANSLATING = "translating"
    DONE = "done"


class InvalidTransition(Exception):
    """手动输入窗状态机非法跳转。"""


class W3StateMachine:
    """隐藏 → 显示(空白/保留) → 输入中 → 翻译中 → 已出译文。"""

    _ALLOWED: dict[W3State, set[W3State]] = {
        W3State.HIDDEN: {W3State.EMPTY, W3State.DONE},
        W3State.EMPTY: {W3State.TYPING, W3State.HIDDEN},
        W3State.TYPING: {W3State.TRANSLATING, W3State.EMPTY, W3State.HIDDEN},
        W3State.TRANSLATING: {W3State.DONE, W3State.TYPING, W3State.HIDDEN},
        W3State.DONE: {W3State.TYPING, W3State.EMPTY, W3State.HIDDEN},
    }

    def __init__(self) -> None:
        self.state = W3State.HIDDEN
        self._resume = W3State.EMPTY
        self.history: list[W3State] = [W3State.HIDDEN]

    def transition(self, target: W3State) -> W3State:
        if not isinstance(target, W3State):
            raise TypeError("target 必须是 W3State")
        if target not in self._ALLOWED[self.state]:
            raise InvalidTransition(f"{self.state.value} → {target.value} 非法")
        if target is W3State.HIDDEN and self.state is not W3State.HIDDEN:
            self._resume = W3State.DONE if self.state is W3State.DONE else W3State.EMPTY
        self.state = target
        self.history.append(target)
        return self.state

    def hide(self) -> W3State:
        if self.state is not W3State.HIDDEN:
            return self.transition(W3State.HIDDEN)
        return self.state

    def show(self) -> W3State:
        if self.state is W3State.HIDDEN:
            return self.transition(self._resume)
        return self.state

    def cancel_translation(self) -> W3State:
        if self.state is W3State.TRANSLATING:
            return self.transition(W3State.TYPING)
        return self.state


class AppState:
    """极简运行状态：只保留焦点与自有窗口登记。

    划词模块删除后不再有任何 capture / decide_capture / UIA / 剪贴板逻辑；
    ``read_count`` 恒为 0，用于「零系统文本读取」的验收断言。
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.focus = FocusOwner.EXTERNAL
        self._self_hwnds: set[int] = set()
        self.read_count = 0

    # ------------------------------------------------------------ 截图监听
    @property
    def screenshot_enabled(self) -> bool:
        return bool(self.settings.ocr_enabled)

    def should_register_hooks(self) -> dict[str, bool]:
        """仅剩截图 OCR 一个开关；不存在任何后台文本监听。"""
        return {"screenshot": self.screenshot_enabled}

    # ------------------------------------------------------------ 自有窗口
    def register_self_window(self, hwnd: int) -> None:
        self._self_hwnds.add(int(hwnd))

    def unregister_self_window(self, hwnd: int) -> None:
        self._self_hwnds.discard(int(hwnd))

    def is_self_window(self, hwnd: int | None) -> bool:
        return hwnd is not None and int(hwnd) in self._self_hwnds

    def set_focus(self, owner: FocusOwner) -> None:
        if not isinstance(owner, FocusOwner):
            raise TypeError("owner 必须是 FocusOwner")
        self.focus = owner
