# -*- coding: utf-8 -*-
"""文本过滤、语言检测、无损分块、长文本提示与去抖测试。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import unittest

from app import text_logic as TL


class NormalizeTest(unittest.TestCase):
    def test_normalizes_newlines_and_zero_width(self):
        self.assertEqual(TL.normalize_selection(" a\r\nb\u200b \r\n"),
                         "a\nb")

    def test_keeps_paragraph_structure(self):
        self.assertEqual(TL.normalize_selection("A\n\nB\n"), "A\n\nB")

    def test_rejects_non_string(self):
        with self.assertRaises(TypeError):
            TL.normalize_selection(123)


class SkipTest(unittest.TestCase):
    def test_empty_and_short(self):
        self.assertEqual(TL.should_skip("   ").reason, "empty")
        self.assertEqual(TL.should_skip("a").reason, "too_short")

    def test_no_letters(self):
        self.assertEqual(TL.should_skip("2026-11-12 !!").reason, "no_letters")

    def test_windows_paths_and_filenames(self):
        # 只有完整路径 / 链接才过滤；纯文件名现在是可翻译对象（高频核心场景）。
        for value in (r"C:\Users\example\Desktop\report.docx",
                      r"\\server\share\folder", "/Users/example/Desktop",
                      "https://example.com/page"):
            with self.subTest(value=value):
                self.assertEqual(TL.should_skip(value).reason, "path_or_filename")

    def test_bare_filename_is_translatable(self):
        d = TL.should_skip("Annual_Report_2026.docx")
        self.assertFalse(d.skip)
        self.assertEqual(d.kind, "filename")
        self.assertEqual(d.normalized, "Annual Report 2026")
        self.assertTrue(TL.is_bare_filename("report.docx"))
        self.assertEqual(TL.prepare_filename_for_translation("myPhotos-v2.PNG"),
                         "my Photos v2")

    def test_multiple_selected_filenames_are_translatable(self):
        value = "report.docx\nphoto.png\nnotes.txt"
        d = TL.should_skip(value)
        self.assertFalse(d.skip)
        self.assertEqual(d.kind, "filename")
        self.assertEqual(d.normalized, "report\nphoto\nnotes")

    def test_normal_foreign_text_is_translatable(self):
        cases = [
            "Offline translation keeps every selected phrase on this device.",
            "The local model handles the request without any network call.",
            "Das ist ein schöner Tag und die Sonne scheint.",
            "这是一段中文，也需要给出译文。",
            "A/B testing improves the result.",
        ]
        for value in cases:
            with self.subTest(value=value):
                self.assertFalse(TL.should_skip(value).skip, value)

    def test_reason_label(self):
        self.assertIn("路径", TL.should_skip(r"C:\temp\file.pdf").reason_label)
        # 纯文件名现在可译，不再是过滤理由
        self.assertEqual(TL.should_skip("file.pdf").reason_label, "")


class LanguageTest(unittest.TestCase):
    def test_scripts(self):
        self.assertEqual(TL.detect_language("这是一段中文测试文本")[0], "zh")
        self.assertEqual(TL.detect_language("これは日本語のテストです")[0], "ja")
        self.assertEqual(TL.detect_language("이것은 한국어 테스트입니다")[0], "ko")
        self.assertEqual(TL.detect_language("Это тестовый текст")[0], "ru")
        self.assertEqual(TL.detect_language("Hello world, this is a test")[0], "en")

    def test_latin_hints(self):
        code, label = TL.detect_language("Das ist ein schöner Tag und die Sonne scheint nicht.")
        self.assertEqual(code, "de")
        self.assertEqual(label, "德语")

    def test_unknown(self):
        self.assertEqual(TL.detect_language("?!?!")[0], "unknown")


class SplitBlocksTest(unittest.TestCase):
    @staticmethod
    def sample():
        return ("Paragraph one. " + "word " * 900 + "\n\n"
                + "Second paragraph! " * 100 + "\n" + "中文段落。" * 300)

    def test_short_text_single_block(self):
        self.assertEqual(TL.split_blocks("Hello world"), ["Hello world"])

    def test_exact_boundary_single_block(self):
        text = "a" * 2000
        self.assertEqual(TL.split_blocks(text, 2000), [text])

    def test_round_trip_and_size_limit(self):
        text = self.sample()
        blocks = TL.split_blocks(text, 2000)
        self.assertGreater(len(blocks), 1)
        self.assertEqual("".join(blocks), text)
        self.assertLessEqual(max(len(b) for b in blocks), 2000)

    def test_no_boundary_text_still_splits(self):
        text = "x" * 6001
        blocks = TL.split_blocks(text, 1000)
        self.assertEqual("".join(blocks), text)
        self.assertTrue(all(len(b) <= 1000 for b in blocks))

    def test_sentence_boundaries_preferred(self):
        text = ("First sentence. " * 200).strip()
        blocks = TL.split_blocks(text, 300)
        self.assertTrue(all(b.rstrip().endswith(".") for b in blocks[:-1]))

    def test_empty_and_invalid(self):
        self.assertEqual(TL.split_blocks(""), [])
        with self.assertRaises(ValueError):
            TL.split_blocks("abc", 0)
        with self.assertRaises(TypeError):
            TL.split_blocks(None)

    def test_make_blocks_index_and_count(self):
        blocks = TL.make_blocks(self.sample(), 2000)
        self.assertEqual([b.index for b in blocks], list(range(1, len(blocks) + 1)))
        self.assertTrue(all(b.translatable for b in blocks))
        self.assertEqual(sum(b.char_count for b in blocks), len(self.sample()))


class LongTextHintTest(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(TL.long_text_hint(100)[0], "none")
        self.assertEqual(TL.long_text_hint(800)[0], "suggest_maximize")
        self.assertIn("最大化", TL.long_text_hint(800)[1])
        level, message = TL.long_text_hint(6000, 2000)
        self.assertEqual(level, "long_mode")
        self.assertIn("块", message)

    def test_exact_block_count_with_real_text(self):
        text = "Sentence one. " * 400
        level, message = TL.long_text_hint(len(text), 500, text)
        self.assertIn(str(len(TL.split_blocks(text, 500))), message)


class DebouncerTest(unittest.TestCase):
    def test_duplicate_within_window_rejected(self):
        clock = [0.0]
        d = TL.SelectionDebouncer(800, clock=lambda: clock[0])
        self.assertTrue(d.should_accept("Hello world"))
        clock[0] = 0.2
        self.assertFalse(d.should_accept("Hello world"))
        clock[0] = 0.9
        self.assertTrue(d.should_accept("Hello world"))
        self.assertEqual((d.accepted, d.rejected), (2, 1))

    def test_different_text_accepted_and_reset(self):
        d = TL.SelectionDebouncer(800, clock=lambda: 0.0)
        self.assertTrue(d.should_accept("one"))
        self.assertTrue(d.should_accept("two"))
        d.reset()
        self.assertTrue(d.should_accept("one"))

    def test_negative_window_rejected(self):
        with self.assertRaises(ValueError):
            TL.SelectionDebouncer(-1)


if __name__ == "__main__":
    unittest.main()
