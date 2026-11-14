# -*- coding: utf-8 -*-
"""设置对话框与「关于作者」对话框（作者签名与联系方式在这里展示）。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QLayout, QLineEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout,
)

from .. import branding
from ..hotkeys import is_valid_hotkey
from .theme import FONT_BODY_PX
from .widgets import AuthorSignature, CornerTag, set_cls


class SettingsDialog(QDialog):
    """所有配置集中在一个界面；保存后由控制器统一校验与持久化。"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        s = controller.store.settings
        self.setWindowTitle(f"设置 · {branding.APP_NAME}")
        # 划词分组删除后内容变短；数值框 / 下拉统一紧凑化，最小值由布局体检复验。
        self.setMinimumSize(520, 560)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 76, 16, 16)
        root.setSpacing(10)
        # 左上角品牌标签（对话框无圆角遮罩，以四角圆角的小标签内嵌呈现）
        self.corner_tag = CornerTag("设置", "偏好设置", False, self)
        self.corner_tag.move(12, 12)

        # ------------------------------------------------------------ 截图监听
        g1 = QGroupBox("截图监听与识别")
        f1 = QFormLayout(g1)
        self.ocr_box = QCheckBox("启用截图监听（OCR 图片识别）")
        self.ocr_box.setChecked(s.ocr_enabled)
        f1.addRow(self.ocr_box)
        root.addWidget(g1)

        # ------------------------------------------------------------ 快捷键
        g2 = QGroupBox("全局快捷键（格式如 Ctrl+Shift+I）")
        f2 = QFormLayout(g2)
        self.hk_w3 = QLineEdit(s.hotkey_w3)
        self.hk_w3.setPlaceholderText("例如 Ctrl+Shift+I")
        self.hk_ocr = QLineEdit(s.hotkey_ocr)
        self.hk_ocr.setPlaceholderText("例如 Ctrl+Shift+O")
        f2.addRow("手动输入翻译窗", self.hk_w3)
        f2.addRow("截图 OCR 识别", self.hk_ocr)
        root.addWidget(g2)

        # ------------------------------------------------------------ 手动输入翻译窗
        g3 = QGroupBox("手动输入翻译窗")
        f3 = QFormLayout(g3)
        self.w3_top = QCheckBox("窗口始终置顶")
        self.w3_top.setChecked(s.w3_always_on_top)
        self.w3_clear = QCheckBox("关闭时清空内容")
        self.w3_clear.setChecked(s.w3_clear_on_close)
        self.block_chars = QSpinBox()
        self.block_chars.setRange(200, 10000)
        self.block_chars.setSingleStep(200)
        self.block_chars.setValue(s.max_block_chars)
        auto_note = QLabel("输入停止 1 秒后自动翻译；无需点按按钮，也无需快捷键")
        set_cls(auto_note, "sub")
        block_note = QLabel("超长文本按此字数分块，逐块回填、不截断原文")
        set_cls(block_note, "sub")
        # 用户定稿：「窗口始终置顶」与「关闭时清空内容」横版并排，不再上下两行。
        flags = QHBoxLayout()
        flags.setContentsMargins(0, 0, 0, 0)
        flags.setSpacing(22)
        flags.addWidget(self.w3_top)
        flags.addWidget(self.w3_clear)
        flags.addStretch(1)
        f3.addRow(flags)
        f3.addRow("长文本单块字数", self.block_chars)
        f3.addRow("", block_note)
        f3.addRow("自动翻译", auto_note)
        root.addWidget(g3)

        state = QLabel(f"引擎状态：{controller.engine_status()}")
        set_cls(state, "sub")
        root.addWidget(state)

        # ------------------------------------------------------------ 底部色块：签名在左、操作在右（与设计稿一致）
        footer = QFrame()
        footer.setObjectName("footer")
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(10, 7, 10, 7)
        foot_lay.setSpacing(6)
        foot_lay.addWidget(AuthorSignature(lambda: controller.copy_to_clipboard(branding.AUTHOR_WECHAT)))
        foot_lay.addStretch(1)
        # 与「关于」页完全同构：签名左 + 弹性留白 + 右下角唯一主按钮。
        save = QPushButton("保存设置")
        set_cls(save, "primary")
        save.clicked.connect(self._save)
        foot_lay.addWidget(save)
        root.addWidget(footer)
        self.result_warnings: list[str] = []

    def _save(self, _checked: bool = False) -> None:
        for field in (self.hk_w3, self.hk_ocr):
            if not is_valid_hotkey(field.text().strip()):
                self.controller.notify(f"快捷键格式不正确：{field.text()}")
                return
        values = {
            "ocr_enabled": self.ocr_box.isChecked(),
            "hotkey_w3": self.hk_w3.text().strip(),
            "hotkey_ocr": self.hk_ocr.text().strip(),
            "w3_always_on_top": self.w3_top.isChecked(),
            "w3_clear_on_close": self.w3_clear.isChecked(),
            "max_block_chars": self.block_chars.value(),
        }
        self.result_warnings = self.controller.apply_settings(values)
        self.accept()


class AboutDialog(QDialog):
    """关于：产品、离线架构、许可证与作者签名联系方式。"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle(f"关于 · {branding.APP_NAME}")
        # 精简后正文只剩模型 / 协议 + 末尾作者两行，收紧高度避免大片空白。
        self.setMinimumSize(560, 460)
        root = QVBoxLayout(self)
        # 允许窗口高度按正文自适应（默认约束会把 resize 回弹成 layout sizeHint）。
        root.setSizeConstraint(QLayout.SetNoConstraint)
        root.setContentsMargins(16, 76, 16, 16)
        root.setSpacing(8)
        # 左上角品牌标签
        self.corner_tag = CornerTag("关于", "π-Lingo", False, self)
        self.corner_tag.move(12, 12)
        # 用户定稿：红框内的产品元信息行（版本 + 标语）整行删除。
        # 左上角「关于 / π-Lingo」是唯一标题，正文直接从【】分区开始，
        # 分区标题顶格、条目行缩进 2 个全角空格，形成清晰层次。
        # 正文为完整的技术与许可说明，**不再包含作者联系方式**；
        # 联系方式统一由底栏那行可点击复制的签名承载。
        lines = list(branding.about_lines())
        body = QLabel("\n".join(lines))
        body.setWordWrap(True)
        body.setTextFormat(Qt.PlainText)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        body.setStyleSheet(f"font-size:{FONT_BODY_PX}px;color:#241a18;"
                           "background:transparent;padding:10px 12px")
        # 放进滚动区：内容再多也不会被裁，只在需要时出现细滚动条。
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:0}")
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # 底部色块：签名在左、关闭按钮在右（与设置页同一范式）
        footer = QFrame()
        footer.setObjectName("footer")
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(10, 7, 10, 7)
        foot_lay.setSpacing(6)
        foot_lay.addWidget(AuthorSignature(lambda: controller.copy_to_clipboard(branding.AUTHOR_WECHAT)))
        foot_lay.addStretch(1)
        close_btn = QPushButton("关闭")
        set_cls(close_btn, "primary")
        close_btn.clicked.connect(self.accept)
        foot_lay.addWidget(close_btn)
        root.addWidget(footer)
        # 按正文实际高度自适应：默认一屏放完（上限 880），确实放不下才走滚动。
        self._fit_to_content(body, lines)

    def _fit_to_content(self, body: QLabel, lines: list[str]) -> None:
        """按正文估算需要的高度并 resize。

        未显示时 QLabel.heightForWidth() 会返回 -1，故用 QFontMetrics 自己折行估算。
        """
        text_w = max(320, 600 - 32 - 24)   # 窗口宽 - root 左右边距 - 正文内边距
        fm = body.fontMetrics()
        # 实测校准：12px 字号下 fontMetrics().lineSpacing() = 12，29 行正文
        # 实测高 374px（含 24px 内边距），窗口 560 高时刚好铺满且无滚动条。
        # 旧公式把 row_h 抬到 16、开销取 196，会算出 684 导致底部大片空白。
        row_h = max(fm.lineSpacing(), 12)
        rows = 0
        for line in lines:
            if not line:
                rows += 1
                continue
            width = fm.horizontalAdvance(line)
            rows += max(1, (width + text_w - 1) // text_w)
        # 再删除红框内的产品元信息行后，固定开销由 161 降为 141（实测少 20px）。
        # 目标：600×513，viewport 374px = 正文 374px，零滚动、零空白。
        need = rows * row_h + 24 + 141  # 24=正文内边距，141=底栏/边距固定开销
        self.resize(600, max(self.minimumHeight(), min(need, 880)))
