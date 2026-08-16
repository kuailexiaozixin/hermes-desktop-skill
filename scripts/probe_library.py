#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_library.py — 探测本机已装 Hermes Python Library 的健康状况（SKILL.md §5 步骤③）。

检查：Python 版本 ∈ [3.11, 3.14)、能否 import run_agent / AIAgent、版本号、
关键回调参数是否还在（防版本漂移静默失效）、max_iterations 默认值。

用法：
    python scripts/probe_library.py
    python scripts/probe_library.py --json

退出码：0 = 健康；1 = 有阻断性问题；2 = 环境问题。
"""
from __future__ import annotations

import argparse
import importlib.metadata as md
import inspect
import json
import sys


def probe() -> dict:
    info: dict = {
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "python_ok": (3, 11) <= sys.version_info[:3] < (3, 14),
        "importable": False,
        "version": None,
        "path": None,
        "error": None,
        "checks": {},
    }
    # Python 版本
    info["checks"]["python_in_range"] = info["python_ok"]

    # 导入
    try:
        import run_agent  # noqa: F401
        from run_agent import AIAgent

        info["importable"] = True
        info["path"] = getattr(run_agent, "__file__", None)
        try:
            info["version"] = md.version("hermes-agent")
        except Exception:
            info["version"] = None
    except Exception as e:
        info["error"] = f"{type(e).__name__}: {e}"
        info["checks"]["import_ok"] = False
        return info

    info["checks"]["import_ok"] = True

    # 关键 API 是否还在（防静默失效）
    try:
        params = inspect.signature(AIAgent.__init__).parameters
        rc = inspect.signature(AIAgent.run_conversation).parameters
        info["checks"]["has_tool_start_callback"] = "tool_start_callback" in params
        info["checks"]["has_reasoning_callback"] = "reasoning_callback" in params
        info["checks"]["has_event_callback"] = "event_callback" in params
        info["checks"]["has_stream_callback"] = "stream_callback" in rc
        try:
            info["max_iterations_default"] = params["max_iterations"].default
        except (KeyError, AttributeError):
            info["max_iterations_default"] = None
        # 15 个构造器回调应全部存在（stream_callback 在 run_conversation/chat 上单独校验）
        expected = {
            "tool_progress_callback", "tool_start_callback", "tool_complete_callback",
            "thinking_callback", "reasoning_callback", "clarify_callback",
            "read_terminal_callback", "step_callback", "stream_delta_callback",
            "interim_assistant_callback", "tool_gen_callback", "status_callback",
            "notice_callback", "notice_clear_callback", "event_callback",
        }
        missing = sorted(expected - set(params))
        info["checks"]["missing_callbacks"] = missing
        info["checks"]["all_15_callbacks_present"] = not missing
    except Exception as e:
        info["checks"]["signature_probe_error"] = f"{type(e).__name__}: {e}"

    return info


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="探测已装 Hermes Library")
    p.add_argument("--json", action="store_true", help="机器可读输出")
    args = p.parse_args(argv)

    info = probe()
    healthy = (
        info["python_ok"]
        and info["importable"]
        and info["checks"].get("all_15_callbacks_present", False)
        and info["checks"].get("has_stream_callback", False)
    )

    if args.json:
        out = dict(info)
        out["healthy"] = healthy
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"Python          : {info['python_version']} "
              f"{'✅' if info['python_ok'] else '❌ 需 3.11–3.13'}")
        print(f"import run_agent: "
              f"{'✅' if info['importable'] else '❌ ' + str(info['error'])}")
        if info["importable"]:
            print(f"版本            : {info['version']}")
            print(f"路径            : {info['path']}")
            c = info["checks"]
            print(f"tool_start_cb   : {'✅' if c.get('has_tool_start_callback') else '❌'}")
            print(f"reasoning_cb    : {'✅' if c.get('has_reasoning_callback') else '❌'}")
            print(f"event_cb        : {'✅' if c.get('has_event_callback') else '❌'}")
            print(f"stream_callback : {'✅' if c.get('has_stream_callback') else '❌'}")
            print(f"15 构造器回调齐全 : "
                  f"{'✅' if c.get('all_15_callbacks_present') else '❌ 缺 ' + str(c.get('missing_callbacks'))}")
            print(f"max_iterations  : {info.get('max_iterations_default')} "
                  f"(⚠️ 官方文档写 500，源码应为 90)")
        print("-" * 50)
        print("✅ 健康，可以开始集成" if healthy else "❌ 存在问题，先修复再开工")

    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
