# -*- coding: utf-8 -*-
"""Qt 样式表：品牌主色统一为图标 C 案「满版朱红 π」的朱红 #c8402f。

作者联系方式 · 微信号：TheSun_Also_Rises

配色原则（与图标风格协调一致）：
- 主色 red = #c8402f（图标朱红），用于主按钮、滚动条、分组标题、图标 hover、图钉等。
- 译文区保留 teal（与红互补，区分「识别原文 / 中文译文」两种信息）。
- 提示 / 徽章用暖金 gold、第三强调用暖玫瑰 rose，均与朱红同属暖色系、互相协调。
- 中性灰改为暖调，避免与朱红产生冷色冲突。
- 错误态统一用主色红（hint-error / edit error），与图标红一脉相承。
"""

from pathlib import Path
import sys

# 品牌朱红，与 design/v06/icon_c_source.py 的 RED 锁死一致。
BRAND_RED = "#c8402f"

# ---------------------------------------------------------------- 统一字号规范
# 所有窗体共用这一套 px 字号；任何控件不得再写死自己的 font-size。
FONT_TITLE_PX = 13.5     # 左上角核心汉字名称
FONT_SUBTITLE_PX = 10.5  # 灰色小字注释
FONT_BODY_PX = 12        # 正文 / 标签 / 分组标题
FONT_CONTROL_PX = 11.5   # 按钮 / 输入框 / 状态提示（内容可更详细，字号略小）

LIGHT = {
    "bg": "#f7f4f2", "card": "#ffffff", "ink": "#241a18", "sub": "#6b5d59",
    "line": "#ece3df", "btn_line": "#d9bcb5",
    "red": "#c8402f", "red_bg": "#fbeae7",
    "teal": "#0f9b8e", "teal_bg": "#e4f4f1",
    "gold": "#b9760f", "gold_bg": "#fbf0e2",
    "rose": "#a83b5c", "rose_bg": "#fbeaee",
    "bar": "#f3ece9", "input": "#fff8f6", "out": "#eef7f4",
    "out_line": "#a9ddd3", "input_line": "#f0ccc4", "foot": "#faf4f1",
}
DARK = {
    "bg": "#201918", "card": "#2a201e", "ink": "#f6ece9", "sub": "#c2aea9",
    "line": "#433730", "btn_line": "#5e3a33",
    "red": "#d9543f", "red_bg": "#3b211d",
    "teal": "#4fd1c5", "teal_bg": "#1e3c3a",
    "gold": "#e0a85a", "gold_bg": "#463420",
    "rose": "#d97a92", "rose_bg": "#42232c",
    "bar": "#2a201e", "input": "#2a1f1c", "out": "#1c332f",
    "out_line": "#3c6c62", "input_line": "#5e3a33", "foot": "#241b18",
}

_QSS = """
#root {{
  background: {card}; border: 1px solid {line}; border-radius: 14px;
}}
#titlebar {{ background: transparent; border: none; }}
#footer {{ background: {foot}; border-top: 1px solid {line}; }}
/* 手动输入翻译窗：底栏已删除微信联系方式，整条透明、无背景色块、无分隔线。 */
#footerPlain {{ background: transparent; border: none; }}
QLabel {{ color: {ink}; background: transparent; }}
QLabel[cls="sub"] {{ color: {sub}; }}
QLabel[cls="badge"] {{ background: {red_bg}; color: {red}; border-radius: 9px;
  padding: 2px 8px; font-weight: 700; }}
QLabel[cls="badge-rose"] {{ background: {rose_bg}; color: {rose}; border-radius: 9px;
  padding: 2px 8px; font-weight: 700; }}
QLabel[cls="badge-gold"] {{ background: {gold_bg}; color: {gold}; border-radius: 9px;
  padding: 2px 8px; font-weight: 700; }}
QLabel[cls="badge-teal"] {{ background: {teal_bg}; color: {teal}; border-radius: 9px;
  padding: 2px 8px; font-weight: 700; }}
QLabel[cls="hint"] {{ color: {gold}; background: {gold_bg};
  border: 1px solid {gold}; border-radius: 6px; padding: 4px 9px; }}
QLabel[cls="hint-error"] {{ color: {red}; background: {red_bg};
  border: 1px solid {red}; border-radius: 6px; padding: 4px 9px; }}
QLabel[cls="lang"] {{ color: {red}; background: {red_bg}; border-radius: 5px;
  padding: 2px 8px; font-weight: 700; font-size: {font_control}px; }}
/* 统一按钮规范：所有文字按钮与图标按钮共用同一条清晰边框、同一圆角、同一字号。 */
QPushButton {{ background: {card}; color: {ink}; border: 1px solid {btn_line};
  border-radius: 7px; padding: 5px 11px; font-size: {font_control}px; }}
QPushButton:hover {{ background: {red_bg}; border-color: {red}; color: {red}; }}
QPushButton:pressed {{ background: #f6ddd8; }}
QPushButton[cls="primary"] {{ background: {red}; color: #ffffff; border-color: {red}; }}
QPushButton[cls="primary"]:hover {{ background: {red}; color: #ffffff; }}
QPushButton[cls="ghost"] {{ background: transparent; border: 0; color: {sub};
  padding: 2px 4px; font-size: {font_control}px; }}
QPushButton[cls="ghost"]:hover {{ background: transparent; color: {red}; }}
QPushButton[cls="link"] {{ background: transparent; border: 0; color: {red};
  padding: 0; text-align: left; font-size: {font_control}px; }}
QPushButton[cls="link"]:hover {{ color: {red}; text-decoration: underline; }}
/* 「清空输入」「复制译文」与默认按钮完全同款，都有清晰可见的边框；
   只额外保留点击后的「已复制」反馈态，不再使用淡到看不见边框的渐变胶囊。 */
QPushButton[cls="copy"] {{ padding: 5px 13px; }}
QPushButton[cls="copy"][done="true"] {{ background: {teal_bg}; border-color: #7fc9bf;
    color: {teal}; }}
QPushButton[cls="icon"] {{ background: {card}; border: 1px solid {btn_line};
  border-radius: 7px; padding: 0; min-width: 26px; max-width: 26px;
  min-height: 26px; max-height: 26px; color: {sub}; }}
QPushButton[cls="icon"]:hover {{ background: {red_bg}; border-color: {red}; color: {red}; }}
QPushButton[cls="icon"]:checked {{ background: {red_bg}; border-color: {red}; color: {red}; }}
QPushButton[cls="pin"]:checked {{ background: {gold_bg}; border-color: {gold}; color: {gold}; }}
QPlainTextEdit, QTextBrowser {{ background: {input}; color: {ink};
  border: 1px solid {input_line}; border-radius: 8px; padding: 9px 11px;
  font-size: {font_body}px;
  selection-background-color: {red}; selection-color: #ffffff; }}
QPlainTextEdit[cls="output"] {{ background: {out}; color: {teal}; border-color: {out_line};
  selection-background-color: {teal}; selection-color: #ffffff; }}
QPlainTextEdit[cls="error"] {{ background: {red_bg}; color: {red}; border-color: {red};
  selection-background-color: {red}; selection-color: #ffffff; }}
QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #d9bcb5; border-radius: 4px; min-height: 22px; }}
QScrollBar::handle:vertical:hover {{ background: {red}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 9px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #d9bcb5; border-radius: 4px; min-width: 22px; }}
QScrollBar::handle:horizontal:hover {{ background: {red}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}
/* 中间那条装饰性分隔线已按用户定稿移除；handle 保留可拖动，但完全透明不可见。 */
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:vertical {{ height: 5px; }}
QSplitter::handle:horizontal {{ width: 5px; }}
QComboBox, QLineEdit, QSpinBox {{ background: {input}; color: {ink};
  border: 1px solid {line}; border-radius: 7px; padding: 5px 8px; }}
/* 设置页 / 关于页：沿用全局字号规范；输入内容可写得更详细，但字号略小。 */
QDialog QLabel, QDialog QCheckBox, QDialog QGroupBox {{ font-size: {font_body}px; }}
QDialog QLabel[cls="sub"] {{ font-size: {font_control}px; }}
QDialog QGroupBox::title {{ font-size: {font_body}px; }}
QDialog QLineEdit, QDialog QComboBox, QDialog QSpinBox {{
  font-size: {font_control}px; min-height: 26px; padding: 3px 8px;
  border: 1px solid {btn_line}; }}
QDialog QPushButton {{ font-size: {font_control}px; }}
QDialog QSpinBox {{ padding-right: 20px; }}
QDialog QComboBox QAbstractItemView {{ font-size: {font_control}px; min-height: 24px;
  selection-background-color: {red_bg}; selection-color: {red}; }}
/* 数值框步进按钮：默认绘制在自定义边框下会变成残缺的「⌐」，
   这里用 CSS 三角形替代系统箭头，保证两个方向都清晰可辨。 */
QSpinBox {{ padding-right: 20px; }}
QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right;
  width: 18px; border: 0; border-left: 1px solid {line};
  border-top-right-radius: 7px; background: transparent; }}
QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right;
  width: 18px; border: 0; border-left: 1px solid {line};
  border-bottom-right-radius: 7px; background: transparent; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {red_bg}; }}
/* 图片尺寸必须与 QSS 声明一致（12x7），缩放会糊成小方块。 */
QSpinBox::up-arrow {{ image: url("{spin_up}"); width: 12px; height: 7px; }}
QSpinBox::down-arrow {{ image: url("{spin_down}"); width: 12px; height: 7px; }}
QCheckBox {{ color: {ink}; background: transparent; spacing: 7px; }}
/* 明确画出未勾选方框，避免自定义样式下只剩一个悬空的勾、看起来像文字被遮挡。 */
QCheckBox::indicator {{ width: 15px; height: 15px; border: 1px solid #d9bcb5;
  border-radius: 4px; background: #ffffff; }}
QCheckBox::indicator:checked {{ background: {red}; border-color: {red};
  image: url("{check_mark}"); }}
QCheckBox::indicator:unchecked:hover {{ border-color: {red}; background: {red_bg}; }}
QDialog, #settingsRoot, #aboutRoot {{ background: {bg}; }}
QGroupBox {{ color: {ink}; border: 1px solid {line}; border-radius: 8px;
  margin-top: 12px; padding: 10px; }}
QGroupBox::title {{ color: {red}; subcontrol-origin: margin; left: 9px; padding: 0 4px; }}
"""


def _assets_dir() -> str:
    """定位 QSS 图片资源目录，兼容开发态与 PyInstaller 冻结态。"""
    here = Path(__file__).resolve().parent / "assets"
    if here.is_dir():
        return here.as_posix()
    # 冻结态兜底：onedir 下 datas 落在与 exe 同级的 _internal/app/ui/assets
    exe_dir = Path(sys.executable).resolve().parent
    for candidate in (exe_dir / "_internal" / "app" / "ui" / "assets",
                      exe_dir / "app" / "ui" / "assets"):
        if candidate.is_dir():
            return candidate.as_posix()
    return here.as_posix()


def stylesheet(theme: str = "light") -> str:
    palette = DARK if theme == "dark" else LIGHT
    # 步进箭头用 PNG 资源（Qt QSS 不支持 CSS 三角，直接用图片最稳）。
    assets = _assets_dir()
    return _QSS.format(spin_up=f"{assets}/spin_up.png",
                       spin_down=f"{assets}/spin_down.png",
                       check_mark=f"{assets}/check_mark.png",
                       font_body=FONT_BODY_PX, font_control=FONT_CONTROL_PX,
                       **palette)


def palette(theme: str = "light") -> dict[str, str]:
    return dict(DARK if theme == "dark" else LIGHT)
