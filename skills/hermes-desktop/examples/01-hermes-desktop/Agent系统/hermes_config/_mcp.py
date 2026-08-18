from __future__ import annotations

import copy
import json
import os
import re
import shutil
import sys
import threading
from pathlib import Path

from ._paths import _write_config_yaml_full, get_hermes_home, read_config_yaml, update_config_yaml



# ============================================================================
# 6) MCP servers
# ============================================================================
def list_mcp_servers(home: Path | None = None) -> dict:
    """返回 config.yaml 中 mcp_servers 的完整视图（只读）。

    原样透传每条服务器的定义（stdio 传输的 command/args/env，或 HTTP/SSE
    传输的 url/headers/auth 等），仅补一个 ``enabled`` 默认值，供设置中心
    展示与 tools.mcp_tool.register_mcp_servers 直接消费。
    """
    servers = read_config_yaml(home).get("mcp_servers") or {}
    out: dict = {}
    for name, definition in servers.items():
        d = dict(definition) if isinstance(definition, dict) else {}
        d.setdefault("enabled", True)
        out[str(name)] = d
    return out


def upsert_mcp_server(name: str, definition: dict, home: Path | None = None) -> dict:
    """新增/更新一个 MCP 服务器定义并写回 config.yaml（通用持久化）。

    原样保留整条定义（stdio 传输的 command/args/env，或 HTTP/SSE 传输的
    url/headers/auth/connect_timeout 等），不再强制要求 command——
    远程 HTTP/SSE 服务器只有 url。至少需提供 command 或 url 之一；env 与
    headers 保持为字典。
    """
    h = home or get_hermes_home()
    name = (name or "").strip()
    if not name:
        raise ValueError("MCP 服务器名称不能为空")
    d = dict(definition or {})
    entry: dict = {}
    for k, v in d.items():
        if k == "env" and isinstance(v, dict):
            env = {str(kk): str(vv) for kk, vv in v.items() if str(kk).strip()}
            if env:
                entry["env"] = env
        elif k == "args" and isinstance(v, (list, tuple)):
            entry["args"] = [str(a) for a in v]
        elif k == "enabled":
            if v is False:
                entry["enabled"] = False
        elif k == "headers" and isinstance(v, dict):
            headers = {str(kk): str(vv) for kk, vv in v.items() if str(kk).strip()}
            if headers:
                entry["headers"] = headers
        else:
            entry[k] = v
    if not entry.get("command") and not entry.get("url"):
        raise ValueError("MCP 服务器必须提供 command 或 url 之一")
    servers = dict(read_config_yaml(h).get("mcp_servers") or {})
    servers[name] = entry
    update_config_yaml(h, {"mcp_servers": servers})
    return dict(entry)


def remove_mcp_server(name: str, home: Path | None = None) -> bool:
    """删除 MCP 服务器（深合并无法表达删除，故整体重写 mcp_servers）。"""
    h = home or get_hermes_home()
    cfg = read_config_yaml(h)
    servers = dict(cfg.get("mcp_servers") or {})
    if name not in servers:
        return False
    servers.pop(name)
    cfg["mcp_servers"] = servers
    _write_config_yaml_full(h, cfg)
    return True


def set_mcp_enabled(name: str, enabled: bool, home: Path | None = None) -> bool:
    h = home or get_hermes_home()
    cfg = read_config_yaml(h)
    servers = dict(cfg.get("mcp_servers") or {})
    if name not in servers:
        return False
    entry = dict(servers[name]) if isinstance(servers[name], dict) else {}
    if enabled:
        entry.pop("enabled", None)
    else:
        entry["enabled"] = False
    servers[name] = entry
    cfg["mcp_servers"] = servers
    _write_config_yaml_full(h, cfg)
    return True


def trigger_mcp_discovery() -> None:
    """后台连接本示例已启用的 MCP 服务器（stdio / SSE / HTTP）。

    复用 Hermes 真实库的 ``tools.mcp_tool.register_mcp_servers``，与进程内
    AIAgent 共用同一全局工具注册表；这样默认启用全部工具集的 Agent 就能看到
    MCP 工具。失败静默处理，不阻断主流程（例如未安装 mcp SDK 时直接跳过）。
    """
    try:
        import threading
        from tools.mcp_tool import register_mcp_servers
    except Exception:
        return

    def _run() -> None:
        try:
            servers = list_mcp_servers() or {}
            enabled = {
                n: dict(d)
                for n, d in servers.items()
                if isinstance(d, dict) and d.get("enabled", True)
            }
            if enabled:
                register_mcp_servers(enabled)
        except Exception:
            pass

    threading.Thread(target=_run, name="example-mcp-discovery", daemon=True).start()
