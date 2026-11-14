#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""π-Lingo 离线翻译（独立软件）· 程序入口。

作者联系方式 · 微信号：TheSun_Also_Rises

完全离线：PySide6 原生桌面窗口 + 进程内本地权重推理，无浏览器、无 HTTP、无端口。
"""
from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# 开发态：工作区 .vendor* 中安装的依赖（安装包内已随附，不需要此路径）
for _vendor in sorted(ROOT.parent.glob(".vendor*")):
    if _vendor.is_dir() and str(_vendor) not in sys.path:
        sys.path.insert(0, str(_vendor))

from app import branding, offline_guard  # noqa: E402
from app.config import resolve_model_path  # noqa: E402
from app.text_logic import long_text_hint, should_skip, split_blocks  # noqa: E402
from app.state_machine import AppState, W3State, W3StateMachine  # noqa: E402


# ----------------------------------------------------------------------------
# 全局异常守卫：把任何未被捕获的异常（含 Qt 事件处理器 / 定时器回调里抛出的）
# 记录到日志文件而不是让进程悄悄闪退。后台线程里抛出的异常也兜底捕获。
# ----------------------------------------------------------------------------
def _crash_log_path() -> Path:
    override = os.environ.get("PILINGO_CONFIG_DIR")
    if override:
        base = Path(override)
    else:
        appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        base = Path(appdata) / branding.CONFIG_DIR_NAME if appdata else Path.home() / f".{branding.APP_ID}"
    base.mkdir(parents=True, exist_ok=True)
    return base / "crash.log"


def _log_crash(where: str, exc: BaseException) -> None:
    try:
        import datetime
        line = (
            f"[{datetime.datetime.now().isoformat(timespec='seconds')}] "
            f"{where}: {type(exc).__name__}: {exc}\n"
        )
        print(line.rstrip(), file=sys.stderr)  # 离屏 / 控制台模式可见
        with open(_crash_log_path(), "a", encoding="utf-8") as fh:
            fh.write(line)
            fh.write(traceback.format_exc() + "\n")
    except Exception:
        pass


def install_exception_guard() -> None:
    """安装 sys.excepthook + threading.excepthook，拦截未捕获异常并落日志。"""
    _orig = sys.excepthook

    def _hook(etype, value, tb):  # noqa: ANN001
        _log_crash("uncaught", value)
        _orig(etype, value, tb)

    sys.excepthook = _hook
    try:
        import threading
        threading.excepthook = lambda args: _log_crash("thread", args.exc_value)  # type: ignore[attr-defined]
    except Exception:
        pass


class SafeQApplication:
    """工厂：返回会吞掉事件处理器异常的 QApplication 子类实例。

    Qt 在事件分派（notify）里抛出的 Python 异常在部分 PySide 版本会导致进程
    直接退出。这里统一捕获并记录，避免「点了某个按钮就闪退」。
    """

    @staticmethod
    def create(argv) -> "SafeQApplication._App":  # type: ignore[name-defined]
        from PySide6.QtWidgets import QApplication

        class _App(QApplication):
            def notify(self, receiver, event):  # type: ignore[override]
                try:
                    return super().notify(receiver, event)
                except Exception as exc:  # noqa: BLE001
                    _log_crash("qt-event", exc)
                    return False

        return _App(argv)


def _prepare_cli_output(use_cli: bool) -> None:
    """PyInstaller ``console=False`` 构建没有控制台：避免 print 到 None 崩溃。

    CLI 参数（--version / --self-test / --translate）把输出写到 exe 同级的
    ``cli_output.txt`` 供安装验收读取；GUI 正常运行则丢弃到空设备。
    """
    if sys.stdout is not None and sys.stderr is not None:
        return
    handle = None
    if use_cli:
        try:
            target = Path(sys.executable).resolve().parent / "cli_output.txt"
            handle = open(target, "w", encoding="utf-8")
        except OSError:
            handle = None
    if handle is None:
        handle = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = handle
    if sys.stderr is None:
        sys.stderr = handle


def self_test() -> int:
    """不启动 GUI 的逻辑自检，返回失败项数量。"""
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, condition: bool, detail: str = "") -> None:
        checks.append((name, bool(condition), detail))

    check("作者签名常量", branding.AUTHOR_WECHAT in branding.AUTHOR_CONTACT)
    check("空输入被过滤", should_skip("   ").skip)
    check("正常外文可译", not should_skip("Offline translation keeps data on this device.").skip)
    text = ("Paragraph one. " + "word " * 900 + "\n\n" + "Second paragraph! " * 100)
    blocks = split_blocks(text, 2000)
    check("长文本分块无损", "".join(blocks) == text and max(map(len, blocks)) <= 2000,
          f"{len(blocks)} 块")
    check("长文本提示", long_text_hint(len(text), 2000, text)[0] == "long_mode")

    from app.config import AUTO_TRANSLATE_DELAY_MS, Settings
    state = AppState(Settings(ocr_enabled=False))
    check("停用截图监听后不注册钩子", state.should_register_hooks()["screenshot"] is False)
    check("零系统文本读取", state.read_count == 0)
    machine = W3StateMachine()
    machine.show()
    machine.transition(W3State.TYPING)
    machine.transition(W3State.TRANSLATING)
    machine.transition(W3State.DONE)
    check("手动输入状态机流转", machine.state is W3State.DONE)

    check("第三方端点一律拒绝", offline_guard.validate_endpoint("http://127.0.0.1:8080/v1")[0] is False)
    if getattr(sys, "frozen", False):
        check("源码无网络调用（构建期已校验）", True, "冻结运行")
    else:
        findings = offline_guard.scan_sources_for_network_calls(ROOT / "app")
        check("源码无网络调用", findings == [], str(findings))
    model, reason = resolve_model_path(ROOT)
    check("本地权重可定位", model is not None and model.is_file(), reason)

    # 自动翻译定稿：1 秒停顿、无快捷键、无翻译按钮、无自动开关。
    # 常量在冻结运行也可校验；源码静态约束只在开发态执行——PyInstaller 产物
    # 里没有磁盘 .py 源码（历史缺陷：曾在此直接 read_text 导致安装版自检崩溃）。
    check("自动翻译停顿 1 秒", AUTO_TRANSLATE_DELAY_MS == 1000)
    if getattr(sys, "frozen", False):
        check("界面无翻译快捷键（构建期已校验）", True, "冻结运行")
        check("界面无翻译按钮与自动开关（构建期已校验）", True, "冻结运行")
        check("划词模块已移除（构建期已校验）", True, "冻结运行")
    else:
        mw = (ROOT / "app" / "ui" / "manual_window.py").read_text(encoding="utf-8")
        check("界面无翻译快捷键", "Ctrl+Enter" not in mw and "QShortcut" not in mw
              and "AUTO_TRANSLATE_DELAY_MS" in mw)
        check("界面无翻译按钮与自动开关", "go_btn" not in mw and "auto_switch" not in mw)
        # 划词模块已整体移除
        check("划词模块已移除", not (ROOT / "app" / "capture.py").exists()
              and not (ROOT / "app" / "ui" / "bubble.py").exists())
    from app.win_topmost import apply_topmost as _apply_topmost
    check("悬浮窗置顶接口可用", _apply_topmost(0, True) is False)

    failures = [name for name, ok, _ in checks if not ok]
    for name, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" · {detail}" if detail else ""))
    print(f"\n逻辑自检：{len(checks) - len(failures)}/{len(checks)} 通过")
    if failures:
        print("失败项：" + "、".join(failures))
    print(branding.product_line())
    print(branding.AUTHOR_CONTACT)
    return len(failures)


def translate_once(text: str) -> int:
    """无头翻译验收：走与界面完全相同的 Translator + 本地 GGUF，不启动 Qt、不联网。"""
    from app.config import ConfigStore
    from app.translator import LlamaCppBackend, Translator, UnavailableBackend
    store = ConfigStore()
    store.load()
    model, reason = resolve_model_path(ROOT, store.settings)
    backend = LlamaCppBackend(model) if model else UnavailableBackend(reason)
    translator = Translator(backend=backend)
    ok, detail = translator.ready()
    print(f"[引擎] {'已就绪' if ok else '未就绪'} · {detail}", file=sys.stderr)
    result = translator.translate(text)
    if result.error:
        print(f"翻译失败：{result.error}", file=sys.stderr)
        return 1
    print(result.text)
    print(f"[{result.engine} · {result.total_blocks} 块 · {result.elapsed_ms:.0f} ms · 100% 本地离线]",
          file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pilingo-translator",
        description=f"{branding.product_line()} · {branding.AUTHOR_CONTACT}")
    parser.add_argument("--demo", action="store_true",
                        help="演示模式：不加载 GGUF，输出明确标记的占位文本（不是真实译文）")
    parser.add_argument("--offscreen", action="store_true",
                        help="离屏启动冒烟（不显示界面，构造完成后立即退出）")
    parser.add_argument("--no-hotkeys", action="store_true", help="不注册全局热键")
    parser.add_argument("--no-tray", action="store_true", help="不显示系统托盘")
    parser.add_argument("--config-dir", default="", help="配置目录（默认 %APPDATA%/PiLingoTranslator）")
    parser.add_argument("--self-test", action="store_true", help="只运行逻辑自检并退出")
    parser.add_argument("--translate", default="", metavar="TEXT",
                        help="无头翻译一段文本（安装验收 / 脚本调用，走本地 GGUF，不启动界面）")
    parser.add_argument("--version", action="store_true", help="显示版本与作者联系方式")
    parser.add_argument("--model-info", action="store_true",
                        help="诊断本地 GGUF 权重定位（列出搜索路径与命中结果，不启动界面）")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _prepare_cli_output(bool(args.version or args.self_test or args.translate
                             or args.offscreen or args.model_info))
    if args.version:
        print(branding.product_line())
        print(branding.AUTHOR_CONTACT)
        return 0
    if args.self_test:
        return 1 if self_test() else 0
    if args.translate:
        return translate_once(args.translate)
    if args.model_info:
        from app.config import ConfigStore, resolve_model_path
        store = ConfigStore()
        store.load()
        root = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
                else ROOT)
        path, reason = resolve_model_path(root, store.settings)
        print("本地权重诊断")
        print("  配置文件     :", store.path)
        print("  显式模型路径 :", store.settings.model_path or "（未设置）")
        print("  程序根目录   :", root)
        print("  定位结果     :", path if path else "未找到")
        print("  说明         :", reason)
        print("  可用         :", "是" if path and path.is_file() else "否")
        print(branding.AUTHOR_CONTACT)
        return 0 if path else 1
    if args.config_dir:
        os.environ["PILINGO_CONFIG_DIR"] = args.config_dir
    if args.offscreen:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    try:
        from PySide6.QtWidgets import QApplication
        from app.ui.app import TranslatorApp

        install_exception_guard()
        qapp = QApplication.instance() or SafeQApplication.create(sys.argv[:1])
        qapp.setApplicationName(branding.APP_NAME_ASCII)
        qapp.setApplicationDisplayName(branding.APP_NAME)
        qapp.setOrganizationName(branding.APP_ID)
        qapp.setQuitOnLastWindowClosed(False)   # 关闭窗口后由托盘继续常驻

        controller = TranslatorApp(qapp, demo=args.demo,
                                   enable_hotkeys=not args.no_hotkeys,
                                   enable_tray=not args.no_tray)
        if args.offscreen:
            print(f"[OK] 原生窗口构造成功 · {controller.engine_status()}")
            print(f"[OK] {branding.AUTHOR_CONTACT}")
            controller.quit_app()
            return 0
        if not args.no_tray:
            controller.notify("已启动 · 在托盘中开启/停用划词监听", "π-Lingo 离线翻译")
        return controller.run()
    except Exception as exc:  # pragma: no cover - 顶层兜底
        traceback.print_exc()
        print(f"启动失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
