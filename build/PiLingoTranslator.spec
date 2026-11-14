# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包规格（只打包程序本体；GGUF/OCR 模型由 Inno Setup 直接分发）。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
ICON = ROOT / "resources" / "PiLingo.ico"

# 开发态依赖装在工作区 .vendor*（避免覆盖系统 Python）。打包时必须一起收进去，
# 否则安装完会出现「引擎未就绪 / OCR 导入失败」。
# 关键修正：rapidocr_onnxruntime 在运行期用 Path(__file__).parent 相对加载
# models/*.onnx 与 config.yaml——若只把它的 .py 打进 PYZ，运行时 __file__ 会指向
# 虚拟路径，导致找不到权重（这正是安装版 OCR 报错的根因）。因此该包必须作为
# 「磁盘松散文件」分发，并剔除出 PYZ。其余推理依赖用 collect_all 完整收集。
import sys  # noqa: E402
from PyInstaller.utils.hooks import collect_all  # noqa: E402

VENDOR_DIRS = [p for p in ROOT.parent.glob(".vendor*") if p.is_dir()]
for _vendor in VENDOR_DIRS:
    if str(_vendor) not in sys.path:
        sys.path.insert(0, str(_vendor))

HIDDEN = [
    "app", "app.branding", "app.config", "app.hotkeys", "app.offline_guard",
    "app.text_logic", "app.state_machine", "app.translator", "app.ocr",
    "app.ui", "app.ui.theme", "app.ui.widgets",
    "app.ui.manual_window", "app.ui.ocr_window", "app.ui.dialogs",
    "app.ui.tray", "app.ui.app",
]

# 需要随包完整收集（代码 + 数据 + 原生扩展）的第三方推理依赖。
# 注意：rapidocr_onnxruntime 不在此处 collect_all，它在下方作为松散文件单独处理。
PACK_PACKAGES = [
    "llama_cpp", "onnxruntime", "numpy", "numpy.libs",
    "PIL", "cv2", "shapely", "pyclipper",
]
extra_binaries: list = []
extra_datas: list = []
for _pkg in PACK_PACKAGES:
    try:
        __import__(_pkg.split(".")[0])
    except ImportError:
        continue
    try:
        _bins, _datas, _hidden = collect_all(_pkg)
    except Exception as _exc:  # pragma: no cover - 平台 / 依赖相关
        print(f"[warn] collect_all({_pkg}) 失败：{_exc}")
        continue
    extra_binaries += _bins
    extra_datas += _datas
    for _h in _hidden:
        if _h not in HIDDEN:
            HIDDEN.append(_h)

# 可选增强依赖：装了就打进去，没装也不影响构建
import importlib.util as _ilu  # noqa: E402
for _mod in ("llama_cpp", "onnxruntime", "rapidocr", "uiautomation"):
    try:
        if _ilu.find_spec(_mod.split(".")[0]) is not None and _mod not in HIDDEN:
            HIDDEN.append(_mod)
    except (ImportError, ValueError):
        pass

# 注意：rapidocr_onnxruntime 不在 PyInstaller 收集范围内（已加入 excludes），也不走
# datas——datas 条目以 .py 结尾时 PyInstaller 会把它当成「模块」而错建为目录。它的整包
# （.py + models/*.onnx + config.yaml）由 build_installer.py 在 PyInstaller 之后直接
# 拷入 dist/_internal/rapidocr_onnxruntime/，保证运行时 __file__ 是真实目录。

datas = [
    (str(ROOT / "licenses"), "licenses"),
    (str(ROOT / "resources" / "models" / "README.md"), "resources/models"),
    # QSS 里引用的图片资源（步进箭头）：必须随包分发，否则安装版箭头空白。
    (str(ROOT / "app" / "ui" / "assets"), "app/ui/assets"),
    # 新 icon 唯一真源：运行时托盘 / 窗口图标要读真实文件，不能只内嵌进 exe。
    (str(ROOT / "resources" / "PiLingo.ico"), "resources"),
] + extra_datas

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)] + [str(p) for p in VENDOR_DIRS],
    binaries=extra_binaries,
    datas=datas,
    hiddenimports=HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # rapidocr_onnxruntime / rapidocr 只以「磁盘松散文件」形式随包分发（见 extra_datas），
    # 必须彻底排除出 PyInstaller 的模块收集，否则会与松散包目录冲突、把 __init__.py
    # 错建为目录导致运行时导入失败。运行期由 app.ocr 用 importlib 动态导入。
    # yaml（PyYAML）在 PyInstaller 下常被只收成 C 扩展而漏掉纯 Python 的 __init__.py，
    # 导致 import 后成命名空间包、缺少 yaml.load；同样排除并由 build_installer 注入真实包。
    excludes=["tkinter", "matplotlib", "notebook", "IPython",
              "rapidocr_onnxruntime", "rapidocr", "yaml"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)
# rapidocr_onnxruntime 必须作为磁盘松散文件（见上方 extra_datas），因此从 PYZ 剔除，
# 否则双重存在时 PYZ 优先，运行时 __file__ 又变回虚拟路径导致模型加载失败。
a.pure = [t for t in a.pure if not str(t[0]).startswith("rapidocr_onnxruntime")]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PiLingoTranslator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(ROOT / "build" / "version_info.txt"),
    icon=str(ICON) if ICON.is_file() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PiLingoTranslator",
)
