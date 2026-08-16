"""main.py — Hermes Desktop 底座的 FastHTML 路由层（通用，与任何业务解耦）

定位
====
本文件**只做 HTTP 路由与页面外壳**，一行业务逻辑都不写：

    浏览器/pywebview  ──HTTP/SSE──►  main.py（本文件）
                                        │
                          ┌─────────────┼──────────────┬───────────────┐
                          ▼             ▼              ▼               ▼
                   agent_runtime   hermes_config   frameworks       sessions
                   （集成内核）     （配置/技能/    （循环/委派/     （多会话
                                     MCP/Cron）     原生指令）       持久化）

集成内核在 `agent_runtime.py`，配置面在 `hermes_config.py`，框架面在 `frameworks/`，
会话持久化在 `sessions.py`。前端资源在 `static/app.css` + `static/app.js`。

三个实测得来的关键约束（改这个文件前务必先看）
==============================================
1. **静态资源必须走 `static_path`，不能自己写 `/assets/app.css` 路由。**
   FastHTML 的内置静态路由是 `/{fname:path}.{ext:static}`，它在 `fast_app()` 里
   **先于**用户路由注册，会抢先拦截所有 `.css` / `.js` 请求。实测：自定义
   `@app.get("/assets/app.css")` 永远拿不到请求，返回 404。正确做法是把
   `static_path` 指到资源目录，然后按 `/app.css` `/app.js` 引用。
2. **`rt` 是函数，没有 `.get/.post`。** 用 `@app.get(...)` / `@app.post(...)`。
3. **路由参数必须带类型注解**，否则 FastHTML 会忽略该参数并告警。

SSE 契约（与 agent_runtime.stream_agent_chat 一致）
==================================================
    {"choices":[{"delta":{"content": "..."}}]}     文本增量（OpenAI chunk 形状）
    {"type":"reasoning","text":str}                 思考过程
    {"type":"action","tool":str,"preview":str}      工具开始
    {"type":"action_result","tool":...,"result":{}} 工具结束
    {"type":"done","final":str,"messages":[...]}    收尾（本文件在此落盘会话）
    {"error":{"message":str}}                       异常

运行
====
    pip install -r requirements.txt
    python main.py            # 纯服务模式，浏览器打开 http://127.0.0.1:5001
    python launcher.py        # 桌面窗口模式（pywebview）
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import threading
from pathlib import Path
from typing import Any, Iterator

# 冻结态（PyInstaller）：HERMES_HOME 必须在任何 hermes 导入前指向可写路径
if getattr(sys, "frozen", False):
    os.environ.setdefault(
        "HERMES_HOME",
        os.path.join(os.path.dirname(sys.executable), "hermes_data"),
    )

from fasthtml.common import (  # noqa: E402
    Body, Button, Div, Head, Html, Input, Label, Link, Meta, Option, Script, Select, Span, Title, fast_app,
)
from starlette.responses import (  # noqa: E402
    FileResponse, JSONResponse, StreamingResponse,
)

import asyncio  # noqa: E402

import agent_runtime as ar  # noqa: E402
import frameworks as fw  # noqa: E402
import hermes_config as hc  # noqa: E402
import host_tools  # noqa: E402
import wiki_engine as we  # noqa: E402  # LLM Wiki 引擎（进程内三层互联知识库）
import cron_scheduler as cron_sched  # noqa: E402  # 定时任务后台调度执行器
import json as _json, os as _cron_os, threading as _cron_th

# 定时任务执行历史记录（内存 + JSON 文件持久化）
_CRON_HISTORY_FILE = _cron_os.path.join(_cron_os.path.dirname(_cron_os.path.abspath(__file__)), ".cron_history.json")
_cron_history_lock = _cron_th.Lock()

def _load_cron_history():
    """从文件加载执行历史。"""
    if _cron_os.path.exists(_CRON_HISTORY_FILE):
        try:
            with open(_CRON_HISTORY_FILE, "r", encoding="utf-8") as _f:
                return _json.load(_f)
        except Exception:
            pass
    return []

def _save_cron_history(records):
    """保存执行历史到文件。"""
    try:
        with open(_CRON_HISTORY_FILE, "w", encoding="utf-8") as _f:
            _json.dump(records, _f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _add_cron_record(job_id, job_name, status, result="", error=""):
    """添加一条执行记录。"""
    with _cron_history_lock:
        records = _load_cron_history()
        records.append({
            "job_id": job_id,
            "job_name": job_name,
            "time": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "result": result,
            "error": error,
        })
        # 最多保留 200 条
        if len(records) > 200:
            records = records[-200:]
        _save_cron_history(records)
from channels import ChannelBridge  # noqa: E402  # 进程内 IM 桥（替换外部 gateway 进程）
from channels.weixin_qr_login import start_qr_login, get_qr_status, cancel_qr_login  # noqa: E402
bridge = ChannelBridge()  # 单例：连接管理 + 入站→进程内 Agent→出站
import atexit  # noqa: E402
atexit.register(bridge.shutdown)
import mcpstore_client as mstore  # noqa: E402  # MCP 商店（LobeHub 社区生态，完全在线）
import sessions  # noqa: E402
import skillhub_client as shub  # noqa: E402  # 技能商店（SkillHub 社区，完全在线）
import hermes_skills_client as hskills  # noqa: E402  # Hermes 官方 skills-index / Skills Hub
import unified_skills_client as unified  # noqa: E402  # 统一技能市场（SkillHub + Hermes 各源，来源标注）
import hermes_features as hf  # noqa: E402  # 补充功能模块（Goals/MOA/Checkpoints 等 13 项）

APP_TITLE = "Hermes Desktop"


# ---------------------------------------------------------------------------
# 静态资源目录（开发态 = ./static；冻结态 = _MEIPASS/static）
# ---------------------------------------------------------------------------
def _static_dir() -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        p = Path(base) / "static"
        if p.is_dir():
            return str(p)
    return str(Path(__file__).resolve().parent.parent / "static")


STATIC_DIR = _static_dir()

app, rt = fast_app(
    pico=False, htmx=False, live=False,          # 全手写前端，不引入 pico/htmx
    title=APP_TITLE,
    static_path=STATIC_DIR,                       # 见文件头约束 1
    default_hdrs=False,                           # 页面结构完全自定义
)

# ── 开发态：前端源码模块禁用浏览器缓存 ─────────────────────────────────────
# FastHTML 静态服务不设 Cache-Control，浏览器会对 /src/*.js 做启发式缓存，
# 导致升级后仍加载旧版 ES module（界面不更新）。这里对前端脚本/样式加
# no-cache：浏览器每次向服务端重新验证，etag 变化即重新下载。
from starlette.middleware.base import BaseHTTPMiddleware as _BHMW

class _NoCacheStatic(_BHMW):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/src/") or path.endswith((".js", ".mjs", ".css")):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response

app.add_middleware(_NoCacheStatic)


# ---------------------------------------------------------------------------
# 通用小工具
# ---------------------------------------------------------------------------
def _ok(**kw) -> dict:
    return {"ok": True, **kw}


def _err(msg: str, **kw) -> dict:
    return {"ok": False, "error": str(msg), **kw}


def _guard(fn, *a, **kw) -> dict:
    """把任意后端调用包成 {ok:...}，异常不 500、原因回显到前端。"""
    try:
        r = fn(*a, **kw)
    except Exception as e:  # noqa: BLE001
        return _err(f"{type(e).__name__}: {e}")
    if isinstance(r, dict) and "ok" in r:
        return r
    return _ok(data=r)


_MD_EXT = ["fenced_code", "tables", "sane_lists", "nl2br"]

# A1：Markdown 渲染白名单——只允许 Markdown 产生的结构标签，禁用任意原始 HTML 注入。
# 关键：保留 code/div/span/pre 的 class（供代码高亮、Mermaid 识别）；链接仅放行安全协议。
_SAFE_TAGS = frozenset({
    "p", "br", "div", "span", "code", "pre", "blockquote", "strong", "em",
    "b", "i", "u", "s", "a", "img", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td",
    "sub", "sup", "del", "ins",
})
_SAFE_ATTRS = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title", "width", "height"],
    "code": ["class"], "span": ["class"], "div": ["class"], "pre": ["class"],
    "th": ["class"], "td": ["class"],
    "h1": ["class"], "h2": ["class"], "h3": ["class"],
    "h4": ["class"], "h5": ["class"], "h6": ["class"],
}
_SAFE_PROTOCOLS = ["http", "https", "mailto"]


def render_markdown(text: str) -> str:
    """把助手文本渲染成 HTML。markdown 缺失时降级为转义纯文本（不崩）。

    A1 安全加固：python-markdown 默认**放行原始 HTML**，若不净化，代理被诱导或
    web/file 工具回传的 ``<script>`` / ``<img onerror>`` 等会被当作活 HTML 注入
    DOM（self-XSS）。这里渲染后用 bleach 按白名单净化，仅保留 Markdown 结构与
    必要的 class（代码高亮 / Mermaid 识别依赖这些 class）。
    """
    try:
        import markdown
        html = markdown.markdown(text or "", extensions=_MD_EXT,
                                 output_format="html")
    except Exception:
        import html as _h
        return "<pre>%s</pre>" % _h.escape(text or "")
    try:
        import bleach
        html = bleach.clean(
            html, tags=_SAFE_TAGS, attributes=_SAFE_ATTRS,
            protocols=_SAFE_PROTOCOLS, strip=True,
        )
    except Exception:
        # bleach 缺失时退化为「最坏情况仍安全」：整体转义，宁可丢失富格式也不注入
        import html as _h
        html = _h.escape(html)
    return html


def _msg_text(content: Any) -> str:
    """把 OpenAI 消息 content（str 或多模态 list）压成可显示文本。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content
                       if isinstance(p, dict) and p.get("type") == "text")
    return "" if content is None else str(content)



# ── 前端 JS 错误捕获（调试用）────────────────────────────────
_JS_ERRORS = []

@app.post('/api/js-errors')
def _recv_js_error(req: dict):
    _JS_ERRORS.append(req)
    return {'ok': True}

@app.get('/api/js-errors')
def _get_js_errors():
    return {'errors': _JS_ERRORS, 'count': len(_JS_ERRORS)}

# ── 子模块导入（触发路由注册）────────────────────────────────
from . import pages, chat, models, toolsets, skills, mcp, loops, misc, features, mcp_server, logs, structured, tools_catalog

# ── MCP 客户端发现（对标真实 Hermes Desktop 接线）─────────────────
# 真实 Desktop 在 dashboard 进程启动后调用 start_background_mcp_discovery；
# 本示例复用同一思路：把已配置的 MCP 服务器（stdio/SSE/HTTP 三种传输）交给
# tools.mcp_tool.register_mcp_servers 连接，与进程内 AIAgent 共用同一全局
# 工具注册表，从而让默认启用全部工具集的 Agent 能看到 MCP 工具。
try:
    hc.trigger_mcp_discovery()
except Exception:
    pass

def serve_only() -> None:
    """纯服务模式：不开窗口，只起 HTTP（调试 / 冒烟 / 远程访问用）。"""
    import uvicorn
    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"),
                port=int(os.environ.get("PORT", "5001")), log_level="warning")


# 注意：这里**必须**用 `__name__` 守卫而不是 FastHTML 惯用的模块级 `serve()`。
# launcher.py 会 `from main import app` 再自己起 uvicorn；模块级 serve() 一旦被
# 求值就可能在导入期阻塞或触发 reload 子进程，在冻结态尤其危险。
if __name__ == "__main__":
    serve_only()
# ── 热重载（开发调试用：前端代码修改后自动刷新页面）────────────────────
import os as _hr_os, time as _hr_time

_HR_STATIC_DIR = _hr_os.path.join(_hr_os.path.dirname(_hr_os.path.dirname(__file__)), "static")
_HR_SNAPSHOT: dict[str, float] = {}

def _hr_take_snapshot() -> dict[str, float]:
    """扫描 static/ 下所有文件的修改时间。"""
    snap: dict[str, float] = {}
    base = _HR_STATIC_DIR
    if not _hr_os.path.isdir(base):
        return snap
    for root, _dirs, files in _hr_os.walk(base):
        for f in files:
            fp = _hr_os.path.join(root, f)
            try:
                snap[fp] = _hr_os.path.getmtime(fp)
            except OSError:
                pass
    return snap

@app.get('/api/hot-reload')
async def _hot_reload_sse():
    """SSE 端点：前端代码变更时推送 'reload' 事件。
    浏览器连接后每 1s 轮询文件修改时间，检测到变化时推送信号。
    """
    global _HR_SNAPSHOT
    if not _HR_SNAPSHOT:
        _HR_SNAPSHOT = _hr_take_snapshot()

    from starlette.responses import StreamingResponse
    import asyncio

    async def _event_stream():
        global _HR_SNAPSHOT
        # 先发一个 connected 事件确认连接成功
        yield f"event: connected\ndata: {_hr_time.time()}\n\n"
        while True:
            await asyncio.sleep(1.0)
            curr = _hr_take_snapshot()
            if curr != _HR_SNAPSHOT:
                _HR_SNAPSHOT = curr
                yield f"event: reload\ndata: {_hr_time.time()}\n\n"
                # 发完即停，浏览器收到后刷新页面，会重新连接
                return

    return StreamingResponse(_event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "Connection": "keep-alive",
                                      "X-Accel-Buffering": "no"})