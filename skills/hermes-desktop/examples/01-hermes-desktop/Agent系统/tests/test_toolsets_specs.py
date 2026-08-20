"""test_toolsets_specs.py — 方案 A 重构的持久回归护栏（离线、无网络、无 LLM）。

断言组：
  S1  Spec 表完备性：30 个工具集全登记，label/purpose/分类合法；
  S2  诊断路径完备：凡声明 env 的工具集必有 probe_env 或 probe_fn
      （防 FAL_KEY 式「配置项存在但探测分支漏掉」回归）；
  S3  TRIAL 生成：27 个试用条目键集合固定；多工具模板连接词正确；
      未登记工具集走通用兜底句；
  S4  兼容视图形状：labels=30 键 / categories=29 键（sogou_weixin 走默认分类）
      / env=14 键，与重构前基线一致；
  S5  状态一致性：面板启用态与 build_agent 实际生效态等价
      （config.yaml 单一事实源，读侧验证、不写配置）。

用法：python tests/test_toolsets_specs.py（退出码 0=全过 / 1=失败）
     或 pytest tests/test_toolsets_specs.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_runtime._toolset_specs import (  # noqa: E402
    TOOLSET_SPECS, CATEGORY_ORDER, ToolsetSpec,
    TOOLSET_LABELS, TOOLSET_CATEGORIES, TOOLSET_RUNTIME_HINTS, ENV_REQUIRED,
    TRIAL_FORCE, TRIAL_PROMPTS,
    build_trial_force, build_trial_prompt, get_spec,
)

EXPECTED_NAMES = {
    "file", "code_execution", "memory", "skills", "browser", "browser-cdp",
    "web", "x_search", "session_search", "sogou_weixin", "vision", "image_gen",
    "video_gen", "video", "tts", "computer_use", "cronjob", "todo", "kanban",
    "project", "delegation", "clarify", "feishu_doc", "feishu_drive", "discord",
    "discord_admin", "homeassistant", "hermes-yuanbao", "terminal", "spotify",
}
EXPECTED_TRIAL_KEYS = {
    "web", "x_search", "image_gen", "file", "code_execution", "browser",
    "browser-cdp", "memory", "todo", "vision", "video_gen", "tts",
    "computer_use", "cronjob", "kanban", "delegation", "discord", "feishu_doc",
    "session_search", "clarify", "discord_admin", "feishu_drive",
    "hermes-yuanbao", "homeassistant", "project", "skills", "video",
}
EXPECTED_ENV_KEYS = {
    "browser-cdp", "image_gen", "video_gen", "tts", "x_search", "spotify",
    "homeassistant", "hermes-yuanbao", "discord", "discord_admin",
    "feishu_doc", "feishu_drive", "web", "vision",
}


def test_s1_spec_completeness():
    assert set(TOOLSET_SPECS.keys()) == EXPECTED_NAMES, \
        "Spec 表工具集名单与基线不符：%r" % (set(TOOLSET_SPECS.keys()) ^ EXPECTED_NAMES,)
    cat_set = set(CATEGORY_ORDER)
    for name, spec in TOOLSET_SPECS.items():
        assert isinstance(spec, ToolsetSpec)
        assert spec.label, f"{name}: label 为空"
        assert spec.purpose, f"{name}: purpose 为空"
        assert spec.category in cat_set, f"{name}: 分类 {spec.category!r} 未登记"


def test_s2_diagnostic_path_for_env_specs():
    """凡声明 env 的工具集必须有诊断路径（probe_env 或 probe_fn）。"""
    for name, spec in TOOLSET_SPECS.items():
        if spec.env:
            assert spec.probe_env or spec.probe_fn, \
                f"{name}: 声明了 env 但无 probe_env/probe_fn（诊断路径缺失）"
    # env 探测型三件套：probe_env 必须覆盖全部 env 变量（FAL_KEY 回归专项）
    for name in ("image_gen", "video_gen", "tts"):
        spec = TOOLSET_SPECS[name]
        probe_vars = {es.var for es in spec.probe_env}
        assert set(spec.env) <= probe_vars, \
            f"{name}: probe_env 未覆盖全部 env: 缺 {set(spec.env) - probe_vars}"


def test_s3_trial_generation():
    assert set(TRIAL_FORCE.keys()) == EXPECTED_TRIAL_KEYS, \
        "TRIAL_FORCE 键集合漂移：%r" % (set(TRIAL_FORCE.keys()) ^ EXPECTED_TRIAL_KEYS,)
    assert set(TRIAL_PROMPTS.keys()) == EXPECTED_TRIAL_KEYS
    # 多工具模板连接词
    assert " write_file 和 read_file " in TRIAL_FORCE["file"]
    assert "web_search 或 web_extract" in TRIAL_FORCE["web"]
    assert "run_python 或 run_javascript" in TRIAL_FORCE["code_execution"]
    # 单工具模板
    assert "browser-cdp 工具集中的 browser_cdp 工具" in TRIAL_FORCE["browser-cdp"]
    # 兜底句（未登记工具集）
    fb = build_trial_force("not_exists_toolset")
    assert fb == "你必须使用【not_exists_toolset】工具集中的工具来完成以下任务，不要使用其他工具集。"
    assert build_trial_prompt("not_exists_toolset") == \
        "请使用与【not_exists_toolset】相关的工具完成一个最小任务，并说明执行结果。"
    # 强制指令格式守卫：全部条目含「不要使用其他工具集」收束语
    for name, txt in TRIAL_FORCE.items():
        assert txt.endswith("不要使用其他工具集。"), f"{name}: 强制指令缺收束语"


def test_s4_compat_view_shapes():
    assert set(TOOLSET_LABELS.keys()) == EXPECTED_NAMES  # 30 键
    # categories：sogou_weixin 走默认分类不入表（与基线一致，discover 侧 .get 兜底）
    assert set(TOOLSET_CATEGORIES.keys()) == EXPECTED_NAMES - {"sogou_weixin"}
    assert set(ENV_REQUIRED.keys()) == EXPECTED_ENV_KEYS  # 14 键
    # hints 只含非空项；terminal/sogou_weixin 无提示
    assert "terminal" not in TOOLSET_RUNTIME_HINTS
    assert "sogou_weixin" not in TOOLSET_RUNTIME_HINTS
    assert all(v for v in TOOLSET_RUNTIME_HINTS.values())


def test_s5_panel_vs_agent_consistency():
    """面板启用态 == build_agent 实际生效态（config 单一事实源）。"""
    from agent_runtime._tools import _resolve_disabled_toolsets, DISABLED_TOOLSETS
    from hermes_config import get_hermes_home, read_config_yaml

    agent_cfg = (read_config_yaml(get_hermes_home()).get("agent", {}) or {})
    cfg_user_disabled = set(agent_cfg.get("disabled_toolsets") or [])

    effective = set(_resolve_disabled_toolsets(web_search=True))
    expected = set(DISABLED_TOOLSETS) | cfg_user_disabled
    assert effective == expected, \
        "一致性断言失败: agent=%r expected=%r" % (sorted(effective), sorted(expected))
    # web_search=False 时额外禁用 web/browser（原语义保持）
    effective_offline = set(_resolve_disabled_toolsets(web_search=False))
    assert effective_offline == expected | {"web", "browser"}


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("[PASS]", name)
        except AssertionError as e:
            failed += 1
            print("[FAIL]", name, "-", e)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("[ERROR]", name, "-", f"{type(e).__name__}: {e}")
    print("-" * 50)
    print("总计 %d 项，失败 %d 项" % (len(tests), failed))
    sys.exit(1 if failed else 0)
