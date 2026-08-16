"""hermes_features.py — 为 hermes-desktop 补充 Hermes Library 已有但前端缺失的功能。

本模块实现 13 个缺失功能模块的后端 API 逻辑（排除 Pets）：
  - Goals 持久化目标 | Context Compression 上下文压缩 | Checkpoints 对话快照
  - MOA 多智能体混合 | Backup 备份/恢复 | Profiles 配置管理
  - Projects 项目管理 | Blueprints 蓝图 | Bundles 捆绑包
  - Curator 策展 | Journey 旅程 | Security Audit 安全审计
  - Provider Routing 提供者路由 | Batch Processing 批量处理

每个功能独立成函数，由 main.py 注册路由，不依赖 hermes-agent 内部模块。
数据存储统一在 HERMES_HOME 下。
"""

# 拆包后统一 re-export，保持 `import x as m; m.xxx` 完全兼容

from ._goals import (goals_get, goals_set, goals_pause, goals_resume, goals_clear, goals_mark_done, goals_add_subgoal, goals_remove_subgoal, goals_evaluate, compress_conversation)
from ._checkpoints import (checkpoints_list, checkpoints_create, checkpoints_restore, checkpoints_delete)
from ._moa import (moa_get, moa_save, moa_set_active, moa_delete, moa_encode_turn)
from ._backup import (backup_create, backup_list, backup_restore, backup_delete, snapshots_list, snapshots_create, snapshots_restore, snapshots_prune)
from ._profiles import (profiles_list, profiles_create, profiles_switch, profiles_delete, profiles_export, profiles_import, profiles_rename)
from ._projects import (projects_list, projects_create, projects_update, projects_delete, projects_activate, projects_add_folder, projects_remove_folder)
from ._blueprints import (blueprints_list, blueprints_fill)
from ._bundles import (bundles_list, bundles_get, bundles_install, bundles_uninstall, bundles_reload)
from ._curator import (curator_get, curator_toggle, curator_apply, curator_archive, curator_restore, curator_pin, curator_prune, curator_backup, curator_backups, curator_rollback)
from ._journey import (journey_get, journey_node_detail, journey_delete, journey_edit)
from ._security import (security_audit_run)
from ._routing import (routing_get, routing_save)
from ._batch import (batch_list_distributions, batch_run, batch_status)

