# -*- coding: utf-8 -*-
"""离线守卫：运行时阻断所有出站连接，并静态检查源码不引入网络调用。

作者联系方式 · 微信号：TheSun_Also_Rises

PRD 硬约束：零出站请求、无遥测、无在线 OCR / 在线大模型、不提供第三方接入，
且不允许「仅本机回环 HTTP」调用模型引擎。本模块是该约束的可执行与可验收实现。
"""
from __future__ import annotations

import re
import socket
import threading
from pathlib import Path
from urllib.parse import urlparse

BLOCK_REASON = "π-Lingo 离线翻译：已禁止全部网络连接（零出站）"


class NetworkBlockedError(RuntimeError):
    """有代码试图建立网络连接时被抛出。"""


_ORIGINALS: dict[str, object] = {}
_ENABLED = False
_LOCK = threading.RLock()
_ATTEMPTS: list[tuple[str, str]] = []


def _record(address: object) -> None:
    try:
        host, port = address[0], address[1]  # type: ignore[index]
        entry = (str(host), str(port))
    except Exception:
        entry = (str(address), "?")
    with _LOCK:
        _ATTEMPTS.append(entry)


def _guarded_connect(self: socket.socket, address: object) -> None:
    _record(address)
    raise NetworkBlockedError(BLOCK_REASON)


def _guarded_connect_ex(self: socket.socket, address: object) -> int:
    _record(address)
    raise NetworkBlockedError(BLOCK_REASON)


def _guarded_create_connection(*args: object, **kwargs: object) -> socket.socket:
    address = args[0] if args else kwargs.get("address")
    _record(address)
    raise NetworkBlockedError(BLOCK_REASON)


def enable() -> bool:
    """启用阻断（幂等）。返回本次是否真的执行了安装。"""
    global _ENABLED
    with _LOCK:
        if _ENABLED:
            return False
        _ORIGINALS.update({
            "connect": socket.socket.connect,
            "connect_ex": socket.socket.connect_ex,
            "create_connection": socket.create_connection,
        })
        socket.socket.connect = _guarded_connect  # type: ignore[assignment]
        socket.socket.connect_ex = _guarded_connect_ex  # type: ignore[assignment]
        socket.create_connection = _guarded_create_connection  # type: ignore[assignment]
        _ENABLED = True
        return True


def disable() -> bool:
    """恢复原始 socket 行为（幂等），供测试与关闭程序时调用。"""
    global _ENABLED
    with _LOCK:
        if not _ENABLED:
            return False
        socket.socket.connect = _ORIGINALS["connect"]  # type: ignore[assignment]
        socket.socket.connect_ex = _ORIGINALS["connect_ex"]  # type: ignore[assignment]
        socket.create_connection = _ORIGINALS["create_connection"]  # type: ignore[assignment]
        _ENABLED = False
        return True


def is_enabled() -> bool:
    with _LOCK:
        return _ENABLED


def blocked_attempts() -> tuple[tuple[str, str], ...]:
    with _LOCK:
        return tuple(_ATTEMPTS)


def reset_attempts() -> None:
    with _LOCK:
        _ATTEMPTS.clear()


def validate_endpoint(url: str) -> tuple[bool, str]:
    """第三方 / BYO 端点校验：一律拒绝（包括 127.0.0.1 回环）。

    返回 ``(allowed, reason)``，allowed 恒为 False —— 本软件不提供任何在线接入。
    """
    if not isinstance(url, str) or not url.strip():
        return False, "未配置第三方端点（本软件不提供在线接入）"
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() in {"http", "https", "ws", "wss", "ftp"}:
        return False, "完全离线：拒绝任何网络端点，包含仅本机回环 HTTP"
    return False, "端点格式不支持；本软件仅使用进程内本地权重"


# ------------------------------------------------------------ 静态验收
_BANNED = (
    (r"\brequests\s*\.\s*(get|post|put|delete|patch|Session|request)\s*\(", "requests"),
    (r"\burllib\s*\.\s*request\b", "urllib.request"),
    (r"\bhttp\s*\.\s*client\b", "http.client"),
    (r"\bhttpx\s*\.", "httpx"),
    (r"\baiohttp\s*\.", "aiohttp"),
    (r"\bsocket\s*\.\s*create_connection\s*\(", "socket.create_connection"),
    (r"\bsocket\s*\.\s*socket\s*\(", "socket.socket"),
    (r"\bWebEngineView\b|\bQWebEngineView\b", "Web 前端组件"),
    (r"\bwebbrowser\s*\.", "webbrowser"),
)


def scan_sources_for_network_calls(root: Path | str) -> list[str]:
    """扫描应用源码，返回违规位置列表；无违规返回空列表。

    ``offline_guard.py`` 自身是唯一允许持有 socket 引用的文件，跳过。
    """
    root = Path(root)
    findings: list[str] = []
    if not root.is_dir():
        return [f"源码目录不存在：{root}"]
    for path in sorted(root.rglob("*.py")):
        if path.name == "offline_guard.py" or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            findings.append(f"{path}: 无法读取（{exc}）")
            continue
        for pattern, label in _BANNED:
            for match in re.finditer(pattern, text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.name}:{line} 出现 {label}")
    return findings
