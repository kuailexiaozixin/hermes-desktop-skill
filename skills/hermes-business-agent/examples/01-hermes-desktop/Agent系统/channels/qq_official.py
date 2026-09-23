"""channels/qq_official.py — QQ 官方机器人 Bot API v2（进程内直连，无外部 SDK）。

设计：
- 出站（发送）：纯标准库 HTTPS 调用 OpenAPI v2（getAppAccessToken + v2/users|groups 消息接口）。
  鉴权：``Authorization: QQBot <access_token>`` + ``X-Impl-Version: v2``。
- 入站（接收）：官方 WebSocket Gateway（wss）。``websockets`` 为**可选懒导入**依赖——
  仅入站需要，且默认已在冻结 venv 内（15.0.1）；若缺失，连接器仍可「仅发送」（诚实降级，
  不崩溃、不伪装成功）。入站消息经后台线程推入线程安全队列，由桥的 supervisor 通过
  ``poll_once()`` 排出，复用进程内 Agent 全链路。
- 严格遵循 ``ChannelConnector`` 契约；模块顶层**不**硬导入任何第三方库，确保在冻结 venv
  缺包时仍能干净 import。

参考（接入票据 / OpenAPI v2 / WebSocket 网关）：
  https://q.qq.com  ·  https://bot.qq.com/wiki/develop/api-v2/
注意：官方已弃用旧 ``Token`` 鉴权，统一用 ``Access Token``（getAppAccessToken 获取）。
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any

from .base import (
    ChannelConnector, ChannelError, ChannelMeta, InboundMessage,
    OutboundResult, http_post_json,
)

# ── 端点（OpenAPI v2 官方）───────────────────────────────────────────────
_TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
_API_BASE = "https://api.sgroup.qq.com"
_WS_URL = "wss://api.sgroup.qq.com/websocket/"

# WebSocket OP 码（官方 v2 网关协议）
_OP_HELLO = 0
_OP_IDENTIFY = 1
_OP_RESUME = 2
_OP_HEARTBEAT = 3
_OP_HEARTBEAT_ACK = 4
_OP_DISPATCH = 6
_OP_RECONNECT = 7
_OP_INVALID_SESSION = 9

# 事件订阅 intents（位掩码）。默认值覆盖「群@消息 + 频道私信」；
# 单聊(C2C) intent 请按官方「事件订阅」文档在 UI 的 intents 字段覆盖。
#   GROUP_AT_MESSAGE_CREATE = 1 << 25
#   DIRECT_MESSAGE          = 1 << 12
_DEFAULT_INTENTS = (1 << 25) | (1 << 12)


class QQOfficialConnector(ChannelConnector):
    meta = ChannelMeta(
        cid="qq", label="QQ（官方）", icon="🐧", mode="polling",
        desc="QQ 官方机器人 Bot API v2（OpenAPI 发送 + WebSocket 接收，进程内直连）",
        needs_bridge=False,
        fields=[
            {"key": "app_id", "label": "AppID", "secret": False,
             "placeholder": "QQ 开放平台机器人的 AppID"},
            {"key": "client_secret", "label": "AppSecret", "secret": True,
             "placeholder": "QQ 开放平台机器人的 AppSecret"},
            {"key": "allowed_users", "label": "允许的用户 openid（逗号分隔，留空=全部）",
             "secret": False, "placeholder": "可选，例如 openid1,openid2"},
            {"key": "allowed_groups", "label": "允许的群 openid（逗号分隔，留空=全部）",
             "secret": False, "placeholder": "可选，例如 group_openid1"},
            {"key": "intents", "label": "事件订阅 intents（位掩码，高级）",
             "secret": False, "placeholder": str(_DEFAULT_INTENTS)},
        ],
    )

    def __init__(self) -> None:
        super().__init__()
        self._app_id: str = ""
        self._secret: str = ""
        self._access_token: str = ""
        self._token_expire: float = 0.0
        self._allow_users: set[str] = set()
        self._allow_groups: set[str] = set()
        self._intents: int = _DEFAULT_INTENTS
        self._queue: list[InboundMessage] = []
        self._queue_lock = threading.Lock()
        self._ws_thread: threading.Thread | None = None
        self._ws_stop: threading.Event | None = None
        self._ws_session: str | None = None
        self._ws_seq: int | None = None
        self._ws_available: bool = True

    # —— 配置 ──
    def configure(self, config: dict) -> None:
        super().configure(config)
        self._app_id = (self._cfg.get("app_id") or "").strip()
        self._secret = (self._cfg.get("client_secret") or "").strip()
        au = (self._cfg.get("allowed_users") or "").strip()
        ag = (self._cfg.get("allowed_groups") or "").strip()
        self._allow_users = {x.strip() for x in au.split(",") if x.strip()} if au else set()
        self._allow_groups = {x.strip() for x in ag.split(",") if x.strip()} if ag else set()
        try:
            self._intents = int(str(self._cfg.get("intents") or "").strip() or _DEFAULT_INTENTS)
        except ValueError:
            self._intents = _DEFAULT_INTENTS

    # —— 鉴权 ──
    def _ensure_token(self) -> str:
        if self._access_token and time.time() < self._token_expire - 60:
            return self._access_token
        resp = http_post_json(_TOKEN_URL, {
            "appId": self._app_id, "clientSecret": self._secret})
        tok = resp.get("access_token")
        if not tok:
            raise ChannelError("获取 QQ access_token 失败：" +
                               str(resp.get("error", resp))[:200])
        self._access_token = tok
        self._token_expire = time.time() + float(resp.get("expires_in", 7200))
        return tok

    def _auth_headers(self) -> dict:
        return {"Authorization": "QQBot " + self._ensure_token(),
                "X-Impl-Version": "v2"}

    # —— 生命周期 ──
    def connect(self) -> dict:
        if not self._app_id or not self._secret:
            return {"ok": False, "error": "缺少 AppID / AppSecret"}
        # 探活：先取 token（失败即暴露配置错误）
        try:
            self._ensure_token()
        except ChannelError as e:
            return {"ok": False, "error": str(e)[:200]}
        self._connected = True
        # 入站：尝试启动 WebSocket 后台线程（缺失 websockets 时仅发送）
        try:
            import websockets  # noqa: F401  仅探活导入
        except Exception:
            self._ws_available = False
        if self._ws_available:
            self._ws_stop = threading.Event()
            self._ws_thread = threading.Thread(
                target=self._ws_runner, name="qq-ws", daemon=True)
            self._ws_thread.start()
        return {"ok": True,
                "inbound": "websocket" if self._ws_available else "disabled(需 websockets)"}

    def disconnect(self) -> None:
        self._connected = False
        if self._ws_stop is not None:
            self._ws_stop.set()
        if self._ws_thread is not None:
            self._ws_thread.join(timeout=3)
            self._ws_thread = None
        self._ws_stop = None

    def health(self) -> dict:
        return {"ok": True, "connected": self._connected,
                "inbound": "websocket" if self._ws_available else "send-only",
                "token_valid": bool(self._access_token)}

    # —— 出站 ──
    def send(self, recipient: str, text: str) -> OutboundResult:
        if not self._connected:
            return OutboundResult(ok=False, error="未连接")
        # recipient 约定：g:<group_openid> 群消息；c:<channel_id> 频道消息；其余按 C2C 用户 openid
        kind = "user"
        target = recipient
        if recipient.startswith("g:"):
            kind, target = "group", recipient[2:]
        elif recipient.startswith("c:"):
            kind, target = "channel", recipient[2:]
        if kind == "group":
            url = f"{_API_BASE}/v2/groups/{target}/messages"
        elif kind == "channel":
            url = f"{_API_BASE}/v2/channels/{target}/messages"
        else:
            url = f"{_API_BASE}/v2/users/{target}/messages"
        last_err = None
        last_id = None
        for part in self._split_long(text, 4000):
            try:
                resp = http_post_json(url, {"content": part, "msg_type": 0},
                                      headers=self._auth_headers(), timeout=20)
                if resp.get("code", 0) not in (0, None) and "id" not in resp:
                    last_err = str(resp.get("message") or resp.get("code"))[:200]
                    self._refresh_token_on_401(resp)
                    continue
                last_id = resp.get("id") or last_id
                last_err = None
            except ChannelError as e:
                last_err = str(e)[:200]
                self._refresh_token_on_401(str(e))
        return OutboundResult(ok=last_err is None, error=last_err, message_id=last_id)

    def _refresh_token_on_401(self, resp: Any) -> None:
        # 令牌失效则作废，下次发送重新获取
        txt = resp if isinstance(resp, str) else json.dumps(resp)
        if "401" in txt or "token" in txt.lower() and "invalid" in txt.lower():
            self._access_token = ""

    # —— 入站（队列排出，供桥 supervisor 调用）──
    def poll_once(self) -> list[InboundMessage]:
        with self._queue_lock:
            out, self._queue = self._queue, []
        return out

    # —— WebSocket 网关（后台线程）──
    def _ws_runner(self) -> None:
        try:
            asyncio.run(self._ws_loop())
        except Exception:  # noqa: BLE001  线程级兜底，避免静默退出
            pass

    async def _ws_loop(self) -> None:
        import websockets  # 懒导入：仅入站需要
        stop = self._ws_stop
        while self._connected and (stop is None or not stop.is_set()):
            try:
                async with websockets.connect(
                        _WS_URL,
                        additional_headers=[
                            ("Authorization", "QQBot " + self._ensure_token()),
                            ("X-Impl-Version", "v2"),
                        ]) as ws:
                    hello = json.loads(await ws.recv())
                    interval = (hello.get("d", {}) or {}).get("heartbeat_interval", 30000)
                    # 鉴权 / 重连
                    if self._ws_session:
                        await ws.send(json.dumps({"op": _OP_RESUME, "d": {
                            "token": "QQBot " + self._access_token,
                            "session_id": self._ws_session, "seq": self._ws_seq}}))
                    else:
                        await ws.send(json.dumps({"op": _OP_IDENTIFY, "d": {
                            "token": "QQBot " + self._access_token,
                            "intents": self._intents, "shard": [0, 0]}}))
                    # 心跳任务
                    hb = asyncio.ensure_future(self._ws_heartbeat(ws, interval / 1000.0, stop))
                    async for raw in ws:
                        if stop and stop.is_set():
                            break
                        try:
                            msg = json.loads(raw)
                        except Exception:  # noqa: BLE001
                            continue
                        op = msg.get("op")
                        if op == _OP_DISPATCH:
                            self._ws_seq = msg.get("s")
                            self._ws_session = (msg.get("d", {}) or {}).get("session_id",
                                                                           self._ws_session)
                            self._on_dispatch(msg.get("t"), msg.get("d", {}) or {})
                        elif op == _OP_RECONNECT:
                            break  # 退出内层，外层重连
                        elif op == _OP_INVALID_SESSION:
                            self._ws_session = None
                            break
                    hb.cancel()
            except Exception:  # noqa: BLE001
                if stop and stop.is_set():
                    break
                await asyncio.sleep(3)  # 断线退避后重连

    async def _ws_heartbeat(self, ws, interval: float, stop) -> None:
        try:
            while self._connected and (stop is None or not stop.is_set()):
                await asyncio.sleep(interval)
                await ws.send(json.dumps(
                    {"op": _OP_HEARTBEAT, "d": self._ws_seq}))
        except Exception:  # noqa: BLE001
            pass

    def _on_dispatch(self, event: str | None, d: dict) -> None:
        if not event or not isinstance(d, dict):
            return
        text = (d.get("content") or d.get("message") or "").strip()
        if not text:
            return
        # 群@ / 频道@ / 单聊 统一抽取
        author = d.get("author", {}) or {}
        uid = str(author.get("user_openid") or author.get("id")
                  or d.get("user_openid") or d.get("author_id") or "")
        group = d.get("group_openid") or d.get("guild_id") or ""
        channel = d.get("channel_id") or ""
        if self._allow_users and uid and uid not in self._allow_users:
            return
        if self._allow_groups and group and group not in self._allow_groups:
            return
        # recipient 约定回写：群用 g: 前缀，频道用 c: 前缀，单聊用 openid
        if group:
            recipient = "g:" + group
        elif channel:
            recipient = "c:" + channel
        else:
            recipient = uid
        with self._queue_lock:
            self._queue.append(InboundMessage(
                channel="qq",
                sender_id=uid or recipient,
                sender_name=author.get("username") or uid or recipient,
                conversation_key=recipient,
                text=text,
                message_id=str(d.get("id") or d.get("msg_id") or ""),
                raw={"event": event, "d": d},
            ))
