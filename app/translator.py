# -*- coding: utf-8 -*-
"""翻译引擎：Translator 单例 + 可插拔后端 + 长文本分块调度。

作者联系方式 · 微信号：TheSun_Also_Rises

手动输入 / OCR 识别原文两类入口共用同一个 Translator 实例。
后端默认为进程内 llama-cpp-python 加载本地 GGUF；不启动服务、不监听端口、不联网。
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from . import branding
from .text_logic import normalize_selection, split_blocks

SYSTEM_HINT = (
    "你是一个专业的翻译引擎。把用户给出的文本忠实翻译为简体中文，只输出译文，不要解释、"
    "不要添加标题或注释。\n严格约束：\n"
    "1. 保留原文的段落划分与换行结构；\n"
    "2. 数字、型号、版本号、日期、URL、代码标识符与专有名词按原样保留；\n"
    "3. 不得输出「译文：」「以下是翻译」等前缀，也不要复述原文；\n"
    "4. 源语言由你自动识别，无论原文是何种语言，都译成简体中文。\n\n"
)


class ModelUnavailableError(RuntimeError):
    """本地权重或推理依赖不可用。"""


class TranslationError(RuntimeError):
    """推理过程失败。"""


def build_prompt(text: str, src: str = "auto", dst: str = "zh-CN") -> str:
    """构造 Hy-MT2 提示词；src 仅作提示，实际由模型自动识别。"""
    if not isinstance(text, str):
        raise TypeError("text 必须是 str")
    lang_hint = "" if src in ("", "auto") else f"（原文语言提示：{src}）"
    return f"将以下文本翻译为{branding.TARGET_LANGUAGE_LABEL}{lang_hint}。\n\n{SYSTEM_HINT}{text}"


class TranslatorBackend(Protocol):
    name: str

    def available(self) -> tuple[bool, str]: ...

    def translate(self, text: str, src: str, dst: str) -> str: ...

    def translate_stream(self, text: str, src: str, dst: str,
                         on_delta: Callable[[str], None]) -> str: ...


class UnavailableBackend:
    """默认后端：没有本地权重或依赖时明确报错，绝不伪造译文。"""

    name = "unavailable"

    def __init__(self, reason: str = "未加载本地模型权重"):
        self.reason = reason

    def available(self) -> tuple[bool, str]:
        return False, self.reason

    def translate(self, text: str, src: str, dst: str) -> str:
        raise ModelUnavailableError(self.reason)

    def translate_stream(self, text: str, src: str, dst: str,
                         on_delta: Callable[[str], None]) -> str:
        raise ModelUnavailableError(self.reason)


class DemoBackend:
    """仅 ``--demo`` 显式启用：用于验证界面链路，输出带醒目标记，不是真实译文。"""

    name = "demo"

    def available(self) -> tuple[bool, str]:
        return True, "演示模式（未加载 Hy-MT2，输出为占位文本，不是真实译文）"

    @staticmethod
    def _fake(text: str) -> str:
        preview = text.strip().replace("\n", " ")[:80]
        return f"【演示模式 · 非真实译文】已收到 {len(text)} 字符的原文，本机模型未加载。原文预览：{preview}"

    def translate(self, text: str, src: str, dst: str) -> str:
        return self._fake(text)

    def translate_stream(self, text: str, src: str, dst: str,
                         on_delta: Callable[[str], None]) -> str:
        out = self._fake(text)
        for i in range(0, len(out), 12):
            on_delta(out[i:i + 12])
        return out


class LlamaCppBackend:
    """进程内加载 GGUF（首选后端）。依赖 llama-cpp-python，运行期才导入。"""

    name = "llama-cpp-python (in-process)"

    def __init__(self, model_path: Path | str, n_ctx: int = 2048,
                 n_threads: int | None = None, n_gpu_layers: int = 0):
        self.model_path = Path(model_path)
        self.n_ctx = n_ctx
        self.n_threads = n_threads or max(1, min(8, os.cpu_count() or 4))
        self.n_gpu_layers = n_gpu_layers
        self._llm = None
        self._lock = threading.Lock()

    def available(self) -> tuple[bool, str]:
        if not self.model_path.is_file():
            return False, f"本地权重不存在：{self.model_path}"
        try:
            import importlib.util
            if importlib.util.find_spec("llama_cpp") is None:
                return False, "未安装 llama-cpp-python（进程内推理依赖）"
        except Exception as exc:
            return False, f"依赖探测失败：{exc}"
        return True, f"本地权重就绪：{self.model_path.name}"

    def _ensure_loaded(self):
        if self._llm is not None:
            return self._llm
        with self._lock:
            if self._llm is not None:
                return self._llm
            ok, reason = self.available()
            if not ok:
                raise ModelUnavailableError(reason)
            from llama_cpp import Llama  # 延迟导入
            self._llm = Llama(
                model_path=str(self.model_path), n_ctx=self.n_ctx,
                n_threads=self.n_threads, n_gpu_layers=self.n_gpu_layers,
                use_mmap=True, verbose=False,
            )
            return self._llm

    @staticmethod
    def _max_tokens(text: str) -> int:
        return max(128, min(2048, len(text) * 2 + 64))

    @staticmethod
    def _content(response: object) -> str:
        try:
            return str(response["choices"][0]["message"]["content"]).strip()  # type: ignore[index]
        except (KeyError, IndexError, TypeError) as exc:
            raise TranslationError(f"推理返回格式异常：{exc}") from exc

    def translate(self, text: str, src: str, dst: str) -> str:
        llm = self._ensure_loaded()
        response = llm.create_chat_completion(
            messages=[{"role": "user", "content": build_prompt(text, src, dst)}],
            temperature=0.0, top_p=0.9, repeat_penalty=1.05,
            max_tokens=self._max_tokens(text), stream=False,
        )
        return self._content(response)

    def translate_stream(self, text: str, src: str, dst: str,
                         on_delta: Callable[[str], None]) -> str:
        llm = self._ensure_loaded()
        chunks: list[str] = []
        for part in llm.create_chat_completion(
            messages=[{"role": "user", "content": build_prompt(text, src, dst)}],
            temperature=0.0, top_p=0.9, repeat_penalty=1.05,
            max_tokens=self._max_tokens(text), stream=True,
        ):
            try:
                delta = part["choices"][0]["delta"].get("content", "")  # type: ignore[index]
            except (KeyError, IndexError, TypeError):
                continue
            if delta:
                chunks.append(str(delta))
                on_delta(str(delta))
        if not chunks:
            raise TranslationError("流式推理未返回任何内容")
        return "".join(chunks).strip()

    def unload(self) -> None:
        with self._lock:
            self._llm = None


@dataclass
class TranslationResult:
    text: str
    total_blocks: int
    done_blocks: int
    cancelled: bool = False
    elapsed_ms: float = 0.0
    engine: str = ""
    error: str = ""


class Translator:
    """单例翻译调度器：空输入不请求、超长自动分块、可取消、模型忙时串行排队。"""

    def __init__(self, backend: TranslatorBackend | None = None,
                 max_block_chars: int = 2000, clock: Callable[[], float] = time.monotonic):
        if max_block_chars < 1:
            raise ValueError("max_block_chars 必须 >=1")
        self._backend = backend or UnavailableBackend()
        self.max_block_chars = max_block_chars
        self._clock = clock
        self._lock = threading.RLock()
        self._status = "idle"
        self.request_count = 0
        self.cancelled_count = 0
        self.last_result: TranslationResult | None = None

    @property
    def backend(self) -> TranslatorBackend:
        return self._backend

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    def ready(self) -> tuple[bool, str]:
        return self._backend.available()

    def set_backend(self, backend: TranslatorBackend) -> None:
        with self._lock:
            self._backend = backend

    def translate(self, text: str, src: str = "auto", dst: str = branding.TARGET_LANGUAGE,
                  on_block: Callable[[int, int, str], None] | None = None,
                  cancel: Callable[[], bool] | None = None,
                  stream: bool = False,
                  on_delta: Callable[[str], None] | None = None) -> TranslationResult:
        """执行翻译。``cancel()`` 返回 True 时在块边界停止并保留已完成译文。"""
        if not isinstance(text, str):
            raise TypeError("text 必须是 str")
        started = self._clock()
        with self._lock:                       # 模型忙时排队而非并发加载权重
            normalized = normalize_selection(text)
            if not normalized:
                result = TranslationResult("", 0, 0, engine=self._backend.name)
                self.last_result = result
                return result                 # 空输入：不计数、绝不调用后端
            self._status = "translating"
            self.request_count += 1
            try:
                blocks = split_blocks(normalized, self.max_block_chars)
                total = len(blocks)
                pieces: list[str] = []
                done = 0
                for index, block in enumerate(blocks, start=1):
                    if cancel is not None and cancel():
                        self.cancelled_count += 1
                        result = TranslationResult("\n".join(pieces), total, done,
                                                   cancelled=True, engine=self._backend.name)
                        self.last_result = result
                        return result
                    if not block.strip():
                        pieces.append(block)   # 纯分隔块原样保留结构
                        translated = block
                    else:
                        try:
                            if stream and on_delta is not None:
                                translated = self._backend.translate_stream(
                                    block.strip(), src, dst, on_delta)
                            else:
                                translated = self._backend.translate(block.strip(), src, dst)
                        except ModelUnavailableError as exc:
                            result = TranslationResult("", total, done, engine=self._backend.name,
                                                       error=str(exc))
                            self.last_result = result
                            return result
                        except Exception as exc:
                            result = TranslationResult("\n".join(pieces), total, done,
                                                       engine=self._backend.name,
                                                       error=f"推理失败：{exc}")
                            self.last_result = result
                            return result
                        pieces.append(translated)
                        done += 1
                    if on_block is not None:
                        on_block(index, total, translated)
                result = TranslationResult("\n".join(pieces), total, done,
                                           engine=self._backend.name)
                self.last_result = result
                return result
            finally:
                self._status = "idle"
                if self.last_result is not None:
                    self.last_result.elapsed_ms = (self._clock() - started) * 1000.0

    def unload(self) -> None:
        unload = getattr(self._backend, "unload", None)
        if callable(unload):
            unload()


# ---------------------------------------------------------------- 单例
_INSTANCE: Translator | None = None
_INSTANCE_LOCK = threading.Lock()


def get_translator(**kwargs) -> Translator:
    """三条输入通路共用的唯一实例。"""
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = Translator(**kwargs)
        return _INSTANCE


def reset_translator() -> None:
    """仅供测试与显式重载模型时调用。"""
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = None


@dataclass
class TranslationJob:
    """UI 线程与工作线程之间传递的任务描述。"""
    text: str
    source: str = "manual"
    src: str = "auto"
    stream: bool = False
    meta: dict = field(default_factory=dict)
