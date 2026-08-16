"""channels/dingtalk.py — 钉钉自定义机器人。

出站：https://oapi.dingtalk.com/robot/send?access_token=KEY ，带 timestamp+sign 签名。
入站：回调事件（平台推送），同样用 timestamp+sign 校验。
签名算法（钉钉官方）：sign = base64( HMAC-SHA256( key=secret, msg=timestamp+secret ) )，timestamp 为毫秒。
"""
from __future__ import annotations

import time

from .base import (
    ChannelConnector, ChannelMeta, InboundMessage, OutboundResult,
    b64_hmac_sha256, http_post_json,
)

_SEND = "https://oapi.dingtalk.com/robot/send?access_token={key}"


class DingTalkConnector(ChannelConnector):
    meta = ChannelMeta(
        cid="dingtalk", label="钉钉", icon="🔔", mode="webhook",
        desc="钉钉自定义机器人（出站 + 回调签名校验）",
        fields=[
            {"key": "webhook_key", "label": "Access Token", "secret": True,
             "placeholder": "robot/send?access_token= 后的 KEY"},
            {"key": "secret", "label": "加签 Secret", "secret": True,
             "placeholder": "安全设置中的加签密钥（留空则不加签）"},
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
        return "/wh/dingtalk"

    def connect(self) -> dict:
        if not self._key:
            return {"ok": False, "error": "缺少 Access Token"}
        self._connected = True
        return {"ok": True}

    def disconnect(self) -> None:
        self._connected = False

    def _sign(self) -> dict:
        if not self._secret:
            return {}
        ts = str(int(time.time() * 1000))
        # 钉钉签名算法：base64( HMAC-SHA256( key=secret, msg=timestamp+"\n"+secret ) )
        return {"timestamp": ts, "sign": b64_hmac_sha256(self._secret, ts + "\n" + self._secret)}

    def send(self, recipient: str, text: str) -> OutboundResult:
        if not self._key:
            return OutboundResult(ok=False, error="未配置 Access Token")
        last_err = None
        ok_any = False
        for part in self._split_long(text, 2000):
            try:
                resp = http_post_json(
                    _SEND.format(key=self._key),
                    {"msgtype": "text", "text": {"content": part}, **self._sign()},
                    timeout=20)
                if resp.get("errcode") not in (0, None):
                    last_err = str(resp.get("errmsg") or resp.get("errcode"))[:200]
                    continue
                ok_any = True
            except Exception as e:  # noqa: BLE001
                last_err = str(e)[:200]
        return OutboundResult(ok=ok_any, error=last_err)

    def handle_webhook(self, payload: dict, headers: dict,
                       raw_body: bytes | None = None) -> list[InboundMessage]:
        # 钉钉入站回调携带 timestamp / sign（与出站同源算法）
        if self._secret:
            ts = str(payload.get("timestamp", ""))
            sign = payload.get("sign", "")
            if not ts or not self._constant_time_eq(sign, b64_hmac_sha256(self._secret, ts + self._secret)):
                return []
        text = (payload.get("text") or {}).get("content") if isinstance(payload.get("text"), dict) else payload.get("text")
        if not text:
            return []
        return [InboundMessage(
            channel="dingtalk",
            sender_id=str(payload.get("senderId") or payload.get("unionId") or ""),
            sender_name=str(payload.get("senderNick") or ""),
            conversation_key=str(payload.get("conversationId") or payload.get("chatbotUserId") or ""),
            text=str(text),
            message_id=str(payload.get("msgId") or ""),
            raw=payload,
        )]

    @staticmethod
    def _constant_time_eq(a: str, b: str) -> bool:
        import hmac as _h
        return _h.compare_digest(a, b)
