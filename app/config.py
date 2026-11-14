# -*- coding: utf-8 -*-
"""配置模型与持久化：零第三方依赖、类型安全、损坏可恢复、原子写入。

作者联系方式 · 微信号：TheSun_Also_Rises
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, get_origin, get_type_hints

from . import branding
from .hotkeys import HotkeyError, parse_hotkey

THEMES = ("light", "dark")
# 手动输入翻译：输入停止后固定 1 秒自动翻译，不可配置、无需点按或快捷键。
AUTO_TRANSLATE_DELAY_MS = 1000
LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})?$")

# 开发态回退：复用既有 V0.3 已核验的权重，避免在开发目录重复存放 1 GiB 文件。
DEV_MODEL_FALLBACK_REL = Path("..") / "Π-Lingo" / "resources" / "models" / "bundled" / branding.TRANSLATION_MODEL_FILE


@dataclass
class Settings:
    # 截图监听（OCR）
    ocr_enabled: bool = True
    # 全局快捷键（划词相关热键已随模块删除）
    hotkey_w3: str = "Ctrl+Shift+I"
    hotkey_ocr: str = "Ctrl+Shift+O"
    # 手动输入窗
    w3_visible: bool = False
    w3_always_on_top: bool = True
    w3_clear_on_close: bool = False
    w3_maximized: bool = False
    # 图片识别窗：与手动输入窗同一套「置顶常驻」策略
    ocr_window_always_on_top: bool = True
    w3_geometry: dict[str, int] = field(default_factory=lambda: {
        "x": 120, "y": 120, "width": 420, "height": 500,
    })
    # 文本与窗口
    max_block_chars: int = 2000
    theme: str = "light"
    font_size: int = 13
    # 引擎
    model_path: str = ""
    ocr_model_dir: str = ""
    ocr_min_confidence: float = 0.5
    source_language: str = "auto"
    # 其它
    autostart: bool = False
    history_enabled: bool = False
    network_guard: bool = True
    global_hotkeys: bool = True

    # ------------------------------------------------------------ 校验
    def validate_and_fix(self) -> list[str]:
        """就地修正非法值，返回 warning 列表；任何输入都不会抛异常。"""
        warnings: list[str] = []
        defaults = Settings()
        for f in fields(Settings):
            name = f.name
            value = getattr(self, name, None)
            expected = _FIELD_TYPES.get(name)
            if expected is bool:
                ok = isinstance(value, bool)
            elif expected is int:
                ok = isinstance(value, int) and not isinstance(value, bool)
            elif expected is float:
                ok = isinstance(value, (int, float)) and not isinstance(value, bool)
            elif expected is str:
                ok = isinstance(value, str)
            elif expected is dict:
                ok = isinstance(value, dict)
            else:
                ok = value is not None
            if not ok:
                setattr(self, name, getattr(defaults, name))
                warnings.append(f"{name}: 类型非法，已恢复默认值")
                value = getattr(self, name)

        if self.theme not in THEMES:
            self.theme = "light"
            warnings.append("theme: 非法枚举，已恢复 light")
        if self.source_language != "auto" and not LANGUAGE_RE.match(self.source_language):
            self.source_language = "auto"
            warnings.append("source_language: 格式非法，已恢复 auto")

        for key in ("hotkey_w3", "hotkey_ocr"):
            spec = getattr(self, key)
            try:
                hk = parse_hotkey(spec)
                setattr(self, key, hk.display)  # 规范化显示
            except HotkeyError:
                setattr(self, key, getattr(defaults, key))
                warnings.append(f"{key}: 快捷键非法，已恢复默认值")

        ranges = {
            "max_block_chars": (200, 10000),
            "font_size": (10, 24),
            "ocr_min_confidence": (0.0, 1.0),
        }
        for name, (lo, hi) in ranges.items():
            value = getattr(self, name)
            clamped = max(lo, min(hi, value))
            if clamped != value:
                setattr(self, name, clamped)
                warnings.append(f"{name}: 超出范围，已夹紧到 {clamped}")

        geom = self.w3_geometry
        if not isinstance(geom, dict):
            self.w3_geometry = defaults.w3_geometry
            warnings.append("w3_geometry: 非法，已恢复默认")
        else:
            cleaned: dict[str, int] = {}
            for k, (lo, hi, dflt) in {
                "x": (-10000, 20000, 120), "y": (-10000, 20000, 120),
                "width": (320, 4000, 480), "height": (240, 3000, 420),
            }.items():
                v = geom.get(k)
                if not isinstance(v, int) or isinstance(v, bool) or not (lo <= v <= hi):
                    cleaned[k] = dflt
                    warnings.append(f"w3_geometry.{k}: 非法，已恢复默认")
                else:
                    cleaned[k] = v
            self.w3_geometry = cleaned
        return warnings

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# 注解在 `from __future__ import annotations` 下是字符串，必须显式解析成真实类型。
_FIELD_TYPES = {name: (get_origin(tp) or tp) for name, tp in get_type_hints(Settings).items()}


def default_config_path() -> Path:
    override = os.environ.get("PILINGO_CONFIG_DIR")
    if override:
        base = Path(override)
    else:
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) / branding.CONFIG_DIR_NAME if appdata else Path.home() / f".{branding.APP_ID}"
    return base / "settings.json"


def resolve_model_path(app_root: Path | None = None, settings: Settings | None = None,
                       env: dict[str, str] | None = None) -> tuple[Path | None, str]:
    """定位本地 GGUF 权重。优先级：显式配置 > 环境变量 > 安装目录 > 开发态回退。

    返回 ``(path, reason)``；找不到时 path 为 None，但绝不触发任何下载。
    """
    env = os.environ if env is None else env
    settings = settings or Settings()
    candidates: list[tuple[Path, str]] = []
    if settings.model_path:
        candidates.append((Path(settings.model_path), "settings.model_path"))
    env_path = env.get("PILINGO_MODEL_PATH")
    if env_path:
        candidates.append((Path(env_path), "PILINGO_MODEL_PATH"))

    # 权重目录候选：显式配置 > 安装目录 > _internal > 工程根 > 环境变量指定目录。
    model_dirs: list[tuple[Path, str]] = []
    if app_root is not None:
        model_dirs.append((Path(app_root) / "resources" / "models" / "bundled", "安装目录"))
        model_dirs.append((Path(app_root) / "_internal" / "resources" / "models" / "bundled",
                           "安装目录 _internal"))
    if getattr(sys, "frozen", False):
        # PyInstaller 冻结后 __file__ 落在临时解包目录，权重实际随包安装在 exe 同级目录。
        exe_dir = Path(sys.executable).resolve().parent
        model_dirs.append((exe_dir / "resources" / "models" / "bundled", "安装目录（冻结运行）"))
        model_dirs.append((exe_dir / "_internal" / "resources" / "models" / "bundled",
                           "安装目录 _internal（冻结运行）"))
    model_dirs.append((Path(__file__).resolve().parent.parent / "resources" / "models" / "bundled",
                       "工程目录"))
    env_dir = env.get("PILINGO_MODEL_DIR")
    if env_dir:
        model_dirs.append((Path(env_dir), "PILINGO_MODEL_DIR"))
    candidates.append((Path(__file__).resolve().parent.parent / DEV_MODEL_FALLBACK_REL,
                       "开发态复用 V0.3 权重"))

    for path, reason in candidates:
        try:
            if path.is_file() and path.stat().st_size > 0:
                return path, reason
        except OSError:
            continue

    # 用户可能手动放入了其它命名 / 其它量化档的 GGUF；扫描权重目录里的任意 .gguf，
    # 优先精确匹配默认档，其次取体积最大的（通常是最完整可用的权重）。
    seen: set[str] = set()
    for folder, label in model_dirs:
        key = str(folder)
        if key in seen or not folder.is_dir():
            continue
        seen.add(key)
        try:
            ggufs = [p for p in folder.glob("*.gguf") if p.is_file() and p.stat().st_size > 0]
        except OSError:
            continue
        if not ggufs:
            continue
        exact = [p for p in ggufs if p.name == branding.TRANSLATION_MODEL_FILE]
        chosen = (exact or sorted(ggufs, key=lambda p: p.stat().st_size, reverse=True))[0]
        return chosen, f"{label}内置权重（自动识别 {chosen.name}）"

    searched = "、".join(dict.fromkeys(str(p) for p, _ in model_dirs))
    return None, ("未找到本地权重；已搜索：" + searched +
                  "。请把 GGUF 放入 resources/models/bundled/，"
                  "或在「设置 → 模型路径」指定，或设置 PILINGO_MODEL_DIR。")


class ConfigStore:
    """线程安全的 JSON 配置仓库。读取损坏文件时自动恢复默认，不抛异常。"""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path is not None else default_config_path()
        self._lock = threading.RLock()
        self.settings = Settings()
        self.warnings: list[str] = []
        self.last_error: str = ""

    def load(self) -> Settings:
        with self._lock:
            self.warnings = []
            self.last_error = ""
            if not self.path.exists():
                self.settings = Settings()
                return self.settings
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                self.last_error = f"配置读取失败：{exc}"
                self.warnings.append("配置文件损坏，已恢复默认设置")
                self.settings = Settings()
                return self.settings
            if not isinstance(raw, dict):
                self.warnings.append("配置文件格式非法，已恢复默认设置")
                self.settings = Settings()
                return self.settings
            known = {f.name for f in fields(Settings)}
            merged = {k: v for k, v in raw.items() if k in known}
            try:
                self.settings = Settings(**merged)
            except TypeError as exc:
                self.warnings.append(f"配置字段异常（{exc}），已恢复默认设置")
                self.settings = Settings()
            self.warnings.extend(self.settings.validate_and_fix())
            return self.settings

    def save(self) -> bool:
        """原子写入：先写同目录 .tmp，再 os.replace；失败降级为直接覆盖写。"""
        with self._lock:
            data = json.dumps(self.settings.as_dict(), ensure_ascii=False, indent=2)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + ".tmp")
            try:
                tmp.write_text(data, encoding="utf-8")
                os.replace(tmp, self.path)
                return True
            except OSError as exc:
                self.last_error = f"原子写入失败，尝试直接写入：{exc}"
                try:
                    self.path.write_text(data, encoding="utf-8")
                    return True
                except OSError as exc2:
                    self.last_error = f"配置写入失败：{exc2}"
                    return False

    def update(self, **kwargs: Any) -> list[str]:
        """只接受已知字段；更新后立即校验并持久化。"""
        with self._lock:
            known = {f.name for f in fields(Settings)}
            for key, value in kwargs.items():
                if key not in known:
                    raise KeyError(f"未知配置项：{key}")
                setattr(self.settings, key, value)
            warnings = self.settings.validate_and_fix()
            self.save()
            self.warnings = warnings
            return warnings
