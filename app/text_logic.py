# -*- coding: utf-8 -*-
"""文本逻辑：选中文本过滤、语言检测、长文本分块、字数提示、重复去抖。

作者联系方式 · 微信号：TheSun_Also_Rises

本模块零第三方依赖，是「逻辑层无错误」的核心可测单元。
"""
from __future__ import annotations

import bisect
import hashlib
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Callable

_ZERO_WIDTH = "\u200b\u200c\u200d\u2060\ufeff"
_STRIP_TABLE = {ord(ch): None for ch in _ZERO_WIDTH}

_WIN_ABS_RE = re.compile(r"^[A-Za-z]:[\\/]")
_UNC_RE = re.compile(r"^\\\\")
_URI_RE = re.compile(r"^(file|https?|ftp|mailto):", re.I)
_FILENAME_RE = re.compile(r"^[^\\/:*?\"<>|\r\n]{1,255}\.[A-Za-z0-9]{1,10}$")
_EXT_TAIL_RE = re.compile(r"\.[A-Za-z0-9]{1,10}($|[\s\\/:])")

_LANG_LABELS = {
    "zh": "中文", "en": "英语", "ja": "日语", "ko": "韩语", "ru": "俄语",
    "de": "德语", "fr": "法语", "es": "西班牙语", "it": "意大利语",
    "pt": "葡萄牙语", "ar": "阿拉伯语", "unknown": "未知语言",
}
_LATIN_HINTS = {
    "de": {"der", "die", "das", "und", "ist", "nicht", "mit", "für", "auf", "ein", "eine", "zu", "von", "sich"},
    "fr": {"le", "la", "les", "des", "une", "est", "pas", "pour", "avec", "dans", "sur", "que", "qui", "nous"},
    "es": {"el", "los", "las", "una", "es", "para", "con", "por", "que", "en", "del", "como", "más"},
    "it": {"il", "la", "gli", "una", "è", "per", "con", "che", "non", "sono", "del", "nella"},
    "pt": {"os", "as", "uma", "é", "para", "com", "por", "que", "não", "mais", "do", "da"},
}
_LATIN_DEFAULT = "en"

_SENTENCE_END = set(".!?。！？;；")
_SUGGEST_MAXIMIZE = 500


# ---------------------------------------------------------------- 归一化 / 过滤
def normalize_selection(text: str) -> str:
    """统一换行、去零宽字符与行尾空白，保留段落结构；首尾空白去除。"""
    if not isinstance(text, str):
        raise TypeError("文本必须是 str")
    s = text.replace("\r\n", "\n").replace("\r", "\n")
    s = s.translate(_STRIP_TABLE)
    s = "\n".join(line.rstrip() for line in s.split("\n"))
    return s.strip()


def looks_like_path(text: str) -> bool:
    """识别「选中文件 / 目录 / 单个文件名 / URL」，用于免打扰过滤。"""
    if not isinstance(text, str):
        raise TypeError("文本必须是 str")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines or len(lines) > 3:
        return False
    joined = " ".join(lines)
    if _WIN_ABS_RE.match(joined) or _UNC_RE.match(joined) or _URI_RE.match(joined):
        return True
    if joined.startswith("/") or joined.startswith("~/"):
        return True
    for line in lines:
        # 只有完整路径才过滤。单个文件名（report.docx）是高频翻译对象，
        # 不再当作路径跳过——V0.3 的「文件名免打扰」规则在此反转。
        if _WIN_ABS_RE.match(line):
            return True
        if "\\" in line and " " not in line and _EXT_TAIL_RE.search(line):
            return True
        if "/" in line and " " not in line and _EXT_TAIL_RE.search(line):
            return True
    return False


def is_bare_filename(text: str) -> bool:
    """是否为一个或若干个纯文件名（不含路径分隔符、带常见扩展名）。"""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return bool(lines) and len(lines) <= 3 and all(_FILENAME_RE.match(line) for line in lines)


def prepare_filename_for_translation(text: str) -> str:
    """把文件名整理成模型易读的文本：去扩展名、分隔符转空格、驼峰拆词。

    ``Annual_Report_2026.docx`` -> ``Annual Report 2026``
    扩展名 / 版本号 / 数字保持可读，不参与改写；仅用于翻译请求，
    不回写磁盘、不改动用户文件。
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines or not all(_FILENAME_RE.match(line) for line in lines):
        return ""
    prepared: list[str] = []
    for line in lines:
        stem = line.rsplit(".", 1)[0]
        stem = re.sub(r"[_\-.]+", " ", stem)
        stem = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", stem)
        stem = re.sub(r"\s+", " ", stem).strip()
        if stem:
            prepared.append(stem)
    return "\n".join(prepared)


@dataclass(frozen=True)
class SkipDecision:
    skip: bool
    reason: str
    normalized: str
    kind: str = ""          # "filename" 表示选中内容是文件名，需按文件名语义翻译

    @property
    def reason_label(self) -> str:
        return {
            "": "", "empty": "空选择", "too_short": "内容过短",
            "no_letters": "无字母内容", "path_or_filename": "完整路径 / 链接，已跳过",
            "too_long": "单次文本超出上限",
        }.get(self.reason, self.reason)


def should_skip(text: str, min_chars: int = 2,
                max_total_chars: int | None = None) -> SkipDecision:
    """判断一段选中文本是否应该被翻译成译文请求。"""
    n = normalize_selection(text)
    if not n:
        return SkipDecision(True, "empty", n)
    if len(n) < min_chars:
        return SkipDecision(True, "too_short", n)
    if not any(ch.isalpha() for ch in n):
        return SkipDecision(True, "no_letters", n)
    if looks_like_path(n):
        return SkipDecision(True, "path_or_filename", n)
    if is_bare_filename(n):
        prepared = prepare_filename_for_translation(n)
        if prepared and any(ch.isalpha() for ch in prepared):
            # 文件名翻译是高频核心场景：送模型的是整理后的词干，
            # 扩展名等符号不进入译文，符合「纯译名」规范。
            return SkipDecision(False, "", prepared, kind="filename")
    if max_total_chars is not None and len(n) > max_total_chars:
        return SkipDecision(True, "too_long", n)
    return SkipDecision(False, "", n)


# ---------------------------------------------------------------- 语言检测
def _script_counts(text: str) -> dict[str, int]:
    tally = {k: 0 for k in ("han", "latin", "kana", "hangul", "cyrillic", "arabic", "other")}
    for ch in text:
        if ch.isspace() or unicodedata.category(ch) in {"Pc", "Po", "Ps", "Pe", "Sm", "Sc", "So"}:
            continue
        code = ord(ch)
        if 0x3400 <= code <= 0x9FFF or 0xF900 <= code <= 0xFAFF:
            tally["han"] += 1
        elif 0x3040 <= code <= 0x30FF or 0x31F0 <= code <= 0x31FF:
            tally["kana"] += 1
        elif 0x1100 <= code <= 0x11FF or 0xAC00 <= code <= 0xD7AF:
            tally["hangul"] += 1
        elif 0x0400 <= code <= 0x052F:
            tally["cyrillic"] += 1
        elif 0x0600 <= code <= 0x06FF:
            tally["arabic"] += 1
        elif ch.isascii() and ch.isalpha():
            tally["latin"] += 1
        elif ch.isalpha():
            tally["latin"] += 1  # 带变音符的拉丁字母
        elif ch.isdigit():
            continue
        else:
            tally["other"] += 1
    return tally


def detect_language(text: str) -> tuple[str, str]:
    """返回 ``(语言码, 中文标签)``。仅用于界面标签，不影响模型自动识别。"""
    if not isinstance(text, str):
        raise TypeError("文本必须是 str")
    tally = _script_counts(text)
    total = sum(tally.values())
    if total == 0:
        return "unknown", _LANG_LABELS["unknown"]
    for script, code in (("kana", "ja"), ("hangul", "ko"),
                         ("cyrillic", "ru"), ("arabic", "ar")):
        if tally[script] / total >= 0.15:
            return code, _LANG_LABELS[code]
    if tally["han"] / total >= 0.30:
        return "zh", _LANG_LABELS["zh"]
    if tally["latin"] > 0:
        words = re.findall(r"[A-Za-zÀ-ÿ']+", text.lower())
        scores = {lang: sum(1 for w in words if w in vocab)
                  for lang, vocab in _LATIN_HINTS.items()}
        best = max(scores, key=lambda k: scores[k])
        if scores[best] >= 2:
            return best, _LANG_LABELS[best]
        return _LATIN_DEFAULT, _LANG_LABELS[_LATIN_DEFAULT]
    return "unknown", _LANG_LABELS["unknown"]


# ---------------------------------------------------------------- 长文本分块
@dataclass(frozen=True)
class TextBlock:
    index: int
    text: str
    char_count: int

    @property
    def translatable(self) -> bool:
        return bool(self.text.strip())


def split_blocks(text: str, max_chars: int = 2000) -> list[str]:
    """按「段落 / 句末 / 空格」优先切分，保证 ``''.join(blocks) == text``。

    单块永不超过 max_chars（除非 max_chars 非法时会抛 ValueError）。
    """
    if not isinstance(text, str):
        raise TypeError("文本必须是 str")
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
        raise ValueError("max_chars 必须是 >=1 的整数")
    n = len(text)
    if n == 0:
        return []
    if n <= max_chars:
        return [text]

    primary: list[int] = []
    secondary: list[int] = []
    for i in range(1, n + 1):
        prev = text[i - 1]
        if prev == "\n":
            primary.append(i)
        elif prev in _SENTENCE_END and (i == n or text[i].isspace()):
            primary.append(i)
        elif prev.isspace():
            secondary.append(i)

    blocks: list[str] = []
    start = 0
    while start < n:
        limit = start + max_chars
        if limit >= n:
            blocks.append(text[start:])
            break
        cut = 0
        pos = bisect.bisect_right(primary, limit) - 1
        if pos >= 0 and primary[pos] > start:
            cut = primary[pos]
        else:
            pos = bisect.bisect_right(secondary, limit) - 1
            if pos >= 0 and secondary[pos] > start:
                cut = secondary[pos]
        if cut <= start:
            cut = limit
        blocks.append(text[start:cut])
        start = cut
    return blocks


def make_blocks(text: str, max_chars: int = 2000) -> list[TextBlock]:
    return [TextBlock(i, chunk, len(chunk))
            for i, chunk in enumerate(split_blocks(text, max_chars), start=1)]


def long_text_hint(char_count: int, max_chars: int = 2000,
                   text: str | None = None) -> tuple[str, str]:
    """返回 ``(级别, 提示文案)``；级别为 none / suggest_maximize / long_mode。

    传入原文 ``text`` 时按真实段落 / 句边界计算块数，否则按容量估算。
    """
    if char_count > max_chars:
        blocks = (len(split_blocks(text, max_chars)) if text is not None
                  else (char_count + max_chars - 1) // max_chars)
        return "long_mode", (f"长文本模式：{char_count} 字，共 {blocks} 块，"
                            "自动分块、逐块流式回填（内容不截断）")
    if char_count > _SUGGEST_MAXIMIZE:
        return "suggest_maximize", (f"长文本 {char_count} 字：建议点右上角最大化按钮，"
                                    "输入区与译文区可独立滚动")
    return "none", ""


# ---------------------------------------------------------------- 去抖
class SelectionDebouncer:
    """同一段文本在时间窗内重复捕获只放行一次（F1.5）。"""

    def __init__(self, window_ms: int = 800, clock: Callable[[], float] = time.monotonic):
        if window_ms < 0:
            raise ValueError("window_ms 不能为负")
        self.window_ms = window_ms
        self._clock = clock
        self._last_key: str | None = None
        self._last_at: float | None = None
        self.accepted = 0
        self.rejected = 0

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha256(normalize_selection(text).encode("utf-8")).hexdigest()

    def should_accept(self, text: str) -> bool:
        key = self._key(text)
        now = self._clock()
        if (self._last_key == key and self._last_at is not None
                and (now - self._last_at) * 1000.0 < self.window_ms):
            self.rejected += 1
            return False
        self._last_key = key
        self._last_at = now
        self.accepted += 1
        return True

    def reset(self) -> None:
        self._last_key = None
        self._last_at = None
