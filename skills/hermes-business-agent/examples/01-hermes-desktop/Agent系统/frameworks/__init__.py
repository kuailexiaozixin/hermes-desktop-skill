"""frameworks — Hermes 三大「上层框架」在 Library 模式下的落地

本模块把桌面端需要、但 Hermes Library 不直接暴露成品 API 的三块能力聚合在一起：

  Part 1  循环（Loops）        —— 8 大官方循环的本地化落地 + 用户自定义循环
  Part 2  子智能体委派         —— 原生 tools.delegate_tool 的桥接层与编排
  Part 3  原生斜杠指令         —— hermes_cli.commands 注册表的能力分类与服务端执行

诚实原则（贯穿全模块）
======================
桌面端是 Hermes 的 **Library 模式单进程构建**（进程内 AIAgent，无常驻 Gateway /
无 cron 守护 / 无消息平台），因此各能力的真实状态各不相同，UI 必须如实标注，
绝不虚报「全部支持」。凡是本构建确实做不到的（gateway_only 指令、TTY 交互指令、
周期守护调度），一律显式标注为不可用并说明原因，而不是假装成功。
"""
from __future__ import annotations

from ._utils import _build_agent, _extract_json_list


# ── 子模块导入与重导出 ───────────────────────────────────────────────────────
from . import loops, delegation, commands

# Part 1 — Loops
from .loops import (
    BUILTIN_LOOPS,
    STATUS_LABELS,
    get_loop_flags,
    save_builtin_loop_settings,
    list_custom_loops,
    upsert_custom_loop,
    delete_custom_loop,
    run_custom_loop,
    run_builtin_loop,
    get_run,
    is_builtin_runnable,
    get_loops_payload,
)

# Part 2 — Delegation
from .delegation import (
    DELEGATION_DEFAULTS,
    get_delegation_config,
    save_delegation_config,
    set_parent_model_cfg,
    set_parent_agent,
    run_delegation,
    run_delegation_async,
    list_native_subagents,
    list_delegations,
    get_delegation,
    cancel_delegation,
    restart_branch,
    restart_delegation,
)

# Part 3 — Commands
from .commands import (
    FRONTEND_COMMANDS,
    SERVER_COMMANDS,
    TERMINAL_BOUND,
    list_native_commands,
    native_command_count,
    parse_command,
    execute_command,
    classify_command,
)

__all__ = [
    # Loops
    "BUILTIN_LOOPS", "STATUS_LABELS",
    "get_loop_flags", "save_builtin_loop_settings",
    "list_custom_loops", "upsert_custom_loop", "delete_custom_loop",
    "run_custom_loop", "run_builtin_loop", "get_run", "is_builtin_runnable",
    "get_loops_payload",
    # Delegation
    "DELEGATION_DEFAULTS",
    "get_delegation_config", "save_delegation_config",
    "set_parent_model_cfg", "set_parent_agent",
    "run_delegation", "run_delegation_async",
    "list_native_subagents", "list_delegations", "get_delegation", "cancel_delegation",
    "restart_branch", "restart_delegation",
    # Commands
    "FRONTEND_COMMANDS", "SERVER_COMMANDS", "TERMINAL_BOUND",
    "list_native_commands", "native_command_count",
    "parse_command", "execute_command", "classify_command",
]