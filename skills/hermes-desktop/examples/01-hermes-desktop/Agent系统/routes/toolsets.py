import json

from starlette.responses import JSONResponse, StreamingResponse

from typing import Iterator
from pathlib import Path
from server import app
from ._helpers import _err, _guard, _ok
import agent_runtime as ar
import hermes_config as hc
import wiki_engine as we
# 设置中心 · 工具与集成
# ---------------------------------------------------------------------------
@app.get("/api/toolsets")
def api_toolsets():
    try:
        items = ar.discover_toolsets()
    except Exception as e:  # noqa: BLE001
        # 未安装 hermes-agent 时如实返回，不假装有工具
        return _err(f"{type(e).__name__}: {e}", items=[],
                    hint="未检测到 hermes-agent，工具矩阵不可用。")
    return _ok(items=items, disabled_toolsets=list(ar.DISABLED_TOOLSETS),
               automation=list(ar.AUTOMATION_TOOLSETS))


@app.post("/api/toolsets/toggle")
async def api_toolset_toggle(req):
    body = await req.json()
    return _guard(ar.set_toolset_disabled, body.get("name") or "",
                  bool(body.get("disabled")))

@app.post("/api/toolsets/configure")
async def api_toolset_configure(req):
    body = await req.json()
    return _guard(ar.configure_toolset, body.get("name") or "",
                  body.get("values") or {})

@app.post("/api/toolsets/test")
async def api_toolset_test(req):
    body = await req.json()
    return _guard(ar.test_toolset, body.get("name") or "")

@app.post("/api/toolsets/batch")
async def api_toolset_batch(req):
    """批量操作：同时启用/禁用多个工具集。"""
    body = await req.json()
    names = body.get("names", []) or []
    disabled = bool(body.get("disabled", False))
    results = []
    for n in names:
        n = (n or "").strip()
        if not n:
            continue
        r = ar.set_toolset_disabled(n, disabled)
        results.append(r)
    return _ok(results=results, count=len(results))

@app.get("/api/settings/loop")
async def api_get_loop():
    """获取当前 Loop 设置（max_iterations）。"""
    from hermes_config import get_hermes_home, read_config_yaml
    home = get_hermes_home()
    cfg = read_config_yaml(home)
    agent = cfg.get("agent", {}) or {}
    loop = agent.get("loop", {}) or {}
    mi = loop.get("max_iterations", 90)
    return _ok(max_iterations=mi)


@app.post("/api/settings/loop")
async def api_save_loop(req):
    """保存 Loop 设置（max_iterations）。"""
    from hermes_config import get_hermes_home, read_config_yaml, update_config_yaml
    body = await req.json()
    mi = int(body.get("max_iterations", 90))
    mi = max(1, min(200, mi))  # 限制范围 1-200
    home = get_hermes_home()
    cfg = read_config_yaml(home)
    agent = cfg.get("agent", {}) or {}
    agent.setdefault("loop", {})["max_iterations"] = mi
    update_config_yaml(home, {"agent": agent})
    # 注入环境变量
    os.environ["HERMES_MAX_ITERATIONS"] = str(mi)
    return _ok(message=f"Loop max_iterations 已设为 {mi}", max_iterations=mi)


@app.post("/api/toolsets/test-all")
async def api_toolset_test_all(req):
    """全部检测：测试所有非架构禁用工具集，返回汇总结果。"""
    from tools.registry import registry
    items = ar.discover_toolsets()
    results = {}
    for ts in items:
        if ts.get("arch_disabled"):
            continue
        name = ts.get("name", "")
        if name:
            r = ar.test_toolset(name)
            results[name] = {"available": r.get("available"), "reason": r.get("reason")}
    return _ok(results=results, total=len(results))


@app.post("/api/toolsets/install-deps")
async def api_toolset_install_deps(req):
    """一键安装工具集缺失的依赖。

    支持的安装方式：
      - computer_use: 通过 venv 中的 hermes.exe 安装 cua-driver
    """
    body = await req.json()
    name = body.get("name", "")
    import subprocess, os, shutil
    from pathlib import Path

    if name == "computer_use":
        # 查找 venv 中的 hermes.exe（优先 VIRTUAL_ENV，再按已知路径）
        hermes_bin = None
        _venv = os.environ.get("VIRTUAL_ENV")
        if _venv:
            _p = Path(_venv) / "Scripts" / "hermes.exe"
            if _p.exists():
                hermes_bin = _p
        if not hermes_bin:
            # 已知安装路径
            _known = Path(r"D:\临时环境") / "hermes-desktop-01" / "Scripts" / "hermes.exe"
            if _known.exists():
                hermes_bin = _known
        if not hermes_bin:
            return _err("未找到 hermes.exe，请确认 hermes-agent 已安装。")
        try:
            proc = subprocess.run(
                [str(hermes_bin), "computer-use", "install"],
                capture_output=True, text=True, timeout=120,
                env={k: v for k, v in os.environ.items()
                     if k not in ("PYTHONHOME", "PYTHONPATH")},
            )
            if proc.returncode != 0:
                return _err(f"安装失败：{proc.stderr.strip() or proc.stdout.strip()}")
        except subprocess.TimeoutExpired:
            return _err("安装超时（120s），请重试。")
        except Exception as e:
            return _err(f"安装异常：{e}")
        # 安装后查找 cua-driver.exe 位置
        cua_driver_paths = [
            Path.home() / "AppData" / "Local" / "Programs" / "Cua" / "cua-driver" / "bin" / "cua-driver.exe",
            Path("C:/Program Files/Cua/cua-driver/bin/cua-driver.exe"),
        ]
        cua_driver_exe = None
        for p in cua_driver_paths:
            if p.exists():
                cua_driver_exe = str(p.resolve())
                break
        if cua_driver_exe is None:
            # 再用 shutil.which 找一次
            _found = shutil.which("cua-driver")
            if _found:
                cua_driver_exe = _found
        if cua_driver_exe:
            # 把 HERMES_CUA_DRIVER_CMD 写入 config.yaml，使后端能定位到
            from hermes_config import get_hermes_home, read_config_yaml, update_config_yaml
            home = get_hermes_home()
            cfg = read_config_yaml(home)
            env = dict(cfg.get("agent", {}).get("env", {}))
            env["HERMES_CUA_DRIVER_CMD"] = cua_driver_exe
            update_config_yaml(home, {"agent": {"env": env}})
        # 清除 check_fn 缓存
        try:
            from tools.registry import invalidate_check_fn_cache
            invalidate_check_fn_cache()
        except Exception:
            pass
        msg = f"cua-driver 安装成功"
        if cua_driver_exe:
            msg += f"（{cua_driver_exe}）"
        _out = (proc.stdout or "").strip() or (proc.stderr or "").strip() or ""
        return _ok(message=msg, output=_out)

    if name == "cronjob":
        # cronjob 需要 HERMES_INTERACTIVE=1（在 Library 模式下，审批由应用自有系统处理，此 env var 仅用于通过 check_fn）
        from hermes_config import get_hermes_home, read_config_yaml, update_config_yaml
        home = get_hermes_home()
        cfg = read_config_yaml(home)
        env = dict(cfg.get("agent", {}).get("env", {}))
        env["HERMES_INTERACTIVE"] = "1"
        update_config_yaml(home, {"agent": {"env": env}})
        try:
            from tools.registry import invalidate_check_fn_cache
            invalidate_check_fn_cache()
        except Exception:
            pass
        return _ok(message="定时任务已启用（HERMES_INTERACTIVE=1）")

    if name == "kanban":
        # kanban 需要 HERMES_KANBAN_TASK=1 且 kanban.db 存在
        from hermes_config import get_hermes_home, read_config_yaml, update_config_yaml
        import sqlite3
        home = get_hermes_home()
        # 创建 kanban.db（SQLite，确保框架可正常打开）
        _db = home / "kanban.db"
        if not _db.exists() or _db.stat().st_size == 0:
            _conn = sqlite3.connect(str(_db))
            _conn.close()
        # 设置 env var
        cfg = read_config_yaml(home)
        env = dict(cfg.get("agent", {}).get("env", {}))
        env["HERMES_KANBAN_TASK"] = "1"
        update_config_yaml(home, {"agent": {"env": env}})
        try:
            from tools.registry import invalidate_check_fn_cache
            invalidate_check_fn_cache()
        except Exception:
            pass
        return _ok(message="看板工具已启用（HERMES_KANBAN_TASK=1）")

    if name == "video":
        # 视频处理需要 FFmpeg
        import urllib.request as _ur, zipfile as _zip
        import shutil as _shutil_v
        import tempfile as _tmpf
        from pathlib import Path as _Path_tmp
        try:
            _ff = _shutil_v.which("ffmpeg")
            if _ff:
                return _ok(message=f"FFmpeg 已安装（{_ff}）")
            # 下载 FFmpeg（Windows 精简版）
            _ff_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            _dl_path = _tmpf.mkdtemp()
            _zip_path = _Path_tmp(_dl_path) / "ffmpeg.zip"
            _ur.urlretrieve(_ff_url, str(_zip_path))
            # 解压到用户目录
            _ff_dir = Path.home() / "AppData" / "Local" / "Programs" / "ffmpeg"
            _ff_dir.mkdir(parents=True, exist_ok=True)
            with _zip.ZipFile(str(_zip_path), 'r') as _z:
                # 只提取 ffmpeg.exe
                for _name in _z.namelist():
                    if _name.endswith("ffmpeg.exe"):
                        _z.extract(_name, str(_ff_dir))
                        _exe = _ff_dir / "ffmpeg.exe"
                        if not _exe.exists():
                            # 可能在子目录中
                            _extracted = _ff_dir / _name
                            _extracted.rename(_exe) if _extracted.exists() else None
                        break
            # 清理临时文件
            _shutil_v.rmtree(_dl_path, ignore_errors=True)
            # 验证（直接检查安装路径，不依赖PATH）
            _ff_exe = _ff_dir / "ffmpeg.exe"
            if _ff_exe.exists():
                return _ok(message=f"FFmpeg 已安装（{_ff_exe}）")
            return _err("FFmpeg 下载失败，请手动安装。")
        except Exception as e:
            return _err(f"安装异常：{e}")

    return _err(f"工具集「{name}」暂不支持一键安装，请检查环境提示后重试。")


# 工具集「试用」预置最小任务（用户未输入时自动跑，实际调用工具验证可用性）
# 工具集试用：强制指令（system 级注入，确保模型使用指定工具集）
TRIAL_FORCE: dict[str, str] = {
    "web": "你必须使用 web 工具集中的 web_search 或 web_extract 工具来完成以下任务，不要使用其他工具集。",
    "x_search": "你必须使用 x_search 工具集中的 x_search 工具来完成以下任务，不要使用其他工具集。",
    "image_gen": "你必须使用 image_gen 工具集中的 generate_image 工具来完成以下任务，不要使用其他工具集。",
    "file": "你必须使用 file 工具集中的 write_file 和 read_file 工具来完成以下任务，不要使用其他工具集。",
    "code_execution": "你必须使用 code_execution 工具集中的 run_python 或 run_javascript 工具来完成以下任务，不要使用其他工具集。",
    "browser": "你必须使用 browser 工具集中的 browser 工具来完成以下任务，不要使用其他工具集。",
    "browser-cdp": "你必须使用 browser-cdp 工具集中的 browser_cdp 工具来完成以下任务，不要使用其他工具集。",
    "memory": "你必须使用 memory 工具集中的 read_memory 或 write_memory 工具来完成以下任务，不要使用其他工具集。",
    "todo": "你必须使用 todo 工具集中的 create_todo 或 list_todos 工具来完成以下任务，不要使用其他工具集。",
    "vision": "你必须使用 vision 工具集中的 vision 工具来完成以下任务，不要使用其他工具集。",
    "video_gen": "你必须使用 video_gen 工具集中的 generate_video 工具来完成以下任务，不要使用其他工具集。",
    "tts": "你必须使用 tts 工具集中的 text_to_speech 工具来完成以下任务，不要使用其他工具集。",
    "computer_use": "你必须使用 computer_use 工具集中的 computer_use 工具来完成以下任务，不要使用其他工具集。",
    "cronjob": "你必须使用 cronjob 工具集中的 cronjob 工具来完成以下任务，不要使用其他工具集。",
    "kanban": "你必须使用 kanban 工具集中的 kanban 工具来完成以下任务，不要使用其他工具集。",
    "delegation": "你必须使用 delegation 工具集中的 delegate_task 工具来完成以下任务，不要使用其他工具集。",
    "discord": "你必须使用 discord 工具集中的 discord 工具来完成以下任务，不要使用其他工具集。",
    "feishu_doc": "你必须使用 feishu_doc 工具集中的 feishu_doc 工具来完成以下任务，不要使用其他工具集。",
    "session_search": "你必须使用 session_search 工具集中的 session_search 工具来完成以下任务，不要使用其他工具集。",
    "clarify": "你必须使用 clarify 工具集中的 clarify 工具来完成以下任务，不要使用其他工具集。",
    "discord_admin": "你必须使用 discord_admin 工具集中的 discord_admin 工具来完成以下任务，不要使用其他工具集。",
    "feishu_drive": "你必须使用 feishu_drive 工具集中的 feishu_drive 工具来完成以下任务，不要使用其他工具集。",
    "hermes-yuanbao": "你必须使用 hermes-yuanbao 工具集中的 hermes_yuanbao 工具来完成以下任务，不要使用其他工具集。",
    "homeassistant": "你必须使用 homeassistant 工具集中的 homeassistant 工具来完成以下任务，不要使用其他工具集。",
    "project": "你必须使用 project 工具集中的 project 工具来完成以下任务，不要使用其他工具集。",
    "skills": "你必须使用 skills 工具集中的 skills 工具来完成以下任务，不要使用其他工具集。",
    "video": "你必须使用 video 工具集中的 video 工具来完成以下任务，不要使用其他工具集。",
}

TRIAL_PROMPTS = {
    "web": "请使用联网搜索工具搜索「人工智能最新进展」，简要总结 3 条要点。",
    "x_search": "请使用 X 检索工具搜索「AI」，简要总结结果。",
    "image_gen": "请使用图像生成工具生成一张「蓝色小猫」的图片，并说明是否成功。",
    "file": "请使用文件工具在工作目录创建一个文件 trial_test.txt（内容 hello），然后读取它并返回内容。",
    "code_execution": "请使用代码执行工具运行 Python：print(6*7)，并告诉我输出结果。",
    "browser": "请使用浏览器工具打开 https://example.com 并返回页面标题。",
    "browser-cdp": "请使用 CDP 浏览器工具打开 https://example.com 并返回页面标题。",
    "memory": "请使用记忆工具向 MEMORY.md 追加一条测试条目「试用验证」，再读取确认。",
    "todo": "请使用待办工具创建一条测试待办「试用验证」，再列出待办。",
    "vision": "请使用图像理解工具说明它能识别什么（无需实际图片）。",
    "video_gen": "请使用视频生成工具生成一段 5 秒的「海浪」视频，并返回结果。",
    "tts": "请使用语音合成工具将「你好，世界」转为语音，并返回结果。",
    "computer_use": "请使用电脑自动化工具描述当前桌面状态，并返回结果。",
    "cronjob": "请使用定时任务工具列出当前所有定时任务，并返回结果。",
    "kanban": "请使用看板工具列出所有任务，并返回结果。",
    "delegation": "请使用子任务委派工具将「计算 1+1」作为一个子任务执行，并返回结果。",
    "discord": "请使用 Discord 工具列出当前可用的 Discord 操作，并返回结果。",
    "feishu_doc": "请使用飞书文档工具列出当前可用的飞书操作，并返回结果。",
    "session_search": "请使用历史检索工具搜索与「测试」相关的会话，并返回结果。",
    "clarify": "请使用澄清提问工具对「帮我写个程序」这个模糊需求进行追问，列出需要澄清的问题。",
    "discord_admin": "请使用 Discord 管理工具列出当前可用的管理操作，并返回结果。",
    "feishu_drive": "请使用飞书云盘工具列出当前可用的飞书云盘操作，并返回结果。",
    "hermes-yuanbao": "请使用元宝工具列出当前可用的元宝操作，并返回结果。",
    "homeassistant": "请使用 HomeAssistant 工具列出当前可用的智能家居操作，并返回结果。",
    "project": "请使用项目管理工具列出当前可用的项目操作，并返回结果。",
    "skills": "请使用技能库工具列出当前可用的技能操作，并返回结果。",
    "video": "请使用视频处理工具列出当前可用的视频操作，并返回结果。",
}

@app.post("/api/toolsets/browser-cdp/detect")
async def api_toolset_browser_cdp_detect():
    """自动检测 Edge 浏览器 CDP 端点并配置 BROWSER_CDP_URL。"""
    import os
    from pathlib import Path
    
    edge_exe = Path("C:/") / "Program Files (x86)" / "Microsoft" / "Edge" / "Application" / "msedge.exe"
    edge_installed = edge_exe.exists()
    
    dt_port = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data" / "DevToolsActivePort"
    dt_exists = dt_port.exists()
    
    result = {
        "edge_installed": edge_installed,
        "edge_path": str(edge_exe) if edge_installed else None,
        "devtools_active_port_exists": dt_exists,
        "cdp_url": None,
        "port": None,
        "ws_path": None,
        "message": "",
    }
    
    if not edge_installed:
        result["message"] = "未检测到 Microsoft Edge 浏览器。"
        return _ok(**result)
    
    if not dt_exists:
        result["message"] = f"Edge 已安装，但未开启远程调试。请先启动 Edge 并添加 --remote-debugging-port=9222 参数。"
        return _ok(**result)
    
    try:
        port_text = dt_port.read_text().strip()
        _lines = port_text.splitlines()
        _port = _lines[0].strip() if _lines else ""
        _path = _lines[1].strip() if len(_lines) > 1 else "/devtools/browser/"
        cdp_url = f"ws://127.0.0.1:{_port}{_path}"
        result["cdp_url"] = cdp_url
        result["port"] = int(_port) if _port.isdigit() else None
        result["ws_path"] = _path
        result["message"] = f"检测到 Edge CDP 端点: {cdp_url}"
    except Exception as e:
        result["message"] = f"读取 DevToolsActivePort 失败: {e}"
        return _ok(**result)
    
    # 自动配置环境变量
    try:
        from tools.registry import invalidate_check_fn_cache
        from hermes_config import get_hermes_home, read_config_yaml, update_config_yaml
        home = get_hermes_home()
        cfg = read_config_yaml(home)
        agent = cfg.get("agent") or {}
        env = dict(agent.get("env") or {})
        env["BROWSER_CDP_URL"] = result["cdp_url"]
        cfg.setdefault("agent", {})
        cfg["agent"]["env"] = env
        update_config_yaml(home, cfg)
        os.environ["BROWSER_CDP_URL"] = result["cdp_url"]
        invalidate_check_fn_cache()
        result["auto_configured"] = True
        result["message"] = f"✅ 已自动配置 BROWSER_CDP_URL={result['cdp_url']}"
    except Exception as e:
        result["auto_configured"] = False
        result["message"] = f"检测到 CDP 端点但自动配置失败: {e}"
    
    return _ok(**result)

@app.post("/api/toolsets/env-values")
async def api_toolset_env_values(req):
    """返回指定工具集已配置的环境变量及当前值（前端显示用）。"""
    body = await req.json()
    name = (body.get("name") or "").strip()
    import os
    from agent_runtime import ENV_REQUIRED
    env_vars = ENV_REQUIRED.get(name, [])
    values = {}
    for v in env_vars:
        val = os.environ.get(v, "")
        if val:
            values[v] = val
    return _ok(name=name, env_values=values, count=len(values))

@app.post("/api/toolsets/trial")
async def api_toolset_trial(req):
    """实际试用：用真实模型让 agent 调用该工具完成最小任务，SSE 流式回吐执行过程。

    - 注入 system 级强制指令，确保模型优先使用指定工具集
    - 超时保护：stream_agent_chat 硬超时（120s）
    - 副作用防护：危险工具集需确认标识
    - 模型检查：检测当前模型是否支持工具调用
    """
    import asyncio as _asyncio
    body = await req.json()
    name = (body.get("name") or "").strip()
    text = (body.get("text") or "").strip()
    timeout = int(body.get("timeout", 120))
    confirmed = bool(body.get("confirmed", False))

    # #12 副作用防护：危险工具集需前端确认（单一事实源见 agent_runtime 的 DANGEROUS_TOOLSETS）
    if name in ar.DANGEROUS_TOOLSETS and not confirmed:
        return JSONResponse(_err("该工具集可能会写入实际数据，请确认后重试（confirmed=true）"), status_code=400)

    if not text:
        text = TRIAL_PROMPTS.get(
            name, f"请使用与【{name}】相关的工具完成一个最小任务，并说明执行结果。")
    try:
        model_cfg = hc.get_active_model_cfg(None)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"读取模型配置失败：{e}"), status_code=500)

    # #14 检查模型是否支持工具调用（仅做软提示，不拒绝）
    _model_name = (model_cfg.get("model") or "").lower()
    # 实际上所有主流模型都支持工具调用，但有些免费模型可能不支持
    # 这里只做提示，不拒绝
    _model_tool_hint = ""
    if any(x in _model_name for x in ["mini", "lite", "free", "flash"]):
        _model_tool_hint = "注意：当前模型可能不支持工具调用，试用可能失败。"

    # 注入 system 级强制指令，要求模型必须使用指定工具集
    force_msg = TRIAL_FORCE.get(name, f"你必须使用【{name}】工具集中的工具来完成以下任务，不要使用其他工具集。")
    messages = [
        {"role": "system", "content": force_msg + ("\n" + _model_tool_hint if _model_tool_hint else "")},
        {"role": "user", "content": text},
    ]

    def wrapped() -> Iterator[bytes]:
        yield ("data: " + json.dumps(
            {"type": "meta", "trial": name, "model": model_cfg.get("model"),
             "tool_hint": _model_tool_hint,
             "cost_warn": "试用会调用真实 AI 模型，消耗 API 额度。"},
            ensure_ascii=False) + "\n\n").encode()
        if _model_tool_hint:
            yield ("data: " + json.dumps(
                {"type": "reasoning", "text": _model_tool_hint},
                ensure_ascii=False) + "\n\n").encode()
        try:
            # 使用 stream_agent_chat 的硬超时参数 + 试用专用 agent 工厂
            # 确保模型能调用目标工具集（即使 check_fn 返回 False）
            def _trial_factory(mcfg, **kw):
                return ar.build_trial_agent(name, mcfg, **kw)
            for chunk in ar.stream_agent_chat(
                messages, model_cfg,
                max_iterations=hc.get_loop_max_iterations(),
                approval_check=ar.extract_approval,
                deep_think=False, web_search=True,
                timeout=timeout,
                agent_factory=_trial_factory,
            ):
                yield chunk
        except Exception as e:  # noqa: BLE001
            yield ("data: " + json.dumps(
                {"type": "error", "message": f"{type(e).__name__}: {e}"},
                ensure_ascii=False) + "\n\n").encode()

    return StreamingResponse(
        wrapped(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
