# -*- coding: utf-8 -*-
"""翻译调度（单例 / 空输入 / 分块 / 取消 / 排队 / 错误）与 OCR 链路测试。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import threading
import time
import unittest

from app import branding
from app.ocr import (NullOCRProvider, OCRPipeline, RapidOCRProvider,
                     StaticOCRProvider, TextLine, assess_lines, organize_lines)
from app.translator import (DemoBackend, LlamaCppBackend, ModelUnavailableError,
                            TranslationResult, Translator, UnavailableBackend,
                            build_prompt, get_translator, reset_translator)
from tests import cleanup_tmp, make_tmp


class FakeBackend:
    name = "fake"

    def __init__(self, fail: Exception | None = None):
        self.calls: list[str] = []
        self.fail = fail
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def available(self):
        return True, "fake ready"

    def translate(self, text, src, dst):
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if self.fail:
                raise self.fail
            self.calls.append(text)
            time.sleep(0.01)
            return "【译】" + text[:12]
        finally:
            with self._lock:
                self.active -= 1

    def translate_stream(self, text, src, dst, on_delta):
        out = self.translate(text, src, dst)
        on_delta(out)
        return out


class TranslatorTest(unittest.TestCase):
    def tearDown(self):
        reset_translator()

    def test_empty_input_never_calls_backend(self):
        backend = FakeBackend()
        tr = Translator(backend)
        for value in ("", "   ", "\n\t "):
            result = tr.translate(value)
            self.assertEqual(result.text, "")
            self.assertEqual(result.total_blocks, 0)
        self.assertEqual(backend.calls, [])
        self.assertEqual(tr.request_count, 0)

    def test_single_block(self):
        backend = FakeBackend()
        tr = Translator(backend)
        result = tr.translate("Hello world")
        self.assertEqual(result.total_blocks, 1)
        self.assertEqual(result.done_blocks, 1)
        self.assertTrue(result.text.startswith("【译】"))
        self.assertEqual(backend.calls, ["Hello world"])

    def test_long_text_split_into_ordered_blocks(self):
        backend = FakeBackend()
        tr = Translator(backend, max_block_chars=120)
        text = ("Offline translation keeps every selected phrase on this device. " * 30)
        seen: list[tuple[int, int, str]] = []
        result = tr.translate(text, on_block=lambda i, t, c: seen.append((i, t, c)))
        self.assertGreater(result.total_blocks, 1)
        self.assertEqual(result.done_blocks, result.total_blocks)
        self.assertEqual([i for i, _, _ in seen], list(range(1, result.total_blocks + 1)))
        self.assertEqual(len(backend.calls), result.total_blocks)
        self.assertFalse(result.cancelled)
        self.assertFalse(result.error)

    def test_pure_separator_blocks_are_not_sent_to_model(self):
        backend = FakeBackend()
        tr = Translator(backend, max_block_chars=20)
        text = "aaaaaaaaaa\n\nbbbbbbbbbb"
        result = tr.translate(text)
        self.assertTrue(all(call.strip() for call in backend.calls))
        self.assertEqual(result.done_blocks, 2)

    def test_cancel_before_first_block(self):
        backend = FakeBackend()
        tr = Translator(backend)
        result = tr.translate("Hello world", cancel=lambda: True)
        self.assertTrue(result.cancelled)
        self.assertEqual(result.done_blocks, 0)
        self.assertEqual(backend.calls, [])

    def test_cancel_between_blocks_keeps_completed_text(self):
        backend = FakeBackend()
        tr = Translator(backend, max_block_chars=60)
        counter = [0]

        def cancel():
            counter[0] += 1
            return counter[0] > 1

        result = tr.translate("Sentence one is here. " * 20, cancel=cancel)
        self.assertTrue(result.cancelled)
        self.assertEqual(result.done_blocks, 1)
        self.assertIn("【译】", result.text)

    def test_model_unavailable_is_reported_not_faked(self):
        tr = Translator(UnavailableBackend("权重未加载"))
        result = tr.translate("Hello world")
        self.assertIn("权重未加载", result.error)
        self.assertEqual(result.text, "")
        ok, _ = tr.ready()
        self.assertFalse(ok)

    def test_unexpected_backend_error_is_captured(self):
        tr = Translator(FakeBackend(fail=RuntimeError("推理崩了")))
        result = tr.translate("Hello world")
        self.assertIn("推理崩了", result.error)

    def test_stream_backend(self):
        backend = FakeBackend()
        tr = Translator(backend)
        deltas: list[str] = []
        result = tr.translate("Hello world", stream=True, on_delta=deltas.append)
        self.assertTrue(deltas)
        self.assertTrue(result.text.startswith("【译】"))

    def test_busy_requests_are_serialized(self):
        backend = FakeBackend()
        tr = Translator(backend)
        results: list[TranslationResult] = []

        def work():
            results.append(tr.translate("thread text"))

        threads = [threading.Thread(target=work) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(results), 3)
        self.assertEqual(backend.max_active, 1, "模型忙时应排队而不是并发推理")

    def test_singleton_shared_by_three_input_channels(self):
        first = get_translator(backend=FakeBackend())
        second = get_translator()
        self.assertIs(first, second)
        self.assertEqual(second.request_count, 0)

    def test_invalid_constructor(self):
        with self.assertRaises(ValueError):
            Translator(FakeBackend(), max_block_chars=0)
        with self.assertRaises(TypeError):
            Translator(FakeBackend()).translate(123)

    def test_prompt_and_demo_backend(self):
        prompt = build_prompt("Hello", "en")
        self.assertIn("简体中文", prompt)
        self.assertIn("Hello", prompt)
        self.assertIn("自动识别", prompt)
        self.assertIn("演示模式", DemoBackend().translate("Hello", "auto", "zh-CN"))
        self.assertEqual(branding.TRANSLATION_MODEL_BYTES, 1_133_080_448)

    def test_llama_backend_requires_local_file(self):
        backend = LlamaCppBackend("C:/definitely-missing-model.gguf")
        ok, reason = backend.available()
        self.assertFalse(ok)
        self.assertIn("不存在", reason)
        with self.assertRaises(ModelUnavailableError):
            backend.translate("text", "auto", "zh-CN")


class OCRTest(unittest.TestCase):
    def test_organize_lines_by_rows(self):
        lines = [
            TextLine("World", 0.95, (50, 2, 90, 18)),
            TextLine("Hello", 0.94, (2, 0, 45, 18)),
            TextLine("second", 0.9, (2, 40, 60, 58)),
            TextLine("line", 0.9, (65, 41, 100, 58)),
        ]
        self.assertEqual(organize_lines(lines), ["Hello World", "second line"])

    def test_organize_lines_without_boxes_keeps_order(self):
        lines = [TextLine("A"), TextLine("B"), TextLine("C")]
        self.assertEqual(organize_lines(lines), ["A", "B", "C"])
        self.assertEqual(organize_lines([]), [])

    def test_assess_lines(self):
        self.assertFalse(assess_lines([])[0])
        self.assertIn("未识别到文字", assess_lines([])[1])
        self.assertFalse(assess_lines([TextLine("x", 0.2)], 0.5)[0])
        self.assertTrue(assess_lines([TextLine("x", 0.9)], 0.5)[0])

    def test_pipeline_recognize_then_translate(self):
        tr = Translator(FakeBackend())
        provider = StaticOCRProvider(["Language", "Export report", "Save changes"])
        pipeline = OCRPipeline(tr, provider)
        result = pipeline.process(b"fake-image-bytes")
        self.assertTrue(result.ok)
        self.assertEqual(result.recognized_text, "Language\nExport report\nSave changes")
        self.assertIn("【译】", result.translated_text)
        self.assertIn("Hy-MT2", result.engine)

    def test_pipeline_empty_recognition(self):
        pipeline = OCRPipeline(Translator(FakeBackend()), StaticOCRProvider([]))
        result = pipeline.process(b"")
        self.assertFalse(result.ok)
        self.assertIn("重新框选", result.message)
        self.assertEqual(result.translated_text, "")

    def test_pipeline_unavailable_provider(self):
        pipeline = OCRPipeline(Translator(FakeBackend()), NullOCRProvider("OCR 未启用"))
        result = pipeline.process(b"")
        self.assertFalse(result.ok)
        self.assertIn("OCR 未启用", result.message)

    def test_pipeline_writes_nothing_to_disk(self):
        tmp = make_tmp()
        try:
            pipeline = OCRPipeline(Translator(FakeBackend()),
                                   StaticOCRProvider(["Language", "Save changes"]))
            pipeline.process(b"in-memory-bitmap")
            self.assertEqual(list(tmp.rglob("*")), [])
        finally:
            cleanup_tmp(tmp)


_RAPIDOCR_AVAILABLE = False
try:
    import importlib
    import sys as _sys
    from pathlib import Path as _Path
    _here = _Path(__file__).resolve()
    for _cand in (_here.parent.parent.parent, _here.parent.parent):
        _v = _cand / ".vendor-ocr"
        if _v.is_dir() and str(_v) not in _sys.path:
            _sys.path.insert(0, str(_v))
    import rapidocr_onnxruntime  # type: ignore  # noqa: F401
    _RAPIDOCR_AVAILABLE = True
except ImportError:
    _RAPIDOCR_AVAILABLE = False


@unittest.skipUnless(_RAPIDOCR_AVAILABLE, "rapidocr_onnxruntime 不在测试路径上，跳过")
class OCRSubmoduleFixTest(unittest.TestCase):
    """回归：冻结构建里 ch_ppocr_v3_det 被解析成空命名空间包，导致
    ``module 'ch_ppocr_v3_det' has no attribute 'TextDetector'``。

    ``_register_submodules`` 必须把真实的 ``rapidocr_onnxruntime.*`` 子模块登记到顶层名，
    使 ``importlib.import_module('ch_ppocr_v3_det')`` 解析到带 TextDetector 的模块。
    """

    def test_register_maps_bare_names_to_real_submodules(self):
        RapidOCRProvider._register_submodules()
        import sys
        for bare in ("ch_ppocr_v3_det", "ch_ppocr_v3_rec", "ch_ppocr_v2_cls"):
            self.assertIn(bare, sys.modules, f"{bare} 未被登记到 sys.modules")
            self.assertTrue(sys.modules[bare].__name__.startswith("rapidocr_onnxruntime."),
                            f"{bare} 指向了错误的模块：{sys.modules[bare].__name__}")

    def test_bare_import_resolves_to_textdetector(self):
        RapidOCRProvider._register_submodules()
        import importlib
        mod = importlib.import_module("ch_ppocr_v3_det")
        self.assertTrue(hasattr(mod, "TextDetector"),
                        "顶层名 ch_ppocr_v3_det 缺少 TextDetector（冻结阴影未绕开）")


if __name__ == "__main__":
    unittest.main()
