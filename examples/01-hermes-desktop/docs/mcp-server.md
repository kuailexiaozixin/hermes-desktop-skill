# Hermes 作为 MCP 服务器（让外部程序连接本应用）

> 本文件是「MCP 客户端 vs MCP 服务器」中**服务器**一侧的准确说明，供学习与本桌面应用扩展参考。
> 内容均来自对真实 `hermes_agent` 源码（`mcp_serve.py`、`agent/transports/hermes_tools_mcp_server.py`）
> 与 `hermes-llms-full.txt` 的实证，非臆测。

## 一句话区分

- **MCP 客户端**（本应用提供了客户端管理界面）：本应用去**连接**外部的 MCP 工具服务器，把别人的工具拿来用。本应用实现了「浏览目录 / 一键安装 / 启用停用 / 编辑移除」的管理界面，并在内嵌的 AIAgent 会话启动时读取 `config.yaml` 的 `mcp_servers` 去连接；连接动作由 AIAgent 在会话内完成，本应用自身不维持常驻的客户端连接进程。
- **MCP 服务器**（本文件讲的就是它）：本应用**被**外部程序连接，把自己的能力暴露出去给人家用。

## Hermes 的两种 MCP 服务器形态

经源码实证，Hermes Library 可作为 MCP 服务器，有**两种形态，且都是独立进程、走 stdio 协议**（不是 HTTP、不是进程内）：

### 形态一：会话桥接服务器（conversation bridge）

- 启动命令：`hermes mcp serve`（主 `hermes` CLI 子命令；需安装 `mcp` 包，`-v` 可查看版本与工具列表）
- 源码：`mcp_serve.py` 的 `create_mcp_server()` / `run_mcp_server()`
- 它把本应用的**会话 / 消息 / 审批**作为 MCP 工具暴露给外部客户端（Claude Code、Cursor、Codex 等）。
- 暴露的 10 个工具：

  | 工具 | 作用 |
  | --- | --- |
  | `conversations_list` | 列出各平台的会话 |
  | `conversation_get` | 查看单个会话详情 |
  | `messages_read` | 读取历史消息 |
  | `attachments_fetch` | 列出某条消息的附件 |
  | `events_poll` | 轮询新事件（消息 / 审批请求 / 审批结果） |
  | `events_wait` | 长轮询等待下一个事件 |
  | `messages_send` | 向某平台会话发送消息（`platform:chat_id` 格式） |
  | `channels_list` | 列出可发送消息的频道与目标 |
  | `permissions_list_open` | 列出待处理的审批请求 |
  | `permissions_respond` | 响应审批（allow-once / allow-always / deny） |

- 数据来源：读取 **HERMES_HOME** 的会话数据库 / 频道目录（与本桌面应用是**同一份数据**）。
- 依赖：需安装 `mcp` 包（`pip install 'mcp'`），缺失时给出明确报错而非静默失效。

### 形态二：工具面服务器（tool surface）

- 启动命令：`python -m agent.transports.hermes_tools_mcp_server`
- 源码：`agent/transports/hermes_tools_mcp_server.py` 的 `_build_server()` / `main()`
- 它把 **Hermes 自身的工具**经 stdio 暴露给一个被子进程（主要为 **Codex 集成**：当 Codex 接管主循环时，经此把 Hermes 更丰富的工具面带给 Codex）。
- 暴露的是**精选子集**（而非全部），例如：
  `web_search`、`web_extract`、`browser_navigate/_click/_type/_snapshot/...`、`vision_analyze`、
  `image_generate`、`skill_view`、`skills_list`、`text_to_speech`、`kanban_*`。
- **刻意不暴露**：`terminal` / `read_file` / `write_file` / `patch` / `search_files`（这些由 Codex 自己的内置覆盖）；
  以及 `delegate_task` / `memory` / `session_search` / `todo`（这些需要运行中的 AIAgent 上下文，无状态回调无法驱动）。
- 依赖：同样需 `mcp` 包。

## 外部客户端怎么连（以会话桥接为例）

在外部客户端（如 Claude Desktop 的 `claude_desktop_config.json`）里配置：

```json
{
  "mcpServers": {
    "hermes": {
      "command": "hermes",
      "args": ["mcp", "serve"]
    }
  }
}
```

客户端启动后会拉起 `hermes mcp serve` 这个独立进程，通过 stdio 与本应用（同一 HERMES_HOME）互通。

## 与本桌面应用架构的关系（重要，避免误用）

本桌面应用（示例 01）采用「进程内集成」形态：**不起第二个进程、不起 gateway、不开 API Server**。

因此：

1. **本应用自身不内嵌 MCP 服务器。** 上面的两种服务器都是**独立进程**，需要你**单独运行**对应命令。
2. **数据是互通的。** 服务器进程读的是同一个 HERMES_HOME 数据目录，所以它与本桌面应用看到的是同一批会话/消息。
3. **`out-of-scope` ≠ `forbidden`。** 本示例不内嵌 MCP 服务器，是因为其当前为单进程形态；但 Hermes 作为 MCP 服务器本身是官方支持的、真实存在的能力，你想用时单独跑命令即可。
4. **安全提示。** MCP 服务器会把工具暴露给连接它的客户端，且本示例为本地单进程运行、无额外网络鉴权边界，请只在可信环境使用。

## 本应用提供的只读信息接口

为方便查看状态，本应用提供了一个**只读**接口（不内嵌服务器，只做信息展示）：

- `GET /api/mcp-server/info`
  - 返回 `mcp_available`（当前环境是否装了 `mcp` 包）、两种服务器的启动命令、客户端配置片段、设计边界说明与安提示。
  - 用途：在设置/调试时确认「能不能跑 MCP 服务器」「该用什么命令」。

## 本应用提供的应用托管接口（启动 / 停止 / 探活）

除只读信息外，本应用还可在前端「MCP 服务器」面板**一键托管启动/停止工具面 MCP 服务器**并对其做 initialize 探活，用于本地自检与验证。托管实例的 stdio 归本应用所有，仅供本机探活/演示；外部客户端（mcporter / VS Code / Claude Code 等）各自独立 spawn 新进程，与本实例共享同一 HERMES_HOME，互不冲突。

- `GET /api/mcp-server/status`
  - 返回 `running`（各形态托管进程：pid / running / started_at）、`python_ready`（是否找到含工具面模块的 python）、`python`、`hermes_home`。
- `POST /api/mcp-server/start`（body `{"kind":"tool_surface"}`）
  - 托管启动**工具面** MCP 服务器子进程（`python -m agent.transports.hermes_tools_mcp_server`，`-u` 无缓冲，env 带 `HERMES_HOME` + 正确 `PYTHONHOME`）。会话桥接形态当前发行版不可用，仅支持工具面。
- `POST /api/mcp-server/stop`（body `{"kind":"tool_surface"}`）
  - 终止托管子进程（terminate → kill → taskkill 兜底）。
- `POST /api/mcp-server/probe`（body `{"kind":"tool_surface"}`）
  - 对运行中的托管进程发送 MCP initialize 探活，返回 `server_info`（如 `hermes-tools v1.29.0`）与 `protocolVersion`。

> 托管仅用于验证命令可用、进程可起、initialize 握手成功；真正让外部程序连接时，仍请各客户端按 `info` 返回的命令自行 spawn（共享同一数据目录）。
