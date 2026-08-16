# 路线选型 — 示例旗舰实现（from examples/01-hermes-desktop，已实测）

> 本文件从 `references/04-rendering-frameworks.md` 抽出：路线如何在该旗舰示例中**数据驱动 + 现成壳**落地。
> 属示例耦合内容，不进入技能核心骨干（核心骨干见 `references/04-rendering-frameworks.md` 的 §需求澄清 / §1–§4）。
>
> **范围澄清（重要）**：本文件的「路线选型」指的是**桌面 GUI 框架路线**（`templates/fasthtml_minimal` ↔ `templates/tkinter_minimal`，即 FastHTML / Tkinter），与「调用 Python Library 的 5 条技术路线」（进程内直跑 / Hermes 网关 / spawn CLI / API Server / `/v1`）是**两个正交维度**，互不影响：前者决定桌面窗口/界面用什么壳，后者决定 `AIAgent` 如何被调用。本技能中 5 条 Library 调用路线**平等可选、无先后顺序**（见 `SKILL.md` 定位与 `references/02-integration-core.md` §2 路径图）；本文件只谈 GUI 壳的选型，不暗示任何 Library 调用路线的优先或默认。

---

两条路线在本技能里**不是靠手写代码分叉**，而是靠"数据驱动 + 现成壳"落地：

## 5.1 配置驱动决定走哪条路线

`launcher.json` 是启动器的唯一数据源（节选，行号/字段以实际文件为准）：

```json
{
  "app_name": "你的应用",
  "entry": "main.py",            // 业务入口（FastHTML 服务 + 路由）
  "venv_name": "your-app-venv",  // 外置隔离 venv 名（见 10/11）
  "requirements": ["hermes-agent[web]==0.19.0", "python-fasthtml", "pywebview", "markdown", "uvicorn"],
  "host": "127.0.0.1",
  "port": 5001,
  "window": { "width": 920, "height": 700 }
}
```

`launcher.py` 读这份配置 → 决定用哪个 venv、哪个入口、哪个端口、开多大的窗口，
**不写死任何路线判断**。要换 GUI 框架只改配置 + 换 `templates/` 里的骨架。

## 5.2 两套最小骨架直接派生

`templates/` 下已内置两套**自包含最小骨架**，复制即用、互不依赖：

| 骨架 | 路线 | 关键文件 |
| --- | --- | --- |
| `templates/fasthtml_minimal/` | FastHTML + SSE（pywebview 壳由 launcher 提供） | `main.py` + `README.md` |
| `templates/tkinter_minimal/` | Tkinter（标准库窗口） | `main.py` + `README.md` |

两者都遵循同一套内核约定：`from run_agent import AIAgent` 进程内直跑、
冻结态 `HERMES_HOME` 守卫（`if getattr(sys, "frozen", False)` 下指 `<exe>/hermes_data`）、
`disabled_toolsets=["terminal"]`、`quiet_mode=True`。

## 5.3 选型不是一次性决定

需求澄清阶段定的路线，开发中途仍可切换：业务代码（`agent_runtime.py`、
自建工具、`operations.py`）与 GUI 壳解耦，换壳不碰内核。这也是为什么本技能
把"共享内核"（01/03/07）与"GUI 壳"（04-rendering-frameworks）分开成不同 reference 节点。
