import asyncio
import os
import sys

from routes import Path, _err, _guard, _ok, app, hc, mstore
# 设置中心 · MCP
# ---------------------------------------------------------------------------
@app.get("/api/mcp")
def api_mcp():
    """已安装的 MCP 服务器。

    形状契约（前端 `for...of` 迭代，必须是 list 而非 dict）：
        items: [{name, definition:{command,args,env}, enabled}]
    hc.list_mcp_servers() 返回的是 {name: {...}} 字典，这里显式摊平成列表；
    历史上直接回传字典曾导致前端 `for (const s of items)` 抛
    TypeError（面板白屏），故由 smoke_test_web 的契约断言长期看守。
    """
    def _payload() -> dict:
        items = []
        for name, d in (hc.list_mcp_servers() or {}).items():
            d = dict(d or {})
            # 透传完整定义（command/args/env 或 url/headers 等）；items 仍为 list
            items.append({
                "name": name,
                "definition": d,
                "enabled": bool(d.get("enabled", True)),
            })
        items.sort(key=lambda x: x["name"].lower())
        return {"ok": True, "items": items}
    return _guard(_payload)

@app.post("/api/mcp")
async def api_mcp_save(req):
    body = await req.json()
    name = body.get("name") or ""
    if not name:
        return _err("服务器名不能为空")
    res = _guard(hc.upsert_mcp_server, name, body.get("definition") or {})
    try:
        hc.trigger_mcp_discovery()
    except Exception:
        pass
    return res

@app.post("/api/mcp/{name}/enabled")
async def api_mcp_enabled(name: str, req):
    body = await req.json()
    res = _guard(hc.set_mcp_enabled, name, bool(body.get("enabled")))
    try:
        hc.trigger_mcp_discovery()
    except Exception:
        pass
    return res

@app.delete("/api/mcp/{name}")
def api_mcp_del(name: str):
    return _guard(hc.remove_mcp_server, name)


# ---------------------------------------------------------------------------
# MCP 市场（LobeHub 社区生态，完全在线：浏览/搜索/安装/卸载）
# 前端组件：static/mcpstore.js（initMcpStore），API 对标 业务示例
# ---------------------------------------------------------------------------

@app.post("/api/open-in-explorer")
async def open_in_explorer(req):
    """在系统文件管理器中打开指定目录（pywebview 桌面 API 的 HTTP 替代）。"""
    try:
        body = await req.json()
    except Exception:
        return _err("请求体解析失败")
    d = (body.get("dir") or "").strip()
    if not d:
        return _err("缺少目录路径")
    p = Path(d).expanduser()
    if not p.exists():
        return _err(f"路径不存在：{d}")
    try:
        if sys.platform == "win32":
            os.startfile(str(p))
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(p)])
        return _ok(dir=str(p))
    except Exception as e:
        return _err(f"打开失败：{e}")

@app.get("/api/mcp-store/servers")
async def mcp_store_servers(req):
    """浏览 MCP 目录（LobeHub 精选 + 在线增补），支持搜索/分类/排序/分页。"""
    qp = req.query_params
    q = (qp.get("q") or "").strip()
    category = (qp.get("category") or "").strip()
    try:
        page = int(qp.get("page") or 1)
    except (TypeError, ValueError):
        page = 1
    try:
        pageSize = int(qp.get("pageSize") or 24)
    except (TypeError, ValueError):
        pageSize = 24
    sort = (qp.get("sort") or "installCount").strip()
    lobehub = (qp.get("lobehub") or "1") != "0"
    try:
        res = await asyncio.to_thread(
            mstore.search_mcp, q=q, category=category, page=page,
            pageSize=pageSize, sort=sort, include_lobehub=lobehub)
        return _ok(**res)
    except Exception as e:
        return _err(str(e), items=[])

@app.get("/api/mcp-store/categories")
def mcp_store_categories():
    """MCP 分类列表（含中文标签）。"""
    try:
        return _ok(**mstore.get_categories())
    except Exception as e:
        return _err(str(e), categories=[])

@app.get("/api/mcp-store/meta/{slug}")
async def mcp_store_meta(slug: str):
    """按 slug 取 LobeHub 详情：真实启动配置(command/args/env) + 分类 + 发布者。

    用于「一键安装」与「配置安装」弹窗动态补全。best-effort：字段缺失即留空。
    """
    try:
        meta = await asyncio.to_thread(mstore.get_lobehub_meta, slug)
        return _ok(**meta)
    except Exception as e:
        return _err(str(e))

@app.get("/api/mcp-store/installed")
def mcp_store_installed():
    """已安装（config.yaml.mcp_servers）的 MCP 服务器列表。"""
    def _p() -> dict:
        items = []
        for name, d in (hc.list_mcp_servers() or {}).items():
            d = dict(d or {})
            items.append({
                "name": name, "command": d.get("command", ""),
                "args": list(d.get("args") or []),
                "env": dict(d.get("env") or {}),
                "url": d.get("url", ""),
                "headers": dict(d.get("headers") or {}),
                "enabled": bool(d.get("enabled", True)), "builtin": False,
            })
        items.sort(key=lambda x: x["name"].lower())
        return {"ok": True, "items": items}
    return _guard(_p)

@app.post("/api/mcp-store/install")
async def mcp_store_install(req):
    """安装 MCP：写入 config.yaml.mcp_servers。
    载荷：{"slug"}（取 LobeHub 精选定义安装，含 env Key 收集）或
          {"name","command","args","env"}（stdio 手动安装）或
          {"name","url","headers","env"}（HTTP/SSE 远程安装）。"""
    body = await req.json()
    slug = (body.get("slug") or "").strip()
    env_in = body.get("env") or {}
    if slug:
        d = mstore.get_mcp_def(slug)
        if not d:
            # 非精选 MCP：尝试从 LobeHub 详情页动态取启动配置（一键安装全站 MCP）
            try:
                meta = mstore.get_lobehub_meta(slug)
            except Exception:
                meta = None
            if meta and meta.get("command"):
                d = {
                    "command": meta.get("command"),
                    "args": list(meta.get("args") or []),
                    "env": dict(meta.get("env") or {}),
                    "runtime": meta.get("runtime", ""),
                    "homepage": meta.get("homepage", ""),
                }
        if not d:
            return _err(f"未能从 LobeHub 获取 {slug} 的启动配置，请用「手动添加」")
        name = (body.get("name") or slug).strip()
        definition = {
            "command": d.get("command"),
            "args": list(d.get("args") or []),
            "env": {**(d.get("env") or {}),
                    **{k: v for k, v in env_in.items() if str(v).strip()}},
        }
        if d.get("url"):
            definition["url"] = d["url"]
        if d.get("headers"):
            definition["headers"] = d["headers"]
        if not definition.get("command"):
            definition.pop("command", None)
        missing = [k for k, v in (definition["env"] or {}).items()
                   if not str(v).strip()]
        if missing:
            return _err("缺少必填环境变量: " + ", ".join(missing),
                        envRequired=missing)
    else:
        name = (body.get("name") or "").strip()
        if not name:
            return _err("服务器名必填")
        url = (body.get("url") or "").strip()
        headers_in = body.get("headers") or {}
        definition = {
            "command": (body.get("command") or "").strip(),
            "args": list(body.get("args") or []),
            "env": {k: v for k, v in env_in.items() if str(v).strip()},
        }
        if url:
            definition["url"] = url
            if isinstance(headers_in, dict):
                hd = {str(k): str(v) for k, v in headers_in.items() if str(v).strip()}
                if hd:
                    definition["headers"] = hd
        if not definition["command"] and not definition.get("url"):
            return _err("启动命令与 URL 至少填一项")
        if not definition["command"]:
            definition.pop("command")  # 纯远程服务器无需 command 字段
    try:
        entry = hc.upsert_mcp_server(name, definition)
        try:
            hc.trigger_mcp_discovery()
        except Exception:
            pass
        return _ok(name=name, server=entry)
    except Exception as e:
        return _err(str(e))

@app.delete("/api/mcp-store/installed/{name}")
def mcp_store_remove(name: str):
    """移除 MCP 服务器（写回 config.yaml）。"""
    if not hc.remove_mcp_server(name):
        return _err(f"未找到 MCP 服务器 {name}")
    return _ok(name=name)

@app.post("/api/mcp-store/installed/{name}/enable")
async def mcp_store_enable(name: str, req):
    """启用/停用 MCP 服务器。"""
    body = await req.json()
    enabled = bool(body.get("enabled", True))
    if not hc.set_mcp_enabled(name, enabled):
        return _err(f"未找到 MCP 服务器 {name}")
    return _ok(name=name, enabled=enabled)

@app.post("/api/mcp-store/installed/{name}/save")
async def mcp_store_save(name: str, req):
    """编辑保存 MCP 定义（command/args/env 或 url/headers）。"""
    body = await req.json()
    cur = hc.list_mcp_servers()
    if name not in cur:
        return _err(f"未找到 MCP 服务器 {name}")
    cur_d = cur[name] if isinstance(cur[name], dict) else {}
    definition = {
        "command": (body.get("command") or cur_d.get("command") or "").strip(),
        "args": body.get("args") if body.get("args") is not None else cur_d.get("args"),
        "env": body.get("env") if body.get("env") is not None else cur_d.get("env"),
    }
    url = (body.get("url") or cur_d.get("url") or "").strip()
    if url:
        definition["url"] = url
        hd = body.get("headers")
        if hd is None:
            hd = cur_d.get("headers")
        if isinstance(hd, dict):
            definition["headers"] = hd
    if not definition.get("command") and not definition.get("url"):
        return _err("启动命令与 URL 至少保留一项")
    if not definition.get("command"):
        definition.pop("command", None)
    try:
        entry = hc.upsert_mcp_server(name, definition)
        try:
            hc.trigger_mcp_discovery()
        except Exception:
            pass
        return _ok(name=name, server=entry)
    except Exception as e:
        return _err(str(e))

