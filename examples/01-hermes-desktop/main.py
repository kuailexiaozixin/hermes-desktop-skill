"""main.py — 入口（路由注册在 routes/ 包）"""
from __future__ import annotations

# 冻结态 HERMES_HOME 必须在任何导入前设置
import os, sys
if getattr(sys, "frozen", False):
    os.environ.setdefault(
        "HERMES_HOME",
        os.path.join(os.path.dirname(sys.executable), "hermes_data"),
    )

from routes import app, serve_only  # noqa: E402

if __name__ == "__main__":
    serve_only()
