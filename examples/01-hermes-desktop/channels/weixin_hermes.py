"""channels/weixin_hermes.py — Hermes 官方 iLink 微信 Bot（进程内长轮询，无外部 SDK）。

设计：
- 采用 Hermes 官方 iLink Bot API 的「长轮询」模式（HTTP long-poll，~35s 超时），
  无需公网 IP 或 Webhook——与桌面本地部署天然契合。
- 出站：文本/媒体经 iLink API（send / send_image / send_document ...）。
- 媒体：入站媒体经 CDN 以加密引用下发，用 per-file AES-128-ECB(PKCS#7) 密钥解密
  （``cryptography`` 为**可选懒导入**，已在冻结 venv 内 46.0.7；缺失时仅跳过媒体解密）。
- 凭证来源：``hermes gateway setup --channel weixin`` 扫码后保存于
  ``~/.hermes/weixin/accounts/``（account_id / token / base_url）。本连接器直接复用这些值，
  不依赖外部 gateway 进程——Agent 仍在桌面进程内直跑。

⚠️ 诚实声明（务必对照你的 ``hermes gateway setup`` 输出核实）：
  iLink 的底层 HTTP 字段级 envelope 未完全公开。本实现按 docs/channels-qq-wechat.md
  披露的端点名（getupdates / send / getuploadurl / getconfig）、``context_token`` 回显、
  AES-128-ECB + ``errcode=-14`` 会话过期等契约实现，路径/包体字段为「最佳努力」，
  **首次上线前需用真实 base_url/凭证联调验证**。所有端点 URL 均可通过 config 的
  ``api_base`` / 各 path 字段覆盖，便于对齐真实网关。
"""
from __future__ import annotations

import base64
import json
import threading
import time
from typing import Any

from .base import (
    ChannelConnector, ChannelError, ChannelMeta, InboundMessage,
    OutboundResult, http_post_json,
)
from .weixin_qr_login import load_weixin_account

# 默认 iLink API base（可用 config.api_base 覆盖）
_DEFAULT_BASE = "https://ilinkai.weixin.qq.com"
_POLL_TIMEOUT = 35


class WeixinHermesConnector(ChannelConnector):
    meta = ChannelMeta(
        cid="wechat", label="微信(iLink)", icon="💚", mode="polling",
        desc="Hermes 官方 iLink 微信 Bot（长轮询接收 + 媒体 AES 解密，进程内直连）",
        needs_bridge=False,
        fields=[
            {"key": "api_base", "label": "API Base URL", "secret": False,
             "placeholder": _DEFAULT_BASE},
            {"key": "account_id", "label": "Account ID", "secret": False,
             "placeholder": "iLink Bot 身份，形如 xxx@im.bot"},
            {"key": "token", "label": "Token", "secret": True,
             "placeholder": "iLink Bot token（扫码后自动生成）"},
            {"key": "media_secret", "label": "媒体 AES 密钥（可选）", "secret": True,
             "placeholder": "16 字节 base64/hex；留空则跳过媒体解密"},
            {"key": "qr_login_url", "label": "扫码登录页 URL（可选，展示用）",
             "secret": False, "placeholder": "终端二维码对应的登录页（可选）"},
        ],
    )

    def __init__(self) -> None:
        super().__init__()
        self._base: str = _DEFAULT_BASE
        self._account_id: str = ""
        self._token: str = ""
        self._media_secret: bytes | None = None
        self._qr_url: str = ""
        self._ctx_tokens: dict[str, str] = {}   # peer -> context_token（发送需回显）
        self._buf: Any = None                     # 长轮询同步游标
        self._lock = threading.Lock()

    # —— 配置 ──
    def configure(self, config: dict) -> None:
        super().configure(config)
        self._base = (self._cfg.get("api_base") or _DEFAULT_BASE).rstrip("/")
        self._account_id = (self._cfg.get("account_id") or "").strip()
        self._token = (self._cfg.get("token") or "").strip()
        self._qr_url = (self._cfg.get("qr_login_url") or "").strip()
        ms = (self._cfg.get("media_secret") or "").strip()
        self._media_secret = self._parse_key(ms) if ms else None
        # 若前端只给了 account_id，自动从扫码登录保存的凭证文件中补 token/base_url
        if self._account_id and not self._token:
            persisted = load_weixin_account(self._account_id)
            if persisted:
                self._token = str(persisted.get("token") or "").strip()
                self._base = str(persisted.get("base_url") or self._base).strip().rstrip("/")
                if not self._qr_url:
                    self._qr_url = str(persisted.get("qr_login_url") or "").strip()

    @staticmethod
    def _parse_key(s: str) -> bytes | None:
        try:
            raw = base64.b64decode(s, validate=True)
            if len(raw) == 16:
                return raw
        except Exception:  # noqa: BLE001
            pass
        try:  # hex
            raw = bytes.fromhex(s)
            if len(raw) == 16:
                return raw
        except Exception:  # noqa: BLE001
            pass
        return None

    # —— 生命周期 ──
    def connect(self) -> dict:
        if not self._account_id or not self._token:
            return {"ok": False, "error": "缺少 account_id / token（请点击「扫码登录」一键授权）"}
        self._connected = True
        return {"ok": True, "inbound": "long-poll",
                "qr_login_url": self._qr_url or None}

    def disconnect(self) -> None:
        self._connected = False

    def health(self) -> dict:
        return {"ok": True, "connected": self._connected,
                "media_decrypt": self._media_secret is not None,
                "base": self._base}

    # —— 出站 ──
    def send(self, recipient: str, text: str) -> OutboundResult:
        if not self._connected:
            return OutboundResult(ok=False, error="未连接")
        ctx = self._ctx_tokens.get(recipient)
        last_err = None
        last_id = None
        for part in self._split_long(text, 4000):
            try:
                resp = http_post_json(f"{self._base}/send", {
                    "account_id": self._account_id,
                    "token": self._token,
                    "to": recipient,
                    "text": part,
                    **({"context_token": ctx} if ctx else {}),
                }, timeout=20)
                if resp.get("errcode", 0) not in (0, None):
                    last_err = str(resp.get("errmsg") or resp.get("errcode"))[:200]
                    if resp.get("errcode") == -14:
                        raise ChannelError("iLink 会话过期(errcode=-14)，需重跑 hermes gateway setup 扫码")
                    continue
                last_id = resp.get("msg_id") or resp.get("id") or last_id
                last_err = None
            except ChannelError as e:
                return OutboundResult(ok=False, error=str(e)[:200])
            except Exception as e:  # noqa: BLE001
                last_err = str(e)[:200]
        return OutboundResult(ok=last_err is None, error=last_err, message_id=last_id)

    # —— 入站（长轮询，供桥 supervisor 调用）──
    def poll_once(self) -> list[InboundMessage]:
        if not self._connected:
            return []
        try:
            resp = http_post_json(f"{self._base}/getupdates", {
                "account_id": self._account_id,
                "token": self._token,
                "timeout": _POLL_TIMEOUT,
                **({"buf": self._buf} if self._buf is not None else {}),
            }, timeout=_POLL_TIMEOUT + 10)
        except ChannelError as e:
            # 瞬错直接返回空，桥已记录；会话过期则上抛以提示
            if "errcode=-14" in str(e) or "-14" in str(e):
                raise
            return []
        return self._parse_updates(resp)

    def _parse_updates(self, resp: dict) -> list[InboundMessage]:
        # 响应形态未完全公开：兼容 {"messages":[...]} 与直接 [...] 两种
        msgs = resp.get("messages")
        if msgs is None and isinstance(resp, list):
            msgs = resp
        if not isinstance(msgs, list):
            return []
        self._buf = resp.get("buf", self._buf)
        out: list[InboundMessage] = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            mid = str(m.get("message_id") or m.get("id") or "")
            peer = str(m.get("from", {}).get("peer") if isinstance(m.get("from"), dict)
                       else m.get("peer") or m.get("from_user") or "")
            text = m.get("text") or ""
            ctx = m.get("context_token")
            if ctx and peer:
                self._ctx_tokens[peer] = ctx
            if not text and not m.get("media"):
                continue
            out.append(InboundMessage(
                channel="wechat",
                sender_id=peer or mid,
                sender_name=m.get("from", {}).get("name") if isinstance(m.get("from"), dict) else peer,
                conversation_key=peer or mid,
                text=str(text),
                message_id=mid,
                raw=m,
            ))
        return out

    # —— 媒体解密（可选，懒导入 cryptography）──
    def decrypt_media(self, ciphertext: bytes) -> bytes | None:
        """用配置密钥对 iLink 加密媒体做 AES-128-ECB(PKCS#7) 解密。"""
        if not self._media_secret or not ciphertext:
            return None
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.primitives.padding import PKCS7
            cipher = Cipher(algorithms.AES(self._media_secret), modes.ECB())
            dec = cipher.decryptor()
            plain = dec.update(ciphertext) + dec.finalize()
            return PKCS7(128).unpadder().update(plain) + PKCS7(128).unpadder().finalize()
        except Exception:  # noqa: BLE001
            return None
