# Goals 集成 — 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#goals` 抽出：该旗舰示例对 Goals 的实际改动（后端薄封装 / 路由 / 聊天后处理 / 前端面板 / 续跑）。
> 属示例耦合内容，不进入技能核心骨干（内核机制、集成铁律、验证、反模式红线见 `references/08-capability-integration.md#goals` §1–§2 / §4–§5）。

---

## 3. examples 落地清单（实际改动）

### 3.1 后端薄封装 — `hermes_features.py`
- `_goals_mod()`：惰性 `import hermes_cli.goals as g`（不可用返回 `None`，全模块降级）。
- `_serialize_goal_state(s)`：**自己写**序列化（内核 `GoalState.to_json` 用 `asdict`，
  但 `GoalContract` 非 dataclass，`asdict` 会失败）→ 用 `contract.to_dict()` + `getattr`
  安全取值，额外算 `has_contract` / `is_waiting`。
- `_goal_manager(conv_id)`：建 `g.GoalManager(str(conv_id))`，异常→`(None, err)`。
- `_goal_judge_available()`：探测 `get_text_auxiliary_client("goal_judge")`；任何异常→`False`
  （安全兜底，避免 §1.2.1 的盲目续跑）。
- 函数：`goals_get / goals_set(text,max_turns?,contract_text?) / goals_pause / goals_resume
  / goals_clear / goals_mark_done / goals_add_subgoal / goals_remove_subgoal / goals_evaluate`。
- `goals_set`：用 `parse_contract` 拆 headline+契约；支持显式 `contract_text` 覆盖合并。
- `goals_get`：**`status=="cleared"` 视为无有效目标，返回 `state=None`**（让前端显示
  「设定目标」表单，而非一个已清除的死目标）。
- `goals_evaluate(conv_id, last_response)`：
  - 无 goal → `{active:False}`；
  - 裁判不可用 → 返回 `decision={"verdict":"manual","should_continue":False}`，**不烧轮次、不调裁判**；
  - last_response 为空 → 只返回当前状态；
  - 否则 `evaluate_after_turn(...)` 并透传 `decision`（含 `continuation_prompt`）。
  - 全函数 try/except → `ok:False` 隔离，绝不向上抛。

### 3.2 路由 — `routes/features.py`（接 `conv_id`）
- `GET  /api/features/goals?conv_id=` → `goals_get`
- `POST /api/features/goals`（`{conv_id,text,max_turns,contract}`）→ `goals_set`
- `POST /api/features/goals/evaluate`（`{conv_id,last_response}`）→ `goals_evaluate`
- `POST /api/features/goals/{pause,resume,clear,mark-done,subgoal,subgoal/remove}` → 对应函数
- 旧的玩具路由 `/api/features/goals/{gid}/update|delete|active` 已**全部删除**（前端同步不再引用）。
- 路由层不引入 `_err`/`JSONResponse`；`conv_id` 缺失时返回 `{"ok":False,"error":"缺少 conv_id"}`
  （与前端 `d.ok` 约定一致）。

### 3.3 聊天后处理 — `routes/chat.py`（`api_chat` 的 `wrapped()` done 之后）
- `hf.goals_evaluate(cid, final_text)` 包 try/except，**结果附到 `done` 事件的 `goal` 字段**。
- 任何异常隔离，绝不影响对话落盘与前端渲染（与 B1/B2/B3 防御同级别）。

### 3.4 前端 — `static/src/panels/other.js`（`renderGoalsPanel`）
- 清空 `body.innerHTML`（修复旧版重复 append）；读 `State.conv_id`。
- 真实 `GoalState` 展示：状态徽标、轮次 `used/max`、上次裁判结论、泊车屏障、完成契约
  （outcome/verification/constraints/boundaries/stop_when）、子目标列表（增/移除）。
- 操作按钮：暂停 / 继续 / 标记完成 / 清除（按 `status` 显隐）；手动模式提示。
- **文案真实化**：不再谎称「每轮判断」；改为「每轮后由裁判模型判断；未满足时点『继续目标』推进」。

### 3.5 续跑（透明可控，绝不自动连跑）
- `static/src/chat.js` 的 `done` 处理：若 `obj.goal.active && judge_available &&
  decision.should_continue` → 底部浮条「🎯 目标进行中：<reason>  [继续目标 ▶]」。
- 点击 → 把 `decision.continuation_prompt`（或兜底文案）写入输入框并 `sendMessage()`，
  **由用户显式驱动下一轮**（自动喂回列为下一步、默认关闭）。
