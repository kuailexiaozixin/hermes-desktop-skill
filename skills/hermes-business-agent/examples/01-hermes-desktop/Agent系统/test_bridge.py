#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_bridge.py — 离线桥接测试（注入 FakeAIAgent，无需 hermes-agent / API Key）。

验证 `agent_runtime.stream_agent_chat` 的「进程内 AIAgent → SSE 字节流」桥接契约：
注入 FakeAIAgent（模拟 AIAgent 的 stream_callback 与构造器回调），断言产出的事件流
包含 delta / reasoning / action / action_result / done，且无 error。

设计要点：
  * FakeAIAgent 只依赖 agent_runtime 暴露的 factory 契约：
        factory(model_cfg, max_iterations=..., ephemeral_system_prompt=...,
                tool_start_callback=..., tool_complete_callback=...,
                reasoning_callback=..., tool_progress_callback=..., web_search=...)
        agent.run_conversation(user_message=..., system_message=...,
                               conversation_history=..., stream_callback=...) -> dict
  * 不 import run_agent / 不联网 / 不触发真实 LLM——结构级、确定性、可重复。
  * 作为 quality_check 的 [3] 离线桥接测试门禁（scripts/quality_check.py step_bridge）。

退出码：0 = 全部通过；1 = 有失败。
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agent_runtime  # noqa: E402

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  OK   {name}" + (f"  ({detail})" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL {name}" + (f"  ({detail})" if detail else ""))


class FakeAIAgent:
    """离线假 AIAgent：记录回调，按桥接契约模拟一次流式对话与工具事件。"""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.tool_start_cb = kwargs.get("tool_start_callback")
        self.tool_complete_cb = kwargs.get("tool_complete_callback")
        self.reasoning_cb = kwargs.get("reasoning_callback")
        self.tool_progress_cb = kwargs.get("tool_progress_callback")

    def run_conversation(self, **kw):
        stream_cb = kw.get("stream_callback")
        if self.reasoning_cb:
            self.reasoning_cb("thinking step one")
        if self.tool_start_cb:
            self.tool_start_cb("t1", "browse", "https://example.com")
        if self.tool_progress_cb:
            self.tool_progress_cb("moa.reference", "label", "text", None)
        if stream_cb:
            stream_cb("Hello ")
            stream_cb("World")
        if self.tool_complete_cb:
            self.tool_complete_cb("t1", "browse", "https://example.com", {"ok": True})
        return {
            "final_response": "Hello World",
            "messages": [{"role": "assistant", "content": "Hello World"}],
        }


def parse_sse(blob: bytes):
    """把 SSE 字节流（data: {json}\\n\\n）解析成 dict 列表。"""
    events = []
    for block in blob.decode("utf-8", "replace").split("\n\n"):
        block = block.strip()
        if not block:
            continue
        data = None
        for line in block.splitlines():
            if line.startswith("data:"):
                data = line[5:].strip()
        if data:
            try:
                events.append(json.loads(data))
            except Exception:
                pass
    return events


def test_bridge():
    global PASS, FAIL
    print("=" * 56)
    print(" 离线桥接测试 (test_bridge / FakeAIAgent)")
    print("=" * 56)

    def _fake_factory(model_cfg, **kw):
        # stream_agent_chat 以 `factory(model_cfg, ...)` 调用（model_cfg 为位置参数）
        return FakeAIAgent(model_cfg=model_cfg, **kw)
    factory = _fake_factory
    messages = [{"role": "user", "content": "hi"}]

    chunks = []
    try:
        for chunk in agent_runtime.stream_agent_chat(
                messages, {}, agent_factory=factory, timeout=30):
            chunks.append(chunk)
    except Exception as e:  # noqa: BLE001
        check("stream_agent_chat 不抛异常", False, f"{type(e).__name__}: {e}")
        return

    blob = b"".join(chunks)
    check("产出 SSE 字节", bool(blob))
    parsed = parse_sse(blob)
    check("事件流非空", len(parsed) > 0, f"{len(parsed)} 事件")

    # 事件类型计数
    counts = {}
    for ev in parsed:
        if "choices" in ev and ev["choices"]:
            counts["delta"] = counts.get("delta", 0) + 1
        else:
            t = ev.get("type", "?")
            counts[t] = counts.get(t, 0) + 1

    check("delta 事件", counts.get("delta", 0) >= 2, f"{counts.get('delta', 0)}")
    check("reasoning 事件", counts.get("reasoning", 0) > 0, f"{counts.get('reasoning', 0)}")
    check("action 事件", counts.get("action", 0) > 0, f"{counts.get('action', 0)}")
    check("action_result 事件", counts.get("action_result", 0) > 0, f"{counts.get('action_result', 0)}")
    check("done 事件", counts.get("done", 0) > 0, f"{counts.get('done', 0)}")
    check("无 error 事件", counts.get("error", 0) == 0, f"error={counts.get('error', 0)}")

    # done 事件契约：final + html + messages
    for ev in parsed:
        if ev.get("type") == "done":
            check("done.final == 'Hello World'", ev.get("final") == "Hello World", str(ev.get("final")))
            check("done.html 非空", bool(ev.get("html")))
            check("done.messages 为 list", isinstance(ev.get("messages"), list))
            break

    # 文本增量累积校验
    text = ""
    for ev in parsed:
        if "choices" in ev and ev["choices"]:
            d = ev["choices"][0].get("delta", {}) or {}
            c = d.get("content")
            if c:
                text += c
    check("增量文本含 'Hello World'", "Hello World" in text, text)


def main():
    test_bridge()
    print("-" * 56)
    print(f"RESULT: {PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
