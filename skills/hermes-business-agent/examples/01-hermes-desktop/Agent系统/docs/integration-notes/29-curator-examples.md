## Curator 策展 — 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#curator` 抽出：该旗舰示例对 Curator 的实际落地（后端薄封装 `hermes_features.py` §10 / 路由 `routes/features.py` 12 条 / 前端 `renderCuratorPanel`）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#curator`）。

---

## §2 examples 桌面集成（`hermes_features.py` §10）

- **`_curator_mods()`**：惰性 `import agent.curator as _cur, tools.skill_usage as _su, agent.curator_backup as _cb`；任一缺失返回 `None` → 调用方据此返回 `{ok, available:False}`。
- **`_ensure_home_env()`**：幂等 `os.environ["HERMES_HOME"] = _get_home()`。
- **`curator_get()`**：`load_state()` + `usage_report()` + `agent_created_report()` + `list_archived_skill_names()` → `{ok, available:True, enabled, paused, interval_hours, stale_after_days, archive_after_days, consolidate, prune_builtins, last_run_at, run_count, usage, agent_created_total, by_state{active,stale,archived}, pinned, archived}`，缺失/异常 → `{ok:False, available:True, error}`。
- **`curator_toggle(enabled)`**：`set_paused(not enabled)`（运行时暂停/恢复自动整理）；返回 `{ok, available:True, enabled, paused}`。
- **`curator_apply(dry_run)`**：`dry_run=True` 返回将受影响的候选预览（排除 pinned/已归档）；`dry_run=False` 调 `apply_automatic_transitions()` 返回 `counts`。
- **`curator_archive(name)`**：空名拒绝；**pinned 先拒**（诚实提示先取消固定）；否则 `archive_skill(name)` → `{ok, message}`。
- **`curator_restore(name)`**：`restore_skill(name)` → `{ok, message}`。
- **`curator_pin(name, pinned)`**：非 agent 创建技能拒绝；`set_pinned(name, pinned)` → `{ok, name, pinned}`。
- **`curator_prune(days, dry_run)`**：遍历 `agent_created_report()`，排除 pinned/已归档，按空闲天数（`last_activity_at` 或 `created_at`）筛选；`dry_run` 仅列候选，`False` 则逐个 `archive_skill` 并汇报 `archived`/`failures`。
- **`curator_backup(reason)` / `curator_backups()` / `curator_rollback(backup_id, yes)`**：透传 `curator_backup`；`backup` 未启用返回 `{ok:False, error}`（诚实，不谎报成功）；`rollback` 需 `yes=True` 确认（否则 `need_confirm`）。
- **`routes/features.py`**：12 条 `/api/features/curator*`（`GET` 状态 / `POST` 切换 / `POST` 自动整理 / `POST` 归档 / `POST` 恢复 / `POST` 固定 / `POST` 批量清理 / `POST` 快照 / `GET` 快照列表 / `POST` 回滚）。
- **`other.js` `renderCuratorPanel`**：`available:False` 诚实降级；真实状态概览（启用/暂停/间隔/阈值/合并/清理内置/上次运行）+ 启用复选框（取消勾选=暂停，使用记录仍追踪）+ 运行自动整理 + agent 创建技能 by_state 统计 + 全量使用遥测列表（来源/使用/查看/打补丁/最近活动 + 固定/归档/恢复动作）+ 已归档列表（可恢复）+ 批量清理空闲技能（预览/归档）+ 技能树快照/回滚（创建/列出/回滚，回滚前再拍安全快照）。
