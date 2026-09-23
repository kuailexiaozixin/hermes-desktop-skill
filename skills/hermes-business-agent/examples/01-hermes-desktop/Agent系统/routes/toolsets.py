import json

from starlette.responses import JSONResponse, StreamingResponse

from typing import Iterator
from server import app
from ._helpers import _err, _guard, _ok
import agent_runtime as ar
import hermes_config as hc

# 设置中心 · 工具与集成
# 方案 A/D 重构：
#   * TRIAL_FORCE / TRIAL_PROMPTS 由 agent_runtime._toolset_specs 单一事实源派生
#     （ar 包级导出），本文件不再维护两张平行字典；
#   * 一键安装分支由 spec.installer 键分发（cua/cronjob/kanban/ffmpeg），
#     并移除个人环境硬编码路径；
#   * test-all 改为线程池并行探测；
#   * /api/settings/loop 迁至 routes/loops.py（内聚修正）；
#   * 新增场景预设端点 /api/toolsets/profiles、/api/toolsets/profile（方案 C）。
# ---------------------------------------------------------------------------


def _ensure_toolset(name: str):
    """校验工具集名是否有效（TOOLSET_SPECS 单一事实源）。

    无效时返回错误响应 dict（ok:False），有效时返回 None。
    供 toggle / configure / test / batch 复用，避免对未定义工具集名产生「伪成功」
    （例如 test 把未知工具集误判为可用）。
    """
    name = (name or "").strip()
    if not name:
        return _err("工具集名为空。")
    if name not in ar.TOOLSET_SPECS:
        return _err(f"工具集「{name}」不存在或未定义。")
    return None


@app.get("/api/toolsets")
def api_toolsets():
    try:
        items = ar.discover_toolsets()
    except Exception as e:  # noqa: BLE001
        # 未安装 hermes-agent 时如实返回，不假装有工具
        return _err(f"{type(e).__name__}: {e}", items=[],
                    hint="未检测到 hermes-agent，工具矩阵不可用。")
    return _ok(items=items, disabled_toolsets=list(ar.DISABLED_TOOLSETS),
               automation=list(ar.AUTOMATION_TOOLSETS),
               category_order=list(ar.CATEGORY_ORDER))


@app.post("/api/toolsets/toggle")
async def api_toolset_toggle(req):
    body = await req.json()
    name = (body.get("name") or "").strip()
    e = _ensure_toolset(name)
    if e is not None:
        return e
    if name in ar.DISABLED_TOOLSETS:
        return _err(f"工具集「{name}」已按架构禁用，不可由用户切换。", arch_disabled=True)
    return _guard(ar.set_toolset_disabled, name, bool(body.get("disabled")))

@app.post("/api/toolsets/configure")
async def api_toolset_configure(req):
    body = await req.json()
    name = (body.get("name") or "").strip()
    e = _ensure_toolset(name)
    if e is not None:
        return e
    return _guard(ar.configure_toolset, name, body.get("values") or {})

@app.post("/api/toolsets/test")
async def api_toolset_test(req):
    body = await req.json()
    name = (body.get("name") or "").strip()
    e = _ensure_toolset(name)
    if e is not None:
        return e
    return _guard(ar.test_toolset, name)

@app.post("/api/toolsets/batch")
async def api_toolset_batch(req):
    """批量操作：同时启用/禁用多个工具集。"""
    body = await req.json()
    names = body.get("names", []) or []
    disabled = bool(body.get("disabled", False))
    clean = [(n or "").strip() for n in names if (n or "").strip()]
    invalid = [n for n in clean if n not in ar.TOOLSET_SPECS]
    if invalid:
        return _err(f"以下工具集不存在或未定义：{', '.join(invalid)}")
    results = []
    for n in clean:
        r = ar.set_toolset_disabled(n, disabled)
        results.append(r)
    return _ok(results=results, count=len(results))


@app.post("/api/toolsets/test-all")
async def api_toolset_test_all(req):
    """全部检测：测试所有非架构禁用工具集，返回汇总结果（线程池并行探测）。"""
    items = ar.discover_toolsets()
    targets = [ts.get("name", "") for ts in items
               if not ts.get("arch_disabled") and ts.get("name")]
    from concurrent.futures import ThreadPoolExecutor

    def _probe_one(nm: str):
        r = ar.test_toolset(nm)
        return nm, {"available": r.get("available"), "reason": r.get("reason")}

    results = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for nm, res in ex.map(_probe_one, targets):
            results[nm] = res
    return _ok(results=results, total=len(results))


# ---------------------------------------------------------------------------
# 一键安装：按 spec.installer 键分发（分支逻辑与重构前逐字一致）
# ---------------------------------------------------------------------------
def _install_cua(body: dict) -> dict:
    """computer_use：通过 venv 中的 hermes.exe 安装 cua-driver。"""
    import subprocess, os, shutil
    from pathlib import Path

    # 查找 hermes.exe（优先 VIRTUAL_ENV，再 PATH 兜底；不再硬编码个人环境路径）
    hermes_bin = None
    _venv = os.environ.get("VIRTUAL_ENV")
    if _venv:
        _p = Path(_venv) / "Scripts" / "hermes.exe"
        if _p.exists():
            hermes_bin = _p
    if not hermes_bin:
        _found = shutil.which("hermes")
        if _found:
            hermes_bin = Path(_found)
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


def _install_cronjob(body: dict) -> dict:
    """cronjob：需要 HERMES_INTERACTIVE=1（Library 模式下审批由应用自有系统处理，
    此 env var 仅用于通过 check_fn）。"""
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


def _install_kanban(body: dict) -> dict:
    """kanban：需要 HERMES_KANBAN_TASK=1 且 kanban.db 存在。"""
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


def _install_ffmpeg(body: dict) -> dict:
    """video：视频处理需要 FFmpeg。"""
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
        from pathlib import Path
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


_INSTALLERS = {
    "computer_use": _install_cua,
    "cronjob": _install_cronjob,
    "kanban": _install_kanban,
    "video": _install_ffmpeg,
}


@app.post("/api/toolsets/install-deps")
async def api_toolset_install_deps(req):
    """一键安装工具集缺失的依赖（按 spec.installer 键分发）。"""
    body = await req.json()
    name = body.get("name", "")
    fn = _INSTALLERS.get(name)
    if fn is not None:
        return fn(body)
    return _err(f"工具集「{name}」暂不支持一键安装，请检查环境提示后重试。")


# 工具集「试用」预置最小任务与强制指令：由 _toolset_specs 单一事实源派生
# （ar.TRIAL_FORCE / ar.TRIAL_PROMPTS，与重构前两字典逐字等价）。

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
    env_vars = ar.ENV_REQUIRED.get(name, [])
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
    body = await req.json()
    name = (body.get("name") or "").strip()
    text = (body.get("text") or "").strip()
    timeout = int(body.get("timeout", 120))
    confirmed = bool(body.get("confirmed", False))

    # #12 副作用防护：危险工具集需前端确认（单一事实源见 agent_runtime 的 DANGEROUS_TOOLSETS）
    if name in ar.DANGEROUS_TOOLSETS and not confirmed:
        return JSONResponse(_err("该工具集可能会写入实际数据，请确认后重试（confirmed=true）"), status_code=400)

    if not text:
        text = ar.build_trial_prompt(name)
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
    force_msg = ar.build_trial_force(name)
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
# 场景预设（方案 C）：一键批量应用 disabled_toolsets
# ---------------------------------------------------------------------------
TOOLSET_PROFILES = [
    {"key": "safe_minimal", "name": "安全最小",
     "desc": "仅保留文件读写/长期记忆/待办/澄清提问/历史检索/联网检索，"
             "禁用全部自动化与第三方集成",
     "enabled": ["file", "memory", "todo", "clarify", "session_search", "web"]},
    {"key": "office", "name": "办公自动化",
     "desc": "安全最小 + 浏览器自动化/电脑自动化/代码执行/定时任务",
     "enabled": ["file", "memory", "todo", "clarify", "session_search", "web",
                  "browser", "computer_use", "code_execution", "cronjob"]},
    {"key": "full", "name": "完整能力",
     "desc": "启用除 terminal（架构禁用）外的全部工具集",
     "enabled": None},
]


def _profile_disabled_set(profile: dict, all_names: list, arch_names: set) -> list:
    enabled = profile.get("enabled")
    if enabled is None:  # full：不禁用任何（terminal 本就架构禁用）
        return []
    en = set(enabled)
    return [n for n in all_names if n not in en and n not in arch_names]


def _current_profile_key(items: list) -> str:
    all_names = [t["name"] for t in items if not t.get("arch_disabled")]
    arch_names = set(t["name"] for t in items if t.get("arch_disabled"))
    cur_disabled = set(t["name"] for t in items
                       if t.get("disabled") and not t.get("arch_disabled"))
    for p in TOOLSET_PROFILES:
        if set(_profile_disabled_set(p, all_names, arch_names)) == cur_disabled:
            return p["key"]
    return "custom"


@app.get("/api/toolsets/profiles")
def api_toolset_profiles():
    try:
        items = ar.discover_toolsets()
    except Exception as e:  # noqa: BLE001
        return _err(f"{type(e).__name__}: {e}", profiles=TOOLSET_PROFILES,
                    current="custom")
    return _ok(profiles=TOOLSET_PROFILES, current=_current_profile_key(items))


@app.post("/api/toolsets/profile")
async def api_toolset_profile_apply(req):
    body = await req.json()
    key = (body.get("key") or "").strip()
    p = next((x for x in TOOLSET_PROFILES if x["key"] == key), None)
    if p is None:
        return _err(f"未知预设：{key}")
    try:
        items = ar.discover_toolsets()
    except Exception as e:  # noqa: BLE001
        return _err(f"工具矩阵不可用：{e}")
    all_names = [t["name"] for t in items if not t.get("arch_disabled")]
    arch_names = set(t["name"] for t in items if t.get("arch_disabled"))
    disabled = _profile_disabled_set(p, all_names, arch_names)
    r = ar.set_toolset_profile(disabled)
    return _ok(**r, applied=key, disabled_count=len(disabled))


# ---------------------------------------------------------------------------
