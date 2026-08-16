## Profiles 配置管理 — 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#profiles` 抽出：该旗舰示例对 Profiles 的实际落地（后端薄封装 `hermes_features.py` §6 / 路由 `routes/features.py` 4 条 / 前端 `renderProfilesPanel`）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#profiles`）。

---

## §2 examples 桌面集成（`hermes_features.py` §6）

- **`_profiles_mod()`**：惰性 `import hermes_cli.profiles`；失败（未装内核）返回 `None`，调用方据此返回 `{ok, available:False}`。
- **`_ensure_home_env()`**：幂等 `os.environ["HERMES_HOME"] = _get_home()`，保证内核看到与 examples 一致的路径。
- **`profiles_list()`**：`pm.get_active_profile()` + `pm.list_profiles()` → `{ok, available:True, items:[{name, is_current, is_default, path, gateway_running, model, provider, has_env, skill_count, alias_name, description}], current}`。
- **`profiles_create(name, clone_from=None)`**：`normalize_profile_name` + `validate_profile_name`（友好报错）→ `pm.create_profile(canon, clone_from=...)`；返回 `{ok, name, path, note}`（note 提示技能需在该 profile 内 `hermes skills install`）。
- **`profiles_switch(name)`**：`pm.set_active_profile(canon)`；返回 `{ok, current, note:"下次启动生效"}`。
- **`profiles_delete(name)`**：`pm.delete_profile(canon, yes=True)`。
- **`routes/features.py`**：4 条 `/api/features/profiles*`（`GET` 列表 / `POST` 创建[透传 `clone_from`] / `POST` 切换 / `POST` 删除）结构不变。
- **`other.js` `renderProfilesPanel`**：`available:False` 诚实降级；展示真实元信息（path / model / provider / skill_count / gateway_running / description / is_default / is_current）+ 可选「克隆自」下拉 + 创建/切换/删除诚实提示（切换下次启动生效、删除停网关与后端）。
