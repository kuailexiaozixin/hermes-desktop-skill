# mcp_serve — MCP 服务

> **模块**: `mcp_serve.py`
> **来源**: 本机已装 `hermes-agent 0.19.0` 源码（ast 静态解析，未 import）
> **说明**: 将 Hermes 暴露为 MCP 服务器的实现。

## 模块文档

Hermes MCP Server — expose messaging conversations as MCP tools.

Starts a stdio MCP server that lets any MCP client (Claude Code, Cursor, Codex,
etc.) list conversations, read message history, send messages, poll for live
events, and manage approval requests across all connected platforms.

Matches OpenClaw's 9-tool MCP channel bridge surface:
  conversations_list, conversation_get, messages_read, attachments_fetch,
  events_poll, events_wait, messages_send, permissions_list_open,
  permissions_respond

Plus: channels_list (Hermes-specific extra)

Usage:
    hermes mcp serve
    hermes mcp serve --verbose

MCP client config (e.g. claude_desktop_config.json):
    {
        "mcpServers": {
            "hermes": {
                "command": "hermes",
                "args": ["mcp", "serve"]
            }
        }
    }

### 模块文档

Hermes MCP Server — expose messaging conversations as MCP tools.

Starts a stdio MCP server that lets any MCP client (Claude Code, Cursor, Codex,
etc.) list conversations, read message history, send messages, poll for live
events, and manage approval requests across all connected platforms.

Matches OpenClaw's 9-tool MCP channel bridge surface:
  conversations_list, conversation_get, messages_read, attachments_fetch,
  events_poll, events_wait, messages_send, permissions_list_open,
  permissions_respond

Plus: channels_list (Hermes-specific extra)

Usage:
    hermes mcp serve
    hermes mcp serve --verbose

MCP client config (e.g. claude_desktop_config.json):
    {
        "mcpServers": {
            "hermes": {
                "command": "hermes",
                "args": ["mcp", "serve"]
            }
        }
    }

### class QueueEvent

> 继承: `object` ｜ 方法数: 0（公开 0）

An event in the bridge's in-memory queue.


### class EventBridge

> 继承: `object` ｜ 方法数: 10（公开 6）

Background poller that watches SessionDB for new messages and
maintains an in-memory event queue with waiter support.

This is the Hermes equivalent of OpenClaw's WebSocket gateway bridge.
Instead of WebSocket events, we poll the SQLite database for changes.

#### def `__init__()`

#### def `start(self)`

Start the background polling thread.

#### def `stop(self)`

Stop the background polling thread.

#### def `poll_events(self, after_cursor: int = 0, session_key: Optional[str] = None, limit: int = 20) -> dict`

Return events since after_cursor, optionally filtered by session_key.

#### def `wait_for_event(self, after_cursor: int = 0, session_key: Optional[str] = None, timeout_ms: int = 30000) -> Optional[dict]`

Block until a matching event arrives or timeout expires.

#### def `list_pending_approvals(self) -> List[dict]`

List approval requests observed during this bridge session.

#### def `respond_to_approval(self, approval_id: str, decision: str) -> dict`

Resolve a pending approval (best-effort without gateway IPC).


### 顶层函数

#### def `create_mcp_server(event_bridge: Optional[EventBridge] = None) -> FastMCP`

Create and return the Hermes MCP server with all tools registered.

**异常**: `ImportError`

#### def `run_mcp_server(verbose: bool = False) -> None`

Start the Hermes MCP server on stdio.

