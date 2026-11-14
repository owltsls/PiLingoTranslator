# -*- coding: utf-8 -*-
"""OCR 图片翻译：可插拔识别接口 + RapidOCR 按需加载 + 识别文本行整理。

作者联系方式 · 微信号：TheSun_Also_Rises

职责边界：OCR 只负责「把图里的字认出来」，翻译一律交给 Translator（腾讯 Hy-MT2）。
位图只在内存中处理，不落盘、不上传。
"""
from __future__ import annotations

import importlib.util
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from . import branding


class OCRUnavailableError(RuntimeError):
    """识别依赖 / 模型不可用。"""


@dataclass(frozen=True)
class TextLine:
    text: str
    confidence: float = 1.0
    box: tuple[float, float, float, float] | None = None  # x1,y1,x2,y2

    @property
    def center_y(self) -> float:
        if self.box is None:
            return 0.0
        return (self.box[1] + self.box[3]) / 2.0

    @property
    def left_x(self) -> float:
        return 0.0 if self.box is None else min(self.box[0], self.box[2])


class OCRProvider(Protocol):
    name: str

    def available(self) -> tuple[bool, str]: ...

    def recognize(self, image: object) -> list[TextLine]: ...


class NullOCRProvider:
    """M1/M2 占位：OCR 未启用时明确不可用，不影响手动输入主链路。"""

    name = "none"

    def __init__(self, reason: str = "OCR 引擎尚未加载（M3 落地 RapidOCR + PP-OCRv5 轻量模型）"):
        self.reason = reason

    def available(self) -> tuple[bool, str]:
        return False, self.reason

    def recognize(self, image: object) -> list[TextLine]:
        raise OCRUnavailableError(self.reason)


class StaticOCRProvider:
    """测试 / 演示用的确定性识别器。"""

    name = "static"

    def __init__(self, lines: Sequence[TextLine] | Sequence[str]):
        self.lines = [TextLine(text) if isinstance(text, str) else text
                      for text in lines]

    def available(self) -> tuple[bool, str]:
        return True, "静态识别器（测试用）"

    def recognize(self, image: object) -> list[TextLine]:
        return list(self.lines)


class RapidOCRProvider:
    """RapidOCR + ONNX Runtime + PP-OCRv5/v6 mobile 轻量模型（进程内 CPU）。

    依赖与模型都按需加载；缺依赖时 ``available()`` 返回原因，软件其余功能不受影响。
    """

    name = "RapidOCR + ONNX Runtime"

    def __init__(self, model_dir: Path | str | None = None):
        self.model_dir = Path(model_dir) if model_dir else None
        self._engine = None

    def available(self) -> tuple[bool, str]:
        found = (importlib.util.find_spec("rapidocr_onnxruntime")
                 or importlib.util.find_spec("rapidocr"))
        if found is None:
            return False, "未安装 rapidocr-onnxruntime（轻量 OCR 推理依赖）"
        try:
            import cv2  # noqa: F401  RapidOCR 视觉预处理依赖
        except ImportError:
            return False, "未安装 opencv-python（RapidOCR 视觉依赖，缺它识别会失败）"
        if self.model_dir is not None and not self.model_dir.is_dir():
            return False, f"识别模型目录不存在：{self.model_dir}"
        return True, "RapidOCR 就绪（PP-OCRv5/v6 mobile · 本地离线）"

    @staticmethod
    def _to_array(image: object):
        """内存位图 → numpy 数组；不写任何临时文件。"""
        import numpy as np

        if isinstance(image, (bytes, bytearray, memoryview)):
            from PIL import Image
            pil = Image.open(io.BytesIO(bytes(image))).convert("RGB")
            return np.asarray(pil)
        if hasattr(image, "convert") and hasattr(image, "size"):  # PIL.Image
            return np.asarray(image.convert("RGB"))
        if hasattr(image, "shape"):                              # numpy.ndarray
            return np.asarray(image)
        raise TypeError("OCR 只接受内存位图（bytes / PIL.Image / numpy.ndarray）")

    @staticmethod
    def _register_submodules() -> None:
        """把 ``rapidocr_onnxruntime.*`` 子模块登记到顶层名，绕开 RapidOCR 在冻结构建
        里可能的顶层名阴影问题。开发态（真实包）与冻结构建里都安全、幂等。
        """
        import sys
        try:
            mod = importlib.import_module("rapidocr_onnxruntime")
        except ImportError:
            return
        prefix = mod.__name__ + "."
        for bare in ("ch_ppocr_v3_det", "ch_ppocr_v3_rec", "ch_ppocr_v2_cls"):
            try:
                sys.modules[bare] = importlib.import_module(prefix + bare)
            except ImportError:
                continue

    def _ensure_engine(self):
        if self._engine is not None:
            return self._engine
        ok, reason = self.available()
        if not ok:
            raise OCRUnavailableError(reason)
        self._register_submodules()
        # 用 importlib 动态导入而非顶层 ``from ... import``：避免 PyInstaller 静态扫描时
        # 把 rapidocr_onnxruntime 当成包收集进 PYZ，导致 __init__.py 被错建为目录、
        # 运行时导入失败。动态导入让该包只以「磁盘松散文件」形式随包分发。
        try:
            mod = importlib.import_module("rapidocr_onnxruntime")
            RapidOCR = getattr(mod, "RapidOCR")
        except (ImportError, AttributeError):
            try:
                mod = importlib.import_module("rapidocr")
                RapidOCR = getattr(mod, "RapidOCR")
            except (ImportError, AttributeError) as exc:
                raise OCRUnavailableError(f"RapidOCR 导入失败：{exc}") from exc
        kwargs = {}
        if self.model_dir is not None:
            kwargs["det_model_path"] = str(self.model_dir / "det.onnx")
            kwargs["rec_model_path"] = str(self.model_dir / "rec.onnx")
            kwargs["cls_model_path"] = str(self.model_dir / "cls.onnx")
        self._engine = RapidOCR(**kwargs)
        return self._engine

    def recognize(self, image: object) -> list[TextLine]:
        engine = self._ensure_engine()
        array = self._to_array(image)
        raw, _ = engine(array)
        if not raw:
            return []
        lines: list[TextLine] = []
        for item in raw:
            try:
                box_points, text, score = item[0], str(item[1]), float(item[2])
                xs = [float(p[0]) for p in box_points]
                ys = [float(p[1]) for p in box_points]
                box = (min(xs), min(ys), max(xs), max(ys))
            except (IndexError, TypeError, ValueError):
                continue
            if text.strip():
                lines.append(TextLine(text.strip(), score, box))
        return lines


def organize_lines(lines: Sequence[TextLine], y_tolerance: float = 12.0) -> list[str]:
    """按行聚类（同一行的多个文本框左右拼接），保持从上到下的阅读顺序。"""
    if not lines:
        return []
    if all(line.box is None for line in lines):
        return [line.text for line in lines if line.text.strip()]
    usable = [line for line in lines if line.text.strip()]
    if not usable:
        return []
    usable.sort(key=lambda item: (item.center_y, item.left_x))
    rows: list[list[TextLine]] = []
    for line in usable:
        if rows and abs(line.center_y - rows[-1][0].center_y) <= y_tolerance:
            rows[-1].append(line)
        else:
            rows.append([line])
    out: list[str] = []
    for row in rows:
        row.sort(key=lambda item: item.left_x)
        out.append(" ".join(item.text for item in row))
    return out


def assess_lines(lines: Sequence[TextLine], min_confidence: float = 0.5) -> tuple[bool, str]:
    """识别质量评估：空结果 / 置信度过低要提示重框选，并保留原文供核对。"""
    if not lines:
        return False, "未识别到文字，请重新框选或改用清晰的图片"
    avg = sum(line.confidence for line in lines) / len(lines)
    if avg < min_confidence:
        return False, f"识别置信度偏低（{avg:.2f}），建议重新框选；下方保留识别原文供核对"
    return True, ""


@dataclass
class OCRResult:
    recognized_text: str
    translated_text: str
    lines: list[TextLine]
    ok: bool
    message: str
    engine: str


class OCRPipeline:
    """识别 → 按行整理 → 交给统一的 Translator 单例翻译。"""

    def __init__(self, translator, provider: OCRProvider | None = None,
                 min_confidence: float = 0.5):
        self.translator = translator
        self.provider = provider or NullOCRProvider()
        self.min_confidence = min_confidence

    def process(self, image: object, cancel=None) -> OCRResult:
        try:
            lines = self.provider.recognize(image)
        except OCRUnavailableError as exc:
            return OCRResult("", "", [], False, str(exc), self.provider.name)
        except Exception as exc:
            return OCRResult("", "", [], False, f"识别失败：{exc}", self.provider.name)
        recognized = "\n".join(organize_lines(lines))
        ok, message = assess_lines(lines, self.min_confidence)
        translated = ""
        if ok and recognized.strip():
            if cancel is not None and cancel():
                return OCRResult(recognized, "", lines, False, "已取消翻译", self.provider.name)
            result = self.translator.translate(recognized, cancel=cancel)
            translated = result.text
            if result.error:
                message = result.error
                ok = False
        return OCRResult(recognized, translated, list(lines), ok, message,
                         f"{self.provider.name} → {branding.TRANSLATION_ENGINE}")
