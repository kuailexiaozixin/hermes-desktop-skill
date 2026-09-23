# example01 架构与边界（Architecture）

> 本文件声明 `01-hermes-desktop` 的模块划分与**依赖边界**，防止未来回归。
> 依据《example01 独立性/耦合度批判报告》执行（尤其建议 1/2/3/6/8）后沉淀。

## 1. 三层边界

本示例把代码分为 **业务层 / 适配层 / 内核层** 三层，依赖只能自上而下：

```
┌─────────────────────────────────────────────────────────────────────┐
│  业务层（Business）                                                    │
│  routes/* 、hermes_features 、hermes_config 、hermes_skills_client 、  │
│  unified_skills_client 、mcpstore_client 、skillhub_client 、sessions、│
│  wiki_engine 、context_provider 、memory_providers 、cron_scheduler 、 │
│  app_tools/* 、file_tools 、host_tools 、file_preview 、channels/* 、  │
│  frameworks/*                                                         │
└───────────────┬─────────────────────────────────────────────────────┘
                │  只依赖：适配层接口 / 同层模块 / 共享状态(app_state) / server.app
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  适配层（Adapter / Anti-Corruption）                                   │
│  hermes_adapter.py  —— 唯一允许 import Hermes 内部 API 的薄封装         │
│  agent_runtime.py  —— 集成内核：Agent 工厂 / 流式 / 审批 / 工具集        │
│                       （内部经 hermes_adapter 访问 Hermes）             │
└───────────────┬─────────────────────────────────────────────────────┘
                │  只依赖：Hermes Library（run_agent / tools / agent / plugins）
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  内核层（Hermes Library，第三方）                                       │
│  run_agent.AIAgent 、tools.* 、agent.* 、plugins.* 、cron.*            │
└─────────────────────────────────────────────────────────────────────┘
```

**边界规则**：
1. **业务层不得直接 `import run_agent / tools.* / agent.* / plugins.*`**；对 Hermes 内部 API
   的访问一律经 `hermes_adapter`（或由 `agent_runtime` 这个集成内核间接提供）。
2. `agent_runtime` 是唯一「集成内核」，可访问 Hermes；其内部对 AIAgent 构建 / tools.registry /
   agent.* / plugins.* 的调用应收敛到 `hermes_adapter`（见 §4 进展）。
3. 升级 `hermes-agent` 时，优先只改 `hermes_adapter` 与 `agent_runtime`，业务层不动。

## 2. 模块职责与依赖

| 层 | 模块 | 职责 | 主要依赖 |
|----|------|------|---------|
| 入口/服务 | `main.py` / `launcher.py` | 纯服务 / 桌面壳入口 | `server` |
| 服务 | `server.py` | FastHTML `app` 创建与挂载（静态资源/middleware/js-errors/热重载/serve_only），触发路由注册 | fasthtml, `routes` |
| 路由 | `routes/*.py` | HTTP/SSE 路由定义（显式 import 依赖，无命名空间总线） | `server.app`, `routes._helpers`, 业务模块 |
| 路由工具 | `routes/_helpers.py` | 路由层共享小工具（_ok/_err/_guard/render_markdown/cron 历史） | 标准库 |
| 共享状态 | `app_state.py` | 全局单例 `bridge` 集中持有 + 状态快照 + 所有权清单 | `channels` |
| 适配层 | `hermes_adapter.py` | Hermes 内部 API 防腐层（AIAgent 构建/tools.registry/agent.*/plugins.*） | `run_agent` 等（仅此处） |
| 集成内核 | `agent_runtime.py` | Agent 工厂 / 流式桥接 / 审批 / 工具集 | `hermes_adapter`, Hermes |
| 业务能力 | `hermes_features.py` 等 | Goals/MOA/快照等 13 项能力、配置、技能市场、会话、Wiki、记忆、定时任务 | 适配层/同层 |
| 渠道 | `channels/*` | IM 桥（Telegram/Slack/飞书…） | `app_state.bridge` |
| 框架 | `frameworks/*` | 循环 / 委派 / 原生指令 | 适配层 |
| 测试 | `tests/`, `test_bridge.py` | 单元/结构测试 + 离线桥接自测 | 各模块 |

## 3. 关键设计决策（防回归）

- **无命名空间总线**：`routes` 包不再 re-export 业务符号；子模块显式 `from server import app` /
  `from ._helpers import ...` / `import agent_runtime as ar`。
- **app 单一所有权**：`server.py` 创建 `app`；`routes` 只 `from server import app, APP_TITLE`（re-export 兼容旧引用），不创建。
- **循环导入纪律**：`server.py` **先创建 app，再 `import routes`** 触发注册；`routes` 不得 `from server import serve_only`（serve_only 由 main/launcher 从 server 导入）。
- **全局单例唯一登记处**：新增全局可变对象必须在 `app_state.py` 登记所有权与锁。
- **Hermes 访问唯一入口**：新代码如需 Hermes 内部 API，一律经 `hermes_adapter`。

## 4. 防腐层进展（对照批判报告建议 3）

- ✅ `hermes_adapter.py` 已建立，封装：AIAgent 构建（`create_agent`/`get_agent_class`）、
  `tools.registry`（registry/discover/invalidate/tool_error/tool_result）、`tools.*`（delegate/code_exec/browser/mcp/kanban）、
  `agent.*`（prompt_builder/models_dev/context_compressor/auxiliary_client/skill_bundles/learning_*）、
  `plugins.*`（context_engine/memory/holographic）。
- ✅ `agent_runtime.py` 的 3 处 AIAgent 构建已收敛到 `hermes_adapter.create_agent`；能力探测用 `get_agent_class`。
- ⏳ 其余业务模块（context_provider/memory_providers/hermes_features/hermes_skills_client 等）对
  Hermes 内部 API 的调用可继续迁移到适配层（建议在升级 hermes-agent 时随版本同步迁移，降低一次性回归风险）。
