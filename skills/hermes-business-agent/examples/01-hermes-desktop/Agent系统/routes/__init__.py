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



from ._helpers import (  # noqa: E402  # 路由层共享小工具（re-export，兼容旧 from routes import ...）
    _add_cron_record, _err, _guard, _load_cron_history, _msg_text,
    _ok, _save_cron_history, render_markdown,
)

import asyncio  # noqa: E402

import agent_runtime as ar  # noqa: E402
import frameworks as fw  # noqa: E402
import hermes_config as hc  # noqa: E402
import host_tools  # noqa: E402
import wiki_engine as we  # noqa: E402  # LLM Wiki 引擎（进程内三层互联知识库）
import cron_scheduler as cron_sched  # noqa: E402  # 定时任务后台调度执行器
from channels.weixin_qr_login import start_qr_login, get_qr_status, cancel_qr_login  # noqa: E402
from app_state import bridge  # noqa: E402  # 全局单例（re-export，兼容旧 from routes import bridge）
import mcpstore_client as mstore  # noqa: E402  # MCP 商店（LobeHub 社区生态，完全在线）
import sessions  # noqa: E402
import skillhub_client as shub  # noqa: E402  # 技能商店（SkillHub 社区，完全在线）
import hermes_skills_client as hskills  # noqa: E402  # Hermes 官方 skills-index / Skills Hub
import unified_skills_client as unified  # noqa: E402  # 统一技能市场（SkillHub + Hermes 各源，来源标注）
import hermes_features as hf  # noqa: E402  # 补充功能模块（Goals/MOA/Checkpoints 等 13 项）

from server import app, APP_TITLE  # noqa: E402  # app/APP_TITLE 由 server.py 创建（re-export，兼容旧 from routes import app/APP_TITLE；serve_only 由 main.py 直接从 server 导入）

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
