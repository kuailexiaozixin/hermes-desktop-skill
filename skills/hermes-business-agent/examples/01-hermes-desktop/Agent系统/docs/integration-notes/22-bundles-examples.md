## Bundles 捆绑包 — 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#bundles` 抽出：该旗舰示例对 Bundles 的实际落地（后端薄封装 `hermes_features.py` §9 / 路由 `routes/features.py`）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#bundles`）。

---

## 2.1 复用内核，绝不手写 JSON / 分家

```python
# hermes_features.py §9
def _bundles_mod():
    try:
        import agent.skill_bundles as m
        return m
    except Exception:
        return None

def bundles_list() -> dict:
    m = _bundles_mod()
    if m is None:
        return {"ok": True, "available": False, "error": "内核 skill_bundles 不可用", "items": []}
    items = [{
        "name": i.get("name"), "slug": i.get("slug"),
        "description": i.get("description") or "", "skills": i.get("skills") or [],
        "instruction": i.get("instruction") or "", "path": i.get("path"),
    } for i in m.list_bundles()]
    return {"ok": True, "available": True, "items": items}
```

## 2.2 路由（routes/features.py）

```
GET  /api/features/bundles              → 列表
POST /api/features/bundles             → 创建/覆盖（name, skills, description, instruction, overwrite）
POST /api/features/bundles/uninstall    → 卸载
POST /api/features/bundles/reload       → 重新扫描（内核缓存与磁盘同步）
```
