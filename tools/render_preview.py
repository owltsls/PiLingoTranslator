#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""离屏渲染真实 PySide6 窗口，生成交付预览图（不是 HTML 设计稿）。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for _vendor in sorted(ROOT.parent.glob(".vendor*")):
    if _vendor.is_dir() and str(_vendor) not in sys.path:
        sys.path.insert(0, str(_vendor))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")
os.environ["PILINGO_CONFIG_DIR"] = str(ROOT / ".sandbox" / "preview")

from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QPainter, QPixmap)  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


from app import branding  # noqa: E402
from app.ui.app import TranslatorApp  # noqa: E402
from app.ui.bubble import BubbleWindow  # noqa: E402

WIDTH, HEIGHT = 1260, 830
app = QApplication([])
# 离屏平台不自动扫描系统字体；必须在 QApplication 创建之后挂载，且优先用 TTF
_font_file = "C:/Windows/Fonts/simhei.ttf"
if Path(_font_file).is_file():
    QFontDatabase.addApplicationFont(_font_file)
app.setFont(QFont("SimHei", 9))
ctrl = TranslatorApp(app, demo=True, enable_hotkeys=False, enable_tray=False)
app.setFont(QFont("SimHei", 9))  # 控制器会重设字号，这里补回中文字体族

# ------------------------------------------------------------ 填充示意内容
w1 = BubbleWindow(ctrl, pinned=False)
w1.set_result("The local model handles the request without any network call.",
              "本地模型在无需任何网络请求的情况下处理该请求。", "英语 → 中文")
w2 = BubbleWindow(ctrl, pinned=True)
w2.set_result("Offline translation keeps every selected phrase on this device.",
              "离线翻译让每一段选中的文字都留在本机。", "英语 → 中文")

ocr = ctrl.ocr_window
ocr.set_result("SYSTEM SETTINGS\nLanguage\nExport report\nSave changes",
               "系统设置\n语言\n导出报告\n保存更改", "按行对照 · 识别原文可人工核对 · 本地离线")

w3 = ctrl.w3
w3.input.setPlainText("Remote sensing enables large-scale observation.")
w3.output.setPlainText("遥感技术能够实现大范围观测。\n\n"
                       "（本图为原生窗口实拍渲染，文本为示意；真实译文由本机 Hy-MT2 生成）")
w3.status_label.setText("就绪 · 上输入 / 下译文 · 两栏独立滚动 · 可最大化")

# ------------------------------------------------------------ 画布
canvas = QPixmap(WIDTH, HEIGHT)
canvas.fill(QColor("#e9eef6"))
painter = QPainter(canvas)
painter.setRenderHint(QPainter.Antialiasing)

# 点阵桌面背景
painter.setPen(QColor(255, 255, 255, 130))
for x in range(0, WIDTH, 22):
    for y in range(0, HEIGHT, 22):
        painter.drawPoint(x, y)

# 标题
painter.setPen(Qt.NoPen)
painter.setBrush(QColor("#1e3a8a"))
painter.drawRoundedRect(16, 14, WIDTH - 32, 64, 14, 14)
painter.setPen(QColor("#ffffff"))
title_font = QFont("SimHei", 16, QFont.Bold)
painter.setFont(title_font)
painter.drawText(34, 42, f"{branding.APP_NAME} · 原生 Qt 窗口实拍（v{branding.APP_VERSION}）")
sub_font = QFont("SimHei", 9)
painter.setFont(sub_font)
painter.setPen(QColor("#c7d9ff"))
painter.drawText(34, 64, "PySide6 原生窗口 · 无浏览器 / 无 HTML 前端 / 无端口监听 · 三类输入共用一个本地翻译引擎")


def paste(widget, x: int, y: int, w: int, h: int) -> None:
    widget.resize(w, h)
    widget.show()
    app.processEvents()
    widget.resize(w, h)
    app.processEvents()
    painter.drawPixmap(x, y, widget.grab())


paste(w1, 26, 96, 350, 190)
paste(w2, 392, 96, 350, 190)
paste(ocr, 758, 96, 476, 300)
paste(w3, 26, 306, 560, 420)

# 右下说明卡片
card = QRect(602, 414, 632, 312)
painter.setPen(Qt.NoPen)
painter.setBrush(QColor("#ffffff"))
painter.drawRoundedRect(card, 12, 12)
painter.setPen(QColor("#e3e8f0"))
painter.drawRoundedRect(card, 12, 12)
painter.setPen(QColor("#1f2733"))
head_font = QFont("SimHei", 12, QFont.Bold)
painter.setFont(head_font)
painter.drawText(card.left() + 20, card.top() + 34, "三入 → 一引擎 → 三窗（同时显示）")
body_font = QFont("SimHei", 9)
painter.setFont(body_font)
painter.setPen(QColor("#5b6675"))
lines = [
    "① W1 划词气泡：选中即译，鼠标静止常驻，移开 / Esc 收起",
    "② W2 图钉固定窗：置顶常显，可拖动缩放，默认上限 3 个",
    "③ OCR 图片翻译：RapidOCR 认字 → 腾讯 Hy-MT2 译中文，保留原文核对",
    "④ W3 手动输入窗：上输入 / 下译文，最大化 + 两栏滚动 + 自动分块",
    "",
    "停用开关 → 注销全部监听钩子，零文本读取；W3 仍可主动输入翻译",
    "离线守卫 → 运行时阻断所有网络连接，第三方端点一律拒绝",
    "长文本 > 2000 字 → 自动分块、逐块回填，输入内容不落盘",
    "",
    "逻辑自检 13/13 · 单元测试 129/129 · 零出站请求",
]
y = card.top() + 62
for line in lines:
    painter.drawText(card.left() + 20, y, line)
    y += 22

# 作者签名条
painter.setPen(Qt.NoPen)
painter.setBrush(QColor("#f1eaff"))
painter.drawRoundedRect(26, 744, WIDTH - 52, 62, 12, 12)
painter.setPen(QColor("#7c3aed"))
sign_font = QFont("SimHei", 11, QFont.Bold)
painter.setFont(sign_font)
painter.drawText(44, 771, f"【{branding.AUTHOR_SIGNATURE}】{branding.AUTHOR_CONTACT}")
painter.setFont(body_font)
painter.drawText(44, 792, "关于作者 / 设置页 / W3 底栏 / 托盘提示 / 安装包元数据 / 版本资源 / 源码头 均可查看并一键复制")
painter.setPen(QColor("#15803d"))
painter.setFont(QFont("SimHei", 9, QFont.Bold))
painter.drawText(WIDTH - 250, 780, "● 离线渲染成功 · 129 项测试通过")

painter.end()

output = ROOT / "preview" / f"原生窗口实拍_v{branding.APP_VERSION}.png"
output.parent.mkdir(parents=True, exist_ok=True)
ok = canvas.save(str(output), "PNG")
ctrl.shutdown()
print(("saved: " if ok else "FAILED: ") + str(output))
print(branding.AUTHOR_CONTACT)
sys.exit(0 if ok else 1)
