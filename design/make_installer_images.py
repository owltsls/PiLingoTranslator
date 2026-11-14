# -*- coding: utf-8 -*-
"""从唯一 icon 真源生成 Inno Setup 所需的向导图。

作者联系方式 · 微信号：TheSun_Also_Rises

产物：
  resources/wizard_large.png   164x314  modern 向导左侧大图
  resources/wizard_small.png   55x55    向导右上角小图

用法：python design/make_installer_images.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "resources"
ICO = OUT / "PiLingo.ico"

from PySide6.QtCore import Qt, QRectF  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def build() -> None:
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv[:1])
    # 离屏渲染中文必须显式挂载字体（msyh.ttc 会 segfault）
    fid = QFontDatabase.addApplicationFont(r"C:/Windows/Fonts/simhei.ttf")
    families = QFontDatabase.applicationFontFamilies(fid)
    family = families[0] if families else "SimHei"

    if not ICO.is_file():
        raise SystemExit(f"缺少 icon 真源：{ICO}")
    icon = QIcon(str(ICO))

    # ---- 大图：暖白底 + 顶部朱红色块 + 居中图标 + 产品名 ----
    w, h = 164, 314
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor("#faf4f1"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#c8402f"))
    p.drawRoundedRect(QRectF(0, 0, w, 96), 0, 0)
    pm = icon.pixmap(72, 72)
    p.drawPixmap((w - 72) // 2, 18, pm)
    p.setPen(QColor("#c8402f"))
    f = QFont(family, 15)
    f.setBold(True)
    p.setFont(f)
    p.drawText(QRectF(0, 116, w, 34), Qt.AlignCenter, "π-Lingo")
    p.setPen(QColor("#6b5d59"))
    f2 = QFont(family, 10)
    p.setFont(f2)
    p.drawText(QRectF(0, 152, w, 28), Qt.AlignCenter, "离线翻译")
    f3 = QFont(family, 8)
    p.setFont(f3)
    p.setPen(QColor("#a89a95"))
    p.drawText(QRectF(12, 250, w - 24, 50), Qt.AlignCenter | Qt.TextWordWrap,
               "100% 本地离线\n数据不出本机")
    p.end()
    large = OUT / "wizard_large.png"
    img.save(str(large))
    print("[OK]", large.name, large.stat().st_size, "B")

    # ---- 小图：透明底 + 图标 ----
    small_img = QImage(55, 55, QImage.Format_ARGB32)
    small_img.fill(Qt.transparent)
    p2 = QPainter(small_img)
    p2.setRenderHint(QPainter.Antialiasing, True)
    p2.drawPixmap(3, 3, icon.pixmap(49, 49))
    p2.end()
    small = OUT / "wizard_small.png"
    small_img.save(str(small))
    print("[OK]", small.name, small.stat().st_size, "B")


if __name__ == "__main__":
    build()
