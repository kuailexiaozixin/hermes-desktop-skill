"""frameworks 共享工具函数。

``_build_agent`` 和 ``_extract_json_list`` 被 loops.py 和 delegation.py 共用，
拆出为独立模块以避免循环导入与代码重复。
"""
from __future__ import annotations

import json
import re
from typing import Any


def _build_agent(*args, **kwargs):
    """延迟导入 build_agent，避免 frameworks ↔ agent_runtime 循环导入。"""
    from agent_runtime import build_agent
    return build_agent(*args, **kwargs)


def _extract_json_list(text: str) -> list[str]:
    """从 agent 输出中提取 JSON 数组（容错：去 ```json 围栏 / 取首个 [ ] 区间）。"""
    if not text:
        return []
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    m = re.search(r"\[.*\]", s, re.S)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return []
    if isinstance(arr, list):
        return [str(x).strip() for x in arr if str(x).strip()]
    return []