"""channels/feishu.py — 飞书（Lark）机器人。

出站：群机器人 Webhook（https://open.feishu.cn/open-apis/bot/v2/hook/<key>）。
入站：事件订阅回调（平台推送到本地接收器），用飞书签名校验真实性。
签名算法（飞书官方）：sign = base64( HMAC-SHA256( key=secret, msg=timestamp+"\\n"+secret ) )。
"""
from __future__ import annotations

from .base import (
    ChannelConnector, ChannelMeta, InboundMessage, OutboundResult,
    b64_hmac_sha256, http_post_json,
)

_HOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/{key}"


def feishu_sign(secret: str, timestamp: str) -> str:
    return b64_hmac_sha256(secret, timestamp + "\n" + secret)


class FeishuConnector(ChannelConnector):
    meta = ChannelMeta(
        cid="feishu", label="飞书", icon="🪶", mode="webhook",
        desc="飞书机器人（出站 Webhook + 事件回调签名校验）",
        fields=[
            {"key": "webhook_key", "label": "Webhook Key", "secret": True,
             "placeholder": "open-apis/bot/v2/hook/ 后的 KEY"},
            {"key": "secret", "label": "签名密钥 Secret", "secret": True,
             "placeholder": "事件订阅的 Signing Secret（留空则不校验签名）"},
        ],
    )

    def __init__(self) -> None:
        super().__init__()
        self._key: str = ""
        self._secret: str = ""

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._key = (self._cfg.get("webhook_key") or "").strip()
        self._secret = (self._cfg.get("secret") or "").strip()

    def webhook_path(self) -> str:
        return "/wh/feishu"

    def connect(self) -> dict:
        if not self._key:
            return {"ok": False, "error": "缺少 Webhook Key"}
        self._connected = True
        return {"ok": True}

    def disconnect(self) -> None:
        self._connected = False

    def send(self, recipient: str, text: str) -> OutboundResult:
        if not self._key:
            return OutboundResult(ok=False, error="未配置 Webhook Key")
        last_err = None
        ok_any = False
        for part in self._split_long(text, 2000):
            try:
                resp = http_post_json(
                    _HOOK.format(key=self._key),
                    {"msg_type": "text", "content": {"text": part}}, timeout=20)
                if resp.get("code") not in (0, None):
                    last_err = str(resp.get("msg") or resp.get("code"))[:200]
                    continue
                ok_any = True
            except Exception as e:  # noqa: BLE001
                last_err = str(e)[:200]
        return OutboundResult(ok=ok_any, error=last_err)

    def handle_webhook(self, payload: dict, headers: dict,
                       raw_body: bytes | None = None) -> list[InboundMessage]:
        # 1) URL 验证挑战（飞书首次订阅）
        if payload.get("type") == "url_verification":
            return []  # 由 receiver 直接回 challenge，无需构造消息
        # 2) 签名校验
        if self._secret:
            ts = str(payload.get("header", {}).get("timestamp", ""))
            sign = payload.get("header", {}).get("signature", "")
            if not ts or not sign:
                return []
            if not self._constant_time_eq(sign, feishu_sign(self._secret, ts)):
                return []
        # 3) 解析消息事件
        event = payload.get("event") or {}
        msg = event.get("message") or {}
        if msg.get("message_type") != "text" and not msg.get("content"):
            return []
        try:
            content = __import__("json").loads(msg.get("content") or "{}")
        except Exception:  # noqa: BLE001
            content = {}
        text = content.get("text", "")
        if not text:
            return []
        sender = (event.get("sender") or {}).get("sender_id") or {}
        open_id = sender.get("open_id") or ""
        chat_id = msg.get("chat_id") or open_id
        return [InboundMessage(
            channel="feishu",
            sender_id=open_id or chat_id,
            sender_name=open_id or chat_id,
            conversation_key=chat_id,
            text=text,
            message_id=str(msg.get("message_id") or ""),
            raw=payload,
        )]

    @staticmethod
    def _constant_time_eq(a: str, b: str) -> bool:
        import hmac as _h
        return _h.compare_digest(a, b)
