"""channels/bridge.py — 进程内 IM 桥核心。

职责：
1. 持有各渠道连接器（默认注册表）。
2. 把「入站消息」转交**进程内** AIAgent 生成回复，再经连接器回推平台——全链路不出桌面进程。
3. 维护每渠道连接状态、轮询监督线程、Webhook 接收器、事件流水（供前端实时展示）。

agent 执行方式：默认走 ``agent_runtime.stream_agent_chat``（即 run_agent.AIAgent 进程内直跑）；
测试可注入 ``agent_provider``（伪 Agent）以离线验证，无需 hermes-agent 依赖。
"""
from __future__ import annotations

import json
import threading
import time
from typing import Callable, Iterator

from .base import ChannelConnector, InboundMessage, OutboundResult
from .registry import build_default_registry
from .webhook_server import WebhookReceiver


def _default_agent_provider(messages: list, model_cfg: dict) -> Iterator[bytes]:
    """默认：调用进程内 Hermes AIAgent（run_agent）生成回复。"""
    import agent_runtime as ar
    import hermes_config as hc
    import threading as _th
    return ar.stream_agent_chat(
        messages, model_cfg,
        max_iterations=hc.get_loop_max_iterations(),
        web_search=True,
        cancel_event=_th.Event(),
    )


class ChannelBridge:
    def __init__(self, agent_provider: Callable | None = None,
                 port: int = 18765) -> None:
        self._connectors: dict[str, ChannelConnector] = build_default_registry()
        self.agent_provider = agent_provider or _default_agent_provider
        self._receiver = WebhookReceiver(bridge=self, port=port)
        self._lock = threading.Lock()
        self._sup_stop: dict[str, threading.Event] = {}
        self._sup_threads: dict[str, threading.Thread] = {}
        self._conv_sessions: dict[str, str] = {}   # "channel:key" -> session id
        self._events: list[dict] = []
        self._events_lock = threading.Lock()
        self._max_events = 300

    # ── 注册 / 查询 ──
    def register_connector(self, conn: ChannelConnector) -> None:
        self._connectors[conn.meta.cid] = conn

    def get_connector(self, cid: str) -> ChannelConnector | None:
        return self._connectors.get(cid)

    # ── 连接管理 ──
    def connect(self, cid: str, config: dict) -> dict:
        conn = self._connectors.get(cid)
        if conn is None:
            return {"ok": False, "error": "未知渠道"}
        conn.configure(config)
        r = conn.connect()
        if not r.get("ok"):
            return r
        if conn.meta.mode == "webhook":
            st = self._receiver.start()
            if not st.get("ok"):
                conn.disconnect()
                return {"ok": False, "error": "Webhook 接收器启动失败：" + st.get("error", "")}
            self._receiver.register(conn)
            wh_url = self._receiver.url_for(cid)
        else:
            wh_url = None
            if conn.meta.mode == "polling":
                self._start_supervisor(conn)
        self._log_event(cid, "system", f"已连接（{conn.meta.mode}）")
        return {"ok": True, "mode": conn.meta.mode, "webhook_url": wh_url,
                "needs_bridge": conn.meta.needs_bridge}

    def disconnect(self, cid: str) -> dict:
        conn = self._connectors.get(cid)
        if conn is None:
            return {"ok": True}
        if conn.meta.mode == "polling":
            self._stop_supervisor(cid)
        if conn.meta.mode == "webhook":
            self._receiver.unregister(conn)
        conn.disconnect()
        # 没有任何 webhook 渠道连接时，关闭接收器
        if not any(c.is_connected() and c.meta.mode == "webhook"
                   for c in self._connectors.values()):
            self._receiver.stop()
        self._log_event(cid, "system", "已断开")
        return {"ok": True}

    def status(self) -> dict:
        out = []
        for cid, conn in self._connectors.items():
            out.append({
                "cid": cid, "label": conn.meta.label, "icon": conn.meta.icon,
                "mode": conn.meta.mode, "connected": conn.is_connected(),
                "needs_bridge": conn.meta.needs_bridge,
                "desc": conn.meta.desc,
                "fields": conn.meta.fields,
                "webhook_url": (self._receiver.url_for(cid)
                                if conn.meta.mode == "webhook" and conn.is_connected()
                                else None),
            })
        return {"ok": True, "connectors": out,
                "receiver_running": self._receiver.is_running(),
                "receiver_port": self._receiver.port}

    def test_send(self, cid: str, text: str, recipient: str = "test") -> dict:
        conn = self._connectors.get(cid)
        if conn is None:
            return {"ok": False, "error": "未知渠道"}
        if not conn.is_connected():
            return {"ok": False, "error": "渠道未连接"}
        res = conn.send(recipient, text)
        self._log_event(cid, "out", f"[测试] {text}", recipient, ok=res.ok)
        return {"ok": res.ok, "error": res.error}

    # ── 入站处理 ──
    def on_webhook_messages(self, cid: str, msgs: list[InboundMessage]) -> None:
        for m in msgs:
            try:
                self.on_inbound(m)
            except Exception as e:  # noqa: BLE001
                self._log_event(cid, "error", str(e)[:200])

    def on_inbound(self, msg: InboundMessage) -> str:
        """入站消息 → 进程内 agent → 回推平台，并落盘到对应会话。"""
        import hermes_config as hc
        import sessions
        key = f"{msg.channel}:{msg.conversation_key or msg.sender_id}"
        with self._lock:
            sid = self._conv_sessions.get(key)
            if sid is None:
                conn0 = self._connectors.get(msg.channel)
                label = conn0.meta.label if conn0 else msg.channel
                title = f"📡 {label} · {msg.sender_name or msg.sender_id}"
                sid = sessions.create(title)["id"]
                self._conv_sessions[key] = sid
        sessions.append(sid, "user", msg.text)
        messages = sessions.get_messages(sid)
        try:
            model_cfg = hc.get_active_model_cfg(None)
        except Exception:  # noqa: BLE001
            model_cfg = {"model": "default", "vendor": "default"}
        gen = self.agent_provider(messages, model_cfg)
        reply, error = self._collect_reply(gen)
        if error:
            reply = (reply or "") + f"\n（执行出错：{error}）"
        if not reply:
            reply = "（未生成回复）"
        sessions.append(sid, "assistant", reply)
        conn = self._connectors.get(msg.channel)
        res = conn.send(msg.sender_id, reply) if conn else OutboundResult(ok=False, error="no connector")
        self._log_event(msg.channel, "in", msg.text, msg.sender_name or msg.sender_id)
        self._log_event(msg.channel, "out", reply, msg.sender_id, ok=res.ok)
        return reply

    # ── 工具 ──
    @staticmethod
    def _collect_reply(gen: Iterator[bytes]) -> tuple[str, str | None]:
        """解析 SSE 字节流，拼接助手文本并捕获错误事件。"""
        parts: list[str] = []
        error: str | None = None
        for chunk in gen:
            if isinstance(chunk, (bytes, bytearray)):
                s = bytes(chunk).decode("utf-8", "replace")
            else:
                s = str(chunk)
            s = s.strip()
            if s.startswith("data:"):
                s = s[5:].strip()
            if not s:
                continue
            try:
                d = json.loads(s)
            except Exception:  # noqa: BLE001
                continue
            if "choices" in d:
                c = (d["choices"][0].get("delta") or {}).get("content", "")
                if c:
                    parts.append(c)
            elif d.get("type") == "error":
                error = ((d.get("error") or {}).get("message")
                         or d.get("message") or "agent error")
        return "".join(parts), error

    def _start_supervisor(self, conn: ChannelConnector) -> None:
        self._stop_supervisor(conn.meta.cid)
        stop = threading.Event()
        self._sup_stop[conn.meta.cid] = stop
        t = threading.Thread(target=self._supervisor_loop, args=(conn, stop),
                             name=f"sup-{conn.meta.cid}", daemon=True)
        t.start()
        self._sup_threads[conn.meta.cid] = t

    def _stop_supervisor(self, cid: str) -> None:
        stop = self._sup_stop.pop(cid, None)
        if stop is not None:
            stop.set()
        self._sup_threads.pop(cid, None)

    def _supervisor_loop(self, conn: ChannelConnector, stop: threading.Event) -> None:
        while conn.is_connected() and not stop.is_set():
            try:
                msgs = conn.poll_once()
            except Exception as e:  # noqa: BLE001
                self._log_event(conn.meta.cid, "error", f"轮询异常：{e}"[:200])
                if stop.wait(3):
                    break
                continue
            for m in msgs:
                try:
                    self.on_inbound(m)
                except Exception as e:  # noqa: BLE001
                    self._log_event(conn.meta.cid, "error", str(e)[:200])
            if stop.wait(1):
                break

    def _log_event(self, cid: str, direction: str, text: str,
                   who: str = "", ok: bool | None = None) -> None:
        ev = {"ts": time.time(), "cid": cid, "direction": direction,
              "text": (text or "")[:400], "who": who, "ok": ok}
        with self._events_lock:
            self._events.append(ev)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

    def get_events(self, limit: int = 50) -> list[dict]:
        with self._events_lock:
            return list(reversed(self._events[-limit:]))

    def shutdown(self) -> None:
        for cid in list(self._connectors.keys()):
            try:
                self.disconnect(cid)
            except Exception:  # noqa: BLE001
                pass
        self._receiver.stop()
