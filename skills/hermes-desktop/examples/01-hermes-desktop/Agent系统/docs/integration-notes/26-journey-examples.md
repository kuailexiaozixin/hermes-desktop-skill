## Journey 旅程/学习图谱 — 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#journey` 抽出：该旗舰示例对 Journey 的实际落地（后端薄封装 `hermes_features.py` §11 / 路由 `routes/features.py` / 前端 `renderJourneyPanel`）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#journey`）。

---

## §2 桌面集成（examples/01-hermes-desktop）

### 2.1 后端 `hermes_features.py`（§11 Journey）
- `_journey_mod()`：惰性 `import agent.learning_graph as m`，异常 → `None`（降级 `available:False`）。
- `_journey_mutations_mod()`：惰性 `import agent.learning_mutations as m`，同上。
- `journey_get()`：`mod.build_learning_graph()` → 返回 `{ok, available:True, nodes, edges, clusters, memory, stats}`；模块缺失/异常 → `{ok, available:False, error, nodes:[], ...}`。
- `journey_node_detail(node_id)` / `journey_delete(node_id)` / `journey_edit(node_id, content)`：直接透传 `agent.learning_mutations` 同名函数；模块缺失 → `{ok:False, available:False, message}`。

### 2.2 路由 `routes/features.py`
```
GET  /api/features/journey              -> hf.journey_get()
GET  /api/features/journey/node/{node_id} -> hf.journey_node_detail(node_id)
POST /api/features/journey/delete       -> hf.journey_delete(body.node_id)
POST /api/features/journey/edit         -> hf.journey_edit(body.node_id, body.content)
```

### 2.3 前端 `static/src/panels/other.js`（`renderJourneyPanel`）
- 拉 `/api/features/journey`。
- `available === false` → 显示 `tag warn`「旅程功能不可用（内核 agent.learning_graph 未加载）」+ error 说明，**不渲染任何假数据**。
- 正常：顶部 `stats` 概要（learned_skills / memory_nodes / agent_created / used / edges 数）；`clusters` 分类徽章；节点按 `timestamp` 倒序排成时间线——技能用 `◆`、记忆用 `✎`，附 分类·useCount·relTime；每个节点提供「编辑」（拉 `node_detail` 预填 `prompt` 编辑 → `POST edit`）与「删除」（confirm → `POST delete`，文案说明技能归档可恢复、记忆移除）。
- 空数据：诚实提示「暂无学习记录——多用一段时间 Hermes…」，并点明数据来自 `HERMES_HOME` 的 `skills/` 与 `memories/`。
