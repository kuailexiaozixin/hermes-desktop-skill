"""工具清单（只读）——列出已注册到 Hermes registry 的全部工具。

对齐 Hermes Library 的 ``tools.registry`` 机制：
  - 每个工具由 ``registry.register(name, toolset, schema, handler, ...)`` 在模块导入期
    注册；``model_tools.get_tool_definitions`` / ``run_agent`` / 本示例的
    ``agent_runtime.register_pure_python_tools()`` 都从同一全局注册表取工具。
  - 本视图**只读取**已注册工具的元信息（name / toolset / description / 入参 schema /
    emoji / 是否异步 / 所需环境变量），并把它返回给前端渲染。

安全边界（与结构化输出面板同原则）：
  - 只读注册表元信息，**绝不执行 handler**、**绝不在返回里出现任何密钥**、
    **绝不写配置、绝不触碰 .hermes_data**。
  - 工具的 API 密钥由 Hermes 在进程内托管（config.yaml / 环境变量），本接口拿不到也
    不试图拿；``requires_env`` 只列出“需要哪些环境变量名”，不列出其值。
  - 异常经 ``_guard`` 包成 ``{ok:false, error:...}``，不 500。

来源区分（用于前端徽标）：
  - hermes_builtin：handler 来自 ``tools.*`` 命名空间（Hermes 内置工具集）；
  - example_injected：来自本示例的 ``file_tools`` / ``host_tools`` / ``app_tools``
    （宿主覆盖 + 业务扩展点，即“自定义工具”）；
  - other：来源无法判定的兜底（不影响功能，仅徽标中性）。
"""
from __future__ import annotations

from server import app
from ._helpers import _guard
import agent_runtime as ar


def _origin_of(handler) -> str:
    """根据 handler 的模块判定工具来源。"""
    h = getattr(handler, "__wrapped__", handler)
    mod = getattr(h, "__module__", "") or getattr(type(h), "__module__", "")
    top = (mod or "").split(".")[0]
    if top in ("file_tools", "host_tools", "app_tools"):
        return "example_injected"
    if (mod or "").startswith("tools."):
        return "hermes_builtin"
    return "other"


def _schema_summary(schema) -> dict:
    """把 Hermes 的 function schema 收敛为前端易渲染的结构。

    兼容两种写法：
      - 内层写法（registry 中实际存储）：{"name", "description", "parameters": {...}}
      - 外层写法（get_definitions 返回）：{"type":"function","function": {...}}
    """
    if not isinstance(schema, dict):
        return {"name": None, "description": "", "parameters": None}
    inner = schema
    if "function" in schema and isinstance(schema["function"], dict):
        inner = schema["function"]
    params = inner.get("parameters") or {}
    props = params.get("properties") or {}
    required = list(params.get("required") or [])
    fields = []
    for pname, pdef in props.items():
        if not isinstance(pdef, dict):
            pdef = {"type": "unknown", "description": ""}
        fields.append({
            "name": pname,
            "type": pdef.get("type", "string"),
            "description": pdef.get("description", ""),
            "required": pname in required,
        })
    return {
        "name": inner.get("name"),
        "description": inner.get("description", ""),
        "parameters": {
            "type": params.get("type", "object"),
            "fields": fields,
            "required": required,
        },
    }


def _build_catalog() -> dict:
    # 确保内置工具 + 宿主覆盖 + 业务扩展点都已注册进全局 registry（幂等）。
    ar.register_pure_python_tools()
    from tools.registry import registry

    items = []
    for name in registry.get_all_tool_names():
        entry = registry.get_entry(name)
        if entry is None:
            continue
        ssum = _schema_summary(entry.schema)
        items.append({
            "name": entry.name,
            "toolset": entry.toolset,
            "description": entry.description or ssum.get("description") or "",
            "emoji": entry.emoji or "",
            "is_async": bool(entry.is_async),
            "requires_env": list(entry.requires_env or []),
            "max_result_size_chars": entry.max_result_size_chars,
            "origin": _origin_of(entry.handler),
            "schema": ssum,
        })

    # 按 toolset 分组计数（供前端徽标 / 概览）
    by_toolset: dict[str, int] = {}
    for it in items:
        by_toolset[it["toolset"]] = by_toolset.get(it["toolset"], 0) + 1

    origin_counts = {
        "hermes_builtin": sum(1 for i in items if i["origin"] == "hermes_builtin"),
        "example_injected": sum(1 for i in items if i["origin"] == "example_injected"),
        "other": sum(1 for i in items if i["origin"] == "other"),
    }

    return {
        "ok": True,
        "count": len(items),
        "tools": items,
        "by_toolset": dict(sorted(by_toolset.items())),
        "origin_counts": origin_counts,
        "note": "密钥由 Hermes 在进程内托管，本接口仅读取注册表元信息，不返回任何密钥。",
    }


@app.get("/api/tools-catalog")
def api_tools_catalog():
    return _guard(_build_catalog)
