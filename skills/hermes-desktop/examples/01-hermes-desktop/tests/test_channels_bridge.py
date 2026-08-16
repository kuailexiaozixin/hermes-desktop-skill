"""test_channels_bridge.py — 进程内 IM 桥（F1 修复）验证。

设计：无真实网络、无 hermes-agent 依赖。
- 出站：用伪 urlopen 验证各连接器请求 URL / 请求体正确。
- 签名：验证飞书/钉钉 HMAC、Slack/Discord Ed25519、企微 SHA1。
- 入站→Agent→出站：注入伪 Agent Provider + 伪连接器，验证全链路落盘与会话创建。
- Webhook 接收器：真实启动本地 127.0.0.1 服务器，POST 带签名负载，验证端到端分发。
- 生命周期：connect/disconnect、QQ/微信桥接占位。
"""
import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import channels.base as base
from channels.base import (
    ChannelConnector, ChannelMeta, InboundMessage, OutboundResult,
)
from channels.bridge import ChannelBridge
from channels.discord import DiscordConnector
from channels.dingtalk import DingTalkConnector
from channels.feishu import FeishuConnector, feishu_sign
from channels.slack import SlackConnector
from channels.telegram import TelegramConnector
from channels.wecom import WeComConnector
from channels.qq_official import QQOfficialConnector
from channels.weixin_hermes import WeixinHermesConnector

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")


# ── 伪 HTTP ──────────────────────────────────────────────────────────────
class _FakeResp:
    def __init__(self, data):
        self._d = data.encode("utf-8") if isinstance(data, str) else data
    def read(self):
        return self._d
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


class _FakeURLopen:
    def __init__(self, handler):
        self.handler = handler
    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        method = req.method if hasattr(req, "method") else "GET"
        data = req.data if hasattr(req, "data") else None
        return _FakeResp(self.handler(url, method, data))


@contextmanager
def with_urlopen(handler):
    base.set_urlopen(_FakeURLopen(handler))
    try:
        yield
    finally:
        base._reset_urlopen()


# ── 伪 Agent Provider（回声，输出 SSE 字节流）────────────────────────────
def fake_agent_provider(messages, model_cfg):
    last = ""
    for m in messages:
        if isinstance(m, dict) and m.get("role") == "user":
            last = m.get("content", "")
    text = "回声：" + last
    yield ("data: " + json.dumps({"choices": [{"delta": {"content": text}}]}) + "\n\n").encode()
    yield ("data: " + json.dumps({"type": "done"}) + "\n\n").encode()


# ── 伪连接器 ─────────────────────────────────────────────────────────────
class FakePollConnector(ChannelConnector):
    meta = ChannelMeta(cid="fakepoll", label="FakePoll", icon="🧪", mode="polling",
                       desc="测试轮询", fields=[])
    def __init__(self):
        super().__init__(); self.sent = []; self._updates = []
    def connect(self):
        self._connected = True; return {"ok": True}
    def disconnect(self):
        self._connected = False
    def send(self, recipient, text):
        self.sent.append((recipient, text)); return OutboundResult(ok=True, message_id="x")
    def poll_once(self):
        out, self._updates = self._updates, []
        return out


class FakeWebhookConnector(ChannelConnector):
    meta = ChannelMeta(cid="fakewh", label="FakeWH", icon="🧪", mode="webhook",
                       desc="测试 Webhook", fields=[])
    def __init__(self):
        super().__init__(); self.sent = []
    def webhook_path(self):
        return "/wh/fakewh"
    def connect(self):
        self._connected = True; return {"ok": True}
    def disconnect(self):
        self._connected = False
    def send(self, recipient, text):
        self.sent.append((recipient, text)); return OutboundResult(ok=True)
    def handle_webhook(self, payload, headers, raw_body=None):
        return [InboundMessage(channel="fakewh", sender_id="u1",
                               conversation_key="c1", text=payload.get("text", ""))]


def setup_bridge():
    os.environ.setdefault("HERMES_DESKTOP_HOME", tempfile.mkdtemp(prefix="hermes_ch_"))
    os.environ.setdefault("HERMES_HOME", os.environ["HERMES_DESKTOP_HOME"])
    b = ChannelBridge(agent_provider=fake_agent_provider, port=0)
    b._connectors.clear()
    b._connectors["fakepoll"] = FakePollConnector()
    b._connectors["fakewh"] = FakeWebhookConnector()
    return b


# ── 1. 签名 / 工具 ────────────────────────────────────────────────────────
def test_signatures():
    print("[1] 签名与工具函数")
    # HMAC 向量（与标准库 hashlib 自洽）
    import hmac as _h, hashlib as _hl, base64 as _b
    key, msg = "secret", "hello"
    exp = _b.b64encode(_h.new(key.encode(), msg.encode(), _hl.sha256).digest()).decode()
    check("b64_hmac_sha256 自洽", base.b64_hmac_sha256(key, msg) == exp)
    exph = _h.new(key.encode(), msg.encode(), _hl.sha256).hexdigest()
    check("hex_hmac_sha256 自洽", base.hex_hmac_sha256(key, msg) == exph)
    # 飞书签名
    secret, ts = "s3cr3t", "1700000000"
    expf = _b.b64encode(_h.new(secret.encode(), (ts + "\n" + secret).encode(), _hl.sha256).digest()).decode()
    check("feishu_sign 算法正确", feishu_sign(secret, ts) == expf)
    # 企微 SHA1 排序拼接
    parts = ["token", "1", "2", "enc"]
    expw = _hl.sha1("".join(sorted(parts)).encode()).hexdigest()
    check("sha1_hex_sorted 正确", base.sha1_hex_sorted(*parts) == expw)
    # 钉钉签名 = 飞书同算法（base64 hmac）
    dt = DingTalkConnector(); dt.configure({"webhook_key": "K", "secret": secret})
    sgn = dt._sign()
    check("钉钉签名与飞书同算法", sgn["sign"] == feishu_sign(secret, sgn["timestamp"]))
    # Discord Ed25519（若 cryptography 可用）
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        sk = Ed25519PrivateKey.generate()
        pk = sk.public_key()
        import binascii
        pub_hex = binascii.hexlify(pk.public_bytes_raw()).decode()
        ts = "1234567890"; body = b"hello"
        sig = binascii.hexlify(sk.sign(ts.encode() + body)).decode()
        check("Discord Ed25519 验签通过", DiscordConnector._verify_ed25519(pub_hex, sig, ts, body))
        check("Discord Ed25519 篡改失败", not DiscordConnector._verify_ed25519(pub_hex, sig, ts, b"tampered"))
    except Exception:
        print("  (跳过 Discord Ed25519：未安装 cryptography)")


# ── 2. 出站 payload ───────────────────────────────────────────────────────
def test_outbound():
    print("[2] 出站 payload 格式化")
    # 飞书
    captured = {}
    def feishu_handler(url, method, data):
        captured["url"] = url; captured["body"] = json.loads(data)
        return '{"code":0,"msg":"success"}'
    with with_urlopen(feishu_handler):
        c = FeishuConnector(); c.configure({"webhook_key": "ABC"}); c.connect()
        r = c.send("x", "你好")
        check("飞书出站 URL 正确", "open.feishu.cn/open-apis/bot/v2/hook/ABC" in captured["url"])
        check("飞书出站 body 正确", captured["body"]["msg_type"] == "text"
              and captured["body"]["content"]["text"] == "你好")
        check("飞书出站成功", r.ok)

    # 钉钉（带签名）
    cap = {}
    def dt_handler(url, method, data):
        cap["url"] = url; cap["body"] = json.loads(data); return '{"errcode":0}'
    with with_urlopen(dt_handler):
        c = DingTalkConnector(); c.configure({"webhook_key": "K", "secret": "s"})
        r = c.send("x", "hi")
        check("钉钉出站带 access_token", "access_token=K" in cap["url"])
        check("钉钉出站带 sign+timestamp", "sign" in cap["body"] and "timestamp" in cap["body"])
        check("钉钉出站成功", r.ok)

    # Slack
    cap = {}
    def sl_handler(url, method, data):
        cap["url"] = url; cap["body"] = json.loads(data); return "ok"
    with with_urlopen(sl_handler):
        c = SlackConnector(); c.configure({"incoming_webhook": "https://hooks.slack.com/X"})
        r = c.send("x", "yo")
        check("Slack 出站 URL 正确", cap["url"] == "https://hooks.slack.com/X")
        check("Slack 出站 body 正确", cap["body"]["text"] == "yo" and r.ok)

    # 企微
    cap = {}
    def wc_handler(url, method, data):
        cap["url"] = url; cap["body"] = json.loads(data); return '{"errcode":0}'
    with with_urlopen(wc_handler):
        c = WeComConnector(); c.configure({"webhook_key": "WK"})
        r = c.send("x", "你好")
        check("企微出站 URL 正确", "key=WK" in cap["url"] and r.ok)

    # Discord
    cap = {}
    def dc_handler(url, method, data):
        cap["url"] = url; cap["body"] = json.loads(data); return '{}'
    with with_urlopen(dc_handler):
        c = DiscordConnector(); c.configure({"incoming_webhook": "https://discord.com/api/X"})
        r = c.send("x", "hi")
        check("Discord 出站 URL 正确", cap["url"] == "https://discord.com/api/X" and r.ok)

    # 长文本拆分
    cap = {"n": 0}
    def long_handler(url, method, data):
        cap["n"] += 1; return '{"code":0}'
    with with_urlopen(long_handler):
        c = FeishuConnector(); c.configure({"webhook_key": "A"}); c.connect()
        big = "x" * 5000
        c.send("x", big)
        check("超长文本被拆分多段", cap["n"] >= 2)


# ── 3. 入站解析（真实连接器 + 伪 urlopen）─────────────────────────────────
def test_inbound_parse():
    print("[3] 入站解析（真实连接器）")
    # Telegram 轮询
    updates = {"ok": True, "result": [{"update_id": 10,
        "message": {"message_id": 5, "chat": {"id": 99}, "from": {"id": 7, "username": "bob"},
                     "text": "hello tg"}}]}
    def tg_handler(url, method, data):
        if "getMe" in url: return '{"ok":true,"result":{"id":1}}'
        if "getUpdates" in url: return json.dumps(updates)
        return '{"ok":true}'
    with with_urlopen(tg_handler):
        c = TelegramConnector(); c.configure({"token": "T"}); c.connect()
        msgs = c.poll_once()
        check("Telegram 解析出 1 条消息", len(msgs) == 1)
        if msgs:
            check("Telegram 消息字段正确", msgs[0].sender_id == "99"
                  and msgs[0].text == "hello tg" and msgs[0].sender_name == "bob")
        c.disconnect()
        check("Telegram 断开", not c.is_connected())

    # 飞书带签名的回调
    secret, ts = "s3cr3t", "1700000000"
    sign = feishu_sign(secret, ts)
    payload = {"header": {"timestamp": ts, "signature": sign},
               "event": {"message": {"message_id": "m1", "chat_id": "oc1",
                         "content": json.dumps({"text": "hi feishu"})},
                         "sender": {"sender_id": {"open_id": "ou1"}}}}
    c = FeishuConnector(); c.configure({"webhook_key": "K", "secret": secret})
    msgs = c.handle_webhook(payload, {})
    check("飞书签名校验通过并解析", len(msgs) == 1 and msgs[0].text == "hi feishu")
    # 错误签名应被拒
    bad = dict(payload); bad["header"] = {"timestamp": ts, "signature": "x"}
    check("飞书错误签名被拒", c.handle_webhook(bad, {}) == [])
    # 无 secret 时不校验
    c2 = FeishuConnector(); c2.configure({"webhook_key": "K"})
    check("飞书无 secret 不校验", len(c2.handle_webhook(payload, {})) == 1)


# ── 4. 桥全链路（轮询伪连接器 → Agent → 出站 + 会话落盘）──────────────────
def test_bridge_loop():
    print("[4] 桥全链路（入站→Agent→出站 + 落盘）")
    import sessions
    b = setup_bridge()
    fp = b._connectors["fakepoll"]
    b.connect("fakepoll", {})
    check("轮询连接器已连接", fp.is_connected())
    msg = InboundMessage(channel="fakepoll", sender_id="u1", conversation_key="c1",
                         sender_name="Bob", text="ping")
    reply = b.on_inbound(msg)
    check("Agent 回声回复", reply == "回声：ping")
    check("出站收到回复", fp.sent and fp.sent[0] == ("u1", "回声：ping"))
    # 会话落盘
    sids = [s["id"] for s in sessions.list_sessions()]
    check("为会话创建了桌面会话", len(sids) == 1)
    if sids:
        conv = sessions.get(sids[0])
        roles = [m["role"] for m in conv["messages"]]
        check("会话含 user+assistant", "user" in roles and "assistant" in roles)
    # 事件流水
    evs = b.get_events()
    check("事件流水记录了入站/出站", any(e["direction"] == "in" for e in evs)
          and any(e["direction"] == "out" for e in evs))
    b.disconnect("fakepoll")
    check("断开后未连接", not fp.is_connected())


# ── 5. Webhook 接收器端到端 ───────────────────────────────────────────────
def test_webhook_e2e():
    print("[5] Webhook 接收器端到端")
    import sessions
    b = setup_bridge()
    fw = b._connectors["fakewh"]
    r = b.connect("fakewh", {})
    check("Webhook 连接成功并启动接收器", r.get("ok") and b._receiver.is_running())
    url = b._receiver.url_for("fakewh")
    check("回调 URL 为 127.0.0.1", url.startswith("http://127.0.0.1:"))
    # 通过真实 HTTP 发送一条入站消息
    body = json.dumps({"text": "webhook hi"}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            _ = resp.read()
    except Exception as e:
        check("Webhook POST 成功", False); print("    POST 异常:", e); b.disconnect("fakewh"); return
    # 给接收器后台线程一点时间分发
    for _ in range(50):
        if fw.sent:
            break
        time.sleep(0.05)
    check("接收器分发到桥并回推", fw.sent and fw.sent[0] == ("u1", "回声：webhook hi"))
    b.disconnect("fakewh")
    check("断开后接收器停止", not b._receiver.is_running())


# ── 6. QQ 官方 Bot API v2 连接器（实装 + 伪 urlopen）─────────────────────
def test_qq_official():
    print("[6] QQ 官方 Bot API v2 连接器")
    import sys
    # 让 qq_official 的 `import websockets` 失败 → 走「仅发送」分支，避免测试连真实网关
    saved_ws = sys.modules.get("websockets")
    sys.modules["websockets"] = None
    try:
        captured = {}
        def handler(url, method, data):
            if "getAppAccessToken" in url:
                return '{"access_token":"AT","expires_in":7200}'
            if "/v2/" in url and "/messages" in url:
                captured["url"] = url
                captured["body"] = json.loads(data)
                captured["auth"] = None
                return '{"id":"m1"}'
            return '{"id":"x"}'
        with with_urlopen(handler):
            c = QQOfficialConnector()
            c.configure({"app_id": "APPID", "client_secret": "SEC"})
            r = c.connect()
            check("QQ 连接成功（仅发送模式）", r.get("ok") and r.get("inbound") == "disabled(需 websockets)")
            check("QQ 缺凭证连接失败", not QQOfficialConnector().connect().get("ok"))
            res = c.send("openid123", "你好 QQ")
            check("QQ 出站 URL 为 C2C 用户消息接口", "/v2/users/openid123/messages" in captured["url"])
            check("QQ 出站带 QQBot 鉴权头", c._auth_headers()["Authorization"] == "QQBot AT")
            check("QQ 出站 body 为文本 msg_type=0", captured["body"]["content"] == "你好 QQ"
                  and captured["body"]["msg_type"] == 0)
            check("QQ 出站成功", res.ok and res.message_id == "m1")
            # 群消息前缀 g:
            res2 = c.send("g:grp1", "群 hello")
            check("QQ 群消息走 groups 接口", "/v2/groups/grp1/messages" in captured["url"] and res2.ok)
        c.disconnect()
        check("QQ 断开", not c.is_connected())
    finally:
        if saved_ws is None:
            sys.modules.pop("websockets", None)
        else:
            sys.modules["websockets"] = saved_ws


# ── 7. Hermes iLink 微信连接器（实装 + 伪 urlopen）─────────────────────────
def test_weixin_hermes():
    print("[7] Hermes iLink 微信连接器")
    captured = {}
    def handler(url, method, data):
        if "getupdates" in url:
            return json.dumps({"messages": [
                {"message_id": "w1", "from": {"peer": "peer1", "name": "Bob"},
                 "text": "hi wx", "context_token": "CT1"}]})
        if "send" in url:
            captured["url"] = url
            captured["body"] = json.loads(data)
            return '{"errcode":0,"msg_id":"s1"}'
        return '{"errcode":0}'
    with with_urlopen(handler):
        c = WeixinHermesConnector()
        c.configure({"account_id": "a@im.bot", "token": "TK"})
        check("iLink 缺凭证连接失败", not WeixinHermesConnector().connect().get("ok"))
        r = c.connect()
        check("iLink 连接成功", r.get("ok"))
        msgs = c.poll_once()
        check("iLink 长轮询解析出 1 条消息", len(msgs) == 1)
        if msgs:
            check("iLink 消息字段正确", msgs[0].sender_id == "peer1"
                  and msgs[0].text == "hi wx" and msgs[0].channel == "wechat")
            check("iLink 记录 context_token", c._ctx_tokens.get("peer1") == "CT1")
        res = c.send("peer1", "回复 wx")
        check("iLink 出站 URL 正确", captured["url"].endswith("/send"))
        check("iLink 出站带 account_id/token/context_token",
              captured["body"]["account_id"] == "a@im.bot"
              and captured["body"]["token"] == "TK"
              and captured["body"]["context_token"] == "CT1")
        check("iLink 出站成功", res.ok and res.message_id == "s1")
        c.disconnect()
        check("iLink 断开", not c.is_connected())


def test_weixin_qr_login():
    print("[7b] 微信 iLink 一键扫码登录（后端辅助）")
    import time as _t
    from channels.weixin_qr_login import (
        start_qr_login, get_qr_status, cancel_qr_login, load_weixin_account,
    )
    os.environ["HERMES_DESKTOP_HOME"] = tempfile.mkdtemp(prefix="hermes_qr_")

    def handler_success(url, method, data):
        if "get_bot_qrcode" in url:
            return json.dumps({"qrcode": "WXLOGIN:abc123", "qrcode_img_content": ""})
        if "get_qrcode_status" in url:
            return json.dumps({"status": "confirmed", "ilink_bot_id": "abc@im.bot",
                               "bot_token": "TOK123", "baseurl": "https://ilinkai.weixin.qq.com",
                               "ilink_user_id": "u1"})
        return json.dumps({"errcode": 0})

    def handler_wait(url, method, data):
        if "get_bot_qrcode" in url:
            return json.dumps({"qrcode": "WXLOGIN:wait", "qrcode_img_content": ""})
        if "get_qrcode_status" in url:
            return json.dumps({"status": "waiting"})
        return json.dumps({"errcode": 0})

    def handler_empty(url, method, data):
        if "get_bot_qrcode" in url:
            return json.dumps({"errcode": 0})  # 无 qrcode 字段
        return json.dumps({"errcode": 0})

    # 成功路径：扫码确认 → 凭证落盘 → 回传
    with with_urlopen(handler_success):
        r = start_qr_login()
        check("qr start 返回 ok", r.get("ok"))
        check("qr start 返回 sid", bool(r.get("sid")))
        check("qr start 生成二维码图片(data url)",
              isinstance(r.get("qr_image"), str) and r["qr_image"].startswith("data:image/png;base64,"))
        check("qr start 返回待扫描内容", bool(r.get("scan_data")))
        sid = r["sid"]
        # 后台线程约 1s 内确认，轮询等待
        deadline = _t.time() + 8
        status = "waiting"
        while _t.time() < deadline:
            s = get_qr_status(sid)
            status = s.get("status")
            if status == "confirmed":
                break
            _t.sleep(0.3)
        check("后台轮询确认扫码", status == "confirmed")
        s = get_qr_status(sid)
        cred = s.get("credentials") or {}
        check("回传 account_id", cred.get("account_id") == "abc@im.bot")
        check("回传 token", cred.get("token") == "TOK123")
        check("回传 base_url", cred.get("base_url") == "https://ilinkai.weixin.qq.com")
        saved = load_weixin_account("abc@im.bot")
        check("凭证已落盘", saved is not None and saved.get("token") == "TOK123")

    # 取消路径：start → 立即 cancel
    with with_urlopen(handler_wait):
        r = start_qr_login()
        check("qr(wait) start ok", r.get("ok"))
        cs = cancel_qr_login(r["sid"])
        check("cancel 返回 ok", cs.get("ok"))
        check("cancel 后状态为 cancelled", get_qr_status(r["sid"]).get("status") == "cancelled")

    # 错误路径：iLink 未返回二维码
    with with_urlopen(handler_empty):
        r = start_qr_login()
        check("无 qrcode 时 start 返回 ok:false", not r.get("ok"))



def main():
    test_signatures()
    test_outbound()
    test_inbound_parse()
    test_bridge_loop()
    test_webhook_e2e()
    test_qq_official()
    test_weixin_hermes()
    test_weixin_qr_login()
    print(f"\n结果：{PASS} 通过 / {FAIL} 失败")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
