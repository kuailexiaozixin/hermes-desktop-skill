"""MCP 服务器信息与托管接口

只读信息端点 /api/mcp-server/info 如实报告 Hermes Library 作为 MCP 服务器的
能力与外部客户端配置。

在此基础上新增「应用托管」能力：本桌面可以**托管启动/停止**工具面 MCP 服务器
（`python -m agent.transports.hermes_tools_mcp_server`）这一独立 stdio 子进程，
并对其做 initialize 探活，用于本地自检与一键验证。MCP 服务器本就是独立进程，
应用仅托管、不改变「进程内直跑、不起第二个进程」的架构原则。

设计边界：
- 托管实例的 stdio 归本应用所有，用于探活/验证；外部客户端（mcporter / VS Code /
  Claude Code 等）各自独立 spawn 新进程，与本实例共享同一 HERMES_HOME 数据目录，
  两者不冲突、可共存。
- 会话桥接形态（`hermes mcp serve`）在当前发行版不可用（frozen 缺 mcp / venv 被
  应用控制策略阻止），故托管仅支持工具面形态。
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from routes import app, _ok, _err

# ---------------------------------------------------------------------------
# 常量与运行环境探测
# ---------------------------------------------------------------------------
_TOOL_MODULE = "agent.transports.hermes_tools_mcp_server"

# 候选 python（含应用 venv 的两个位置），选第一个含工具面模块者
_VENV_PY_CANDIDATES = [
    Path(r"D:\临时环境\hermes-desktop-01\Scripts\python.exe"),
    Path(r"C:\Users\贺新\AppData\Local\fasthtml-desktop\venvs\hermes-desktop-01\Scripts\python.exe"),
]
_PYHOME_FALLBACK = Path(r"D:\Python\cpython-3.13.14-windows-x86_64-none")

# 进程注册表：kind -> {"proc": Popen, "started_at": float, "out_q": queue.Queue}
_PROCS: dict = {}
_LOCK = threading.Lock()


def _hermes_home() -> str:
    """与同进程 AIAgent 保持一致的数据目录（HERMES_HOME）。"""
    h = os.environ.get("HERMES_HOME")
    if h:
        return h
    return str(Path(__file__).resolve().parent.parent / ".hermes_data")


def _python_candidates() -> list[str]:
    seen, out = set(), []
    for c in [sys.executable] + [str(p) for p in _VENV_PY_CANDIDATES]:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _pyhome_for(py: str) -> str | None:
    """从 venv 的 pyvenv.cfg 读取 base（home），供 PYTHONHOME 使用。"""
    cfg = Path(py).resolve().parent.parent / "pyvenv.cfg"
    if cfg.exists():
        try:
            for line in cfg.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.strip().lower().startswith("home"):
                    v = line.split("=", 1)[1].strip()
                    if v:
                        return v
        except Exception:
            pass
    if _PYHOME_FALLBACK.exists():
        return str(_PYHOME_FALLBACK)
    return None


def _tool_module_in(py: str) -> bool:
    sp = Path(py).resolve().parent.parent / "Lib" / "site-packages"
    return (sp / "agent" / "transports" / "hermes_tools_mcp_server.py").exists()


def _pick_python() -> str | None:
    for py in _python_candidates():
        try:
            if os.path.exists(py) and _tool_module_in(py):
                return py
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# 子进程 stdin/stdout/stderr 处理
# ---------------------------------------------------------------------------
def _drain(stream) -> None:
    """持续消费 stderr，避免缓冲区写满阻塞子进程。"""
    try:
        for _ in stream:
            pass
    except Exception:
        pass


def _reader(stream, q: queue.Queue) -> None:
    """把 stdout 的 JSON-RPC 行读入队列。"""
    try:
        for raw in stream:
            q.put(raw)
    except Exception:
        pass


def _send(proc, obj) -> None:
    proc.stdin.write(json.dumps(obj).encode() + b"\n")
    proc.stdin.flush()


def _recv(q: queue.Queue, timeout: float):
    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        return None


def _start_tool_surface() -> dict:
    py = _pick_python()
    if not py:
        return _err("未找到含工具面 MCP 模块（agent.transports.hermes_tools_mcp_server）的 python")
    env = dict(os.environ)
    env["HERMES_HOME"] = _hermes_home()
    ph = _pyhome_for(py)
    if ph:
        env["PYTHONHOME"] = ph
    else:
        env.pop("PYTHONHOME", None)

    out_q = queue.Queue()
    try:
        # -u 无缓冲，否则 stdout 的 JSON-RPC 响应无法及时读到
        proc = subprocess.Popen(
            [py, "-u", "-m", _TOOL_MODULE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(Path(__file__).resolve().parent.parent),
        )
    except Exception as e:
        return _err(f"启动失败：{type(e).__name__}: {e}")

    threading.Thread(target=_drain, args=(proc.stderr,), daemon=True).start()
    threading.Thread(target=_reader, args=(proc.stdout, out_q), daemon=True).start()

    entry = {"proc": proc, "started_at": time.time(), "out_q": out_q, "kind": "tool_surface"}
    with _LOCK:
        _PROCS["tool_surface"] = entry
    return _ok(pid=proc.pid, kind="tool_surface", hermes_home=_hermes_home())


def _probe_tool_surface(entry: dict, timeout: float = 25) -> dict:
    proc = entry["proc"]
    if proc.poll() is not None:
        return _err(f"进程已退出（exit code={proc.poll()}）")
    q = entry["out_q"]
    while not q.empty():
        try:
            q.get_nowait()
        except queue.Empty:
            break
    try:
        _send(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "hermes-desktop-probe", "version": "1.0"},
            },
        })
        raw = _recv(q, timeout)
    except Exception as e:
        return _err(f"探活异常：{type(e).__name__}: {e}")
    if raw is None:
        return _err(f"initialize 探活超时（{timeout}s）")
    try:
        obj = json.loads(raw)
    except Exception:
        return _err(f"响应非 JSON：{raw[:200]!r}")
    if "result" in obj:
        r = obj["result"]
        return _ok(
            server_info=r.get("serverInfo"),
            protocolVersion=r.get("protocolVersion"),
            pid=proc.pid,
        )
    return _err(obj.get("error") or obj)


def _kill_proc(proc) -> None:
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=3)
        return
    except Exception:
        pass
    try:
        proc.kill()
        proc.wait(timeout=3)
        return
    except Exception:
        pass
    # taskkill 兜底（/T 连带子进程）
    try:
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 路由：只读信息（保留）
# ---------------------------------------------------------------------------
@app.get('/api/mcp-server/info')
def mcp_server_info(req):
    # 懒探测：未装 mcp 包时不影响整个应用启动
    mcp_available = False
    try:
        import importlib.util
        mcp_available = importlib.util.find_spec("mcp") is not None
    except Exception:
        mcp_available = False

    client_config = {
        "mcpServers": {
            "hermes": {
                "command": "hermes",
                "args": ["mcp", "serve"],
            }
        }
    }

    return {
        "ok": True,
        "mcp_available": mcp_available,
        "transport": "stdio（独立进程）",
        "conversation_bridge_command": "hermes mcp serve",
        "tool_surface_command": "python -m agent.transports.hermes_tools_mcp_server",
        "client_config": client_config,
        "note": (
            "Hermes Library 可作为 MCP 服务器，有「会话桥接」与「工具面暴露」两种形态，"
            "但二者均为独立 stdio 进程，需单独运行且依赖 mcp 包（pip install 'mcp'）。"
            "本桌面应用遵循「进程内直跑、不起第二个进程」的设计，自身不内嵌 MCP 服务器；"
            "如需让外部程序（Claude Code / Cursor / Codex 等）连接，请单独运行上述命令，"
            "它将与本应用共享同一 HERMES_HOME 数据目录。"
        ),
        "security": (
            "MCP 服务器会把工具暴露给连接它的客户端，且进程内路线没有额外鉴权边界，"
            "请只在可信环境使用。"
        ),
    }


# ---------------------------------------------------------------------------
# 路由：托管（启动/停止/探活/状态）
# ---------------------------------------------------------------------------
@app.get('/api/mcp-server/status')
def mcp_server_status():
    items = []
    with _LOCK:
        for kind, entry in list(_PROCS.items()):
            proc = entry["proc"]
            items.append({
                "kind": kind,
                "pid": proc.pid,
                "running": proc.poll() is None,
                "started_at": entry["started_at"],
            })
    py = _pick_python()
    return _ok(
        running=items,
        python_ready=py is not None,
        python=py,
        hermes_home=_hermes_home(),
        note=("托管实例仅用于本机自检/探活；外部客户端（mcporter / VS Code 等）"
              "各自独立 spawn 新进程并共享同一 HERMES_HOME。"),
    )


@app.post('/api/mcp-server/start')
async def mcp_server_start(req):
    kind = "tool_surface"
    try:
        body = await req.json() if req else {}
        kind = (body.get("kind") or "tool_surface")
    except Exception:
        kind = "tool_surface"
    if kind != "tool_surface":
        return _err(
            f"会话桥接形态「{kind}」当前不可用（frozen 缺 mcp / venv 被应用控制策略阻止），"
            "仅支持工具面形态 tool_surface"
        )
    with _LOCK:
        old = _PROCS.get(kind)
        if old is not None:
            if old["proc"].poll() is None:
                return _err(f"{kind} 已在运行（pid={old['proc'].pid}）")
            _PROCS.pop(kind, None)  # 清理已退出的旧实例
    return _start_tool_surface()


@app.post('/api/mcp-server/stop')
async def mcp_server_stop(req):
    kind = "tool_surface"
    try:
        body = await req.json() if req else {}
        kind = (body.get("kind") or "tool_surface")
    except Exception:
        kind = "tool_surface"
    with _LOCK:
        entry = _PROCS.pop(kind, None)
    if entry is None:
        return _err(f"没有运行中的 {kind} 托管进程")
    proc = entry["proc"]
    _kill_proc(proc)
    return _ok(kind=kind, pid=proc.pid)


@app.post('/api/mcp-server/probe')
async def mcp_server_probe(req):
    kind = "tool_surface"
    try:
        body = await req.json() if req else {}
        kind = (body.get("kind") or "tool_surface")
    except Exception:
        kind = "tool_surface"
    with _LOCK:
        entry = _PROCS.get(kind)
    if entry is None:
        return _err(f"没有运行中的 {kind} 托管进程，请先启动")
    return _probe_tool_surface(entry)
