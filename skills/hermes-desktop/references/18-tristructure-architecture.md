# 18 · 三系统解耦架构（高内聚低耦合的工程级落地）

> 本文件回答一个问题：**当业务是一个完整系统（需独立交付、长期演进、底座可整体替换）时，如何组织 Hermes 集成工程，使系统达到高内聚、低耦合。**
> 它把「高内聚低耦合」从**进程内分层**（§8 的 GUI/桥接/Agent 四层）提升到**工程组织层面**（三个独立系统），并进一步落到**各系统内部功能模块**。
> 适用前提：你的业务已超过"给单个桌面应用加个 AI 面板"的规模，需要独立的业务工程、可替换的 Agent 底座、明确的桥接层。
> 参考落地：`examples/01-hermes-desktop` 三系统骨架 + rd-expense-system 实践。

---

## 1. 为什么需要工程级分层

「单工程内嵌」范式（复制 `examples/01` → 在同一个工程里加业务 + Agent）适用于中小型应用。当业务演化成完整系统时，会出现：

- **业务与底座深度耦合**：业务代码 import 底座内部模块（`server`/`routes`/`agent_runtime`…），底座升级换代时业务被拖累，反之业务膨胀污染底座纯净性。
- **单一职责缺失**：一个工程同时是"业务系统"又是"Agent 系统"，职责不清、边界模糊、演进互相拖累。
- **无法独立演进/交付**：业务无法独立打包分发，Agent 底座无法整体替换，两者必须绑定发布。
- **模块内聚下降**：业务逻辑散落各处、copy-paste 泛滥、死代码堆积，难以维护。

**三系统解耦架构**针对上述问题，把工程拆成三个职责单一、依赖单向、接口稳定的独立系统：

| 系统 | 职责 | 关键约束 |
|---|---|---|
| **Agent系统** | 纯净 Hermes 底座（= `examples/01`，零差异） | 可整体替换；不含业务 |
| **业务系统** | 纯业务逻辑与界面，不依赖 Agent | 可独立运行/独立 EXE；不 `import` 任何 Agent 模块 |
| **连接系统** | 纯桥接，唯一装配耦合点 | 负责把业务挂到 Agent、注册工具、注入快照、安装技能 |

---

## 2. 高内聚低耦合的两层落地

### 2.1 系统间（宏观层）：依赖方向铁律

```
业务系统 ──► 连接系统 ──► Agent系统
   │            │            │
   │    (唯一装配耦合点)      │
   └──── 绝不直接 import Agent 模块 ──┘
```

- **单向依赖**：业务系统 → 连接系统 → Agent系统。**业务系统禁止 `import` Agent 系统任何模块**（`server`/`routes`/`agent_runtime`/`tools`/`hermes_config`…）。
- **连接系统是唯一装配点**：所有「业务 ↔ Agent」的桥接（挂业务路由、注册 rd 工具、注入业务快照、安装技能）全部收拢在连接系统的装配函数里（如 `fuse_business_into_agent()`）。
- **Agent系统可整体替换**：它是上游 `examples/01` 的纯净副本，无业务痕迹；升级底座只需「删除→复制→粘贴」三步，业务/连接不动。
- **稳定接口**：三个系统通过**明确的函数接口**协作，不依赖对方的内部实现细节：
  - 业务系统暴露纯业务接口：`build_app()`（自建 app）、`mount_rd_routes(app, rt)`（挂业务路由）、`get_business_snapshot()`（业务快照）。
  - 连接系统暴露装配接口：`fuse_business_into_agent()`（返回融合 app）。
  - Agent系统暴露底座接口：`server.app/rt`、`agent_runtime`、`tools.registry`、`routes.chat`。

### 2.2 系统内部模块间（微观层）：单一职责 + 模块内聚

高内聚低耦合不只存在于三大系统之间，更要求**每个系统内部的模块**同样遵循。三系统只是把内聚边界放大了，内部的模块设计原则不变：

- **单一职责**：一个模块只做一件事。路由模块（`routes_*.py`）只负责页面/接口，不塞 Agent 逻辑；桥接模块只负责装配。
- **模块分层**：GUI/渲染层、桥接层（callback→queue）、Agent 构造层、工具层、数据层分层清晰，不跨层调用。
- **共享抽取**：跨模块重复的辅助逻辑（下拉选项、统计块、表格渲染、端口探测等）抽到公共模块（`components.py`/`helpers.py`），**消除 copy-paste**。
- **禁止死代码**：未被引用的模块、函数、import 一律清理（用 `pyflakes`/`autoflake` 佐证），保持代码库洁净。
- **公共依赖归位**：Agent 使用的业务技能（SKILL）不放在业务系统，而归入连接系统，由连接系统在装配时安装给 Agent。
- **独立入口**：每个系统有自己的一键启动（`启动.bat`）和独立打包（EXE），互不依赖。

---

## 3. 三系统架构总览

```
                        ┌───────────────┐
                        │   业务系统     │  build_app() / mount_rd_routes() / get_business_snapshot()
                        │  (纯业务+UI)   │  独立 EXE、独立启动
                        └───────┬───────┘
                                │ 纯业务接口（不 import Agent）
                                ▼
                        ┌───────────────┐
                        │   连接系统     │  fuse_business_into_agent()
                        │  (纯桥接)     │  ├ 挂业务路由到 Agent app
                        │              │  ├ 注册 rd 工具到 tools.registry
                        │              │  ├ 注入业务快照到 routes.chat
                        │              │  └ 安装业务技能到 HERMES_HOME/skills
                        └───────┬───────┘
                                │ 稳定底座接口
                                ▼
                        ┌───────────────┐
                        │   Agent系统    │  server.app/rt · agent_runtime · tools.registry
                        │  (=01 纯净底座)│  = 上游 example01 零差异，可整体替换
                        └───────────────┘
```

**融合装配流程**（连接系统 `fuse_business_into_agent()`）：
1. 从 Agent系统导入 `server.app` / `server.rt`
2. 调业务系统 `mount_rd_routes(app, rt)` 把业务路由挂到 Agent app
3. 把业务 `get_business_snapshot` 设为 Agent 底座 `routes.chat` 的 `BUSINESS_CONTEXT_HOOK`
4. 注册业务工具到 `tools.registry`、安装业务技能到 `HERMES_HOME/skills`
5. 包装 `stream_agent_chat` 使 Agent 对话感知业务数据
6. 返回「Agent 对话 + 业务路由」融合 app

---

## 4. 决策判据：单工程内嵌 vs 三系统分离

| 判据 | 单工程内嵌（默认） | 三系统分离 |
|---|---|---|
| 业务规模 | 中小型、单一应用 | 完整业务系统、多模块 |
| 独立交付 | 一个 EXE 即可 | 业务需独立打包分发 |
| 底座可替换 | 不关心 | 需频繁/自主升级底座 |
| 业务与 Agent 耦合 | 可接受 | 必须彻底解耦 |
| 长期演进 | 快速迭代小应用 | 多团队/多生命周期演进 |
| 复杂度代价 | 低 | 高（三目录 + 装配层 + 验证） |

> **默认走单工程内嵌**；当业务已具备"完整系统"特征（多模块、需独立交付、底座需可替换、业务与 Agent 解耦是硬约束）时，升级为三系统分离。

---

## 5. 落地步骤（在 examples/01 底座上搭三系统）

1. **建目录**：把 `examples/01` 复制为 `Agent系统/`（保持零差异）；新增 `业务系统/`、`连接系统/`。
2. **业务系统**：从你的业务抽离出纯业务 app（`build_app()` 自建、`mount_rd_routes()` 挂路由、`get_business_snapshot()` 出快照），**确保不 import 任何 Agent 模块**；配独立 `启动.bat` 与独立 EXE 打包。
3. **连接系统**：新建 `bridge.py`，实现 `fuse_business_into_agent()`（见 §3 装配流程）；入口 `main.py` 调装配函数得到融合 app 后启动 uvicorn + pywebview。
4. **Agent系统**：保持 = `examples/01` 纯净底座，写 `替换Agent系统.md` 说明三步替换法。
5. **验证**：跑 §7 三系统验证门禁，确认融合/独立双模式都正常。

---

## 6. 底座替换三步法（Agent系统可整体替换）

```
① 删除旧 Agent系统目录（备份后）
② 复制上游 examples/01 为新的 Agent系统
③ 粘贴原 Agent系统 的运行时数据（HERMES_HOME 等），业务/连接零改动
```

> 前提：业务/连接只通过 §2.1 的稳定接口依赖 Agent，不 import 其内部模块；Agent系统保持零差异、无业务痕迹。

---

## 7. 三系统验证门禁（交付前必跑）

| 检查 | 脚本/方法 | 断言 |
|---|---|---|
| 底座零差异 | `verify_agent_same` | Agent系统 与上游 `examples/01` 代码零差异（仅运行时数据不同） |
| 业务纯净 | `verify_biz_no_agent_import` | 业务系统无 `import server/routes/agent_runtime/tools/hermes_*` |
| 连接唯一装配点 | 代码审查 | 唯一 `from server import` 在连接系统 |
| 融合装配 | `fuse_business_into_agent` 后 | 业务路由 + Agent 对话 `/api/chat` 双 200 |
| 独立运行 | 业务系统独立启动 | 业务路由 200（无 Agent 对话，符合预期） |
| 无死代码 | `pyflakes`/`autoflake` | 无未使用 import/未定义引用 |

---

## 8. 反模式红线（⛔）

- ⛔ **业务系统 `import` Agent 模块**（`server`/`routes`/`agent_runtime`/`tools`）——耦合，破坏独立性。
- ⛔ **业务逻辑散落 / copy-paste 重复辅助函数** —— 破坏模块内聚，应抽公共模块。
- ⛔ **Agent系统被业务污染**（塞业务代码/业务技能）——破坏可替换性。
- ⛔ **装配逻辑散落多个系统** —— 应全部收拢到连接系统唯一装配函数。
- ⛔ **死代码/未引用模块不清理** —— 堆积僵尸代码，难以维护。
