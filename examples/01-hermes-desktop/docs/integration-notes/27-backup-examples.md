## Backup 备份/恢复 — 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#backup` 抽出：该旗舰示例对 Backup 的实际落地（后端薄封装 `hermes_features.py` §5 / 路由 `routes/features.py` / 前端 `renderBackupPanel`）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#backup`）。

---

## §2 桌面集成（hermes_features.py §5）

### 2.1 后端薄封装
- `_backup_mod()`：惰性 `import hermes_cli.backup`（不可用 → `None`）。
- `_backup_dir()` → `<HERMES_HOME>/backups/`（**与状态快照同属 `HERMES_HOME`，路径一致性红线**；内核 walk 排除 `backups/` 防嵌套）。
- `_backup_search_dirs()`：新位置优先，旧 `<HERMES_HOME>/features/backups/` 若存在一并纳入（向后兼容，不丢旧备份）。
- `backup_create()`：
  - 优先 `bk._write_full_zip_backup(dst, home)`（`via="kernel"`）。
  - 内核缺失 → 本地 walk（`via="fallback"`），用**镜像内核**的 `_BACKUP_EXCLUDED_DIRS`/`_BACKUP_EXCLUDED_SUFFIXES`/`_BACKUP_EXCLUDED_NAMES` + `_should_exclude_local`（hermes-agent 仅根级），排除规则与内核一致。
  - 返回 `{ok, name, path, size_mb, via}`（诚实标注走内核还是兜底）。
- `backup_list()`：合并新旧目录，返回 `{ok, items:[{name,size_mb,created}]}`。
- `backup_restore(name)`：
  - 恢复前用内核 `create_quick_snapshot(label=f"pre-restore-{name}", hermes_home=home)` 做**一键回滚安全网**（返回 `pre_restore_snapshot`）。
  - 逐成员解压，**zip-slip 防护**：`dest` 必须落在 `home` 内，否则跳过。
  - 镜像内核 `_IMPORT_SKIP_NAMES`（不覆盖机器专属运行时）/ `_SECRET_FILE_NAMES`（机密 `chmod 0600`）。
  - 返回 `{ok, restored_from, restored, pre_restore_snapshot}`。
- `backup_delete(name)`：跨新旧目录查找并删除。

### 2.2 路由（routes/features.py）
- `GET /api/features/backup` → `backup_list()`
- `POST /api/features/backup` → `backup_create()`
- `POST /api/features/backup/restore` `{name}` → `backup_restore(name)`
- `POST /api/features/backup/delete` `{name}` → `backup_delete(name)`
- （State Snapshots 路由见 `references/08-capability-integration.md#snapshot`：`/api/features/snapshots*`）

### 2.3 前端（other.js `renderBackupPanel`）
- 标题 + 说明「将整个 Hermes 数据目录打包为 ZIP 归档文件」。
- 创建 → `toast('备份完成：{name} ({size_mb} MB)')`；列表行含 `name` / `size_mb` 徽章 / `created` 时间；「恢复」（confirm 后覆盖）/「删除」。
- 恢复成功 toast 提示已自动做恢复前快照（可在「状态快照」回滚）。
- 完整备份本身**不依赖内核**（有本地兜底），故无需 `available:False` 降级；内核缺失仍可用（排除规则正确）。
