## MOA 多智能体混合（Mixture of Agents）— 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#moa` 抽出：该旗舰示例对 MOA 的实际落地（`agent_runtime.py` 接入 `tool_progress_callback` / 前端 `chat.js` 折叠块 + `other.js` 预设编辑器）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#moa`）。

---

## 2.3 agent_runtime 接入

- `build_agent` / `build_trial_agent` 签名加 `tool_progress_callback: Callable | None = None`；在 `reasoning_callback` 之后 `if tool_progress_callback: kwargs["tool_progress_callback"] = tool_progress_callback`。
- `provider == "moa"` 守卫（两处都加，逻辑一致）：先用 `resolve_moa_preset(load_config().get("moa") or {}, model)` 校验预设存在；**`except KeyError` → 降级 `deepseek` 且把 `model` 回退为 `"deepseek-chat"`**（否则拿预设名当 deepseek 模型名会 API 报错）。
- `stream_agent_chat`：`on_tool_progress(name, *args, **kwargs)` → `q.put(("tool_progress", name, args, kwargs))`；worker 内 `agent_factory(...)` 传 `tool_progress_callback=on_tool_progress`；消费循环 `elif kind == "tool_progress": yield _sse({"type":"tool_progress","name":item[1],"args":item[2],"kwargs":item[3]})`。

## 2.4 前端

- `chat.js` `buildTurn()` 新增 `moa` 折叠块（`<details class="moa-refs">`），`handleEvent` 在 `obj.type === "tool_progress"` 时：`name==="moa.reference"` 追加 `.moa-ref`（label=args[0], text=args[1]）、`name==="moa.aggregating"` 追加 `.moa-agg` 提示；均 `turn.moa.open = true`。
- `other.js` `renderMoaPanel` 重写为真实预设编辑器：列出 presets（默认/激活徽标、启用、参考模型增删、聚合模型、fanout 下拉、reference_max_tokens/max_tokens）、设为默认/当前模型/取消激活/删除、新增预设、保存全部、`active_in_agent` 状态、`available:False` 降级；底部「用 MOA 跑一句话」经 `/api/features/moa/encode` 后把标记串塞入输入框并 `sendMessage()`。
