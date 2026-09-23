"""Part 3 — 原生斜杠指令（hermes_cli.commands 注册表）

为何不能直接复用 Hermes 的原生派发层：
  hermes_cli.commands.COMMAND_REGISTRY 是*元数据*清单（CommandDef 无 handler
  字段）：name / aliases / description / category / args_hint / cli_only /
  gateway_only。原生*实现*分散在三处——Gateway(gateway/slash_commands.py)、
  WebUI(hermes_cli/web_server.py)、CLI(hermes_cli/cli_commands_mixin.py)，
  且各自耦合其运行环境（session_store / _running_agents / adapters / hooks），
  不存在可单独 import 的「原生指令函数」。

因此本模块不复制派发层，而是复用 Hermes 的*真实底层原语*（hermes_config 的
get_models_list / save_models_list / get_web_search_status / list_skills 等）
在自有薄派发器里执行「桌面/Web 可行」的子集，其余按能力如实标注。
"""
from __future__ import annotations

# 前端已本地实现（历史在 localStorage）的指令 → 交由前端处理。
# 注意：仅列 0.19.0 COMMAND_REGISTRY 中真实存在的规范名；llm 并非原生指令，已移除。
FRONTEND_COMMANDS = {
    "goal", "learn", "new", "retry", "undo", "title",
    "branch", "sessions", "clear", "help",
}

# 服务端可用真实 Hermes 原语执行的配置/信息类指令
SERVER_COMMANDS = {"model", "status", "skills"}

# 真正需要交互式 TTY 的指令（无桌面等价物）：依赖 $EDITOR / TTY 重绘 / TTY 快照。
# 其余 cli_only 指令（tools/plugins/usage/whoami/profile/reasoning/history/save/
# compress 等）仅是「原生用 TUI 渲染」，桌面可降级为只读信息，不应一律判为 terminal。
# 仅列规范名（canonical）；snapshot 的别名才是 snap，故此处用 snapshot。
TERMINAL_BOUND = {"prompt", "redraw", "snapshot"}


def _command_registry():
    from hermes_cli.commands import COMMAND_REGISTRY
    return COMMAND_REGISTRY


def classify_command(name: str, cli_only: bool, gateway_only: bool) -> str:
    """单条指令的可执行能力分类。

    优先级：前端本地实现 > 网关专属 > 服务端可重实现 > 真正交互式 TTY > 交给 Agent。
    """
    if name in FRONTEND_COMMANDS:
        return "frontend"
    if gateway_only:
        return "gateway"
    if name in SERVER_COMMANDS:
        return "server"
    if name in TERMINAL_BOUND:
        return "terminal"
    return "agent"


def list_native_commands() -> list[dict]:
    """返回 Hermes 原生指令全量清单（含 capability 分类标签）。"""
    out = []
    try:
        reg = _command_registry()
    except Exception as e:  # noqa: BLE001
        return [{"name": "(unavailable)", "description": f"指令注册表不可用：{e}",
                 "capability": "agent", "aliases": [], "category": "",
                 "args_hint": "", "cli_only": False, "gateway_only": False}]
    for c in reg:
        out.append({
            "name": c.name,
            "aliases": list(c.aliases or []),
            "description": c.description,
            "category": c.category,
            "args_hint": c.args_hint or "",
            "cli_only": bool(c.cli_only),
            "gateway_only": bool(c.gateway_only),
            "capability": classify_command(c.name, bool(c.cli_only),
                                           bool(c.gateway_only)),
        })
    return out


def native_command_count() -> dict:
    """统计原生指令分类分布。按 classify_command() 统一分类，每条只入一桶。"""
    buckets = {"server": 0, "frontend": 0, "gateway": 0, "terminal": 0, "agent": 0}
    total = 0
    try:
        for c in _command_registry():
            total += 1
            buckets[classify_command(c.name, bool(c.cli_only),
                                     bool(c.gateway_only))] += 1
    except Exception:
        pass
    return {
        "total": total,
        "server_executable": buckets["server"],
        "frontend_executable": buckets["frontend"],
        "gateway_unsupported": buckets["gateway"],
        "terminal_unsupported": buckets["terminal"],
        "agent_fallback": buckets["agent"],
    }


def parse_command(text: str):
    """解析 ``/name args`` → ``(name, args_str)``。失败返回 ``(None, "")``。"""
    s = (text or "").strip()
    if not s.startswith("/"):
        return None, ""
    body = s[1:].strip()
    if not body:
        return None, ""
    parts = body.split(None, 1)
    return parts[0].lower(), (parts[1].strip() if len(parts) > 1 else "")


def _unsupported_message(name: str, kind: str) -> str:
    if kind == "gateway":
        return (f"🌐 /{name} 是 Hermes 网关/消息平台专属指令（gateway_only），"
                f"需连接 Telegram/Discord/Matrix 等平台；"
                f"本应用为本地桌面前端、未启用网关，无法运行。")
    return (f"⌨️ /{name} 是 Hermes 终端(CLI/TUI)专属指令（cli_only），"
            f"需在 Hermes 原生终端中执行（依赖 $EDITOR / TTY 重绘 / TTY 快照）；"
            f"本应用为桌面前端，无法运行。")


def execute_command(name: str, args: str) -> dict:
    """执行一条服务端可行的原生指令，返回结构化结果。

    返回形态：
      ``{"kind": "server", "text": "..."}``                已用真实原语执行
      ``{"kind": "frontend"}``                              交由前端本地处理
      ``{"kind": "agent"}``                                 交给 Agent(LLM) 处理
      ``{"kind": "terminal"|"gateway", "message": "..."}``  环境不支持，前端提示
    """
    cli_only = gateway_only = False
    try:
        for c in _command_registry():
            if c.name == name or (c.aliases and name in c.aliases):
                cli_only, gateway_only = bool(c.cli_only), bool(c.gateway_only)
                break
    except Exception:
        pass

    cap = classify_command(name, cli_only, gateway_only)
    if cap in ("gateway", "terminal"):
        return {"kind": cap, "message": _unsupported_message(name, cap)}
    if cap in ("frontend", "agent"):
        return {"kind": cap}

    try:
        if name == "model":
            return _exec_model(args)
        if name == "status":
            return _exec_status()
        if name == "skills":
            return _exec_skills(args)
    except Exception as e:  # noqa: BLE001
        return {"kind": "server", "text": f"执行 /{name} 时出错：{e}"}
    return {"kind": "agent"}


def _exec_model(args: str) -> dict:
    from hermes_config import get_llm_config, get_models_list, save_models_list

    cfg = get_llm_config()
    models = get_models_list(cfg)
    if not args:
        active_id = (cfg.get("active") or (models[0].get("id") if models else "")
                     ) if isinstance(cfg, dict) else ""
        lines = ["📡 当前模型配置（llm.json）：", ""]
        for m in models:
            mid = m.get("id", "")
            mark = "✅" if mid == active_id else "  "
            vendor = m.get("vendor") or m.get("provider") or ""
            base = m.get("base_url") or ""
            lines.append(f"{mark} {m.get('name') or mid}  <{mid}>  {vendor} {base}".rstrip())
        if not models:
            lines.append("（llm.json 中暂无 models 列表）")
        lines += ["", "切换模型：/model <id>  例如 /model " + (active_id or "<模型id>")]
        return {"kind": "server", "text": "\n".join(lines)}

    target = args.strip()
    matched = next((m for m in models
                    if m.get("id") == target or m.get("name") == target), None)
    if not matched:
        matched = next((m for m in models if target and target in (m.get("id") or "")), None)
    if not matched:
        return {"kind": "server", "text": f"未找到模型 «{target}»。用 /model 查看可用 id。"}
    save_models_list(models, matched.get("id"))
    return {"kind": "server",
            "text": f"✅ 已将活动模型切换为：{matched.get('name') or matched.get('id')}"
                    f"  <{matched.get('id')}>"}


def _exec_status() -> dict:
    from hermes_config import get_hermes_home, get_llm_config, get_web_search_status, list_skills

    lines = ["📊 Hermes 运行状态", ""]
    try:
        lines.append(f"Hermes 主目录：{get_hermes_home()}")
    except Exception:
        pass
    try:
        cfg = get_llm_config()
        lines.append(f"活动模型：{(cfg.get('active') if isinstance(cfg, dict) else None) or '（未配置）'}")
    except Exception:
        lines.append("活动模型：<读取失败>")
    try:
        ws = get_web_search_status()
        lines.append(f"联网搜索：{ws.get('label')}（{ws.get('backend')}）" if ws.get("ok")
                     else f"联网搜索：{ws.get('message') or '不可用'}")
    except Exception:
        lines.append("联网搜索：<读取失败>")
    try:
        skills = list_skills()
        enabled = sum(1 for s in skills if s.get("enabled", True))
        lines.append(f"技能：共 {len(skills)} 个，启用 {enabled} 个")
    except Exception:
        lines.append("技能：<读取失败>")
    return {"kind": "server", "text": "\n".join(lines)}


def _exec_skills(args: str) -> dict:
    from hermes_config import read_skill, list_skills

    name = args.strip()
    if name:
        sk = read_skill(name)
        if not sk:
            return {"kind": "server", "text": f"未找到技能 «{name}»。"}
        body = sk.get("body") or ""
        snippet = body if len(body) <= 1200 else body[:1200] + "\n…（已截断）"
        return {"kind": "server",
                "text": (f"🧩 技能：{name}\n"
                         f"描述：{sk.get('description') or '（无）'}\n"
                         f"分类：{sk.get('category') or '（无）'}\n"
                         f"启用：{'是' if sk.get('enabled', True) else '否'}\n\n{snippet}")}
    skills = list_skills()
    if not skills:
        return {"kind": "server", "text": "（暂无已安装技能）"}
    lines = [f"🧩 已安装技能（{len(skills)}）：", ""]
    for s in skills:
        mark = "✅" if s.get("enabled", True) else "⛔"
        lines.append(f"{mark} {s.get('name')}  —  {s.get('description') or ''}")
    return {"kind": "server", "text": "\n".join(lines)}