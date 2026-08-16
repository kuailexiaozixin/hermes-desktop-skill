"""
launcher.py — 自包含桌面壳（pywebview），**不依赖任何其它技能**。

职责：后台拉起 FastHTML 服务（main.py 的 app）→ 打开一个桌面窗口指向 localhost →
窗口关闭即退出。打包时以本文件为入口产单文件 EXE（见 build.py）。

运行依赖自举：首次运行（源码态）会在
    D:/临时环境/hermes-desktop-01
创建隔离 venv（--system-site-packages，绝不降级用户全局包），并安装
hermes-agent[web] 等运行依赖，再以该 venv 重入本脚本。冻结（EXE）态跳过此步
（依赖已随包打包进 <exe>/hermes_data 旁）。

环境要求：
    - Windows 需已安装 WebView2 Runtime（Edge 内置，一般已带；缺失则报错见 troubleshooting.md）。
    - 依赖见 requirements.txt（hermes-agent / fasthtml / pywebview / markdown / uvicorn）。
"""
from __future__ import annotations

import os
import sys

# 清除 可能冲突的环境变量，避免 SRE 版本冲突（该变量指向不同 Python 版本的标准库）
os.environ.pop("PYTHONHOME", None)

# ============================================================================
# 隔离 venv 自举（仅源码运行态；冻结态依赖已打包，直接跳过）
# ============================================================================
# hermes-agent 及其固定依赖（如 openai==2.24.0）可能与用户全局环境冲突，故收纳进
# 建在示例目录「之外」的隔离 venv，沿用铁律「外置隔离环境」：不降级全局 site-packages、
# 不污染技能目录。venv 以当前 python 为基（即 启动.bat 所用的、已带 fasthtml 的解释器），
# 借 --system-site-packages 继承 fasthtml/pywebview/markdown/uvicorn，仅 hermes-agent
# 及其专属依赖落入 venv，对用户其余 Python 项目零影响。
# ---------------------------------------------------------------------------
# 配置驱动（标准交付物 launcher.json）
# launcher.json 与本文件同目录；缺失或字段缺失时回退到下方硬编码默认值，
# 保证「无 launcher.json 也能跑」（向后兼容、零风险）。
# ---------------------------------------------------------------------------
def _load_config() -> dict:
    """读取同目录 launcher.json；不存在 / 解析失败 / 非 dict 均返回空 dict（用默认值）。"""
    import json as _json
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.json")
        with open(p, "r", encoding="utf-8") as _f:
            data = _json.load(_f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


_CONFIG = _load_config()

_DEFAULT_REQUIREMENTS = [
    "hermes-agent[web]==0.19.0",
    "python-fasthtml",
    "pywebview",
    "markdown",
    "uvicorn",
]

_VENV_NAME = _CONFIG.get("venv_name", "hermes-desktop-01")
# 仅把与全局环境冲突的 hermes-agent 装进 venv；fasthtml/pywebview/markdown/uvicorn
# 等已由 --system-site-packages 从全局继承（注意 PyPI 名是 python-fasthtml，不是
# fasthtml；误写 fasthtml 会让 pip 找不到分发而整体失败）。若全局缺失这些包，下面
# 的 python-fasthtml 等会兜底装进 venv，保证 venv 自洽。
_REQUIREMENTS = _CONFIG.get("requirements", _DEFAULT_REQUIREMENTS)


def _bootstrap_venv() -> None:
    if getattr(sys, "frozen", False):
        return  # 冻结态：依赖已打包进 EXE，无需 venv
    if os.environ.get("HERMES_DESKTOP_REEXEC") == "1":
        return  # 已在 venv 内，避免重入死循环
    import hashlib as _hl
    import subprocess as _sp
    import venv as _venv

    # venv 已迁移至 D:\临时环境（原 %LOCALAPPDATA%\hermes-desktop\venvs）。
    # 可用 HERMES_DESKTOP_VENV_HOME 环境变量覆盖根目录。
    venv_home = os.environ.get("HERMES_DESKTOP_VENV_HOME", r"D:\临时环境")
    venv_dir = os.path.join(venv_home, _VENV_NAME)
    venv_py = os.path.join(venv_dir, "Scripts", "python.exe")

    if not os.path.exists(venv_py):
        os.makedirs(venv_dir, exist_ok=True)
        print(f"[启动] 创建隔离 venv：{venv_dir}")
        _venv.create(venv_dir, with_pip=True, system_site_packages=True)

    # 指纹：依赖集合变化才重装，避免每次启动都触发 pip
    blob = "\n".join(_REQUIREMENTS)
    fp = _hl.md5(blob.encode("utf-8")).hexdigest()
    fp_file = os.path.join(venv_dir, ".reqs.md5")
    _need_install = True
    try:
        if os.path.exists(fp_file) and open(fp_file, "r", encoding="utf-8").read().strip() == fp:
            _need_install = False
    except Exception:
        _need_install = True
    if _need_install:
        print("[启动] 安装运行依赖（hermes-agent 等）…（首次较慢，请稍候）")
        _sp.call([venv_py, "-m", "pip", "install", "--upgrade", "pip"])
        rc = _sp.call([venv_py, "-m", "pip", "install", *_REQUIREMENTS])
        if rc != 0:
            print("❌ 依赖安装失败（请检查网络后重试）。", file=sys.stderr)
            sys.exit(rc)
        try:
            with open(fp_file, "w", encoding="utf-8") as _f:
                _f.write(fp)
        except Exception:
            pass

    # 重入：用 venv 解释器重新跑本脚本（subprocess.call + sys.exit，禁用 os.execv）
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)  # 清除 可能冲突的环境变量，避免 SRE 版本冲突
    env["HERMES_DESKTOP_REEXEC"] = "1"
    rc = _sp.call([venv_py, *sys.argv], env=env)
    sys.exit(rc)


_bootstrap_venv()

import socket
import threading
import time
import webbrowser
from contextlib import closing

# 冻结态（PyInstaller）：HERMES_HOME 必须在任何 hermes 导入前指向可写路径
if getattr(sys, "frozen", False):
    os.environ.setdefault(
        "HERMES_HOME",
        os.path.join(os.path.dirname(sys.executable), "hermes_data"),
    )

import uvicorn
import webview

HOST = _CONFIG.get("host", "127.0.0.1")
PORT = int(_CONFIG.get("port", 5001))
APP_NAME = _CONFIG.get("app_name", "Hermes Desktop")
_WIN = _CONFIG.get("window", {}) or {}
WIN_W = int(_WIN.get("width", 920))
WIN_H = int(_WIN.get("height", 700))


def _wait_port(host: str, port: int, timeout: float = 20) -> bool:
    """等本地服务起来（避免窗口打开时服务还没 ready）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.3)
    return False


def _serve() -> None:
    """在后台线程跑 FastHTML 服务（延迟导入，保持与业务解耦）。"""
    from main import app

    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def main() -> int:
    server = threading.Thread(target=_serve, daemon=True)
    server.start()

    if not _wait_port(HOST, PORT):
        print("❌ 本地服务启动失败（端口 %d 未就绪）" % PORT, file=sys.stderr)
        return 1

    try:
        webview.create_window(
            APP_NAME,
            f"http://{HOST}:{PORT}",
            width=WIN_W,
            height=WIN_H,
        )
        webview.start()
    except Exception as e:  # WebView2 缺失等
        print(f"⚠️ pywebview 启动失败（{e}），回退到默认浏览器。", file=sys.stderr)
        webbrowser.open(f"http://{HOST}:{PORT}")
        # 浏览器模式下保持进程存活直到用户手动结束
        try:
            while server.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
