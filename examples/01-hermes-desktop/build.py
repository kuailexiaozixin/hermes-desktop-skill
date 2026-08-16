#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — Hermes Desktop 示例的单文件 EXE 打包脚本（最小 venv 配方）

配方要点（见 references/08-packaging.md）：
  * 用「外置隔离 venv」打包：建在 D:/临时环境/ 下（可用 FD_VENV_HOME 改），
    只装 requirements.txt + pyinstaller，**不污染系统全局 Python**（满足项目打包铁律）。
  * --onefile / --noupx / --console（调试可见错误；发布改 --windowed）。
  * Hermes / pywebview / fasthtml / uvicorn 的 hidden-import 逐个列，**禁 --collect-submodules tools**。
  * HERMES_HOME 在冻结态指向 <exe>/hermes_data（main.py / launcher.py 已处理）。

用法：
    python build.py                 # 自动建外置 venv + 打包
    python build.py --windowed      # 发布版（无控制台窗口）
    python build.py --skip-venv     # 假定当前环境已是最小 venv，直接打包
    FD_VENV_HOME="D:/my/venv" python build.py
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REQ = os.path.join(HERE, "requirements.txt")
ENTRY = "launcher.py"  # 桌面壳（拉起服务 + 窗口）作为打包入口

# 外置隔离 venv 位置（项目打包铁律：放示例目录之外）
DEFAULT_VENV_HOME = os.environ.get(
    "FD_VENV_HOME",
    r"D:\临时环境\hermes-desktop-01",
)
VENV_PY = os.path.join(
    DEFAULT_VENV_HOME,
    "Scripts" if os.name == "nt" else "bin",
    "python.exe" if os.name == "nt" else "python",
)


def _bootstrap_venv() -> str:
    """建外置最小 venv + 装依赖 + 装 pyinstaller；返回 venv 解释器路径。"""
    if not os.path.isdir(DEFAULT_VENV_HOME):
        print(f"[build] 建外置隔离 venv: {DEFAULT_VENV_HOME}")
        subprocess.check_call([sys.executable, "-m", "venv", DEFAULT_VENV_HOME])
    # 装运行依赖
    print("[build] 安装 requirements.txt ...")
    subprocess.check_call([VENV_PY, "-m", "pip", "install", "-q", "-r", REQ])
    # 装构建期工具（不进运行时依赖）
    print("[build] 安装 pyinstaller ...")
    subprocess.check_call([VENV_PY, "-m", "pip", "install", "-q", "pyinstaller"])
    return VENV_PY


def _have_pyinstaller(py: str) -> bool:
    try:
        subprocess.check_call(
            [py, "-c", "import PyInstaller"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def build(windowed: bool = False, skip_venv: bool = False) -> int:
    if skip_venv:
        py = sys.executable
    else:
        # 若当前解释器没有 pyinstaller，先建外置 venv 并重入
        if not _have_pyinstaller(sys.executable):
            venv_py = _bootstrap_venv()
            # 重入：用 venv 解释器跑本脚本（带 --skip-venv 避免死循环）
            cmd = [venv_py, __file__, "--skip-venv"]
            if windowed:
                cmd.append("--windowed")
            return subprocess.call(cmd)
        py = sys.executable

    # ---- PyInstaller 参数 ----
    args = [
        os.path.join(HERE, ENTRY),
        "--onefile",
        "--name", "HermesDesktop",
        "--noupx",
        "--clean",
        "--distpath", os.path.join(HERE, "dist"),
        "--workpath", os.path.join(HERE, "build"),
    ]
    args += ["--windowed" if windowed else "--console"]

    # ---- 进程内路线用不到的网关/终端子模块（少拉少膨胀）----
    hermes_top = [
        "run_agent", "agent", "agent.agent_init", "agent.conversation_loop",
        "tools", "toolsets", "toolset_distributions", "hermes_constants",
        "hermes_state", "hermes_logging", "hermes_time", "hermes_bootstrap",
        "hermes_cli", "providers", "model_tools", "plugins", "utils",
    ]
    # 实际常用 toolset 子集（逐个列，禁止 --collect-submodules tools）
    hermes_tools = [
        "tools.file_tools", "tools.web_tools", "tools.memory_tools",
        "tools.code_execution", "tools.browser_tools", "tools.mcp_tools",
        "tools.skills_tools",
        # 以下为本示例进程内代码懒导入的子模块（top-level `tools`/`hermes_cli`
        # 不会自动带出它们，漏列会导致冻结 EXE 在调用对应功能时 ModuleNotFoundError）：
        "tools.registry",        # discover_toolsets / register_pure_python_tools
        "tools.kanban_tools",    # 内置循环 kanban 按需执行
        "tools.delegate_tool",   # 子任务委派
        "hermes_cli.commands",   # 原生指令注册表（/api/commands）
    ]
    pywebview_mods = [
        "webview", "webview.platforms.winforms", "webview.platforms.edgechromium",
        "clr",
    ]
    gui_mods = [
        "fasthtml", "uvicorn", "uvicorn.logging", "uvicorn.loops",
        "uvicorn.loops.auto", "uvicorn.protocols", "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto", "uvicorn.server",
        "starlette", "itsdangerous", "markupsafe", "click",
    ]
    for m in hermes_top + hermes_tools + pywebview_mods + gui_mods:
        args += ["--hidden-import", m]

    # ---- 数据 / 二进制 ----
    args += ["--collect-data", "certifi"]
    args += ["--collect-data", "webview"]   # 打包 webview/lib（WebView2 相关）

    print(f"[build] 运行 PyInstaller（入口 {ENTRY}，解释器 {py}）...")
    return subprocess.call([py, "-m", "PyInstaller.__main__", *args])


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Hermes Desktop 单文件 EXE 打包")
    ap.add_argument("--windowed", action="store_true", help="发布版（无控制台）")
    ap.add_argument("--skip-venv", action="store_true", help="当前已是最小 venv，直接打包")
    a = ap.parse_args()
    return build(windowed=a.windowed, skip_venv=a.skip_venv)


if __name__ == "__main__":
    sys.exit(main())
