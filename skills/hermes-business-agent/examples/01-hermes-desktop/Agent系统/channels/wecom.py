"""channels/wecom.py — 企业微信（群机器人 / 自建应用回调）。

出站：群机器人 Webhook https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=KEY 。
入站：自建应用回调，用 msg_signature = SHA1( 排序拼接(token, timestamp, nonce, encrypt) ) 校验真实性
      （消息体 AES 解密需 cryptography 库，可选；本模块校验签名以确认请求来源）。
"""
from __future__ import annotations

from .base import (
    ChannelConnector, ChannelMeta, InboundMessage, OutboundResult,
    http_post_json, sha1_hex_sorted,
)

_SEND = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"


class WeComConnector(ChannelConnector):
    meta = ChannelMeta(
        cid="qywx", label="企业微信", icon="🏢", mode="webhook",
        desc="企业微信（群机器人出站 + 回调签名校验）",
        fields=[
            {"key": "webhook_key", "label": "Webhook Key", "secret": True,
             "placeholder": "cgi-bin/webhook/send?key= 后的 KEY"},
            {"key": "callback_token", "label": "回调 Token", "secret": True,
             "placeholder": "自建应用回调配置的 Token（入站校验，可选）"},
        ],
    )

    def __init__(self) -> None:
        super().__init__()
        self._key: str = ""
        self._token: str = ""

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._key = (self._cfg.get("webhook_key") or "").strip()
        self._token = (self._cfg.get("callback_token") or "").strip()

    def webhook_path(self) -> str:
        return "/wh/qywx"

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
                    _SEND.format(key=self._key),
                    {"msgtype": "text", "text": {"content": part}}, timeout=20)
                if resp.get("errcode") not in (0, None):
                    last_err = str(resp.get("errmsg") or resp.get("errcode"))[:200]
                    continue
                ok_any = True
            except Exception as e:  # noqa: BLE001
                last_err = str(e)[:200]
        return OutboundResult(ok=ok_any, error=last_err)

    def handle_webhook(self, payload: dict, headers: dict,
                       raw_body: bytes | None = None) -> list[InboundMessage]:
        if self._token:
            # 企业微信回调：msg_signature / timestamp / nonce / encrypt(=payload 文本)
            sig = payload.get("msg_signature", "")
            ts = str(payload.get("timestamp", ""))
            nonce = str(payload.get("nonce", ""))
            enc = payload.get("encrypt", "")
            expect = sha1_hex_sorted(self._token, ts, nonce, enc)
            if not sig or not self._constant_time_eq(sig, expect):
                return []
        # 解密后的明文通常是 JSON {"MsgType":"text","Content":...,"FromUserName":...}
        content = payload.get("Content") or payload.get("content") or ""
        if isinstance(content, dict):
            content = content.get("Content", "")
        if not content:
            return []
        return [InboundMessage(
            channel="qywx",
            sender_id=str(payload.get("FromUserName") or ""),
            sender_name=str(payload.get("FromUserName") or ""),
            conversation_key=str(payload.get("FromUserName") or ""),
            text=str(content),
            message_id=str(payload.get("MsgId") or ""),
            raw=payload,
        )]

    @staticmethod
    def _constant_time_eq(a: str, b: str) -> bool:
        import hmac as _h
        return _h.compare_digest(a, b)
