"""channels/webhook_server.py — 进程内本地推送接收器（仅 127.0.0.1）。

飞书 / 企业微信 / 钉钉 / Slack / Discord 等平台通过「事件回调」把入站消息推送到一个 URL。
本接收器在桌面进程内、绑定 localhost 启动一个极简 HTTP 服务器，按路径把事件转交对应连接器
的 ``handle_webhook()``，并把解析出的消息回送给 bridge。

安全边界：
- 仅绑定 127.0.0.1（TCP 层即拒绝非本机连接）；对外可达性由用户自行用隧道/反代负责（与任何自托管 bot 相同）。
- 各平台自身的签名校验在连接器内完成（飞书/钉钉 HMAC、Slack/Discord Ed25519、企微 SHA1）。
- 这不是 agent 的执行通道——agent 仍在进程内直跑，这里只是「接收 IM 推送」的本地集成端点。
"""
from __future__ import annotations

import http.server
import json
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # 避免循环导入，仅作类型提示
    from .base import ChannelConnector
    from .bridge import ChannelBridge


class _WebhookHTTPServer(http.server.ThreadingHTTPServer):
    """实际 HTTP 服务器类（持有路由表与 bridge 引用）。"""

    def __init__(self, addr, handler, bridge: "ChannelBridge | None", port: int) -> None:
        super().__init__(addr, handler)
        self.bridge = bridge
        self.port = port
        self._routes: dict[str, "ChannelConnector"] = {}
        self._lock = threading.Lock()

    def lookup(self, path: str) -> "ChannelConnector | None":
        return self._routes.get(path)

    def register(self, conn: "ChannelConnector") -> None:
        p = conn.webhook_path()
        if p:
            with self._lock:
                self._routes[p.rstrip("/")] = conn

    def unregister(self, conn: "ChannelConnector") -> None:
        p = conn.webhook_path()
        if p:
            with self._lock:
                self._routes.pop(p.rstrip("/"), None)

    def clear_routes(self) -> None:
        with self._lock:
            self._routes.clear()


class _Handler(http.server.BaseHTTPRequestHandler):
    server: "_WebhookHTTPServer"  # type: ignore[assignment]

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(raw.decode("utf-8", "replace")) if raw else {}
        except Exception:  # noqa: BLE001
            payload = {}
        # URL 验证挑战（飞书 / Slack 首次订阅）
        if payload.get("type") == "url_verification" and "challenge" in payload:
            self._reply(200, {"challenge": payload["challenge"]})
            return
        path = self.path.split("?")[0].rstrip("/")
        conn = self.server.lookup(path)
        if conn is None:
            self._reply(404, {"ok": False, "error": "unknown webhook path"})
            return
        try:
            msgs = conn.handle_webhook(payload, dict(self.headers), raw)
        except Exception as e:  # noqa: BLE001
            self._reply(200, {"ok": False, "error": str(e)[:200]})
            return
        if msgs and self.server.bridge is not None:
            self.server.bridge.on_webhook_messages(conn.meta.cid, msgs)
        self._reply(200, {"ok": True})

    def _reply(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # 静默访问日志
        return


class WebhookReceiver:
    """接收器的门面：持有 _WebhookHTTPServer 实例，提供 start/stop/register 等。"""

    def __init__(self, bridge: "ChannelBridge | None" = None, port: int = 18765) -> None:
        self.bridge = bridge
        self.port = port
        self._httpd: "_WebhookHTTPServer | None" = None
        self._thread: threading.Thread | None = None

    def lookup(self, path: str) -> "ChannelConnector | None":
        return self._httpd.lookup(path) if self._httpd else None

    def register(self, conn: "ChannelConnector") -> None:
        if self._httpd is not None:
            self._httpd.register(conn)

    def unregister(self, conn: "ChannelConnector") -> None:
        if self._httpd is not None:
            self._httpd.unregister(conn)

    def url_for(self, cid: str) -> str:
        return f"http://127.0.0.1:{self.port}/wh/{cid}"

    def start(self) -> dict:
        if self._httpd is not None:
            return {"ok": True, "already": True, "port": self.port}
        try:
            self._httpd = _WebhookHTTPServer(
                ("127.0.0.1", self.port), _Handler, self.bridge, self.port)
        except OSError as e:
            return {"ok": False, "error": f"端口 {self.port} 占用：{e}"}
        if self.port == 0:
            self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, name="wh-receiver", daemon=True)
        self._thread.start()
        return {"ok": True, "port": self.port}

    def stop(self) -> None:
        if self._httpd is not None:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:  # noqa: BLE001
                pass
        self._httpd = None
        self._thread = None

    def is_running(self) -> bool:
        return self._httpd is not None
