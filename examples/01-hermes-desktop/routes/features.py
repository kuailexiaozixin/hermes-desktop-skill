from routes import app, ar, hf
# 「工具集成 / 插件」即命中缓存，无需再等数秒（详见 agent_runtime.get_toolset_matrix）。
def _prime_toolset_cache() -> None:
    try:
        ar.get_toolset_matrix()
    except Exception:  # noqa: BLE001
        pass
try:
    import threading as _th
    _th.Thread(target=_prime_toolset_cache, daemon=True).start()
except Exception:  # noqa: BLE001
    pass




# ===================================================================
# 补充功能路由（hermes_features — 13 个缺失模块）
# ===================================================================
# Goals 常驻目标（复用内核 hermes_cli.goals.GoalManager，按 conv_id 维度）
@app.get('/api/features/goals')
def api_goals_get(req):
    cid = (req.query_params.get('conv_id') or '').strip()
    if not cid:
        return {"ok": False, "error": "缺少 conv_id"}
    return hf.goals_get(cid)

@app.post('/api/features/goals')
async def api_goals_set(req):
    b = await req.json()
    cid = (b.get('conv_id') or '').strip()
    if not cid:
        return {"ok": False, "error": "缺少 conv_id"}
    return hf.goals_set(cid, b.get('text', ''), b.get('max_turns'), b.get('contract'))

@app.post('/api/features/goals/evaluate')
async def api_goals_evaluate(req):
    b = await req.json()
    cid = (b.get('conv_id') or '').strip()
    if not cid:
        return {"ok": False, "error": "缺少 conv_id"}
    return hf.goals_evaluate(cid, b.get('last_response', ''))

@app.post('/api/features/goals/pause')
async def api_goals_pause(req):
    b = await req.json()
    cid = (b.get('conv_id') or '').strip()
    if not cid:
        return {"ok": False, "error": "缺少 conv_id"}
    return hf.goals_pause(cid, b.get('reason', 'user-paused'))

@app.post('/api/features/goals/resume')
async def api_goals_resume(req):
    b = await req.json()
    cid = (b.get('conv_id') or '').strip()
    if not cid:
        return {"ok": False, "error": "缺少 conv_id"}
    return hf.goals_resume(cid)

@app.post('/api/features/goals/clear')
async def api_goals_clear(req):
    b = await req.json()
    cid = (b.get('conv_id') or '').strip()
    if not cid:
        return {"ok": False, "error": "缺少 conv_id"}
    return hf.goals_clear(cid)

@app.post('/api/features/goals/mark-done')
async def api_goals_mark_done(req):
    b = await req.json()
    cid = (b.get('conv_id') or '').strip()
    if not cid:
        return {"ok": False, "error": "缺少 conv_id"}
    return hf.goals_mark_done(cid, b.get('reason', 'user marked done'))

@app.post('/api/features/goals/subgoal')
async def api_goals_subgoal(req):
    b = await req.json()
    cid = (b.get('conv_id') or '').strip()
    if not cid:
        return {"ok": False, "error": "缺少 conv_id"}
    return hf.goals_add_subgoal(cid, b.get('text', ''))

@app.post('/api/features/goals/subgoal/remove')
async def api_goals_subgoal_remove(req):
    b = await req.json()
    cid = (b.get('conv_id') or '').strip()
    if not cid:
        return {"ok": False, "error": "缺少 conv_id"}
    return hf.goals_remove_subgoal(cid, b.get('index'))

# Context Compression 上下文压缩
@app.post('/api/conversations/{cid}/compress')
async def api_conv_compress(cid: str):
    return hf.compress_conversation(cid)

# Checkpoints 对话快照
@app.get('/api/features/checkpoints/{cid}')
def api_checkpoints_list(cid: str):
    return hf.checkpoints_list(cid)

@app.post('/api/features/checkpoints/{cid}')
async def api_checkpoints_create(cid: str, req):
    b = await req.json()
    return hf.checkpoints_create(cid, b.get('label', ''))

@app.post('/api/features/checkpoints/{cid}/{cp_id}/restore')
async def api_checkpoints_restore(cid: str, cp_id: str):
    return hf.checkpoints_restore(cid, cp_id)

@app.post('/api/features/checkpoints/{cid}/{cp_id}/delete')
async def api_checkpoints_delete(cid: str, cp_id: str):
    return hf.checkpoints_delete(cid, cp_id)

# MOA 多智能体混合（Hermes 原生，复用内核 hermes_cli.config + hermes_cli.moa_config）
@app.get('/api/features/moa')
def api_moa_get():
    return hf.moa_get()

@app.post('/api/features/moa')
async def api_moa_save(req):
    b = await req.json()
    return hf.moa_save(b)

@app.post('/api/features/moa/activate')
async def api_moa_activate(req):
    b = await req.json()
    return hf.moa_set_active(b.get('name', ''))

@app.post('/api/features/moa/deactivate')
async def api_moa_deactivate(req):
    b = await req.json()
    return hf.moa_set_active('')

@app.post('/api/features/moa/delete')
async def api_moa_delete(req):
    b = await req.json()
    return hf.moa_delete(b.get('name', ''))

@app.post('/api/features/moa/encode')
async def api_moa_encode(req):
    b = await req.json()
    return hf.moa_encode_turn(b.get('prompt', ''), b.get('preset', ''))

# Backup 备份/恢复
@app.get('/api/features/backup')
def api_backup_list():
    return hf.backup_list()

@app.post('/api/features/backup')
async def api_backup_create():
    return hf.backup_create()

@app.post('/api/features/backup/restore')
async def api_backup_restore(req):
    b = await req.json()
    return hf.backup_restore(b.get('name', ''))

@app.post('/api/features/backup/delete')
async def api_backup_delete(req):
    b = await req.json()
    return hf.backup_delete(b.get('name', ''))

# State Snapshots 状态快照（Hermes 原生，复用内核 hermes_cli.backup）
@app.get('/api/features/snapshots')
def api_snapshots_list():
    return hf.snapshots_list()

@app.post('/api/features/snapshots')
async def api_snapshots_create(req):
    b = await req.json()
    return hf.snapshots_create(b.get('label', ''))

@app.post('/api/features/snapshots/restore')
async def api_snapshots_restore(req):
    b = await req.json()
    return hf.snapshots_restore(b.get('id', ''))

@app.post('/api/features/snapshots/prune')
async def api_snapshots_prune(req):
    b = await req.json()
    return hf.snapshots_prune(b.get('keep', 20))

# Profiles 配置管理
@app.get('/api/features/profiles')
def api_profiles_list():
    return hf.profiles_list()

@app.post('/api/features/profiles')
async def api_profiles_create(req):
    b = await req.json()
    return hf.profiles_create(b.get('name', ''), b.get('clone_from'))

@app.post('/api/features/profiles/switch')
async def api_profiles_switch(req):
    b = await req.json()
    return hf.profiles_switch(b.get('name', ''))

@app.post('/api/features/profiles/delete')
async def api_profiles_delete(req):
    b = await req.json()
    return hf.profiles_delete(b.get('name', ''))

@app.post('/api/features/profiles/export')
async def api_profiles_export(req):
    b = await req.json()
    return hf.profiles_export(b.get('name', ''), b.get('output_path', ''))

@app.post('/api/features/profiles/import')
async def api_profiles_import(req):
    b = await req.json()
    return hf.profiles_import(b.get('archive_path', ''), b.get('name', ''))

@app.post('/api/features/profiles/rename')
async def api_profiles_rename(req):
    b = await req.json()
    return hf.profiles_rename(b.get('old_name', ''), b.get('new_name', ''))

# Projects 项目管理（Hermes 原生 projects.db）
@app.get('/api/features/projects')
def api_projects_list(req):
    inc = str(req.query_params.get('all', '')).lower() in ('1', 'true')
    return hf.projects_list(include_archived=inc)

@app.post('/api/features/projects')
async def api_projects_create(req):
    b = await req.json()
    return hf.projects_create(b)

@app.post('/api/features/projects/{pid}/update')
async def api_projects_update(pid: str, req):
    b = await req.json()
    return hf.projects_update(pid, b)

@app.post('/api/features/projects/{pid}/delete')
async def api_projects_delete(pid: str):
    return hf.projects_delete(pid)

@app.post('/api/features/projects/{pid}/activate')
async def api_projects_activate(pid: str, req):
    try:
        b = await req.json()
    except Exception:
        b = {}
    if isinstance(b, dict) and b.get('clear'):
        return hf.projects_activate('')
    return hf.projects_activate(pid)

@app.post('/api/features/projects/{pid}/add-folder')
async def api_projects_add_folder(pid: str, req):
    b = await req.json()
    return hf.projects_add_folder(pid, b.get('path', ''), bool(b.get('primary')))

@app.post('/api/features/projects/{pid}/remove-folder')
async def api_projects_remove_folder(pid: str, req):
    b = await req.json()
    return hf.projects_remove_folder(pid, b.get('path', ''))

# Blueprints 自动化蓝图（Hermes 原生 cron.blueprint_catalog）
@app.get('/api/features/blueprints')
def api_blueprints_list():
    return hf.blueprints_list()

@app.post('/api/features/blueprints/fill')
async def api_blueprints_fill(req):
    b = await req.json()
    return hf.blueprints_fill(b.get('key', ''), b.get('values') or {})

# Bundles 捆绑包
@app.get('/api/features/bundles')
def api_bundles_list():
    return hf.bundles_list()

@app.post('/api/features/bundles')
async def api_bundles_install(req):
    b = await req.json()
    return hf.bundles_install(
        b.get('name', ''), b.get('skills', []), b.get('description', ''),
        b.get('instruction', ''), bool(b.get('overwrite', False)),
    )

@app.post('/api/features/bundles/uninstall')
async def api_bundles_uninstall(req):
    b = await req.json()
    return hf.bundles_uninstall(b.get('name', ''))

@app.post('/api/features/bundles/reload')
async def api_bundles_reload(req):
    return hf.bundles_reload()

# Curator 策展（复用内核 agent.curator / tools.skill_usage / agent.curator_backup）
@app.get('/api/features/curator')
def api_curator_get():
    return hf.curator_get()

@app.post('/api/features/curator/toggle')
async def api_curator_toggle(req):
    b = await req.json()
    return hf.curator_toggle(b.get('enabled', False))

@app.post('/api/features/curator/apply')
async def api_curator_apply(req):
    b = await req.json()
    return hf.curator_apply(dry_run=bool(b.get('dry_run', False)))

@app.post('/api/features/curator/archive')
async def api_curator_archive(req):
    b = await req.json()
    return hf.curator_archive(b.get('name', ''))

@app.post('/api/features/curator/restore')
async def api_curator_restore(req):
    b = await req.json()
    return hf.curator_restore(b.get('name', ''))

@app.post('/api/features/curator/pin')
async def api_curator_pin(req):
    b = await req.json()
    return hf.curator_pin(b.get('name', ''), bool(b.get('pinned', False)))

@app.post('/api/features/curator/prune')
async def api_curator_prune(req):
    b = await req.json()
    return hf.curator_prune(days=b.get('days', 90), dry_run=bool(b.get('dry_run', True)))

@app.post('/api/features/curator/backup')
async def api_curator_backup(req):
    b = await req.json()
    return hf.curator_backup(b.get('reason', 'manual'))

@app.get('/api/features/curator/backups')
def api_curator_backups():
    return hf.curator_backups()

@app.post('/api/features/curator/rollback')
async def api_curator_rollback(req):
    b = await req.json()
    return hf.curator_rollback(backup_id=b.get('backup_id'), yes=bool(b.get('yes', False)))

# Journey 旅程（复用内核 agent.learning_graph / agent.learning_mutations）
@app.get('/api/features/journey')
def api_journey_get():
    return hf.journey_get()

@app.get('/api/features/journey/node/{node_id}')
def api_journey_node(node_id: str):
    return hf.journey_node_detail(node_id)

@app.post('/api/features/journey/delete')
async def api_journey_delete(req):
    b = await req.json()
    return hf.journey_delete(b.get('node_id') or '')

@app.post('/api/features/journey/edit')
async def api_journey_edit(req):
    b = await req.json()
    return hf.journey_edit(b.get('node_id') or '', b.get('content') or '')

# Security Audit 安全审计
@app.post('/api/features/security-audit')
async def api_security_audit(req):
    try:
        b = await req.json()
    except Exception:
        b = {}
    if not isinstance(b, dict):
        b = {}
    return hf.security_audit_run(
        skip_venv=bool(b.get('skip_venv', False)),
        skip_plugins=bool(b.get('skip_plugins', False)),
        skip_mcp=bool(b.get('skip_mcp', False)),
    )

# Provider Routing 提供者路由
@app.get('/api/features/routing')
def api_routing_get():
    return hf.routing_get()

@app.post('/api/features/routing')
async def api_routing_save(req):
    b = await req.json()
    return hf.routing_save(b)

# Batch Processing 批量处理（Hermes 原生 batch_runner）
@app.get('/api/features/batch/distributions')
def api_batch_distributions():
    return hf.batch_list_distributions()

@app.post('/api/features/batch/run')
async def api_batch_run(req):
    b = await req.json()
    return hf.batch_run(b.get('rows', []), b.get('opts') or {})

@app.get('/api/features/batch/status/{run_id}')
def api_batch_status(run_id: str):
    return hf.batch_status(run_id)


