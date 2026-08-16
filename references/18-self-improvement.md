---
title: 自进化 / 学习循环设计理念（Self-Improvement）
summary: Hermes Agent 区别于其它框架的根性设计——内置学习循环：从经验沉淀记忆与技能、consent-aware 写审批、运行越久越强；含 GUI 集成落地要点。
related: ["references/01-library-api.md", "references/13-agent-modules.md", "references/02-integration-core.md"]
---

# 18 · 自进化 / 学习循环设计理念（Self-Improvement）

> Hermes 官方定位：**"The self-improving AI agent … The only agent with a built-in learning loop — it creates skills from experience, improves them during use, nudges itself to persist knowledge."**
> 对外 slogan：**"The agent that grows with you"**（不是工具，是同事）。

本节是技能的**理念主题文档**，讲「为什么这样设计、机制如何运转、GUI 集成时如何暴露与配合」；
**API 层面**（`memory` 工具、`skill_manage` 工具、memory provider）见 `01-library-api.md` / `13-agent-modules.md`。

---

## 1. 核心问题：AI 失忆症（The Amnesia Problem）

LLM 助手在**会话之间遗忘一切**，能力无法随时间累积。Hermes 用「持久记忆 + 技能沉淀」解决：
**记忆**存小型持久事实（应常驻上下文），**技能**存较长流程（按需加载）——二者协同形成学习闭环。

## 2. 内置学习循环（consent-aware learning loop）

后台自我改进按**计数器**触发，fork 出一个审查 agent（独立 prompt cache，不影响主会话）：

| 触发条件 | 动作 |
|---------|------|
| **每 10 次用户提示** | fork 审查对话 → 决定是否写入**记忆** |
| **每 10 次工具迭代**（同一轮内） | fork 审查 → 决定是否**创建/改进技能** |

```yaml
# config.yaml（相关配置）
display:
  memory_notifications: on      # off | on(默认) | verbose  —— 聊天里显示 💾 Memory updated
memory:
  write_approval: true          # true 时写入先暂存，经 /memory pending → approve/reject 人工审查
```

**consent-aware（用户知情同意）** 是核心理念：学习不是偷偷发生的——默认有通知，可开写审批门让
每次写入都经人工确认；后台审查 fork 与主会话完全隔离。

## 3. 记忆架构（持久记忆）

- **存储**：`~/.hermes/memories/`（`MEMORY.md` / `USER.md`），独立 provider 可扩展（见 `01-library-api` / `13-agent-modules` 的 memory provider）。
- **注入**：会话开始时把记忆作为**冻结快照**注入 system prompt；无 `read` 动作——agent 天然看到记忆。
- **自管理**：agent 用 `memory` 工具 `add / replace / remove`。
- **预取**：每轮前**后台非阻塞预取**相关记忆（与上下文压缩、用量遥测同属 `agent` 运行时）。

## 4. 技能自主沉淀（agent 何时创建技能）

官方时机：成功完成复杂任务（**5+ 工具调用**）、遇到错误/死路后找到可行路径、用户纠正其方法、发现非平凡工作流。

`skill_manage` 动作：`create / patch（推荐，token 高效）/ edit / delete / write_file / remove_file`。
存于 `~/.hermes/skills/`，需定期维护防窄重复技能污染目录（浪费 token）。

## 5. 运维理念：越用越强 vs 可控可回滚

- **profile 隔离**：每 profile 独立 `config.yaml / .env / SOUL.md / memories / skills / sessions / state.db`，可跑多个分工 agent 互不污染。
- **备份/导出**：`hermes backup` / `hermes profile export` 完整打包（含记忆技能，历史会话单独）。
- **容器不可变核心**：托管镜像中 `/opt/hermes` 核心源码不可变，自我改进只作用于 `/opt/data` 数据层；核心改动走 PR 发版。
- **并发约束**：勿让两个进程/容器指向同一数据目录（会话与记忆存储不支持并发写）。

## 6. GUI 集成落地要点（对接 example01）

把「学习循环」暴露进桌面应用，让用户看到并可控：

1. **学习循环状态区**（可放记忆管理面板 / 上下文面板）：
   - 最近一次记忆更新（时间 + 摘要，对应 `memory_notifications`）
   - 技能沉淀计数（最近创建/patched 的技能名）
   - 写审批待审队列（`write_approval` 时的 pending 条目）
2. **写审批接入现有审批闭环**：Hermes 记忆/技能写入审批可映射到 example01 已实现的 `/api/approve` 弹窗闭环，统一「危险/持久写入」审批体验。
3. **记忆/技能可视化**：复用 `memory_providers.py`（provider 切换/向量检索/分层）与 `skills` 面板，展示「冻结快照注入内容」与「技能目录」。
4. **配置面**：`hermes_config.py` 暴露 `display.memory_notifications`、`memory.write_approval` 等配置项。

## 7. 与既有 reference 的导航

| 想查什么 | 去 |
|---------|----|
| `memory` / `skill_manage` 工具的 API | `01-library-api.md` |
| `agent` 包记忆/上下文压缩深主题（类·方法） | `13-agent-modules.md` |
| 给 Agent 接业务记忆/流程（非侵入扩展面） | `02-integration-core.md` |
| 理念与机制（本节） | **本文件 18-self-improvement.md** |

> 一句话：**把 Hermes 的自进化当作「会积累的数字同事」来集成，而不是当作无状态 API 来调用。**
