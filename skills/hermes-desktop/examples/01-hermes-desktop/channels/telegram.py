"""channels/telegram.py — Telegram Bot（进程内纯轮询）。

不依赖任何第三方库：用标准库 urllib 调用 Bot API 的 getUpdates（长轮询）与 sendMessage。
无需入站 HTTP 服务器，最适合作为「进程内桥」的旗舰示例。
"""
from __future__ import annotations

from .base import (
    ChannelConnector, ChannelError, ChannelMeta, InboundMessage,
    OutboundResult, http_get_json, http_post_json,
)

_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramConnector(ChannelConnector):
    meta = ChannelMeta(
        cid="telegram", label="Telegram", icon="✈", mode="polling",
        desc="Telegram Bot（进程内纯轮询，无需公网服务器）",
        fields=[
            {"key": "token", "label": "Bot Token", "secret": True,
             "placeholder": "123456:ABC-DEF…（@BotFather 获取）"},
            {"key": "allowlist", "label": "允许的用户 ID（逗号分隔，留空=全部）",
             "secret": False, "placeholder": "可选，例如 12345,67890"},
        ],
    )

    def __init__(self) -> None:
        super().__init__()
        self._token: str = ""
        self._offset: int = 0
        self._allow: set[str] = set()

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._token = (self._cfg.get("token") or "").strip()
        allow = (self._cfg.get("allowlist") or "").strip()
        self._allow = {a.strip() for a in allow.split(",") if a.strip()} if allow else set()

    def connect(self) -> dict:
        if not self._token:
            return {"ok": False, "error": "缺少 Bot Token"}
        # 先探活，确认 token 有效（getMe）
        try:
            me = http_get_json(_API.format(token=self._token, method="getMe"))
            if not me.get("ok"):
                return {"ok": False, "error": "Token 无效：" + str(me.get("description", ""))[:160]}
        except ChannelError as e:
            return {"ok": False, "error": str(e)[:200]}
        # 轮询由 bridge 的 supervisor 线程统一驱动（避免重复消费 offset）
        self._connected = True
        self._offset = 0
        return {"ok": True}

    def disconnect(self) -> None:
        self._connected = False

    def poll_once(self) -> list[InboundMessage]:
        if not self._connected:
            return []
        try:
            resp = http_get_json(
                _API.format(token=self._token, method="getUpdates"),
                params={"offset": self._offset, "timeout": 5, "limit": 100})
        except ChannelError:
            return []
        if not resp.get("ok"):
            return []
        out: list[InboundMessage] = []
        for upd in resp.get("result", []):
            self._offset = upd.get("update_id", self._offset) + 1
            msg = upd.get("message") or upd.get("edited_message") or {}
            chat = msg.get("chat") or {}
            user = msg.get("from") or {}
            text = msg.get("text") or msg.get("caption") or ""
            uid = str(user.get("id") or chat.get("id") or "")
            if not text or not uid:
                continue
            if self._allow and uid not in self._allow:
                continue
            out.append(InboundMessage(
                channel="telegram",
                sender_id=str(chat.get("id")),
                sender_name=user.get("username") or user.get("first_name") or uid,
                conversation_key=str(chat.get("id")),
                text=text,
                message_id=str(msg.get("message_id")),
                raw=upd,
            ))
        return out

    def send(self, recipient: str, text: str) -> OutboundResult:
        if not self._token:
            return OutboundResult(ok=False, error="未连接")
        last_err = None
        ok_any = False
        last_id = None
        for part in self._split_long(text, 4000):
            try:
                resp = http_post_json(
                    _API.format(token=self._token, method="sendMessage"),
                    {"chat_id": recipient, "text": part, "parse_mode": "Markdown"},
                    timeout=20)
                if not resp.get("ok"):
                    last_err = str(resp.get("description", ""))[:200]
                    continue
                ok_any = True
                last_id = str(resp.get("result", {}).get("message_id"))
            except ChannelError as e:
                last_err = str(e)[:200]
        return OutboundResult(ok=ok_any, error=last_err, message_id=last_id)
