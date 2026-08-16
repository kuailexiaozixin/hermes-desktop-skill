## Provider Routing 路由 — 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#routing` 抽出：该旗舰示例对 Provider Routing 的实际落地（后端薄封装 `hermes_features.py` §13 / 路由 `routes/features.py` / 前端 `renderRoutingPanel`）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#routing`）。

---

## §2 examples 桌面集成（`hermes_features.py` §13）

复用内核 `hermes_cli.config` 的薄封装：

- `_routing_mods()`：惰性 `import hermes_cli.config`，缺失返回 `None` → `available:False` 降级。
- `routing_get()`：
  - `_ensure_home_env()` → `load_config()` → `cfg_get(cfg,"provider_routing")` + `cfg_get(cfg,"openrouter","min_coding_score")` + `cfg_get(cfg,"model","provider")`。
  - 返回 `available:True` + `provider` + `is_openrouter` + `sort`(默认 price) + `only`/`ignore`/`order` + `require_parameters` + `data_collection` + `min_coding_score` + `note`（非 openrouter 时给警告文案）。
  - 内核缺失 → `{"ok":True,"available":False,"error":...}`。
- `routing_save(payload)`：
  - 校验 `sort`∈{price,throughput,latency}（否则 `ok:False`）。
  - `only`/`ignore`/`order`：接受 list 或逗号串（兼容前端），非空才写。
  - `require_parameters`：bool。
  - `data_collection`：仅 `allow`/`deny` 写入，其它不写。
  - `min_coding_score`：在 [0.0,1.0] 才写；空/None → 清除（回退默认 0.65）。
  - `save_config(cfg)` 落盘，返回 `routing_get()`（刷新后的真实状态）。
- `routes/features.py`：`GET /api/features/routing` + `POST /api/features/routing`（POST 透传 payload，不变）。
- `other.js` `renderRoutingPanel` 重建：sort 下拉 + only/ignore/order 输入 + require_parameters 勾选 + data_collection 下拉 + min_coding_score 数字 + 非 openrouter 警告 + `:nitro`/`:floor` 提示 + `available:False` 降级。
