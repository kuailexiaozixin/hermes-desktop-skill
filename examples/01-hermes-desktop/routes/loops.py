from routes import _err, _guard, _ok, app, ar, fw, hc, we
from pathlib import Path
import importlib.metadata as _ilmd
import os as _os
import re

# 插件列表扫描缓存：plugins 包在运行期基本不变（仅安装/卸载时变化），每次进入「插件」
# 页都重新 walk_packages + import 71 个模块约 0.6s，叠加工具集矩阵探测更久；缓存结果。
_PLUGINS_CACHE = {"ts": 0.0, "data": None}
_PLUGINS_TTL = 120.0  # 秒


# ── 插件启用状态（对齐真实 Hermes：默认不启用，仅 plugins.enabled 里的才加载）──
def _plugin_state_sets():
    """从示例自身 HERMES_HOME 的 config.yaml 读取启用/禁用名单。

    对齐真实 hermes_cli.plugins._get_enabled_plugins / _get_disabled_plugins：
    plugins.enabled 是 allow-list（默认不启用），plugins.disabled 是显式黑名单
    （优先级最高，即使在 enabled 里也不加载）。
    """
    try:
        cfg = hc.read_config_yaml()
        pcfg = cfg.get("plugins") if isinstance(cfg, dict) else None
        if not isinstance(pcfg, dict):
            pcfg = {}
        enabled = set(pcfg.get("enabled") or []) if isinstance(pcfg.get("enabled"), (list, tuple)) else set()
        disabled = set(pcfg.get("disabled") or []) if isinstance(pcfg.get("disabled"), (list, tuple)) else set()
        return enabled, disabled
    except Exception:
        return set(), set()


def _plugin_status(name, key, enabled, disabled):
    """返回单个插件的激活状态：enabled / disabled / not_enabled。"""
    if name in disabled or key in disabled:
        return "disabled"
    if name in enabled or key in enabled:
        return "enabled"
    return "not_enabled"


def _plugin_key_from_pkg(pkg_name):
    """把内置插件的点路径（web.brave_free）规范成真实加载器用的斜杠键（web/brave_free）。"""
    return pkg_name.replace(".", "/")


def _discover_entrypoint_plugins():
    """发现通过 pip 入口点（hermes_agent.plugins）安装的插件（只读元数据，安全）。

    对齐真实 hermes_cli.plugins_cmd._discover_entrypoint_plugins —— 这类插件是
    以 Python 包形式安装的，没有插件目录，必须单独枚举入口点才会出现在列表里。
    """
    out = []
    try:
        eps = _ilmd.entry_points()
        group = "hermes_agent.plugins"
        if hasattr(eps, "select"):
            group_eps = eps.select(group=group)
        elif isinstance(eps, dict):
            group_eps = eps.get(group, [])
        else:
            group_eps = [ep for ep in eps if getattr(ep, "group", None) == group]
        for ep in group_eps:
            ver = ""
            desc = ""
            dist = getattr(ep, "dist", None)
            if dist is not None:
                ver = str(getattr(dist, "version", "") or "")
                meta = getattr(dist, "metadata", None)
                if meta is not None:
                    desc = str(meta.get("Summary", "") or "")
            out.append({
                "name": ep.name,
                "label": ep.name,
                "description": desc,
                "version": ver,
                "author": "",
                "kind": "entrypoint",
                "hooks": [],
                "platforms": [],
                "provides_tools": [],
                "requires_env": [],
                "optional_env": [],
                "pip_dependencies": [],
                "module_count": 0,
                "package_count": 0,
                "file_count": 0,
                "top_level": True,
                "category": "📦 功能插件",
                "category_icon": "📦",
                "source": "entrypoint",
                "toolset": None,
            })
    except Exception:
        pass
    return out




# ── Provider 单选激活（对齐官方 Hermes 的 Provider Plugins 区）─────────────
# 插件分类 → config.yaml 的 <section>.<key>（深合并写入，保留其它键）。
# 真实 Hermes 内核按这些标准字段读取当前激活的 provider / backend / engine。
_PROVIDER_FIELD_MAP = {
    "web":            ("web",          "search_backend"),
    "memory":         ("memory",       "provider"),
    "context_engine": ("context",      "engine"),
    "image_gen":      ("image_gen",    "provider"),
    "video_gen":      ("video_gen",    "provider"),
}

def _provider_value_for(name: str) -> str:
    """把插件标识（web.brave_free / memory.honcho）规范成 provider 字段值（brave_free / honcho）。"""
    return (name or "").split(".")[-1]

def _read_active_providers() -> dict:
    """读取当前激活的 provider 值：{category: value}。"""
    try:
        cfg = hc.read_config_yaml()
    except Exception:
        cfg = {}
    out = {}
    for _cat, (_sec, _key) in _PROVIDER_FIELD_MAP.items():
        _sc = cfg.get(_sec) if isinstance(cfg, dict) else None
        out[_cat] = str(_sc.get(_key)) if isinstance(_sc, dict) and _sc.get(_key) else ""
    return out

def _missing_pip_deps(deps) -> list:
    """返回未安装的 pip 依赖名列表（importlib.metadata 探测，只读安全）。"""
    out = []
    for _d in deps or []:
        _d = str(_d).strip()
        if not _d:
            continue
        _n = re.split(r"[<>=~!]", _d)[0].strip().replace("_", "-").lower()
        if not _n:
            continue
        try:
            _ilmd.version(_n)
        except Exception:
            out.append(_d)
    return out

def _scan_bundled_skills(plugin_dir) -> list:
    """扫描插件目录下捆绑的技能（插件自带 skills/*/SKILL.md 或根 SKILL.md）。"""
    out = []
    try:
        if plugin_dir:
            _pd = Path(plugin_dir)
            if _pd.is_dir():
                _skills_dir = _pd / "skills"
                if _skills_dir.is_dir():
                    for _sk in sorted(_skills_dir.glob("*/SKILL.md")):
                        out.append(_sk.parent.name)
                if (_pd / "SKILL.md").is_file():
                    out.insert(0, _pd.name)
    except Exception:
        pass
    return out

@app.get("/api/plugins")
def api_plugins():
    """列出 Hermes 插件（内置 + 用户自定义），按功能分类，含完整元数据。"""
    import pkgutil, importlib, os as _os, yaml, time as _t
    from collections import defaultdict
    # 命中缓存直接返回（插件集在运行期基本不变）
    if _PLUGINS_CACHE["data"] is not None and (_t.time() - _PLUGINS_CACHE["ts"]) < _PLUGINS_TTL:
        return _PLUGINS_CACHE["data"]

    # 启用/禁用名单（示例自身 HERMES_HOME 的 config.yaml）
    _enabled_set, _disabled_set = _plugin_state_sets()
    _active_providers = _read_active_providers()

    # ------------------------------------------------------------------ 类别映射
    _CATEGORY_MAP = {
        "model-providers":  ("🤖 模型提供商", "模型提供商"),
        "platforms":        ("📡 平台渠道", "平台渠道"),
        "memory":           ("🧠 记忆后端", "记忆后端"),
        "browser":          ("🌐 浏览器引擎", "浏览器引擎"),
        "image_gen":        ("🎨 图像生成", "图像生成"),
        "video_gen":        ("🎬 视频生成", "视频生成"),
        "web":              ("🔍 搜索引擎", "搜索引擎"),
        "cron_providers":   ("⏰ 定时任务", "定时任务"),
        "observability":    ("📊 可观测性", "可观测性"),
        "dashboard_auth":   ("🔐 认证", "认证"),
        "context_engine":   ("📋 上下文引擎", "上下文引擎"),
        "hermes-achievements": ("🏆 成就", "成就"),
        "kanban":           ("📋 看板", "看板"),
    }

    # 顶层插件映射到分类（不走"功能插件"默认）
    _TOP_LEVEL_CATEGORY = {
        "context_engine": "context_engine",
        "cron_providers": "cron_providers",
        "disk-cleanup": None,
        "google_meet": None,
        "hermes-achievements": "hermes-achievements",
        "kanban": "kanban",
        "memory": "memory",
        "observability": "observability",
        "security-guidance": None,
        "spotify": None,
        "teams_pipeline": None,
        "web": "web",
        "dashboard_auth": "dashboard_auth",
        "browser": "browser",
        "image_gen": "image_gen",
        "video_gen": "video_gen",
        "model-providers": "model-providers",
        "platforms": "platforms",
    }

    def _classify(pkg_name):
        """根据包名分类。pkg_name 可能是 'disk-cleanup' 或 'web.brave_free' 格式。"""
        # 先检查完整包名是否在顶层映射中
        _top = _TOP_LEVEL_CATEGORY.get(pkg_name)
        if _top is None:
            # 不在顶层映射中：检查前缀是否匹配某个类别
            for key, (icon, label) in _CATEGORY_MAP.items():
                if pkg_name == key or pkg_name.startswith(key + "."):
                    return (icon, label)
            # 仍不匹配，归为功能插件
            return ("📦 功能插件", "功能插件")
        # 在顶层映射中：_top 是类别键或空字符串
        if _top:
            icon, label = _CATEGORY_MAP.get(_top, ("📦 功能插件", "功能插件"))
            return (icon, label)
        return ("📦 功能插件", "功能插件")

    def _parse_plugin_yaml(yaml_path):
        """解析 plugin.yaml 返回元数据 dict，文件不存在时返回空 dict。"""
        if not _os.path.isfile(yaml_path):
            return {}
        try:
            with open(yaml_path, "r", encoding="utf-8") as _f:
                _data = yaml.safe_load(_f)
            if not isinstance(_data, dict):
                return {}
            _meta = {}
            for _k in ("name", "label", "version", "author", "description",
                       "kind", "hooks", "platforms", "provides_tools",
                       "requires_env", "optional_env", "pip_dependencies"):
                _v = _data.get(_k)
                if _v is not None:
                    _meta[_k] = _v
            if "hooks" in _meta and isinstance(_meta["hooks"], list):
                _meta["hooks"] = [str(h) for h in _meta["hooks"]]
            return _meta
        except Exception:
            return {}

    try:
        _plugins_dir = None
        try:
            import plugins as _plugins_pkg
            _plugins_dir = _plugins_pkg.__path__[0]
        except Exception:
            _plugins_dir = None

        if not _plugins_dir or not _os.path.isdir(_plugins_dir):
            return _err("插件目录不可访问", packages=[], categories=[], total=0)

        # 1. 扫描所有模块
        raw = []
        for _mi in pkgutil.walk_packages([_plugins_dir], prefix="plugins."):
            if _mi.name.endswith(".plugin_utils") or _mi.name == "plugins":
                continue
            try:
                _mod = importlib.import_module(_mi.name)
                _doc = (_mod.__doc__ or "").strip()
                _desc = _doc.split("\n")[0] if _doc else ""
                _parts = _mi.name.split(".")
                raw.append({
                    "name": _parts[-1],
                    "full_name": _mi.name,
                    "package_parent": _parts[-2] if len(_parts) > 1 else "",
                    "description": _desc,
                    "ispkg": _mi.ispkg,
                })
            except Exception:
                pass

        # 2. 按插件标识分组：每个子包作为一个独立插件
        groups = defaultdict(list)
        for r in raw:
            if r["ispkg"]:
                # 插件包：用完整路径（不含 plugins. 前缀）作为标识
                if r["package_parent"] == "plugins":
                    _pkg = r["name"]  # 顶层：disk-cleanup
                else:
                    _pkg = r["full_name"][len("plugins."):]  # 子包：web.brave_free
                groups[_pkg].append(r)
            else:
                # 模块文件：归入其父包
                _full = r["full_name"][len("plugins."):]
                _dot = _full.rfind(".")
                _pkg = _full[:_dot] if _dot > 0 else _full
                groups[_pkg].append(r)

        # 3. 工具集映射（走 agent_runtime 缓存，避免每次进入都跑 check_fn 网络探测）
        _toolset_info = {}
        try:
            _matrix = ar.get_toolset_matrix() or {}
            for _name, _info in _matrix.items():
                _tnames = list(_info.get("tools") or [])
                _tnames.sort()
                _toolset_info[_name] = {
                    "available": bool(_info.get("available")),
                    "tool_count": len(_tnames),
                    "tools": _tnames,
                }
        except Exception:
            pass

        # 4. 构建每个插件条目
        packages = []
        categories_map = defaultdict(list)

        for pkg_name in sorted(groups.keys()):
            children = groups[pkg_name]
            pkgs = [c for c in children if c["ispkg"]]
            mods = [c for c in children if not c["ispkg"]]
            _is_top_level = "." not in pkg_name

            # 获取描述
            _desc = ""
            for c in children:
                if c["package_parent"] == "plugins":
                    _desc = c["description"]
                    break

            # 解析 plugin.yaml
            _yaml_meta = {}
            if _plugins_dir and _os.path.isdir(_plugins_dir):
                # 将 pkg_name 中的点转换为路径分隔符
                _rel_path = pkg_name.replace(".", "/")
                _yaml_path = _os.path.join(_plugins_dir, _rel_path, "plugin.yaml")
                _yaml_meta = _parse_plugin_yaml(_yaml_path)

            # 分类
            _icon, _cat_label = _classify(pkg_name)

            _entry = {
                "name": pkg_name,
                "label": _yaml_meta.get("label", pkg_name.split(".")[-1]),
                "description": _yaml_meta.get("description", _desc),
                "version": _yaml_meta.get("version", ""),
                "author": _yaml_meta.get("author", ""),
                "kind": _yaml_meta.get("kind", ""),
                "hooks": _yaml_meta.get("hooks", []),
                "platforms": _yaml_meta.get("platforms", []),
                "provides_tools": _yaml_meta.get("provides_tools", []),
                "requires_env": _yaml_meta.get("requires_env", []),
                "optional_env": _yaml_meta.get("optional_env", []),
                "pip_dependencies": _yaml_meta.get("pip_dependencies", []),
                "module_count": len(children),
                "package_count": len(pkgs),
                "file_count": len(mods),
                "top_level": _is_top_level,
                "category": _cat_label,
                "category_icon": _icon,
                "source": "builtin",
                "key": _plugin_key_from_pkg(pkg_name),
                "status": _plugin_status(pkg_name.split(".")[-1], _plugin_key_from_pkg(pkg_name), _enabled_set, _disabled_set),
                "enabled": _plugin_status(pkg_name.split(".")[-1], _plugin_key_from_pkg(pkg_name), _enabled_set, _disabled_set) == "enabled",
            }
            # 工具集匹配：尝试用插件名和最后一个段匹配
            _ts_name = pkg_name.split(".")[-1]  # 取最后一段
            _entry["toolset"] = _toolset_info.get(_ts_name) or _toolset_info.get(pkg_name)

            _prov_cat = next((_pc for _pc in _PROVIDER_FIELD_MAP
                              if pkg_name == _pc or pkg_name.startswith(_pc + ".")), None)
            _pv = _provider_value_for(pkg_name) if _prov_cat else ""
            _entry["provider_category"] = _prov_cat
            _entry["provider_value"] = _pv
            _entry["is_active_provider"] = bool(_prov_cat and _active_providers.get(_prov_cat) == _pv)
            _entry["pip_missing"] = _missing_pip_deps(_yaml_meta.get("pip_dependencies", []))
            _entry["bundled_skills"] = _scan_bundled_skills(
                _os.path.join(_plugins_dir, _rel_path) if _plugins_dir else None)
            packages.append(_entry)
            categories_map[_cat_label].append(_entry)

        # 5. 检测用户自定义插件
        _user_plugins = []
        try:
            _user_dir = _os.path.expanduser("~/.hermes/plugins")
            if _os.path.isdir(_user_dir):
                for _up_name in sorted(_os.listdir(_user_dir)):
                    _up_path = _os.path.join(_user_dir, _up_name)
                    if _os.path.isdir(_up_path):
                        _yaml_path = _os.path.join(_up_path, "plugin.yaml")
                        _meta = _parse_plugin_yaml(_yaml_path)
                        _user_entry = {
                            "name": _up_name,
                            "label": _meta.get("label", _up_name),
                            "description": _meta.get("description", ""),
                            "version": _meta.get("version", ""),
                            "author": _meta.get("author", ""),
                            "kind": _meta.get("kind", "user"),
                            "hooks": _meta.get("hooks", []),
                            "platforms": _meta.get("platforms", []),
                            "provides_tools": _meta.get("provides_tools", []),
                            "requires_env": _meta.get("requires_env", []),
                            "optional_env": _meta.get("optional_env", []),
                            "pip_dependencies": _meta.get("pip_dependencies", []),
                            "module_count": 0,
                            "package_count": 0,
                            "file_count": len([_f for _f in _os.listdir(_up_path) if _os.path.isfile(_os.path.join(_up_path, _f))]),
                            "top_level": True,
                            "category": "用户安装",
                            "category_icon": "📦",
                            "source": "user",
                            "key": _up_name,
                            "status": _plugin_status(_up_name, _up_name, _enabled_set, _disabled_set),
                            "enabled": _plugin_status(_up_name, _up_name, _enabled_set, _disabled_set) == "enabled",
                            "toolset": None,
                        }
                        _prov_cat2 = next((_pc for _pc in _PROVIDER_FIELD_MAP
                                             if _up_name == _pc or _up_name.startswith(_pc + ".")), None)
                        _pv2 = _provider_value_for(_up_name) if _prov_cat2 else ""
                        _user_entry["provider_category"] = _prov_cat2
                        _user_entry["provider_value"] = _pv2
                        _user_entry["is_active_provider"] = bool(_prov_cat2 and _active_providers.get(_prov_cat2) == _pv2)
                        _user_entry["pip_missing"] = _missing_pip_deps(_meta.get("pip_dependencies", []))
                        _user_entry["bundled_skills"] = _scan_bundled_skills(_up_path)
                        _user_plugins.append(_user_entry)
                        categories_map["用户安装"].append(_user_entry)
        except Exception:
            pass

        # 5.5 pip 入口点插件（hermes_agent.plugins）——真实发现源之一，原面板漏掉
        for _ep in _discover_entrypoint_plugins():
            _ep["key"] = _ep["name"]
            _ep["status"] = _plugin_status(_ep["name"], _ep["name"], _enabled_set, _disabled_set)
            _ep["enabled"] = _ep["status"] == "enabled"
            packages.append(_ep)
            categories_map.setdefault(_ep["category"], []).append(_ep)

        # 6. 分类排序
        _cat_order = ["🤖 模型提供商", "📡 平台渠道", "🧠 记忆后端", "🌐 浏览器引擎",
                      "🎨 图像生成", "🎬 视频生成", "🔍 搜索引擎", "⏰ 定时任务",
                      "📊 可观测性", "🔐 认证", "📋 上下文引擎", "🏆 成就", "📋 看板",
                      "📦 功能插件", "📦 其他", "用户安装"]
        _cat_sort_key = {c: i for i, c in enumerate(_cat_order)}
        _sorted_cats = sorted(categories_map.keys(), key=lambda c: _cat_sort_key.get(c, 99))

        categories = []
        for _cat in _sorted_cats:
            _plugs = categories_map[_cat]
            _plugs.sort(key=lambda p: (not p["top_level"], p["name"]))
            categories.append({"label": _cat, "plugins": _plugs})

        result = _ok(
            packages=packages,
            categories=categories,
            user_plugins=_user_plugins,
            plugin_count=len(packages) + len(_user_plugins),
            module_count=len(raw),
        )
        _PLUGINS_CACHE["data"] = result
        _PLUGINS_CACHE["ts"] = _t.time()
        return result
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}", packages=[], categories=[], total=0)

# ── 插件管理：启用 / 禁用 / 删除 / 配置环境变量 ──────────────────────────
# 统一作用域在示例自身 HERMES_HOME 的 config.yaml 与 .env（不触碰真实 ~/.hermes），
# 与「发现 ≠ 加载」的真实 Hermes 模型对齐：只有 plugins.enabled 里的插件才会在
# 下次会话真正加载；环境变量落盘位置对齐真实 `hermes plugins install` 的 .env。
def _set_plugin_enabled_state(key: str, enabled: bool) -> dict:
    key = (key or "").strip()
    if not key:
        return {"ok": False, "error": "插件标识不能为空"}
    cfg = hc.read_config_yaml()
    if not isinstance(cfg, dict):
        cfg = {}
    pcfg = cfg.get("plugins")
    if not isinstance(pcfg, dict):
        pcfg = {}
    en = set(pcfg.get("enabled") or []) if isinstance(pcfg.get("enabled"), (list, tuple)) else set()
    dis = set(pcfg.get("disabled") or []) if isinstance(pcfg.get("disabled"), (list, tuple)) else set()
    if enabled:
        en.add(key)
        dis.discard(key)
    else:
        en.discard(key)
        dis.add(key)
    hc.update_config_yaml(None, {"plugins": {
        "enabled": sorted(en), "disabled": sorted(dis)}})
    return {"ok": True, "key": key, "enabled": enabled}


@app.post("/api/plugins/toggle")
async def api_plugin_toggle(req):
    """启用/禁用插件：把标识写入示例 HERMES_HOME 的 plugins.enabled / plugins.disabled。"""
    try:
        body = await req.json()
    except Exception:
        body = {}
    key = (body.get("key") or "").strip()
    enabled = bool(body.get("enabled", False))
    if not key:
        return _err("插件标识不能为空")
    res = _set_plugin_enabled_state(key, enabled)
    if not res.get("ok"):
        return _err(res.get("error", "操作失败"))
    # 失效插件列表缓存，保证下次进入立即反映新状态
    _PLUGINS_CACHE["data"] = None
    return _ok(**res)


@app.post("/api/plugins/env")
async def api_plugin_env(req):
    """把插件 requires_env 声明的变量写入示例 HERMES_HOME 的 .env（对齐真实落盘位置）。"""
    try:
        body = await req.json()
    except Exception:
        body = {}
    key = (body.get("key") or "").strip()
    values = body.get("values") or {}
    if not key or not isinstance(values, dict):
        return _err("插件标识或环境变量数据无效")
    saved = []
    for name, val in values.items():
        name = str(name).strip()
        if not name:
            continue
        hc.set_env_value(name, str(val))
        saved.append(name)
    return _ok(ok=True, saved=saved)


@app.post("/api/plugins/delete")
async def api_plugin_delete(req):
    """仅删除用户自行安装的插件（source=user）。内置与入口点插件拒绝删除。"""
    try:
        body = await req.json()
    except Exception:
        body = {}
    key = (body.get("key") or "").strip()
    if not key:
        return _err("插件标识不能为空")
    allowed_roots = [
        hc.get_hermes_home() / "plugins",
        Path(_os.path.expanduser("~/.hermes/plugins")),
    ]
    target = None
    for root in allowed_roots:
        try:
            root_res = root.resolve()
            tgt_res = (root / key).resolve()
            if tgt_res != root_res and root_res in tgt_res.parents and tgt_res.is_dir():
                target = tgt_res
                break
        except Exception:
            continue
    if target is None:
        return _err(f"未找到可删除的用户插件：{key}")
    try:
        import shutil
        shutil.rmtree(target)
        _PLUGINS_CACHE["data"] = None
        return _ok(ok=True, key=key, deleted=str(target))
    except Exception as e:
        return _err(f"删除失败：{e}")


@app.get("/api/loops")
def api_loops():
    return _guard(lambda: {"ok": True, **fw.get_loops_payload()})


@app.post("/api/loops/settings")
async def api_loops_settings(req):
    body = await req.json()
    return _guard(lambda: {"ok": True, "loop": fw.save_builtin_loop_settings(body)})


@app.post("/api/loops/custom")
async def api_loop_upsert(req):
    body = await req.json()
    return _guard(lambda: {"ok": True, "item": fw.upsert_custom_loop(body)})


@app.put("/api/loops/custom/{loop_id}")
async def api_loop_update(loop_id: str, req):
    body = await req.json()
    body["id"] = loop_id
    return _guard(lambda: {"ok": True, "item": fw.upsert_custom_loop(body)})

@app.delete("/api/loops/custom/{loop_id}")
def api_loop_del(loop_id: str):
    return _guard(fw.delete_custom_loop, loop_id)


@app.post("/api/loops/run/{loop_id}")
async def api_loop_run(loop_id: str, req):
    try:
        body = await req.json()
    except Exception:
        body = {}
    if fw.is_builtin_runnable(loop_id):
        return _guard(lambda: {"ok": True, "run": fw.run_builtin_loop(loop_id, body)})
    return _guard(lambda: {"ok": True, "run": fw.run_custom_loop(loop_id)})


@app.get("/api/loops/run/{run_id}")
def api_loop_run_get(run_id: str):
    return _guard(lambda: {"ok": True, "run": fw.get_run(run_id)})


@app.get("/api/delegation")
def api_delegation():
    return _guard(lambda: {
        "ok": True, "config": fw.get_delegation_config(),
        "subagents": fw.list_native_subagents(),
        "running": fw.list_delegations(),
    })


@app.post("/api/delegation/config")
async def api_delegation_cfg(req):
    body = await req.json()
    return _guard(lambda: {"ok": True, "config": fw.save_delegation_config(body)})


@app.post("/api/delegation/run")
async def api_delegation_run(req):
    body = await req.json()
    goal = (body.get("goal") or "").strip()
    if not goal:
        return _err("目标不能为空")
    cfg = hc.get_active_model_cfg(body.get("model_id"))
    return _guard(lambda: {"ok": True,
                           "run": fw.run_delegation_async(goal, cfg, body.get("options") or {})})


@app.post("/api/delegation/{did}/cancel")
def api_delegation_cancel(did: str):
    return _guard(fw.cancel_delegation, did)

@app.post("/api/delegation/{did}/restart-branch")
async def api_delegation_restart_branch(did: str, req):
    b = await req.json()
    return _guard(fw.restart_branch, did, int(b.get("idx") or 0))

@app.post("/api/delegation/{did}/restart")
def api_delegation_restart(did: str):
    return _guard(fw.restart_delegation, did)


# ---------------------------------------------------------------------------
@app.post("/api/plugins/set-provider")
async def api_plugin_set_provider(req):
    """把某个 provider 类插件设为当前激活 provider（写 config.yaml 对应字段）。"""
    try:
        body = await req.json()
    except Exception:
        body = {}
    category = (body.get("category") or "").strip()
    value = (body.get("value") or "").strip()
    fld = _PROVIDER_FIELD_MAP.get(category)
    if not fld:
        return _err(f"未知的 provider 分类：{category}")
    if not value:
        return _err("provider 值不能为空")
    section, key = fld
    try:
        hc.update_config_yaml(None, {section: {key: value}})
    except Exception as e:
        return _err(f"写入配置失败：{e}")
    _PLUGINS_CACHE["data"] = None  # 失效插件列表缓存，active 状态立即反映新 provider
    return _ok(ok=True, category=category, key=key, value=value)

@app.post("/api/plugins/install-deps")
async def api_plugin_install_deps(req):
    """安装插件声明的 pip 依赖（调用应用自身 python -m pip install，落应用 venv）。"""
    import sys as _sys, subprocess as _sp
    try:
        body = await req.json()
    except Exception:
        body = {}
    deps = [str(d).strip() for d in (body.get("deps") or []) if str(d).strip()]
    if not deps:
        return _err("缺少依赖列表")
    py = _sys.executable
    try:
        proc = _sp.run([py, "-m", "pip", "install", *deps],
                       capture_output=True, text=True, timeout=300)
    except Exception as e:
        return _err(f"执行 pip 失败：{e}")
    if proc.returncode != 0:
        return _err("pip 安装失败：" + (proc.stderr or proc.stdout or "")[-800:])
    _PLUGINS_CACHE["data"] = None  # 失效缓存，pip_missing 立即反映
    return _ok(ok=True, installed=deps, output=(proc.stdout or "")[-500:])
