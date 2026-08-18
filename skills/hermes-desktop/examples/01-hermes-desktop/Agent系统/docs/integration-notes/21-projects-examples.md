## Projects 项目 — 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#projects` 抽出：该旗舰示例对 Projects 的实际落地（后端薄封装 `hermes_features.py` §7 / 路由 `routes/features.py` 七条）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#projects`）。

---

## 2.1 复用内核，绝不手写 sqlite / schema

```python
# hermes_features.py §7
def _projects_db_mod():
    try:
        import hermes_cli.projects_db as m   # 惰性导入，内核缺失即降级
        return m
    except Exception as e:
        return None

def _proj_to_ui(p, active_id):
    d = p.to_dict()                            # 直接用内核 dataclass→dict
    d["active"] = (p.id == active_id)
    return d

def projects_list(include_archived=False):
    m = _projects_db_mod()
    if m is None:
        return {"ok": True, "available": False, "error": "内核未安装", "items": [], "active_id": None}
    from hermes_config import get_hermes_home
    db = get_hermes_home() / "projects.db"
    with m.connect_closing(db) as conn:       # 自动随 HOME 走，与 agent 同库
        active_id = m.get_active_id(conn)
        items = [ _proj_to_ui(p, active_id) for p in m.list_projects(conn, include_archived=include_archived) ]
    return {"ok": True, "items": items, "active_id": active_id}
```

## 2.2 七条路由（routes/features.py）

```
GET  /api/features/projects                 → 列表（?all=1 含归档）
POST /api/features/projects                 → 新建（name 必填；folders 归一化；可 set_active）
POST /api/features/projects/{pid}/update    → 改 name/description/icon/color/board_slug
POST /api/features/projects/{pid}/delete    → 硬删
POST /api/features/projects/{pid}/activate  → 设为当前（body.clear → set_active(None)）
POST /api/features/projects/{pid}/add-folder    → 加文件夹（可 is_primary）
POST /api/features/projects/{pid}/remove-folder → 移除文件夹（移主自动重指）
```
