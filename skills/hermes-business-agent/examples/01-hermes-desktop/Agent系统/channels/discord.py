"""channels/discord.py — Discord（出站 Incoming Webhook）。

出站：Incoming Webhook URL 直接 POST {"content":...}。
入站：Discord Interactions 使用 Ed25519 签名（需 cryptography 库）；本模块在缺失该库时
      优雅降级（入站标注为需依赖），出站始终可用。
"""
from __future__ import annotations

from .base import (
    ChannelConnector, ChannelMeta, InboundMessage, OutboundResult,
    http_post_json,
)


class DiscordConnector(ChannelConnector):
    meta = ChannelMeta(
        cid="discord", label="Discord", icon="🎮", mode="webhook",
        desc="Discord（出站 Incoming Webhook；入站 Interactions 需 cryptography）",
        fields=[
            {"key": "incoming_webhook", "label": "Incoming Webhook URL", "secret": True,
             "placeholder": "https://discord.com/api/webhooks/…"},
            {"key": "application_public_key", "label": "Application Public Key", "secret": True,
             "placeholder": "Interactions 验签用（可选，需 cryptography 库）"},
        ],
    )

    def __init__(self) -> None:
        super().__init__()
        self._url: str = ""
        self._pubkey: str = ""

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._url = (self._cfg.get("incoming_webhook") or "").strip()
        self._pubkey = (self._cfg.get("application_public_key") or "").strip()

    def webhook_path(self) -> str:
        return "/wh/discord"

    def connect(self) -> dict:
        if not self._url:
            return {"ok": False, "error": "缺少 Incoming Webhook URL"}
        self._connected = True
        return {"ok": True}

    def disconnect(self) -> None:
        self._connected = False

    def send(self, recipient: str, text: str) -> OutboundResult:
        if not self._url:
            return OutboundResult(ok=False, error="未配置 Webhook")
        last_err = None
        ok_any = False
        for part in self._split_long(text, 2000):
            try:
                resp = http_post_json(self._url, {"content": part}, timeout=20)
                if isinstance(resp, dict) and resp.get("code"):
                    last_err = str(resp.get("message") or resp.get("code"))[:200]
                    continue
                ok_any = True
            except Exception as e:  # noqa: BLE001
                last_err = str(e)[:200]
        return OutboundResult(ok=ok_any, error=last_err)

    def handle_webhook(self, payload: dict, headers: dict,
                       raw_body: bytes | None = None) -> list[InboundMessage]:
        # Discord Interactions 验签（Ed25519）；无 cryptography 或缺少公钥时降级跳过（不接收）
        if self._pubkey and raw_body is not None:
            if not self._verify_ed25519(
                    self._pubkey,
                    headers.get("x-signature-ed25519", ""),
                    headers.get("x-signature-timestamp", ""),
                    raw_body):
                return []
        t = payload.get("type")
        if t == 1:  # PING
            return []
        data = payload.get("data") or {}
        text = (data.get("name") and f"/{data.get('name')}") or ""
        # 交互式指令入站（非聊天转发）；此处仅提取可见文本，便于审计/展示
        if not text:
            return []
        return [InboundMessage(
            channel="discord",
            sender_id=str(payload.get("member", {}).get("user", {}).get("id")
                          or payload.get("user", {}).get("id") or ""),
            sender_name=str(payload.get("member", {}).get("user", {}).get("username")
                            or payload.get("user", {}).get("username") or ""),
            conversation_key=str(payload.get("channel_id") or ""),
            text=text,
            message_id=str(payload.get("id") or ""),
            raw=payload,
        )]

    @staticmethod
    def _verify_ed25519(pubkey_hex: str, sig_hex: str, ts: str,
                        raw_body: bytes) -> bool:
        """Ed25519 验签（Discord Interactions）；公钥为 64 字符 hex = 32 字节。"""
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        except Exception:  # noqa: BLE001
            return False
        try:
            pk = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pubkey_hex))
            pk.verify(bytes.fromhex(sig_hex), ts.encode("utf-8") + raw_body)
            return True
        except Exception:  # noqa: BLE001
            return False
