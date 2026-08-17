# -*- coding: utf-8 -*-
"""test_context_files_native.py — 验证 example 01 已对齐 Hermes 原生 context-files 特性。

覆盖（全部离线、无需 API key，使用 example01 自带 venv 的 hermes-agent）：
  1. build_agent 默认开启原生上下文文件：skip_context_files=False、load_soul_identity=True
     （此前错误地把 skip_context_files 绑在 goal loop 上，默认 True → 不开）。
  2. 给定工作目录（会话绑定文件夹）时，原生发现会扫到该目录下的 AGENTS.md / SOUL.md
     并注入系统提示（build_context_files_prompt 实跑 + agent._build_system_prompt 复验）。
  3. SOUL.md 来自 HERMES_HOME，与官方语义一致；且本示例 Soul 面板写入的文件会被 agent 加载。

运行：D:/临时环境/hermes-desktop-01/Scripts/python.exe -m pytest tests/test_context_files_native.py -q
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 隔离 HOME：绝不触碰真实数据
_TMP_HOME = tempfile.mkdtemp(prefix="ctx_native_home_")
os.environ["HERMES_DESKTOP_HOME"] = _TMP_HOME
os.environ["HERMES_HOME"] = _TMP_HOME
# 离线测试：hermes 在构造 AIAgent 时会校验 provider API key，但本测试只构建 agent 并
# 检查 _build_system_prompt（不发真实请求），故注入一个假 key 让构造通过即可。
os.environ.setdefault("DEEPSEEK_API_KEY", "dummy-for-offline-test")


def _agent_cfg():
    return {"vendor": "deepseek", "model": "deepseek-chat"}


def test_build_agent_enables_native_context_files_by_default():
    """默认配置下，原生上下文文件 + SOUL 必须开启（对照此前 skip_context_files=True 的 bug）。"""
    import agent_runtime as ar
    agent = ar.build_agent(_agent_cfg())
    # 关键断言：此前为 True（关闭），现应为 False（开启）
    assert agent.skip_context_files is False, "原生上下文文件应默认开启 (skip_context_files=False)"
    # SOUL 默认开启：此前为 False（Soul 面板形同虚设）
    assert agent.load_soul_identity is True, "SOUL 人格应默认加载 (load_soul_identity=True)"
    print("  test_build_agent_enables_native_context_files_by_default OK")


def test_working_dir_targets_user_project_and_injects():
    """把工作目录指向用户项目（含 AGENTS.md），原生发现应注入该文件与 SOUL.md。"""
    import agent_runtime as ar
    import agent.prompt_builder as pb

    # 用户项目：放一个 AGENTS.md
    proj = Path(tempfile.mkdtemp(prefix="ctx_proj_"))
    (proj / "AGENTS.md").write_text(
        "# 项目上下文\n这是一个用于测试的原生上下文文件。\n", encoding="utf-8")
    # HERMES_HOME 下的 SOUL.md（Soul 面板写入的位置）
    soul = Path(_TMP_HOME) / "SOUL.md"
    soul.write_text("你是测试助手，语气简洁。\n", encoding="utf-8")

    # build_agent 传入 working_dir → 内部设置 TERMINAL_CWD
    agent = ar.build_agent(_agent_cfg(), working_dir=str(proj))

    # 1) 库函数实跑：该目录下应发现 AGENTS.md，且 SOUL.md 一并注入
    injected = pb.build_context_files_prompt(cwd=str(proj)) or ""
    assert "AGENTS.md" in injected, "build_context_files_prompt 应发现 AGENTS.md"
    assert "Project Context" in injected, "注入文本应包含 # Project Context 段"
    assert "测试助手" in injected, "SOUL.md 内容应被注入"

    # 2) agent 自身系统提示构建应包含上述上下文（复验 example 01 接线）
    sp = agent._build_system_prompt("") or getattr(agent, "_cached_system_prompt", "") or ""
    assert "AGENTS.md" in sp, "agent._build_system_prompt 应含 AGENTS.md"
    assert "测试助手" in sp, "agent._build_system_prompt 应含 SOUL.md 内容"
    print("  test_working_dir_targets_user_project_and_injects OK")


def test_no_working_dir_falls_back_without_stale_env():
    """无绑定文件夹时回退启动目录，且不残留上次会话的 TERMINAL_CWD（防串味）。"""
    import agent_runtime as ar
    os.environ.pop("TERMINAL_CWD", None)
    agent = ar.build_agent(_agent_cfg(), working_dir=None)
    # 未显式设置 → 应已清理/未设置，避免复用上一条会话的目录
    assert "TERMINAL_CWD" not in os.environ, "无绑定时应清除 TERMINAL_CWD，避免串味"
    print("  test_no_working_dir_falls_back_without_stale_env OK")


if __name__ == "__main__":
    test_build_agent_enables_native_context_files_by_default()
    test_working_dir_targets_user_project_and_injects()
    test_no_working_dir_falls_back_without_stale_env()
    print("ALL NATIVE CONTEXT-FILES TESTS PASSED")
