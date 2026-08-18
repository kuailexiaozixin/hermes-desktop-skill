"""routes/_helpers.py — 路由层共享小工具（与业务 / 具体路由解耦）

把原 `routes/__init__.py` 中的通用辅助函数集中到这里，让 `__init__.py` 只负责
app 创建与路由注册（server.py），路由子模块按需 `from ._helpers import ...`，
不再经由命名空间总线（`from routes import _ok, ...`）间接依赖。
"""
from __future__ import annotations

import json as _json
import os as _cron_os
import threading as _cron_th
from typing import Any

# ---------------------------------------------------------------------------
# 定时任务执行历史（内存 + JSON 文件持久化）
# ---------------------------------------------------------------------------
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
    from datetime import datetime as _dt
    with _cron_history_lock:
        records = _load_cron_history()
        records.append({
            "job_id": job_id,
            "job_name": job_name,
            "time": _dt.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
            "result": result,
            "error": error,
        })
        # 最多保留 200 条
        if len(records) > 200:
            records = records[-200:]
        _save_cron_history(records)


# ---------------------------------------------------------------------------
# 响应小工具
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


# ---------------------------------------------------------------------------
# Markdown 渲染（A1 安全加固：白名单净化，防 self-XSS）
# ---------------------------------------------------------------------------
_MD_EXT = ["fenced_code", "tables", "sane_lists", "nl2br"]

# A1：只允许 Markdown 产生的结构标签，禁用任意原始 HTML 注入。
# 保留 code/div/span/pre 的 class（供代码高亮、Mermaid 识别）；链接仅放行安全协议。
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
