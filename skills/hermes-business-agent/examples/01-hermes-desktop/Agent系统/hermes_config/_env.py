from __future__ import annotations

import copy
import json
import os
import re
import shutil
import sys
import threading
from pathlib import Path

from ._paths import get_hermes_home



# ── .env 读写（作用域限定在示例 HERMES_HOME，不触碰真实 ~/.hermes）────────
# 对齐真实 hermes_cli.config.get_env_value / save_env_value 的落盘位置：
# 插件 requires_env 声明的变量最终由 Hermes 从 HERMES_HOME/.env 读取。
def get_env_value(name: str, home: Path | None = None) -> str | None:
    """读取 <HERMES_HOME>/.env 中某个变量的值（dotenv 风格，忽略注释与空行）。"""
    p = (home or get_hermes_home()) / ".env"
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        if k.strip() == name:
            return v.strip().strip('"').strip("'")
    return None


def set_env_value(name: str, value: str, home: Path | None = None) -> None:
    """把某个变量写入 <HERMES_HOME>/.env（已存在则更新，不存在则追加）。"""
    name = str(name).strip()
    if not name:
        raise ValueError("环境变量名不能为空")
    p = (home or get_hermes_home()) / ".env"
    lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    out, replaced = [], False
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s and s.partition("=")[0].strip() == name:
            out.append(f"{name}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{name}={value}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
