"""连接系统 main.py — 融合模式入口

职责：调 bridge.fuse_business_into_agent() 得到「Agent 对话 + 业务路由」融合 app，
用 uvicorn 启动（+ pywebview 原生窗口按需）。
连接系统本身不承载可独立执行的业务功能，只做装配与启动。
"""
import sys, os
from pathlib import Path

# 三系统目录入 sys.path
_base = Path(__file__).resolve().parent.parent
for _d in (_base, _base / "业务系统", _base / "连接系统"):
    _s = str(_d)
    if _s not in sys.path:
        sys.path.insert(0, _s)


# ── onefile 冻结模式：代码执行沙箱子进程分流 + 递归防护 ──
# Hermes 内核 tools.code_execution_tool 用 ``subprocess.Popen([sys.executable, script.py])``
# 派生沙箱子进程；冻结后 sys.executable 就是 EXE 本身，若不加守卫，子进程会重新走
# 启动逻辑拉起第二个 HTTP 服务并卡死（实测 EXE 启动后进程 3→191 指数增长、内存耗尽、
# 系统濒临崩溃）。此处统一拦截所有「把 EXE 当作 python 派生的 .py 子进程」以及
# 「继承环境的递归子进程」。
#
# 1) 代码执行沙箱子进程（HERMES_RPC_SOCKET 场景）：在本进程内直接执行该脚本后退出，
#    让父进程的 execute_code 正常收回 stdout/stderr。
if getattr(sys, "frozen", False) and len(sys.argv) >= 2 and os.path.isfile(sys.argv[1]):
    if "HERMES_RPC_SOCKET" in os.environ:
        _sandbox_script = sys.argv[1]
        try:
            with open(_sandbox_script, "r", encoding="utf-8") as _f:
                _sandbox_code = _f.read()
            exec(compile(_sandbox_code, _sandbox_script, "exec"), {"__name__": "__main__"})
        except SystemExit:
            raise
        except BaseException:
            import traceback as _tb
            _tb.print_exc()
            sys.exit(1)
        sys.exit(0)
    # 2) 其他把 EXE 当作 python 派生的 .py 子进程：一律退出，防止递归
    else:
        print("[guard] 检测到 EXE 被派生为脚本子进程（argv=%s），退出" % sys.argv[1:], file=sys.stderr)
        sys.exit(0)

# ── onefile 冻结模式：递归/多实例熔断器 ───────────────────────────
# 若 EXE 在某条未识别链路中被当作解释器反复派生，这些子进程会继承 RD_MAIN_PID
# 环境变量；RD_MAIN_PID 存在且不等于当前进程，说明本进程是递归/重复派生的子进程，
# 直接退出，避免再次进入启动逻辑造成进程爆炸。
# 注：execute_code 沙箱子进程的环境会被 _scrub_child_env 清掉 RD_MAIN_PID，因此
# 不会被本熔断器误伤（其已被上方守卫 1 拦截）。
if getattr(sys, "frozen", False):
    _rd_main = os.environ.get("RD_MAIN_PID")
    if _rd_main is not None and _rd_main != str(os.getpid()):
        print("[guard] 检测到递归子进程（主实例 pid=%s），本进程退出" % _rd_main, file=sys.stderr)
        sys.exit(0)
    os.environ["RD_MAIN_PID"] = str(os.getpid())

def start() -> None:
    import uvicorn
    from bridge import fuse_business_into_agent

    app = fuse_business_into_agent()
    if app is None:
        raise RuntimeError("融合装配失败且无回退 app")

    PORT = int(os.environ.get("PORT", 0)) or 8800
    print(f"[连接系统] 融合模式启动：http://127.0.0.1:{PORT}/dashboard  （Agent 对话 /）")
    uvicorn.run(app, host="127.0.0.1", port=PORT)


if __name__ == "__main__":
    start()
