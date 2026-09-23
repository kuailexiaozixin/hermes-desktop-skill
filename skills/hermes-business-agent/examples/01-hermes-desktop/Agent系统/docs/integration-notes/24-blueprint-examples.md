## Blueprints 自动化蓝图 — 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#blueprint` 抽出：该旗舰示例对 Blueprints 的实际落地（后端薄封装 `hermes_features.py` §8 / 路由 `routes/features.py` / 前端 `renderBlueprintsPanel` / 桌面端 `deliver` 默认 local 适配）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#blueprint`）。

---

## 3. 集成实现（薄封装，复用内核）

### 3.1 后端（`hermes_features.py` §8）

```python
def _blueprint_catalog_mod():
    try:
        import cron.blueprint_catalog as m
        return m
    except Exception:
        return None

def _cron_jobs_mod():
    try:
        import cron.jobs as m
        return m
    except Exception:
        return None

def blueprints_list() -> dict:
    mod = _blueprint_catalog_mod()
    if mod is None:
        return {"ok": True, "available": False, "items": [],
                "error": "Blueprint 模块不可用（cron 未安装？）"}
    try:
        items = [mod.blueprint_catalog_entry(b) for b in mod.CATALOG]
        return {"ok": True, "available": True, "items": items}
    except Exception as e:
        return {"ok": True, "available": False, "items": [], "error": f"{type(e).__name__}: {e}"}

def blueprints_fill(key: str, values: dict | None = None) -> dict:
    values = values or {}
    cat = _blueprint_catalog_mod()
    if cat is None:
        return {"ok": False, "available": False, "error": "Blueprint 模块不可用（cron 未安装？）"}
    bp = cat.get_blueprint(key)
    if bp is None:
        return {"ok": False, "kind": "notfound", "error": f"未找到蓝图：{key}"}
    try:
        spec = cat.fill_blueprint(bp, values, origin=None)
    except cat.BlueprintFillError as e:
        return {"ok": False, "kind": "validation", "error": str(e)}
    except Exception as e:
        return {"ok": False, "kind": "validation", "error": f"{type(e).__name__}: {e}"}
    jobs = _cron_jobs_mod()
    if jobs is None:
        return {"ok": False, "available": False, "error": "cron.jobs 模块不可用（无法创建定时任务）"}
    try:
        job = jobs.create_job(**spec)
    except Exception as e:
        return {"ok": False, "kind": "create", "error": f"创建定时任务失败：{type(e).__name__}: {e}"}
    return {"ok": True, "job": {
        "id": job.get("id"), "name": job.get("name"),
        "schedule_display": job.get("schedule_display"),
        "deliver": job.get("deliver"), "next_run_at": job.get("next_run_at"),
    }}
```

### 3.2 路由（`routes/features.py`）

```python
@app.get('/api/features/blueprints')
def api_blueprints_list():
    return hf.blueprints_list()

@app.post('/api/features/blueprints/fill')
async def api_blueprints_fill(req):
    b = await req.json()
    return hf.blueprints_fill(b.get('key', ''), b.get('values') or {})
```

> 旧版有 `POST /api/features/blueprints`（创建用户蓝图）和
> `POST /api/features/blueprints/{bid}/delete`（删除）—— 二者没有内核对应物，已删除。

### 3.3 前端（`static/src/panels/other.js` `renderBlueprintsPanel`）

- `GET /api/features/blueprints` → 渲染卡片列表（title/description/category 徽章/
  `scheduleHuman`/tags）。
- 点「设置」→ 按 `item.fields` 的类型逐个渲染输入控件（time/enum/text/weekdays），
  默认值预填。
- 提交 → `POST /api/features/blueprints/fill` `{key, values}` →
  成功展示 job id / `schedule_display` / `deliver`；校验失败（`kind=validation`）展示错误文案。
- `available:False` → 显示降级提示，不渲染表单。

### 3.4 桌面端诚实适配（`deliver` 默认 local）

- 内核蓝图 `deliver` slot 默认 `origin`（= 创建时所在的对话/频道）。桌面端没有聊天起源，
  若直接传 `origin` 会产生「origin 但无 origin」的尴尬状态。
- 前端在渲染 `deliver` 字段时，若 options 含 `local`，**将默认值改为 `local`**
  （仅本地保存输出，不向外部平台投递）。这是 UI 默认值的合理取舍，提交给内核的值仍是用户所选，
  未伪造任何内核行为。用户也可改回 `origin`/其他平台。
