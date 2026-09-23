"""channels/slack.py — Slack（入站 Webhook + Events API 签名校验）。

出站：Incoming Webhook URL（直接 POST {"text":...}）。
入站：Events API 回调（平台推送），用 X-Slack-Signature 校验：
    signature = "v0=" + hex( HMAC-SHA256( key=signing_secret, msg="v0:"+timestamp+":"+raw_body ) )。
"""
from __future__ import annotations

from .base import (
    ChannelConnector, ChannelMeta, InboundMessage, OutboundResult,
    hex_hmac_sha256, http_post_json,
)


class SlackConnector(ChannelConnector):
    meta = ChannelMeta(
        cid="slack", label="Slack", icon="💬", mode="webhook",
        desc="Slack（出站 Incoming Webhook + Events API 签名校验）",
        fields=[
            {"key": "incoming_webhook", "label": "Incoming Webhook URL", "secret": True,
             "placeholder": "https://hooks.slack.com/services/…"},
            {"key": "signing_secret", "label": "Signing Secret", "secret": True,
             "placeholder": "Event Subscriptions 的 Signing Secret（入站校验）"},
        ],
    )

    def __init__(self) -> None:
        super().__init__()
        self._url: str = ""
        self._secret: str = ""

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._url = (self._cfg.get("incoming_webhook") or "").strip()
        self._secret = (self._cfg.get("signing_secret") or "").strip()

    def webhook_path(self) -> str:
        return "/wh/slack"

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
        for part in self._split_long(text, 4000):
            try:
                resp = http_post_json(self._url, {"text": part}, timeout=20)
                # Slack 成功返回 "ok"，失败返回 {"ok":false,"error":...}
                if isinstance(resp, dict) and resp.get("ok") is False:
                    last_err = str(resp.get("error"))[:200]
                    continue
                ok_any = True
            except Exception as e:  # noqa: BLE001
                last_err = str(e)[:200]
        return OutboundResult(ok=ok_any, error=last_err)

    def handle_webhook(self, payload: dict, headers: dict,
                       raw_body: bytes | None = None) -> list[InboundMessage]:
        # URL 验证挑战
        if payload.get("type") == "url_verification":
            return []
        if self._secret:
            ts = headers.get("x-slack-request-timestamp", "")
            sig = headers.get("x-slack-signature", "")
            body = raw_body.decode("utf-8", "replace") if raw_body else ""
            expect = "v0=" + hex_hmac_sha256(self._secret, f"v0:{ts}:{body}")
            if not sig or not self._constant_time_eq(sig, expect):
                return []
        event = payload.get("event") or {}
        if event.get("type") != "message" or event.get("subtype"):
            return []  # 跳过 bot_message / 频道变更等
        text = event.get("text") or ""
        if not text:
            return []
        return [InboundMessage(
            channel="slack",
            sender_id=str(event.get("user") or ""),
            sender_name=str(event.get("user") or ""),
            conversation_key=str(event.get("channel") or ""),
            text=text,
            message_id=str(event.get("event_ts") or ""),
            raw=payload,
        )]

    @staticmethod
    def _constant_time_eq(a: str, b: str) -> bool:
        import hmac as _h
        return _h.compare_digest(a, b)
