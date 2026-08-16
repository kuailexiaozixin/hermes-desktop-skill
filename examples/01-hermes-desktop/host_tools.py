"""host_tools.py — 宿主内预览 / 运行时装库（Hermes Desktop 特有的「宿主能力」工具）

这两类工具不是 Hermes 内置的，而是**桌面宿主**提供给 Agent 的额外能力，
让「Agent 写出一个 Web 应用 → 用户当场看到它跑起来」形成闭环。

1) preview_asgi_app / stop_preview —— 宿主内预览
   设计边界：
   - 目标机可能零 Python，也不打算装 Python → 不能在冻结态跑 PyInstaller 出 EXE。
     改为「宿主内预览」：复用宿主已打包进 EXE 的运行时（uvicorn + fasthtml +
     标准库 + pywebview），零额外体积。
   - 仅能预览「只用宿主打包栈」的程序；若程序 import 了宿主未内置的第三方包，
     载入时会捕获 ImportError 并回报缺失模块名（前端据此渲染「安装并预览」）。
   - 预览是「本机」预览，仅绑定 127.0.0.1，无法跨机器分发。
   - 单实例：重复调用先停旧预览再起新；stop_preview 释放端口。

2) install_library —— 进程内 pip 运行时装库
   - pip 是「运行时安装器」（下载 wheel + 解包到目录），可在进程内 ``pip.main()``
     直接跑，无需 subprocess / 编译器 → **冻结态 EXE 内可行**。
   - 走 ``--target`` 装进持久目录 ``<project_root>/.deps``；ABI 无碍
     （冻结的是原版 CPython，从 PyPI 下对应 cp3xx wheel 直接可用，含 C 扩展）。
   - 三大边界：① 必须联网 PyPI（或镜像）；② 持久目录须落在 EXE 同级可写处；
     ③ 它 ≠ 把用户程序冻成可分发 EXE（那仍须在开发机用 PyInstaller 构建）。
   - 体积代价：打包内置 pip + setuptools 约 +7~10 MB。若不需要该能力，
     可在 build.py 去掉 ``--collect-submodules pip``，本工具会优雅报错。
"""
from __future__ import annotations

import contextlib
import io
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any

try:
    from hermes_config import project_root as _project_root
except Exception:  # pragma: no cover
    def _project_root() -> Path:  # type: ignore[misc]
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).resolve().parent

MAX_TOOL_OUTPUT = 100_000

# tool_result / tool_error 复用 file_tools 的统一入口：优先 Hermes 原生
# `tools.registry`，未安装时本地兜底（保证离线可单测，JSON 形状一致）。
from file_tools import tool_error, tool_result  # noqa: E402

_PREVIEW_STATE: dict = {
    "server": None, "thread": None, "port": None,
    "url": None, "dir": None, "loaded": False,
}
_PREVIEW_LOCK = threading.Lock()


# ============================================================================
# 端口 / 目录 / 依赖路径
# ============================================================================
def _find_free_port(start: int = 7001, end: int = 7999) -> int | None:
    import socket
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
            return port
        except OSError:
            continue
    return None


def _wait_for_port(port: int, timeout: int = 15) -> bool:
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    return True
        except OSError:
            pass
        time.sleep(0.2)
    return False


def _resolve_preview_dir(raw: str) -> Path:
    """把用户传入的 dir 解析为真实目录（绝对路径原样遵从，相对路径相对项目根）。"""
    rel = (raw or "").strip()
    if not rel:
        return _project_root() / "output"
    p = Path(rel).expanduser()
    if p.is_absolute():
        return p.resolve()
    return (_project_root() / rel.lstrip("./\\")).resolve()


def get_deps_dir() -> Path:
    """运行时装库的持久目录：``<project_root>/.deps``（frozen 下即 EXE 同级）。

    该目录会被 ``ensure_deps_on_path`` 注入 ``sys.path[0]``，
    使预览 / run_python 能命中已装的第三方包。
    """
    return _project_root() / ".deps"


def ensure_deps_on_path() -> Path:
    """确保持久 deps 目录存在并处于 sys.path 最前（命中优先级最高）。"""
    deps_dir = get_deps_dir()
    try:
        deps_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    dstr = str(deps_dir)
    if dstr not in sys.path:
        sys.path.insert(0, dstr)
    return deps_dir


def _run_pip_install(pkg: str, deps_dir: Path) -> dict:
    """进程内用宿主内置的 pip 把第三方包装到 deps_dir。返回 {ok, rc, log, error}。"""
    try:
        import pip  # 运行时安装器（非构建工具）
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "rc": -1, "log": "",
                "error": "宿主未内置 pip（构建时未打包 pip/setuptools），"
                         "无法安装第三方库：%s" % e}
    log = io.StringIO()
    old_argv = sys.argv
    try:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            sys.argv = ["pip", "install", "--target", str(deps_dir),
                        "--no-input", "--disable-pip-version-check", pkg]
            rc = pip.main(sys.argv[1:])
        out = log.getvalue()
        return {"ok": rc == 0, "rc": rc, "log": out[-8000:],
                "error": "" if rc == 0 else "pip install 返回非零退出码 %s" % rc}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "rc": -2, "log": log.getvalue()[-8000:],
                "error": "pip 安装过程抛出异常：%s: %s" % (type(e).__name__, e)}
    finally:
        sys.argv = old_argv


# ============================================================================
# 载入用户 ASGI app
# ============================================================================
def _load_user_app(dir_path: Path) -> tuple[Any, str | None, str | None]:
    """从目录载入用户的 ASGI ``app`` 对象。

    返回 ``(app_obj, error, missing_module)``；error 非空即失败；缺失第三方依赖时
    missing_module 为模块名（供前端渲染「安装 X 并预览」）。

    策略：优先 ``dir/app.py``，其次 ``dir/main.py``，再退化为扫描 .py 找顶层暴露
    ``app`` / ``application`` 的模块。载入时把目录临时加入 sys.path，使模块内的
    绝对 import（含 ``from app import app`` 这类同目录引用）可解析。
    """
    ensure_deps_on_path()
    candidates: list[Path] = []
    for name in ("app.py", "main.py"):
        f = dir_path / name
        if f.exists():
            candidates.append(f)
    if not candidates:
        for f in sorted(dir_path.glob("*.py")):
            try:
                txt = f.read_text(encoding="utf-8")
            except Exception:
                continue
            if re.search(r"^\s*(?:app|application)\s*[,=]", txt, re.M):
                candidates.append(f)
    if not candidates:
        return None, (
            "目录中未找到暴露 ASGI `app` 对象的 Python 文件"
            "（需 app.py 或 main.py，且顶层定义 `app = fast_app(...)` 之类）。"
        ), None

    import importlib.util as _ilu
    dir_str = str(dir_path)
    added = dir_str not in sys.path
    if added:
        sys.path.insert(0, dir_str)
    try:
        for f in candidates:
            mod_name = "_preview_user_" + re.sub(r"\W", "_", f.stem)
            spec = _ilu.spec_from_file_location(mod_name, f)
            if spec is None or spec.loader is None:
                continue
            mod = _ilu.module_from_spec(spec)
            try:
                spec.loader.exec_module(mod)
            except ImportError as e:
                msg = str(e)
                missing = msg.split("'")[1] if (msg.count("'") >= 2) else msg
                return None, (
                    "依赖缺失：无法导入模块 '%s'（宿主运行时未内置该第三方包）。"
                    "可调用 install_library(pkg='%s', dir=...) 安装后再预览。"
                    % (missing, missing)
                ), missing
            except Exception as e:  # noqa: BLE001
                return None, "载入 %s 失败：%s: %s" % (f.name, type(e).__name__, e), None
            app_obj = getattr(mod, "app", None) or getattr(mod, "application", None)
            if app_obj is not None and callable(app_obj):
                return app_obj, None, None
        return None, (
            "已载入模块但未找到可调用的 `app` ASGI 对象"
            "（需在模块顶层定义 `app = fast_app(...)`）。"
        ), None
    finally:
        if added:
            try:
                sys.path.remove(dir_str)
            except Exception:
                pass


def _serve_preview(app: Any, port: int) -> None:
    """在守护线程里用宿主 uvicorn 服务用户的 ASGI app（仅绑定 loopback）。"""
    import uvicorn
    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, reload=False,
                         log_level="warning")
    server = uvicorn.Server(cfg)
    with _PREVIEW_LOCK:
        _PREVIEW_STATE["server"] = server
    try:
        server.run()
    finally:
        with _PREVIEW_LOCK:
            if _PREVIEW_STATE.get("server") is server:
                _PREVIEW_STATE["server"] = None


def stop_preview_internal() -> dict:
    """停止当前预览服务并清空状态（单实例保证）。返回 {stopped, port, url}。"""
    with _PREVIEW_LOCK:
        server = _PREVIEW_STATE.get("server")
        port = _PREVIEW_STATE.get("port")
        url = _PREVIEW_STATE.get("url")
        if server is None and _PREVIEW_STATE.get("thread") is None:
            return {"stopped": False}
        try:
            if server is not None:
                server.should_exit = True
        except Exception:
            pass
        _PREVIEW_STATE.update({"server": None, "thread": None, "port": None,
                               "url": None, "dir": None, "loaded": False})
        return {"stopped": True, "port": port, "url": url}


def preview_state() -> dict:
    """只读快照，供前端 /api/preview/state 查询。"""
    with _PREVIEW_LOCK:
        return {"running": bool(_PREVIEW_STATE.get("url")),
                "url": _PREVIEW_STATE.get("url"),
                "port": _PREVIEW_STATE.get("port"),
                "dir": _PREVIEW_STATE.get("dir")}


def _start_preview(d: Path) -> dict:
    """公共启动流程：分配端口 → 载入 app → 停旧 → 起新 → 等端口就绪。"""
    if not d.exists() or not d.is_dir():
        return {"ok": False, "stage": "resolve", "error": "目录不存在或不是目录: %s" % d}
    port = _find_free_port()
    if port is None:
        return {"ok": False, "stage": "port",
                "error": "无法分配空闲端口（7001-7999 均被占用）"}
    app_obj, err, missing = _load_user_app(d)
    if err:
        return {"ok": False, "stage": "load", "error": err, "missing_module": missing}
    stop_preview_internal()
    t = threading.Thread(target=_serve_preview, args=(app_obj, port), daemon=True)
    t.start()
    if not _wait_for_port(port, timeout=15):
        stop_preview_internal()
        return {"ok": False, "stage": "serve",
                "error": "预览服务已启动但端口 %s 在 15s 内未就绪，"
                         "请检查应用入口是否抛出异常（例如模块顶层误调用了 "
                         "serve() / webview.start()）。" % port}
    url = "http://127.0.0.1:%d" % port
    with _PREVIEW_LOCK:
        _PREVIEW_STATE.update({"thread": t, "port": port, "url": url,
                               "dir": str(d), "loaded": True})
    return {"ok": True, "url": url, "port": port, "dir": str(d)}


# ============================================================================
# Schemas
# ============================================================================
PREVIEW_SCHEMA = {
    "name": "preview_asgi_app",
    "description": (
        "在桌面宿主内启动一个 FastHTML / 其他 ASGI Python Web 应用的独立本地预览"
        "服务，并返回 http://127.0.0.1:<port> 形式的 URL；前端会自动弹出原生窗口"
        "预览。\n"
        "用法：传入应用所在目录 dir（相对项目根，例如 'output' 或 'output/计算器'；"
        "也可用绝对路径），该目录需含 app.py 或 main.py，且顶层暴露 ASGI `app` 对象"
        "（如 `app, rt = fast_app(...)`）。\n"
        "限制：预览服务复用宿主已打包的运行时（uvicorn + fasthtml + 标准库），"
        "用户程序只能使用这些依赖；若 import 了宿主未内置的第三方包会明确报错，"
        "此时可用 install_library(pkg=..., dir=...) 安装后再预览。\n"
        "重复调用会先停止上一次预览再启动新的（单实例）。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "dir": {
                "type": "string",
                "description": "应用所在目录（相对项目根，如 'output'；可用绝对路径）。"
                               "需含 app.py/main.py 并暴露 ASGI app。",
            },
        },
        "required": ["dir"],
    },

}

STOP_PREVIEW_SCHEMA = {
    "name": "stop_preview",
    "description": (
        "停止当前由 preview_asgi_app 启动的本地预览服务并释放端口。"
        "当用户不再需要预览、或想关闭正在运行的预览应用时调用；"
        "无运行中的预览时调用也安全。"
    ),
    "parameters": {"type": "object", "properties": {}},

}

INSTALL_SCHEMA = {
    "name": "install_library",
    "description": (
        "用宿主内置的 pip 在进程内安装第三方 Python 库到本机持久目录（.deps），"
        "无需用户机器装 Python，但需联网访问 PyPI（或镜像）。安装后该库可被 "
        "run_python / 预览导入使用。\n"
        "可选参数 dir：若传入应用目录，则安装后直接启动该应用的本地预览"
        "（等价于「安装并预览」）。\n"
        "注意：这仅是「运行时装库」（供预览/导入），并不会把用户程序冻结为可分发 "
        "EXE；要打包成独立 EXE 仍须在开发机用 PyInstaller 构建。\n"
        "用法示例：install_library(pkg='requests')；"
        "或 install_library(pkg='numpy', dir='output')。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "pkg": {"type": "string",
                    "description": "要安装的第三方库名，如 requests / numpy / pandas。"},
            "dir": {"type": "string",
                    "description": "可选。应用目录（相对项目根或绝对路径）；"
                                   "传入则安装后直接预览该应用。"},
        },
        "required": ["pkg"],
    },

}


# ============================================================================
# Handlers
# ============================================================================
def handle_preview_asgi_app(args: dict, **kwargs) -> str:
    d = _resolve_preview_dir(args.get("dir") or "output")
    res = _start_preview(d)
    if not res.get("ok"):
        if res.get("missing_module"):
            # 结构化失败：前端据此渲染「安装 X 并预览」按钮
            return tool_result(ok=False, missing_module=res["missing_module"],
                               dir=str(d), error=res.get("error"))
        return tool_error(res.get("error", "预览启动失败"))
    return tool_result(
        ok=True, url=res["url"], port=res["port"], dir=res["dir"],
        note="预览服务已启动。前端会自动弹出原生窗口预览；也可调用 stop_preview 关闭。",
    )


def handle_stop_preview(args: dict, **kwargs) -> str:
    res = stop_preview_internal()
    if not res.get("stopped"):
        return tool_result(ok=True, stopped=False, note="当前没有运行中的预览服务。")
    return tool_result(ok=True, stopped=True, port=res.get("port"),
                       note="预览服务已停止，端口已释放。")


def handle_install_library(args: dict, **kwargs) -> str:
    pkg = (args.get("pkg") or "").strip()
    if not pkg:
        return tool_error("缺少必填参数 pkg（要安装的第三方库名，如 requests）")
    deps_dir = get_deps_dir()
    inst = _run_pip_install(pkg, deps_dir)
    if not inst["ok"]:
        return tool_result(ok=False, pkg=pkg, error=inst["error"],
                           log=inst.get("log", ""), note="安装 %s 失败。" % pkg)
    ensure_deps_on_path()

    dir_raw = (args.get("dir") or "").strip()
    if not dir_raw:
        return tool_result(
            ok=True, pkg=pkg, dir=str(deps_dir),
            note="已安装 %s 到 %s（进程内 pip；需联网 PyPI）。" % (pkg, deps_dir),
        )
    # 「安装并预览」：装完直接起预览
    res = _start_preview(_resolve_preview_dir(dir_raw))
    if not res.get("ok"):
        return tool_result(ok=False, stage=res.get("stage"), installed=pkg,
                           error=res.get("error"),
                           missing_module=res.get("missing_module"),
                           note="安装 %s 成功但预览失败。" % pkg)
    return tool_result(ok=True, url=res["url"], port=res["port"], dir=res["dir"],
                       installed=pkg, note="已安装 %s 并启动预览。" % pkg)


# ============================================================================
# 注册入口
# ============================================================================
def register_into(registry) -> list[str]:
    """把宿主工具注册进 Hermes registry（归入 ``file`` 工具集，随其一并启用）。"""
    specs = [
        ("preview_asgi_app", PREVIEW_SCHEMA, handle_preview_asgi_app,
         "\U0001f52d", "在宿主内预览用户的 FastHTML/ASGI 应用"),
        ("stop_preview", STOP_PREVIEW_SCHEMA, handle_stop_preview,
         "\u23f9\ufe0f", "停止当前预览服务"),
        ("install_library", INSTALL_SCHEMA, handle_install_library,
         "\U0001f4e6", "用宿主内置 pip 安装第三方库到 .deps（可附 dir 安装并预览）"),
    ]
    for name, schema, handler, emoji, desc in specs:
        registry.register(
            name=name, toolset="file", schema=schema, handler=handler,
            is_async=False, description=desc, emoji=emoji,
            max_result_size_chars=MAX_TOOL_OUTPUT, override=True,
        )
    return [s[0] for s in specs]
