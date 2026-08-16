"""
app_tools/ — 业务工具扩展点（Hermes Desktop 通用底座的唯一「加业务」入口）

本目录默认挂载一个演示工具 `sogou_weixin.py`（搜狗微信搜索），作为「如何挂业务工具」的可复制模板；删去下方 `register_into` 中那一行即回到纯底座、与业务完全解耦。
把本示例复制到自己的工程后，只需在这里实现 `register_into(registry)`，
`agent_runtime.register_pure_python_tools()` 就会在启动时自动调用它。

⚠️ 命名铁律：**绝不可**把本目录改名为 `tools/`。`tools` 是 hermes-agent 的**顶层包**
（tools.registry / tools.file_tools / tools.delegate_tool …），同名目录会遮蔽它，
导致 `from tools.registry import registry` 落到你的空包上，Agent 全部工具失效。

────────────────────────────────────────────────────────────────────────
最小示例：注册一个业务工具（进程内、零 subprocess、自定义 toolset）
────────────────────────────────────────────────────────────────────────

    import json

    MY_SCHEMA = {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "按订单号查询订单详情。",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    }

    def _handle_get_order(args: dict, **kwargs) -> str:
        from tools.registry import tool_error, tool_result
        oid = (args.get("order_id") or "").strip()
        if not oid:
            return tool_error("order_id is required")
        row = my_db.query(oid)          # 你的业务查询
        return tool_result(ok=True, order=row)

    def register_into(registry) -> list[str]:
        registry.register(
            name="get_order", toolset="my_biz", schema=MY_SCHEMA,
            handler=_handle_get_order, is_async=False,
            description="business tool: get_order", emoji="\U0001f9fe",
            max_result_size_chars=100_000, override=True,
        )
        return ["get_order"]

要点：
  * 注册进**自定义 toolset**（如 "my_biz"）即可——`registry` 会自动发现该 toolset，
    `get_tool_definitions(enabled_toolsets=None)` 的默认矩阵会纳入这些工具，
    设置中心「工具与集成」面板也会自动列出它。
  * handler 必须返回 **JSON 字符串**（用 `tool_result` / `tool_error` 构造）。
  * 想给工具集配中文名与用途，在 `agent_runtime.TOOLSET_LABELS` 里加一行即可。
"""
from __future__ import annotations


def register_into(registry) -> list[str]:
    """业务工具注册钩子。默认注册内置业务工具；返回本次注册的工具名列表。"""
    from app_tools import sogou_weixin

    registered: list[str] = []
    registered += sogou_weixin.register_into(registry)
    return registered
