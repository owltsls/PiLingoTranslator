# -*- coding: utf-8 -*-
"""运行状态：手动输入状态机、焦点、截图监听开关。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import unittest

from app.config import Settings
from app.state_machine import (AppState, FocusOwner, InvalidTransition,
                               W3State, W3StateMachine)


class W3StateMachineTest(unittest.TestCase):
    def setUp(self):
        self.machine = W3StateMachine()

    def test_initial_state_is_hidden(self):
        self.assertIs(self.machine.state, W3State.HIDDEN)

    def test_normal_flow(self):
        self.machine.show()
        self.machine.transition(W3State.TYPING)
        self.machine.transition(W3State.TRANSLATING)
        self.assertIs(self.machine.transition(W3State.DONE), W3State.DONE)

    def test_illegal_transition_raises(self):
        with self.assertRaises(InvalidTransition):
            self.machine.transition(W3State.TRANSLATING)  # HIDDEN 不能直接进入翻译中
        with self.assertRaises(TypeError):
            self.machine.transition("DONE")  # type: ignore[arg-type]

    def test_hide_resumes_done(self):
        self.machine.show()
        self.machine.transition(W3State.TYPING)
        self.machine.transition(W3State.TRANSLATING)
        self.machine.transition(W3State.DONE)
        self.machine.hide()
        self.assertIs(self.machine.show(), W3State.DONE)

    def test_cancel_translation(self):
        self.machine.show()
        self.machine.transition(W3State.TYPING)
        self.machine.transition(W3State.TRANSLATING)
        self.assertIs(self.machine.cancel_translation(), W3State.TYPING)


class AppStateTest(unittest.TestCase):
    def test_screenshot_hook_follows_ocr_switch(self):
        state = AppState(Settings(ocr_enabled=True))
        self.assertTrue(state.should_register_hooks()["screenshot"])
        state.settings.ocr_enabled = False
        self.assertFalse(state.should_register_hooks()["screenshot"])

    def test_no_system_text_reading_capability(self):
        state = AppState()
        self.assertEqual(state.read_count, 0)
        self.assertFalse(hasattr(state, "capture"))
        self.assertFalse(hasattr(state, "decide_capture"))

    def test_focus_and_own_windows(self):
        state = AppState()
        state.set_focus(FocusOwner.W3_INPUT)
        self.assertIs(state.focus, FocusOwner.W3_INPUT)
        state.register_self_window(4242)
        self.assertTrue(state.is_self_window(4242))
        state.unregister_self_window(4242)
        self.assertFalse(state.is_self_window(4242))
        with self.assertRaises(TypeError):
            state.set_focus("external")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
