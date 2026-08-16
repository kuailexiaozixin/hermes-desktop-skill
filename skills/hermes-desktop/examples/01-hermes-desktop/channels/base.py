"""channels/base.py — 渠道连接器基类 + 标准库 HTTP / 签名工具。

全部工具函数仅依赖 Python 标准库。所有「发网络请求」的动作都经
``_URLOPEN`` 钩子，便于离线测试用假实现替换（不触碰真实网络）。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

# ── 网络钩子：测试时替换为假实现 ──────────────────────────────────────────
_URLOPEN: Callable[..., Any] = urllib.request.urlopen
_URLOPEN_LOCK = threading.Lock()


def set_urlopen(fn: Callable[..., Any]) -> None:
    """替换底层 HTTP 实现（测试用，例如返回预设的 json）。"""
    global _URLOPEN
    with _URLOPEN_LOCK:
        _URLOPEN = fn


def _reset_urlopen() -> None:
    global _URLOPEN
    with _URLOPEN_LOCK:
        _URLOPEN = urllib.request.urlopen


# ── HTTP 工具（标准库 urllib，超时 + JSON 解析）───────────────────────────
def http_post_json(url: str, payload: dict | list, *,
                   headers: dict | None = None, timeout: float = 20.0) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 **(headers or {})})
    try:
        with _URLOPEN(req, timeout=timeout) as resp:  # type: ignore[call-arg]
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace") if hasattr(e, "read") else ""
        raise ChannelError(f"HTTP {e.code}: {body[:300]}") from e
    except urllib.error.URLError as e:
        raise ChannelError(f"网络错误：{e.reason}") from e
    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError:
        return {"raw": body}


def http_get_json(url: str, *, params: dict | None = None,
                  timeout: float = 20.0) -> dict:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET",
                                 headers={"Accept": "application/json"})
    try:
        with _URLOPEN(req, timeout=timeout) as resp:  # type: ignore[call-arg]
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise ChannelError(f"HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise ChannelError(f"网络错误：{e.reason}") from e
    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError:
        return {"raw": body}


# ── 签名工具（标准库 hashlib / hmac / base64）────────────────────────────
def b64_hmac_sha256(key: str, msg: str) -> str:
    return base64.b64encode(
        hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    ).decode("ascii")


def hex_hmac_sha256(key: str, msg: str) -> str:
    return hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()


def sha1_hex_sorted(*parts: str) -> str:
    """微信/企业微信式签名：对参数排序后拼接做 SHA1（hex）。"""
    return hashlib.sha1("".join(sorted(parts)).encode("utf-8")).hexdigest()


# ── 数据类 ───────────────────────────────────────────────────────────────
@dataclass
class InboundMessage:
    channel: str
    sender_id: str
    text: str
    conversation_key: str | None = None   # 同一对话的稳定标识（chat_id / open_id）
    sender_name: str | None = None
    message_id: str | None = None
    raw: dict | None = None


@dataclass
class OutboundResult:
    ok: bool
    error: str | None = None
    message_id: str | None = None


class ChannelError(Exception):
    """渠道层可恢复/可展示的错误。"""


@dataclass
class ChannelMeta:
    """渠道静态元数据（用于前端渲染配置表单）。"""
    cid: str
    label: str
    icon: str
    mode: str                       # polling | webhook | bridge
    desc: str
    fields: list = field(default_factory=list)   # [{"key","label","secret","placeholder"}]
    needs_bridge: bool = False


# ── 连接器基类 ───────────────────────────────────────────────────────────
class ChannelConnector(ABC):
    """所有 IM 渠道连接器的统一抽象。

    两种 inbound 模式：
    * ``polling``：后台线程反复调用 ``poll_once()`` 拉取消息（Telegram）。
    * ``webhook``：由本地 ``WebhookReceiver`` 把平台推送的事件转交 ``handle_webhook()``
                  （飞书/企微/钉钉/Slack/Discord）。无需自带线程。
    """

    meta: ChannelMeta

    def __init__(self) -> None:
        self._connected = False
        self._lock = threading.Lock()
        self._cfg: dict = {}

    # —— 配置 / 生命周期 ——
    def configure(self, config: dict) -> None:
        self._cfg = dict(config or {})

    @abstractmethod
    def connect(self) -> dict:
        """建立连接；返回 {"ok":bool,"error"?:str}。"""

    @abstractmethod
    def disconnect(self) -> None:
        """断开并释放资源。"""

    def is_connected(self) -> bool:
        return self._connected

    def health(self) -> dict:
        return {"ok": True, "connected": self._connected}

    # —— inbound ——
    def poll_once(self) -> list[InboundMessage]:
        """轮询模式：拉取一批入站消息（默认空，轮询型连接器需重写）。"""
        return []

    def handle_webhook(self, payload: dict, headers: dict,
                       raw_body: bytes | None = None) -> list[InboundMessage]:
        """Webhook 模式：解析平台推送事件（默认空，Webhook 型需重写）。"""
        return []

    def webhook_path(self) -> str | None:
        """Webhook 模式监听的路径（如 "/wh/feishu"）；非 webhook 返回 None。"""
        return None

    # —— outbound ——
    @abstractmethod
    def send(self, recipient: str, text: str) -> OutboundResult:
        """向 recipient 发送文本；recipient 含义因平台而异（chat_id / channel 等）。"""

    # —— 辅助 ——
    def _sleep(self, secs: float) -> None:
        time.sleep(secs)

    @staticmethod
    def _split_long(text: str, limit: int = 4000) -> list[str]:
        """按换行切分；超长单行也按 limit 硬拆，避免超出平台单条消息上限。"""
        out: list[str] = []
        for raw_line in text.split("\n"):
            if len(raw_line) <= limit:
                out.append(raw_line)
                continue
            for i in range(0, len(raw_line), limit):
                out.append(raw_line[i:i + limit])
        return out or [text]
