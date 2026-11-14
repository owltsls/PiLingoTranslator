# -*- coding: utf-8 -*-
"""离屏渲染并截图所有窗体，用于产品评审。

不联网、不加载 GGUF（demo 模式），每个窗体填入示例内容后抓取为 PNG，
合成到中性背景上，方便看清卡片本体与朱红主题。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 用独立临时配置目录：避免读到本机真实配置里的 w3_maximized / 旧窗口尺寸，
# 否则截图会因「上次最大化过」把窗口撑到 1000+ 宽，与设计稿对不上。
_SHOT_CONFIG = Path(__file__).resolve().parent / ".shot_config"
_SHOT_CONFIG.mkdir(parents=True, exist_ok=True)
os.environ["PILINGO_CONFIG_DIR"] = str(_SHOT_CONFIG)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for v in sorted(ROOT.parent.glob(".vendor*")):
    if v.is_dir():
        sys.path.insert(0, str(v))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter
from PySide6.QtWidgets import QApplication, QSplitter

from app.ui.app import TranslatorApp
from app.ui.ocr_window import OCRWindow, ScreenCaptureDialog
from app.ui.dialogs import SettingsDialog, AboutDialog


OUT = ROOT / "preview" / "shots"
OUT.mkdir(parents=True, exist_ok=True)


def render(widget, name: str, pad: int = 30, is_dialog: bool = False) -> None:
    widget.show()
    if is_dialog:
        widget.adjustSize()
    QApplication.instance().processEvents()
    QApplication.instance().processEvents()
    pix = widget.grab()
    img = pix.toImage().convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    canvas = QImage(w + pad * 2, h + pad * 2, QImage.Format_ARGB32)
    canvas.fill(QColor(233, 230, 226))
    p = QPainter(canvas)
    p.drawImage(pad, pad, img)
    p.end()
    path = OUT / f"{name}.png"
    canvas.save(str(path))
    print(f"[OK] {name}.png  ({w}x{h})")


def main() -> int:
    qapp = QApplication(sys.argv[:1])
    # 离屏渲染需要显式挂载中文字体（msyh.ttc 会 segfault，用 simhei.ttf）。
    _fid = QFontDatabase.addApplicationFont(r"C:/Windows/Fonts/simhei.ttf")
    _families = QFontDatabase.applicationFontFamilies(_fid)
    _cjk = _families[0] if _families else "SimHei"
    # 一并挂载 Segoe UI Symbol，让几何/丁巴特图标（✕ ▢ ▣ ⚙ ⧉）在截图中可见；
    # 彩色 emoji（📌 🔒 ✍）仍需系统 emoji 字体，仅截图环境缺字，真实程序不受影响。
    for _sym in (r"C:/Windows/Fonts/seguisym.ttf", r"C:/Windows/Fonts/segoeuisymbol.ttf"):
        if Path(_sym).is_file():
            QFontDatabase.addApplicationFont(_sym)
    qapp.setFont(QFont(_cjk, 13))
    ctrl = TranslatorApp(qapp, demo=True, enable_hotkeys=False, enable_tray=False)

    # ---- W3 手动输入翻译窗（普通） ----
    w3 = ctrl.w3
    w3.input.setPlainText(
        "Offline translation keeps every selected phrase on this device.\n"
        "The local model handles the request without any network call.")
    w3.output.setPlainText(
        "离线翻译让每个被选中的短语都留在本机。\n本地模型在没有任何网络请求的情况下完成翻译。")
    w3.status_hint.set_text("完成 · 2 块 · 4200 ms · 本地离线")
    # 显式给尺寸，不依赖配置目录残留的 w3_geometry（否则会被工具栏撑成 800x800）。
    w3.setGeometry(120, 120, 420, 560)
    w3.show()
    w3.raise_()
    render(w3, "03_w3_normal")

    # ---- W3 手动输入翻译窗（大窗 / 最大化，展示双栏独立滚动） ----
    w3b = ctrl.w3
    w3b.input.setPlainText(
        "Paragraph 1\nOffline translation keeps every selected phrase on this device.\n\n"
        "Paragraph 2\nThe local model handles the request without any network call.\n\n"
        "Paragraph 3\nReviewers can verify this by capturing outbound traffic.\n\n"
        "（此处填入了长文本，上下两栏各自独立滚动）")
    w3b.output.setPlainText(
        "段落 1\n离线翻译让每个被选中的短语都留在本机。\n\n"
        "段落 2\n本地模型在没有任何网络请求的情况下完成翻译。\n\n"
        "段落 3\n评审者可以通过抓取出站流量来验证这一点。\n\n"
        "（译文区与原文区各自拥有独立滚动条）")
    w3b.status_hint.set_text("完成 · 3 块 · 6800 ms · 本地离线")
    w3b.setGeometry(60, 60, 1040, 720)
    w3b.splitter.setOrientation(Qt.Horizontal)
    w3b.splitter.setSizes([520, 520])
    w3b._maximized = True
    w3b.set_corner_subtitle("最大化")
    w3b.max_btn.setText("■")
    w3b.max_btn.setToolTip("还原为小窗")
    w3b.show()
    w3b.raise_()
    render(w3b, "04_w3_maximized")

    # ---- OCR 图片识别翻译窗（自然尺寸） ----
    ocr: OCRWindow = ctrl.ocr_window
    ocr.set_result(
        "OFFLINE\nTRANSLATION\nkeeps data on this device",
        "离线翻译\n让数据留在本机",
        "识别与翻译完成 · 本地离线")
    ocr.show()
    render(ocr, "05_ocr")

    # ---- 截图框选遮罩（模拟选中区域） ----
    cap = ScreenCaptureDialog()
    cap.setGeometry(0, 0, 960, 560)
    cap._selecting = True
    cap._origin = QPoint(170, 130)
    cap._current = QPoint(760, 430)
    cap.repaint()
    render(cap, "06_screencapture")

    # ---- 设置对话框 ----
    settings = SettingsDialog(ctrl)
    render(settings, "07_settings", is_dialog=True)

    # ---- 关于对话框（高度已由 _fit_to_content 按正文自适应，不能再 adjustSize 覆盖） ----
    about = AboutDialog(ctrl)
    render(about, "08_about")

    ctrl.quit_app()
    print(f"\n截图已保存到：{OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
