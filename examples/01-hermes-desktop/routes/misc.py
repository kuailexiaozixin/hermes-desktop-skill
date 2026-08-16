import json
import os
import sys

from starlette.responses import FileResponse, JSONResponse, Response, StreamingResponse

from routes import Path, _add_cron_record, _err, _guard, _load_cron_history, _ok, _save_cron_history, app, ar, bridge, cron_sched, fw, hc, host_tools, render_markdown, sessions, we
from routes import start_qr_login, get_qr_status, cancel_qr_login
# 设置中心 · 定时任务
# ---------------------------------------------------------------------------
@app.get("/api/cron")
def api_cron():
    return _guard(lambda: {"ok": True, "items": hc.list_jobs()})


@app.post("/api/cron")
async def api_cron_add(req):
    body = await req.json()
    jid = body.get("id")
    if jid:
        return _guard(hc.update_job, jid, name=body.get("name"),
                      prompt=body.get("prompt"), schedule=body.get("schedule"),
                      job_type=body.get("job_type"))
    return _guard(hc.add_job, body.get("prompt") or "", body.get("schedule") or "",
                  name=body.get("name"), job_type=body.get("job_type"))


@app.post("/api/cron/{job_id}/status")
async def api_cron_status(job_id: str, req):
    body = await req.json()
    return _guard(hc.set_job_status, job_id, body.get("status") or "paused")


@app.delete("/api/cron/{job_id}")
def api_cron_del(job_id: str):
    return _guard(hc.delete_job, job_id)

@app.post("/api/cron/{job_id}/run")
def api_cron_run(job_id: str):
    """手动立即运行一次定时任务（后台异步执行）。"""
    # 记录执行
    try:
        _jobs = hc.list_jobs()
        _job = next((j for j in _jobs if j.get("id") == job_id), None)
        _name = _job.get("name", job_id) if _job else job_id
        _add_cron_record(job_id, _name, "running")
    except Exception:
        pass
    return _guard(cron_sched.run_job_now, job_id)

@app.get("/api/cron/executions")
def api_cron_executions():
    """获取定时任务执行历史。"""
    try:
        records = _load_cron_history()
        # 按时间倒序
        records.reverse()
        return _ok(ok=True, items=records)
    except Exception as e:
        return _err(str(e), items=[])

@app.post("/api/cron/executions/clear")
def api_cron_executions_clear():
    """清空定时任务执行历史。"""
    try:
        _save_cron_history([])
        return _ok(ok=True)
    except Exception as e:
        return _err(str(e))

@app.put("/api/cron/{job_id}")
async def api_cron_update(job_id: str, req):
    """编辑定时任务。"""
    body = await req.json()
    return _guard(hc.update_job, job_id, name=body.get("name"),
                  prompt=body.get("prompt"), schedule=body.get("schedule"))


# ---------------------------------------------------------------------------
# 原生指令（/xxx）
# ---------------------------------------------------------------------------
@app.get("/api/commands")
def api_commands():
    return _guard(lambda: {"ok": True, "items": fw.list_native_commands(),
                           "count": fw.native_command_count()})


@app.post("/api/command")
async def api_command(req):
    body = await req.json()
    name, args = fw.parse_command(body.get("text") or "")
    if not name:
        return _err("不是一条原生指令")
    return _guard(lambda: {"ok": True, "name": name, **fw.execute_command(name, args)})


# ---------------------------------------------------------------------------
# 审批闭环
# ---------------------------------------------------------------------------
@app.post("/api/approve")
async def api_approve(req):
    body = await req.json()
    cmd = (body.get("command") or "").strip()
    if not cmd:
        return _err("命令为空")
    return ar.execute_approved_command(cmd)


# ---------------------------------------------------------------------------
# 产物与预览
# ---------------------------------------------------------------------------
_TEXT_EXT = {".txt", ".md", ".json", ".csv", ".py", ".js", ".css", ".html", ".yaml",
             ".yml", ".log", ".xml", ".svg"}


@app.get("/api/artifacts")
def api_artifacts():
    """列出 output/ 下的产物（按修改时间倒序，最多 200 条）。"""
    root = Path(hc.output_dir())
    root.mkdir(parents=True, exist_ok=True)
    items = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        rel = p.relative_to(root).as_posix()
        items.append({
            "path": rel, "name": p.name, "size": st.st_size,
            "mtime": st.st_mtime, "ext": p.suffix.lower(),
            "viewable": p.suffix.lower() in _TEXT_EXT or p.suffix.lower() in {
                ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"},
        })
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return _ok(items=items[:200], root=str(root), preview=host_tools.preview_state())


@app.get("/artifact/{path:path}")
def artifact(path: str):
    """安全地把 output/ 下的文件吐回去（拒绝越界路径）。"""
    root = Path(hc.output_dir()).resolve()
    target = (root / path).resolve()
    if not str(target).startswith(str(root)) or not target.is_file():
        return JSONResponse(_err("文件不存在或路径越界"), status_code=404)
    return FileResponse(str(target))


@app.post("/api/preview/stop")
def api_preview_stop():
    return _guard(lambda: json.loads(host_tools.handle_stop_preview({})))


@app.get("/api/preview")
def api_preview():
    return _ok(**host_tools.preview_state())


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------
def _bootstrap() -> None:
    """进程启动时把 Library 运行环境落地（幂等）。失败不阻断启动。"""
    try:
        hc.materialize_hermes_env()
    except Exception as e:  # noqa: BLE001
        print(f"[warn] materialize_hermes_env 失败：{e}", file=sys.stderr)
    try:
        cron_sched.start_scheduler()
        print("[cron] 后台调度线程已启动，定时任务中心现已真正按点触发", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] 定时任务调度器启动失败：{e}", file=sys.stderr)
    try:
        ar.register_pure_python_tools()
    except Exception as e:  # noqa: BLE001
        print(f"[warn] 工具注册跳过（hermes-agent 未就绪）：{e}", file=sys.stderr)


_bootstrap()


# ---------------------------------------------------------------------------
# 配置导出/导入
# ---------------------------------------------------------------------------
@app.get("/api/config/export")
def api_config_export():
    """导出所有配置（模型、技能、MCP）为 JSON。"""
    try:
        import hermes_config as hc
        models = hc.get_models_list()
        skills = hc.list_skills()
        mcp = hc.list_mcp_servers()
        return {"ok": True, "config": {
            "models": models, "skills": skills, "mcp": mcp,
            "exported_at": __import__("time").strftime("%Y-%m-%d %H:%M"),
        }}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/api/config/import")
async def api_config_import(req):
    """导入配置（模型、技能、MCP）。"""
    try:
        body = await req.json()
        cfg = body.get("config") or body
        if not cfg:
            return {"ok": False, "error": "缺少配置数据"}
        import hermes_config as hc
        if "models" in cfg:
            hc.save_models_list(cfg["models"])
        if "skills" in cfg:
            for sk in (cfg["skills"] or []):
                name = sk.get("name") or sk.get("id")
                if name:
                    hc.update_skill(name, sk)
        if "mcp" in cfg:
            raw = cfg["mcp"] or {}
            pairs = []
            if isinstance(raw, dict):
                for nm, df in raw.items():
                    pairs.append((nm, df))
            else:
                for ms in raw:
                    nm = ms.get("name") if isinstance(ms, dict) else None
                    if nm:
                        pairs.append((nm, ms))
            for nm, df in pairs:
                if nm and isinstance(df, dict):
                    hc.upsert_mcp_server(nm, df)
        return {"ok": True, "message": "配置已导入"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------

@app.get("/api/export/full")
async def api_export_full():
    """全量数据导出：聚合会话、Wiki、记忆、看板、配置为 ZIP 包。"""
    import io, zipfile, json, time as _time, re as _re
    try:
        import sessions as _sessions
        import wiki_engine as _we
        import hermes_config as _hc
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            convs = _sessions.list_sessions(include_archived=True)
            for s in convs:
                try:
                    exp = _sessions.export_session(s["id"], fmt="md")
                    if exp.get("ok"):
                        safe_name = _re.sub(r'[\\/:*?"<>|]', "_", str(s.get("title", s["id"])))
                        z.writestr(f"conversations/{safe_name}-{s['id']}.md", exp.get("text", ""))
                except Exception:
                    pass
            try:
                wiki = _we.export_wiki()
                if isinstance(wiki, dict) and wiki.get("ok"):
                    z.writestr("wiki/wiki-export.json", json.dumps(wiki, ensure_ascii=False, indent=2))
            except Exception:
                pass
            try:
                mem_files = _hc.list_memory()
                if isinstance(mem_files, list):
                    for mf in mem_files:
                        name = mf.get("name", "unknown")
                        z.writestr(f"memory/{name}", mf.get("text", ""))
            except Exception:
                pass
            try:
                kanban = _hc.get_kanban()
                tasks = (kanban or {}).get("items", []) if isinstance(kanban, dict) else (kanban or [])
                z.writestr("kanban/kanban.json", json.dumps(tasks, ensure_ascii=False, indent=2))
            except Exception:
                pass
            try:
                config = {
                    "models": _hc.get_models_list(),
                    "skills": _hc.list_skills(),
                    "mcp": _hc.list_mcp_servers(),
                }
                z.writestr("config/config.json", json.dumps(config, ensure_ascii=False, indent=2))
            except Exception:
                pass
            meta = {"exported_at": _time.strftime("%Y-%m-%d %H:%M"), "version": "1.0"}
            z.writestr("export-metadata.json", json.dumps(meta, ensure_ascii=False, indent=2))
        from starlette.responses import StreamingResponse
        return StreamingResponse(iter([buf.getvalue()]), media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=hermes-export.zip"})
    except Exception as e:
        return {"ok": False, "error": str(e)}

# 需求3：补功能屏路由（Soul / 记忆 / 系统提示词 / LLM Wiki / 远程渠道 / Kanban）
# 数据层在 hermes_config.py，此处仅薄路由。
# ---------------------------------------------------------------------------
@app.get("/api/soul")
def api_soul_get():
    return _guard(hc.get_soul)

@app.post("/api/soul")
async def api_soul_post(req):
    b = await req.json()
    return _guard(hc.save_soul, b.get("content") or "", bool(b.get("enabled")))

@app.get("/api/memory")
def api_memory_get():
    return _guard(hc.list_memory)

@app.post("/api/memory/{fname}")
async def api_memory_save(fname: str, req):
    b = await req.json()
    return _guard(hc.save_memory, fname, b.get("text") or "")

@app.get("/api/memory/export")
def api_memory_export():
    """导出记忆数据为 JSON。"""
    try:
        import hermes_config as hc
        files = hc.list_memory()
        return {"ok": True, "files": files, "exported_at": __import__("time").strftime("%Y-%m-%d %H:%M")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/memory/providers")
def api_memory_providers():
    """列出可用记忆 provider + 当前启用（对照 13 §2.2）。"""
    try:
        import memory_providers as _mp
        return {"ok": True, **_mp.list_providers()}
    except Exception as e:
        return {"ok": False, "error": f"provider 列表不可用: {type(e).__name__}: {e}"}


@app.post("/api/memory/provider/switch")
async def api_memory_provider_switch(req):
    """切换记忆 provider（写 config.yaml 的 memory.provider）。"""
    try:
        import memory_providers as _mp
        b = await req.json()
        return _mp.switch_provider(b.get("provider") or "")
    except Exception as e:
        return {"ok": False, "error": f"切换失败: {type(e).__name__}: {e}"}


@app.get("/api/memory/search")
def api_memory_search(q: str = "", category: str = "", limit: int = 10):
    """向量/语义检索记忆（holographic 混合检索）。"""
    try:
        import memory_providers as _mp
        return _mp.search_memory(q, category or None, limit)
    except Exception as e:
        return {"ok": False, "error": f"检索失败: {type(e).__name__}: {e}"}


@app.get("/api/memory/layers")
def api_memory_layers():
    """分层查看记忆（记忆文件 / holographic facts / active provider）。"""
    try:
        import memory_providers as _mp
        return {"ok": True, **_mp.memory_layers()}
    except Exception as e:
        return {"ok": False, "error": f"分层查看失败: {type(e).__name__}: {e}"}

# ── 上下文管理（对照 13 §2.1 上下文压缩引擎：engine 选择 + 压缩状态 + token 跟踪） ──
@app.get("/api/context/engines")
def api_context_engines():
    """列出可用上下文引擎 + 当前启用。"""
    try:
        import context_provider as _cp
        return {"ok": True, **_cp.list_engines()}
    except Exception as e:
        return {"ok": False, "error": f"引擎列表不可用: {type(e).__name__}: {e}"}

@app.post("/api/context/engine")
async def api_context_engine_switch(req):
    """切换上下文引擎（写 config.yaml 的 context.engine）。"""
    try:
        import context_provider as _cp
        b = await req.json()
        return _cp.switch_engine(b.get("engine") or "")
    except Exception as e:
        return {"ok": False, "error": f"切换失败: {type(e).__name__}: {e}"}

@app.get("/api/context/status")
def api_context_status(cid: str = ""):
    """上下文压缩状态 + 会话 token 跟踪。"""
    try:
        import context_provider as _cp
        return {"ok": True, **_cp.get_context_status(cid=cid or None)}
    except Exception as e:
        return {"ok": False, "error": f"状态获取失败: {type(e).__name__}: {e}"}

@app.get("/api/system-prompt")
def api_system_prompt_get():
    return _guard(hc.get_system_prompt)

@app.post("/api/system-prompt")
async def api_system_prompt_post(req):
    b = await req.json()
    return _guard(hc.save_system_prompt, b.get("custom") or "")

# ── LLM Wiki（对齐 Hermes llm-wiki 语义：三层目录 + 互联 + 编译/查询/维护） ──
@app.get("/api/wiki")
def api_wiki_list():
    return _guard(hc.list_wiki)


@app.post("/api/wiki")
async def api_wiki_save(req):
    b = await req.json()
    return _guard(hc.save_wiki, b.get("name") or "", b.get("title") or "",
                  b.get("category") or "通用", b.get("tags") or [], b.get("text") or "",
                  type_=b.get("type") or "summary",
                  sources=b.get("sources") or [], confidence=b.get("confidence") or "")


# ⚠️ 通用 /api/wiki/{name} 路由必须排在所有具体子路由（raw/ingest/query/lint/graph/schema）之后，
# 否则 /api/wiki/graph 等会被 {name} 抢匹配为 name="graph"。见本段末尾。
@app.get("/api/wiki/raw")
def api_wiki_raw_list():
    return _guard(we.list_raw)


@app.post("/api/wiki/raw")
async def api_wiki_raw_add(req):
    b = await req.json()
    text = b.get("text") or ""
    url = (b.get("url") or "").strip()
    if url and not text:
        # 简易 URL 抓取（进程内，标准库；失败抛清晰错误由 _guard 回显）
        import urllib.request
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8", "replace")
            text = f"# Source: {url}\n\n{raw}"
        except Exception as e:  # noqa: BLE001
            return _err(f"抓取失败：{e}")
    name = b.get("name") or (url.split("/")[-1] or "source")
    return _guard(we.add_raw, None, name, text, url)


@app.delete("/api/wiki/raw/{name}")
async def api_wiki_raw_del(name: str):
    from wiki_engine import wiki_dir
    d = wiki_dir().resolve()
    p = (d / "raw" / (name or "").replace("..", "")).resolve()
    if not str(p).startswith(str(d) + os.sep) or not p.is_file():
        return _err("源不存在")
    p.unlink()
    return _ok()


@app.post("/api/wiki/ingest")
async def api_wiki_ingest(req):
    b = await req.json()
    return _guard(we.ingest, None, b.get("raw_names") or None, hc.get_active_model_cfg())


@app.post("/api/wiki/query")
async def api_wiki_query(req):
    b = await req.json()
    return _guard(we.query, None, b.get("question") or "", hc.get_active_model_cfg())


@app.get("/api/wiki/lint")
def api_wiki_lint():
    return _guard(we.lint)


@app.get("/api/wiki/graph")
def api_wiki_graph():
    return _guard(we.graph)


@app.post("/api/wiki/schema")
async def api_wiki_schema(req):
    b = await req.json()
    return _guard(we.generate_schema, None, b.get("domain") or "", hc.get_active_model_cfg())


# ── v2 缺口补齐端点（仍为具体子路由，须排在通用 /{name:path} 之前） ──
@app.post("/api/wiki/rename")
async def api_wiki_rename(req):
    b = await req.json()
    return _guard(we.rename_page, None, b.get("old") or "", b.get("new") or "")


@app.get("/api/wiki/search")
def api_wiki_search(q: str = ""):
    return _guard(we.search, None, q or "")


@app.post("/api/wiki/fix-links")
async def api_wiki_fix_links():
    return _guard(we.fix_broken_links)


@app.get("/api/wiki/export")
def api_wiki_export():
    return _guard(we.export_wiki)


@app.post("/api/wiki/import")
async def api_wiki_import(req):
    b = await req.json()
    return _guard(we.import_wiki, None, b or {})


# ── 通用 /api/wiki/{name} 路由（必须排在 raw/ingest/query/lint/graph/schema/rename/search/fix-links/export/import 之后） ──
# 注意：slug 含类型子目录（如 concepts/page-a），所以 name 必须用 :path 捕获斜杠，
# 否则 Starlette 的单段 {name} 无法匹配多段路径，typed 页面会 404。
# 另外 /html 路由必须排在纯 {name:path} GET 之前，否则后者会贪婪吞掉
# /api/wiki/concepts/page-a/html（把 name 误读成 concepts/page-a/html）。
@app.get("/api/wiki/{name:path}/html")
async def api_wiki_html(name: str):
    """把页面正文渲染为安全 HTML（含 wikilink 占位，前端再做可点击化）。"""
    r = hc.get_wiki(name)
    if not r:
        return _err("条目不存在")
    html = render_markdown(r.get("body") or "")
    return _ok(html=html, slug=(r.get("slug") or name))


@app.get("/api/wiki/{name:path}")
async def api_wiki_get(name: str):
    r = hc.get_wiki(name)
    return r if r else _err("条目不存在")


@app.delete("/api/wiki/{name:path}")
async def api_wiki_delete(name: str):
    return _guard(hc.delete_wiki, name)


@app.get("/api/channels")
def api_channels_get():
    return _guard(hc.get_channels)

@app.post("/api/channels/{cid}")
async def api_channel_save(cid: str, req):
    b = await req.json()
    return _guard(hc.save_channel, cid, b)

@app.get("/api/channels/status")
def api_channels_status():
    """各渠道连接状态 + 本地 Webhook 接收器状态。"""
    return bridge.status()

@app.post("/api/channels/{cid}/connect")
async def api_channel_connect(cid: str, req):
    """连接某渠道（进程内桥）：配置优先取请求体，否则读已保存配置。"""
    try:
        b = await req.json()
    except Exception:  # noqa: BLE001
        b = {}
    config = (b or {}).get("config") or {}
    if not config:
        for c in (hc.get_channels().get("channels") or []):
            if c["id"] == cid:
                config = c.get("config") or {}
                break
    return _guard(bridge.connect, cid, config)

@app.post("/api/channels/{cid}/disconnect")
def api_channel_disconnect(cid: str):
    """断开某渠道。"""
    return _guard(bridge.disconnect, cid)

@app.post("/api/channels/{cid}/test")
async def api_channel_test(cid: str, req):
    """向某渠道发送测试消息（验证出站可达）。"""
    try:
        b = await req.json()
    except Exception:  # noqa: BLE001
        b = {}
    b = b or {}
    text = b.get("text") or "这是来自 Hermes Desktop 的测试消息。"
    recipient = b.get("recipient") or "test"
    return _guard(bridge.test_send, cid, text, recipient)

@app.get("/api/channels/events")
def api_channels_events(limit: int = 50):
    """最近入站/出站事件流水（前端轮询实时展示）。"""
    return {"ok": True, "events": bridge.get_events(limit)}


# ---------------------------------------------------------------------------
# 微信 iLink 一键扫码登录
# ---------------------------------------------------------------------------
@app.post("/api/channels/wechat/qr/start")
def api_wechat_qr_start():
    """开始微信 iLink 扫码登录，返回二维码图片/URL 与会话 ID。"""
    return _guard(start_qr_login)


@app.get("/api/channels/wechat/qr/status")
def api_wechat_qr_status(sid: str):
    """查询指定扫码会话的当前状态与凭证。"""
    return _guard(get_qr_status, sid)


@app.post("/api/channels/wechat/qr/cancel")
def api_wechat_qr_cancel(sid: str):
    """取消指定扫码会话。"""
    return _guard(cancel_qr_login, sid)


@app.get("/api/kanban")
def api_kanban_get():
    return _guard(hc.get_kanban)

@app.post("/api/kanban")
async def api_kanban_add(req):
    b = await req.json()
    return _guard(hc.add_kanban_task, b.get("title") or "", b.get("description") or "")


@app.get("/api/kanban/export")
def api_kanban_export(fmt: str = "json"):
    """导出看板数据为 JSON 或 CSV。"""
    import json
    try:
        import hermes_config as hc
        data = hc.get_kanban()
        tasks = (data or {}).get("items", []) if isinstance(data, dict) else (data or [])
        if fmt == "csv":
            import csv, io
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["ID", "标题", "描述", "状态", "优先级", "创建时间"])
            for t in tasks:
                w.writerow([t.get("id", ""), t.get("title", ""), t.get("description", ""),
                           t.get("status", ""), t.get("priority", ""), t.get("created_at", "")])
            from starlette.responses import Response
            return Response(content=buf.getvalue(), media_type="text/csv; charset=utf-8",
                           headers={"Content-Disposition": "attachment; filename=kanban.csv"})
        return {"ok": True, "tasks": tasks, "exported_at": __import__("time").strftime("%Y-%m-%d %H:%M")}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# 预热工具集矩阵缓存：后台线程提前跑一次 check_fn 网络探测，用户首次打开
