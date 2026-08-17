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
