## 状态快照（State Snapshots）— 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#snapshot` 抽出：该旗舰示例对 State Snapshots 状态快照的实际落地（后端薄封装 `hermes_features.py` / 路由 `routes/features.py` / 前端 `renderSnapshotsPanel`）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#snapshot`）。

---

## 3. examples 落地清单（实际改动）

### 3.1 后端薄封装 — `hermes_features.py` §5.1
- `_backup_mod()`：惰性 `import hermes_cli.backup`（不可用返回 `None`，全模块降级）。
- `_snapshot_home()`：返回 `_get_home()`（见 §2.1，与 backup 同目录）。
- `snapshots_list(limit=50)`：`bk.list_quick_snapshots(limit, hermes_home=home)`，
  把 `files` 由 `dict` 转排序 `list` 便于前端展示。
- `snapshots_create(label)`：`bk.create_quick_snapshot(label, hermes_home=home)`；
  返回 `None` 时提示「当前没有可快照的状态文件」。
- `snapshots_restore(snap_id)`：`bk.restore_quick_snapshot(snap_id, hermes_home=home)`；
  成功返回 `restart_required:True`（`.db` 原子替换后需重启应用生效）。
- `snapshots_prune(keep=20)`：`bk.prune_quick_snapshots(keep, hermes_home=home)` → 透传删除数。
- **加固旧备份**：`_wal_copy_db(src,dst)` 复用内核 `_safe_copy_db`（WAL 安全）；
  `backup_create` 对 `.db` 走它再进 ZIP；`backup_restore` 逐成员解压 + zip-slip 防护。

### 3.2 路由 — `routes/features.py`（4 条）
- `GET  /api/features/snapshots` → `snapshots_list`
- `POST /api/features/snapshots`（`{label}`）→ `snapshots_create`
- `POST /api/features/snapshots/restore`（`{id}`）→ `snapshots_restore`
- `POST /api/features/snapshots/prune`（`{keep}`）→ `snapshots_prune`

### 3.3 前端 — `static/src/panels/other.js`（`renderSnapshotsPanel`）
- 标题「状态快照（Hermes 原生）」+ 与对话快照/完整备份的区别说明 + 橙色提示
  （覆盖核心状态 / 建议关闭应用再恢复 / 恢复后重启）。
- 「创建快照」「清理旧快照(保留20)」按钮 + 列表渲染（id/label/file_count/size 徽标 +
  文件清单 + 恢复按钮，调对应 4 接口）。
- `panels.js` 导出、`views.js` 注册 `snapshots` 视图（`renderSnapshotsView`）、
  `routes/pages.py` 侧栏加「💾 状态快照」导航 + 主区加 `view-snapshots` 容器、
  `app.css` 补 `.tag.err` / `.snapshot-warn`。
