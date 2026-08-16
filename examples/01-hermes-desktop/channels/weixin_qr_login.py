"""channels/weixin_qr_login.py — Hermes iLink 微信一键扫码登录（后端辅助）。

设计目标：
- 让 hermes-desktop 的「微信(iLink)」渠道卡片上有一个「扫码登录」按钮，
  点击后前端弹出二维码，用户用微信扫描并确认，即可完成登录，无需手动
  输入 account_id / token。
- 本模块不依赖 hermes-agent 的内部 gateway.platforms.weixin，而是直接复用
  其已公开的 iLink HTTP 端点与字段约定，用 Python 标准库实现，保持零额外
  重依赖。
- qrcode 库为可选依赖：安装时后端生成 base64 PNG/SVG 二维码图片；缺失时
  返回可扫描的 URL/文本，前端仍可引导用户手动扫描或自行渲染。

流程：
  1. start_qr_login() → 请求 iLink /get_bot_qrcode → 得到二维码内容。
  2. 在后台线程中轮询 /get_qrcode_status，直到状态为 confirmed / expired
     （超限） / cancel（用户取消）。
  3. confirmed 时，把 account_id / token / base_url 写入
     <HERMES_HOME>/weixin/accounts/{account_id}.json，与 hermes gateway setup
     的产物路径一致。
  4. 前端通过 /api/channels/wechat/qr/status?sid=... 轮询状态；成功后用返回的
     凭证调用 /api/channels/wechat 保存并连接。
"""
from __future__ import annotations

import base64
import json
import secrets
import struct
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from . import base as _chbase
from hermes_config import get_hermes_home

# iLink 端点常量（与 hermes-agent gateway/platforms/weixin.py 保持一致）
ILINK_BASE_URL = "https://ilinkai.weixin.qq.com"
EP_GET_BOT_QR = "ilink/bot/get_bot_qrcode"
EP_GET_QR_STATUS = "ilink/bot/get_qrcode_status"

QR_TIMEOUT_SECONDS = 480
QR_REFRESH_LIMIT = 3
POLL_INTERVAL_SECONDS = 1

# ── 线程安全会话表 ─────────────────────────────────────────────────────────
_lock = threading.Lock()
_sessions: Dict[str, Dict[str, Any]] = {}
_session_counter = 0


# ── 轻量 HTTP 工具（标准库）──────────────────────────────────────────────────
def _http_get_json(url: str, timeout: float = 35.0) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "iLink-App-Id": "bot",
            "iLink-App-ClientVersion": str((2 << 16) | (2 << 8) | 0),
        },
    )
    try:
        with _chbase._URLOPEN(req, timeout=timeout) as resp:  # type: ignore[call-arg]
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace") if hasattr(e, "read") else ""
        raise RuntimeError(f"iLink HTTP {e.code}: {body[:300]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"iLink 网络错误：{e.reason}") from e
    if not body:
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"raw": body}


def _random_wechat_uin() -> str:
    value = struct.unpack(">I", secrets.token_bytes(4))[0]
    return base64.b64encode(str(value).encode("utf-8")).decode("ascii")


# ── 二维码图片生成（可选）────────────────────────────────────────────────────
def _qr_data_url(data: str) -> Optional[str]:
    """把字符串渲染为 base64 PNG 二维码图片；qrcode 缺失时返回 None。"""
    try:
        import qrcode  # type: ignore[import]
    except Exception:  # noqa: BLE001
        return None
    try:
        img = qrcode.make(data, error_correction=qrcode.constants.ERROR_CORRECT_M)
        from io import BytesIO  # type: ignore[import]

        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as exc:  # noqa: BLE001
        return None


# ── 凭证持久化（与 hermes gateway setup 同路径）──────────────────────────────
def _account_dir() -> Path:
    path = Path(get_hermes_home()) / "weixin" / "accounts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_weixin_account(
    account_id: str,
    token: str,
    base_url: str,
    user_id: str = "",
) -> Path:
    payload = {
        "token": token,
        "base_url": base_url,
        "user_id": user_id,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    path = _account_dir() / f"{account_id}.json"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


# ── 后台轮询 ───────────────────────────────────────────────────────────────
def _poll_loop(
    sid: str,
    qrcode_value: str,
    qrcode_url: str,
    base_url: str,
    deadline: float,
) -> None:
    """在后台线程中轮询 iLink 扫码状态，直到完成/过期/取消。"""
    refresh_count = 0
    current_base_url = base_url

    while time.monotonic() < deadline:
        with _lock:
            sess = _sessions.get(sid)
            if not sess or sess.get("cancelled"):
                return

        try:
            params = {"qrcode": qrcode_value}
            url = f"{current_base_url.rstrip('/')}/{EP_GET_QR_STATUS}?{urllib.parse.urlencode(params)}"
            status_resp = _http_get_json(url, timeout=35.0)
        except Exception as exc:  # noqa: BLE001
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        status = str(status_resp.get("status") or "wait")
        if status == "scaned":
            with _lock:
                if _sessions.get(sid):
                    _sessions[sid]["status"] = "scaned"
                    _sessions[sid]["message"] = "已扫码，请在微信里确认…"
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if status == "scaned_but_redirect":
            redirect_host = str(status_resp.get("redirect_host") or "").strip()
            if redirect_host:
                current_base_url = f"https://{redirect_host}"
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if status == "expired":
            refresh_count += 1
            if refresh_count > QR_REFRESH_LIMIT:
                with _lock:
                    if _sessions.get(sid):
                        _sessions[sid]["status"] = "expired"
                        _sessions[sid]["message"] = "二维码多次过期，请重新扫码登录"
                return
            # 刷新二维码
            try:
                refresh_url = f"{base_url.rstrip('/')}/{EP_GET_BOT_QR}?bot_type=3"
                qr_resp = _http_get_json(refresh_url, timeout=35.0)
                new_value = str(qr_resp.get("qrcode") or "")
                new_url = str(qr_resp.get("qrcode_img_content") or "")
                if new_value:
                    qrcode_value = new_value
                    qrcode_url = new_url
                    scan_data = qrcode_url if qrcode_url else qrcode_value
                    with _lock:
                        if _sessions.get(sid):
                            _sessions[sid]["qrcode_value"] = qrcode_value
                            _sessions[sid]["qrcode_url"] = qrcode_url
                            _sessions[sid]["scan_data"] = scan_data
                            _sessions[sid]["qr_image"] = _qr_data_url(scan_data)
                            _sessions[sid]["message"] = f"二维码已刷新（{refresh_count}/{QR_REFRESH_LIMIT}）"
                else:
                    with _lock:
                        if _sessions.get(sid):
                            _sessions[sid]["status"] = "error"
                            _sessions[sid]["message"] = "刷新二维码失败"
                    return
            except Exception as exc:  # noqa: BLE001
                with _lock:
                    if _sessions.get(sid):
                        _sessions[sid]["status"] = "error"
                        _sessions[sid]["message"] = f"刷新二维码失败：{exc}"
                return
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if status == "confirmed":
            account_id = str(status_resp.get("ilink_bot_id") or "").strip()
            token = str(status_resp.get("bot_token") or "").strip()
            confirmed_base_url = str(status_resp.get("baseurl") or base_url).strip().rstrip("/")
            user_id = str(status_resp.get("ilink_user_id") or "").strip()
            if not account_id or not token:
                with _lock:
                    if _sessions.get(sid):
                        _sessions[sid]["status"] = "error"
                        _sessions[sid]["message"] = "扫码成功但未返回完整凭证"
                return
            try:
                _save_weixin_account(account_id, token, confirmed_base_url, user_id)
            except Exception as exc:  # noqa: BLE001
                with _lock:
                    if _sessions.get(sid):
                        _sessions[sid]["status"] = "error"
                        _sessions[sid]["message"] = f"保存凭证失败：{exc}"
                return
            with _lock:
                if _sessions.get(sid):
                    _sessions[sid]["status"] = "confirmed"
                    _sessions[sid]["message"] = "微信登录成功"
                    _sessions[sid]["credentials"] = {
                        "account_id": account_id,
                        "token": token,
                        "base_url": confirmed_base_url,
                        "user_id": user_id,
                    }
            return

        # 默认继续等待
        time.sleep(POLL_INTERVAL_SECONDS)

    # 超时
    with _lock:
        if _sessions.get(sid):
            _sessions[sid]["status"] = "timeout"
            _sessions[sid]["message"] = "扫码登录超时，请重试"


# ── 公共 API ───────────────────────────────────────────────────────────────
def start_qr_login(timeout_seconds: int = QR_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """开始一次微信 iLink 扫码登录，返回会话 ID、二维码图片/URL、初始状态。"""
    global _session_counter

    base_url = ILINK_BASE_URL
    try:
        url = f"{base_url.rstrip('/')}/{EP_GET_BOT_QR}?bot_type=3"
        qr_resp = _http_get_json(url, timeout=35.0)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"获取二维码失败：{exc}"}

    qrcode_value = str(qr_resp.get("qrcode") or "").strip()
    qrcode_url = str(qr_resp.get("qrcode_img_content") or "").strip()
    if not qrcode_value:
        return {"ok": False, "error": "iLink 未返回二维码，请检查网络或稍后重试"}

    scan_data = qrcode_url if qrcode_url else qrcode_value
    qr_image = _qr_data_url(scan_data)

    with _lock:
        _session_counter += 1
        sid = f"wechatqr-{_session_counter:06d}-{secrets.token_hex(4)}"
        _sessions[sid] = {
            "status": "waiting",
            "message": "请使用微信扫描下方二维码",
            "qrcode_value": qrcode_value,
            "qrcode_url": qrcode_url,
            "scan_data": scan_data,
            "qr_image": qr_image,
            "cancelled": False,
            "credentials": None,
        }

    deadline = time.monotonic() + timeout_seconds
    thread = threading.Thread(
        target=_poll_loop,
        args=(sid, qrcode_value, qrcode_url, base_url, deadline),
        daemon=True,
        name=f"weixin-qr-{sid}",
    )
    thread.start()

    return {
        "ok": True,
        "sid": sid,
        "status": "waiting",
        "message": "请使用微信扫描下方二维码",
        "qr_image": qr_image,
        "qrcode_url": qrcode_url,
        "scan_data": scan_data,
        "expires_in": timeout_seconds,
    }


def get_qr_status(sid: str) -> Dict[str, Any]:
    """查询指定扫码会话的当前状态。"""
    with _lock:
        sess = _sessions.get(sid)
    if not sess:
        return {"ok": False, "error": "扫码会话不存在或已过期"}
    return {
        "ok": True,
        "status": sess["status"],
        "message": sess["message"],
        "qr_image": sess.get("qr_image"),
        "qrcode_url": sess.get("qrcode_url"),
        "scan_data": sess.get("scan_data"),
        "credentials": sess.get("credentials"),
    }


def cancel_qr_login(sid: str) -> Dict[str, Any]:
    """取消指定扫码会话。"""
    with _lock:
        sess = _sessions.get(sid)
        if sess:
            sess["cancelled"] = True
            sess["status"] = "cancelled"
            sess["message"] = "已取消"
    if not sess:
        return {"ok": False, "error": "扫码会话不存在或已过期"}
    return {"ok": True, "status": "cancelled"}


def load_weixin_account(account_id: str) -> Optional[Dict[str, Any]]:
    """从 HERMES_HOME 读取已保存的微信 iLink 凭证。"""
    path = _account_dir() / f"{account_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def list_weixin_accounts() -> Dict[str, Any]:
    """列出 HERMES_HOME 下所有已保存的微信 iLink 凭证摘要。"""
    accounts = {}
    try:
        for p in _account_dir().glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                accounts[p.stem] = {
                    "base_url": data.get("base_url", ILINK_BASE_URL),
                    "user_id": data.get("user_id", ""),
                    "saved_at": data.get("saved_at", ""),
                }
            except Exception:  # noqa: BLE001
                continue
    except OSError:
        pass
    return accounts
