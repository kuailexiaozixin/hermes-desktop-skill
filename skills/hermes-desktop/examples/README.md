# 示例 / Examples

本目录是 `hermes-desktop` 技能的**可运行参考实现**。每个子目录都是一个独立、可直接运行的
桌面/Web 应用示例，演示将 Hermes Agent 接入不同界面范式的技术路线与可复用的设计模式。
三个示例覆盖三种主流形态：**通用桌面底座（进程内集成）→ 多智能体桌面客户端（pywebview）→
官方 Web UI（FastAPI + vanilla JS）**，由浅入深展示了「进程内 Library 集成」与「外部服务对接」两条主线。

每个示例都附有**「可借鉴要点」**——做你自己的 Hermes 集成时，能直接从该示例里抠走的零件。

| 示例 | 形态 | 技术路线 | 运行期依赖 | 入口 |
|------|------|----------|-----------|------|
| [`01-hermes-desktop/`](01-hermes-desktop/) | 桌面 / 服务 | **进程内集成 Hermes Python Library**，FastHTML 服务端渲染 + pywebview 原生窗口 | `hermes-agent[web]` / `python-fasthtml` / `pywebview` / `uvicorn` 等 | `python main.py`（服务模式 :5001）或 `python launcher.py`（桌面窗口） |
| [`02-hermes-pywebview-multiagent/`](02-hermes-pywebview-multiagent/) | 桌面 | pywebview 原生窗口 + 单文件 `app.py` + 静态 HTML/JS 前端（苹果风格 UI） | `pywebview` + OpenAI 兼容库 | `python app.py`（pywebview 桌面窗口） |
| [`03-nesquena-hermes-webui/`](03-nesquena-hermes-webui/) | Web | FastAPI 后端 + 原生 vanilla JS 前端，三栏布局，无构建步骤 | FastAPI 生态（见其 `requirements.txt`） | `python server.py` 或 `start-webui.bat`（:8787） |

---

## 如何选择

| 你的目标 | 选哪个 |
|---------|--------|
| 想要**最全的通用底座**，把任意业务系统接上 Hermes（工具/技能/MCP/渠道/审批全齐），并作为可复制模板 | **01-hermes-desktop** |
| 想要**多智能体协作 + 可视化 Skill Store** 的桌面客户端体验（PM 自动分解任务、委派给专家） | **02-hermes-pywebview-multiagent** |
| 想要**与官方 Hermes CLI 完全对齐的轻量 Web UI**（三栏、会话/工作区、token 用量环） | **03-nesquena-hermes-webui** |

三条路线并不互斥：01 是「进程内直跑」的完整范式，02/03 是「外部服务/多智能体」的轻量补充，
可交叉参考其前端交互与后端对接方式。

---

## `01-hermes-desktop/` — Hermes Desktop 通用底座（进程内集成完整范式）

一个**标准、通用的 Hermes Desktop 底座**，演示在桌面应用中**进程内集成 Hermes Python Library** 的完整范式：
对标官方 Hermes Desktop 桌面体验，把桌面 AI 助手的通用能力全搬了过来，业务彻底解耦、自包含可运行。
详见 [`01-hermes-desktop/README.md`](01-hermes-desktop/README.md)（另有英文版 `README.en.md`）。

**可借鉴要点：**

- **进程内集成内核**：`agent_runtime.py` 的 `build_agent / stream_agent_chat / 审批`——不起 gateway / 独立 HTTP 服务 / Node，直接在进程内 `AIAgent(...)` 集成，SSE 逐字流式桥接。
- **FastHTML 服务端渲染路由层**：`main.py` 页面外壳 + `/api/*` 端点 + SSE 桥接，`routes/` 子包按功能拆（chat / skills / features / misc…）。
- **配置面统一**：`hermes_config.py` 管模型（36 厂商预设）/ 技能 / MCP / 定时任务 / HERMES_HOME 播种。
- **大一统技能市场**：`unified_skills_client.py` 聚合 8 个技能来源（SkillHub / skills.sh / clawhub / lobehub / browse-sh / 官方 / GitHub / Claude）。
- **LLM Wiki 三层互联知识库**：`wiki_engine.py` 反向链接 + 自动索引 + 图谱。
- **IM 渠道桥接**：`channels/` 10 个连接器（微信/企微/钉钉/飞书/QQ/Slack/Discord/Telegram/Webhook）+ 二维码登录。
- **补充功能 × 13 + 循环/委派/定时 + 审批闭环**：`hermes_features.py` / `frameworks/`，目标拆分给子智能体、危险命令弹窗确认。
- **上下文与记忆管理**：`context_provider.py`（`context.engine` 选择 + 压缩状态 + token 跟踪）、`memory_providers.py`（provider 切换 + 向量检索 + 分层查看）。
- **业务扩展点**：`app_tools/` 挂业务工具（默认带 `sogou_weixin.py` 演示工具，删一行即回纯底座）。
- **打包**：`build.py` PyInstaller 单文件 EXE；`launcher.py` pywebview 桌面壳。

---

## `02-hermes-pywebview-multiagent/` — Hermes Agent Desktop（多智能体协作客户端）

把 Hermes Agent 变成**一支 20 人 AI 团队**的桌面客户端：Project Manager 自动理解需求、分解任务、
委派给专家智能体、汇总交付物。Apple 风格原生桌面，零 Electron 膨胀，支持任意 OpenAI 兼容 LLM。
详见 [`02-hermes-pywebview-multiagent/README.md`](02-hermes-pywebview-multiagent/README.md)。

**可借鉴要点：**

- **多智能体编排范式**：Project Manager 作为编排者，自动把「搭一个电商平台」分解成子任务，委派给
  Product Manager / UI Designer / 3 工程师 / QA / Architect / DevOps 等 20 个角色，实时汇报进度并合成结果。
- **单文件应用架构**：整个后端在 `app.py` 一个文件（pywebview 桥 + SSE + 会话管理），前端 `index.html` 静态加载，结构极简。
- **可视化 Skill Store**：从 CocoLoop Skill Hub 精选 50+ 技能，前端商店一键安装 + 模糊搜索 + 分类标签，演示「技能市场」前端交互。
- **Agent CRUD 看板**：创建/编辑/删除自定义智能体（可配 system prompt / 模型 / 技能标签），实时状态。
- **SSE 流式 + 工具调用折叠**：逐 token 渲染 + 多智能体分区 + 工具卡片自动折叠。
- **原生桌面体验**：pywebview 原生窗口 + 原生文件夹选择器 + 一键模型切换 + Apple 风格灰色卡片设计。

---

## `03-nesquena-hermes-webui/` — Hermes Web UI（官方 Web 界面）

官方 [Hermes Agent](https://hermes-agent.nousresearch.com/) 的轻量 Web 界面：暗色三栏布局（左侧会话导航、
中间聊天、右侧工作区文件浏览），与 CLI 体验完整对齐——终端能做的这里都能做。无构建步骤、无框架、无打包器，
纯 Python + vanilla JS。详见 [`03-nesquena-hermes-webui/README.md`](03-nesquena-hermes-webui/README.md)。

**可借鉴要点：**

- **三栏 Web UI 布局**：会话侧栏 + 聊天中心 + 工作区文件树；模型/Profile/工作区控制在**底部 composer 常驻**。
- **上下文用量环**：圆形 context ring 一眼看到 token 用量——「压缩状态可视化」的极简交互。
- **Hermes Control Center**：侧栏底部启动，聚合所有设置与会话工具。
- **FastAPI + 原生 JS 对接**：`api/` 下数十个按功能拆分的路由模块（会话生命周期 / 工作区 / 插件 / 认证 / 用量…），演示对 Hermes 外部服务 / 网关的完整对接面。
- **会话管理 + 导出 + 恢复**：会话发现、生命周期、恢复、HTML 导出等企业级细节。
- **认证与多端**：密码 / OIDC / passkey / 扩展 sidecar 认证，可多设备原生访问。
- **无构建前端**：vanilla JS + vendor 化（KaTeX / js-yaml / smd），可直接抠走复用。

---

## 参考技能

- 通用桌面底座的技术栈与打包细节见 `fasthtml-desktop` 技能（FastHTML + pywebview）。
- 若你做的是**原生 Tkinter** 桌面应用，见 `tkinter-desktop` 技能（其 `examples/` 有同款组织方式）。

## 许可证

各示例独立开源：`01`、`02`、`03` 均为 MIT（见各目录 `LICENSE`）。
