# -*- coding: utf-8 -*-
"""多尺寸布局体检：拖大 / 拖小时是否出现文字重叠、越界或控件被压扁。

作者联系方式 · 微信号：TheSun_Also_Rises

用法：python preview/check_layout_sizes.py
退出码 0 = 全部通过；非 0 = 存在布局缺陷（详情见输出）。
"""
from __future__ import annotations

import os
import sys
from itertools import combinations
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_SHOT_CONFIG = Path(__file__).resolve().parent / ".shot_config"
_SHOT_CONFIG.mkdir(parents=True, exist_ok=True)
os.environ["PILINGO_CONFIG_DIR"] = str(_SHOT_CONFIG)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for v in sorted(ROOT.parent.glob(".vendor*")):
    if v.is_dir():
        sys.path.insert(0, str(v))

from PySide6.QtCore import QPoint, QRect, Qt  # noqa: E402
from PySide6.QtGui import QFont, QFontDatabase  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QCheckBox, QComboBox, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QSpinBox, QWidget,
)

from app.ui.app import TranslatorApp  # noqa: E402
from app.ui.dialogs import AboutDialog, SettingsDialog  # noqa: E402
from app.ui.ocr_window import OCRWindow  # noqa: E402

TEXT_TYPES = (QLabel, QPushButton, QPlainTextEdit, QCheckBox,
              QComboBox, QLineEdit, QSpinBox)


def relative_rect(win: QWidget, w: QWidget) -> QRect:
    top_left = w.mapTo(win, QPoint(0, 0))
    return QRect(top_left, w.size())


def audit(win: QWidget) -> tuple[list[str], list[str], list[str]]:
    """返回 (越界, 文字重叠, 被压扁)。"""
    win_rect = win.rect()
    widgets = [w for w in win.findChildren(QWidget) if w.isVisible()]
    overflow, overlap, collapsed = [], [], []

    for w in widgets:
        r = relative_rect(win, w)
        if r.width() <= 1 or r.height() <= 1:
            collapsed.append(f"{type(w).__name__}:{w.objectName() or (w.text()[:12] if hasattr(w, 'text') else '')}")
        if (r.left() < -2 or r.top() < -2 or
                r.right() > win_rect.right() + 2 or r.bottom() > win_rect.bottom() + 2):
            overflow.append(f"{type(w).__name__} r=({r.left()},{r.top()},{r.width()},{r.height()})")

    leaves = [w for w in widgets if isinstance(w, TEXT_TYPES)]
    for a, b in combinations(leaves, 2):
        if a.isAncestorOf(b) or b.isAncestorOf(a):
            continue
        ra, rb = relative_rect(win, a), relative_rect(win, b)
        inter = ra.intersected(rb)
        if inter.isEmpty():
            continue
        area = inter.width() * inter.height()
        smaller = min(ra.width() * ra.height(), rb.width() * rb.height())
        if smaller > 0 and area / smaller > 0.25:
            ta = (a.text()[:10] if hasattr(a, "text") else "") or a.objectName() or type(a).__name__
            tb = (b.text()[:10] if hasattr(b, "text") else "") or b.objectName() or type(b).__name__
            overlap.append(f"{ta} × {tb} ({area}px²)")
    return overflow, overlap, collapsed


def main() -> int:
    app = QApplication(sys.argv[:1])
    fid = QFontDatabase.addApplicationFont(r"C:/Windows/Fonts/simhei.ttf")
    fam = QFontDatabase.applicationFontFamilies(fid)
    app.setFont(QFont(fam[0] if fam else "SimHei", 11))
    ctrl = TranslatorApp(app, demo=True, enable_hotkeys=False, enable_tray=False)

    cases: list[tuple[str, QWidget, tuple[int, int], tuple[int, int], tuple[int, int]]] = [
        ("手动输入窗", ctrl.w3, (420, 520), (420, 560), (1040, 720)),
        ("图片识别窗", OCRWindow(ctrl), (480, 420), (533, 473), (760, 560)),
        ("设置", SettingsDialog(ctrl), (520, 560), (520, 640), (700, 760)),
        ("关于", AboutDialog(ctrl), (560, 560), (600, 560), (760, 640)),
    ]

    problems = 0
    shots = ROOT / "preview" / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    for name, win, small, normal, large in cases:
        print(f"\n=== {name} ===")
        for label, size in (("最小", small), ("默认", normal), ("放大", large)):
            win.resize(*size)
            win.show()
            app.processEvents()
            app.processEvents()
            overflow, overlap, collapsed = audit(win)
            bad = len(overflow) + len(overlap) + len(collapsed)
            problems += bad
            print(f"  {label} {size[0]}x{size[1]}: 越界 {len(overflow)} / 重叠 {len(overlap)} / 压扁 {len(collapsed)}"
                  f"  [{'FAIL' if bad else 'OK'}]")
            for msg in (overflow + overlap + collapsed)[:5]:
                print("      !", msg)
            if label == "最小":
                win.grab().save(str(shots / f"size_min_{name}.png"))

        # 强行拖到远小于最小值：Qt 必须把尺寸夹回 minimumSize
        win.resize(200, 150)
        app.processEvents()
        w, h = win.width(), win.height()
        mw, mh = win.minimumWidth(), win.minimumHeight()
        clamped = (w >= mw - 1 and h >= mh - 1)
        print(f"  强行拖到 200x150 -> 实际 {w}x{h}（最小 {mw}x{mh}）"
              f"  [{'OK' if clamped else 'FAIL'}]")
        if not clamped:
            problems += 1
        win.hide()

    ctrl.quit_app()
    print(f"\n布局体检结果：{'全部通过' if problems == 0 else f'{problems} 项缺陷'}")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
