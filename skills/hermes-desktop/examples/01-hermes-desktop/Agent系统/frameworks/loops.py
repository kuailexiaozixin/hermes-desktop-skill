"""Part 1 — 循环（Loops）

8 大官方循环的本地化落地 + 用户自定义循环。
"""
from __future__ import annotations

import copy
import json
import re
import shutil
import threading
import time
import uuid
from typing import Any

try:
    from hermes_config import (
        get_hermes_home, get_loop_max_iterations, get_active_model_cfg,
        create_skill, list_skills, read_config_yaml, update_config_yaml,
    )
except ImportError:  # pragma: no cover - 冻结态兜底
    from hermes_config import (  # type: ignore
        get_hermes_home, get_loop_max_iterations, get_active_model_cfg,
        create_skill, list_skills, read_config_yaml, update_config_yaml,
    )

from ._utils import _build_agent, _extract_json_list

# ############################################################################
# 循环元数据
# ############################################################################
# 状态语义（面板据此打标签，不可混用）：
#   active   : 完全激活且用户可控（Core Agent Loop → max_iterations）
#   embedded : 内嵌于 Core Loop 自动生效，参数固化在内核（Compression）
#   switch   : 提供开关，用户可启用/关闭（Memory / Goal 上下文，经 build_agent 的
#              skip_memory / skip_context_files 接入）
#   ondemand : 原网关版靠常驻调度触发，本版改造为「按需执行」——点按钮即在后台
#              线程跑进程内 AIAgent 完成该循环的核心逻辑
#   gateway  : 仅完整 Hermes Gateway 部署可用、本单进程构建确实不存在的特性
BUILTIN_LOOPS: list[dict[str, Any]] = [
    {
        "id": "core",
        "name": "核心智能体循环",
        "en": "Core Agent Loop",
        "scale": "每轮对话（秒级）",
        "status": "active",
        "desc": "一切能力的心脏：模型思考→调用工具→观察结果→再思考，循环往复直到任务完成或达到迭代上限。你在对话框发的每一条消息都由它驱动。",
        "steps": [
            "接收用户消息并组装上下文（系统提示词+历史+技能）",
            "模型推理：决定直接回答还是调用工具",
            "执行工具（文件读写/联网搜索/代码执行/浏览器自动化…）",
            "把工具结果并入上下文（超过 50% 触发压缩）",
            "重复 2–4，直到产出最终回答或达 max_iterations",
        ],
        "params": [
            {"key": "max_iterations", "label": "最大迭代次数", "editable": True,
             "note": "单轮对话中模型最多可连续调用工具的次数，默认 90"},
        ],
        "usage": "无需手动开启——每次对话自动运行。任务复杂（如多文件重构、批量数据处理）可调大 max_iterations；只做问答可调小以节省 token。",
    },
    {
        "id": "compression",
        "name": "上下文压缩循环",
        "en": "Compression Loop",
        "scale": "上下文超阈值时（自动）",
        "status": "embedded",
        "desc": "内嵌在核心循环第 4 步：当对话上下文占用超过模型窗口约 50% 时，自动把较早的对话压缩成摘要，保住长任务不断线。",
        "steps": [
            "每次迭代后估算上下文 token 占用",
            "超过约 50% 阈值 → 触发压缩",
            "把较早的消息压缩为结构化摘要",
            "摘要替换原文，继续核心循环",
        ],
        "params": [
            {"key": "threshold", "label": "触发阈值", "editable": False,
             "note": "约 50%，固化在 Hermes 内核，本构建不可调"},
        ],
        "usage": "全自动，无需干预。长时间多步任务中看到回答仍然连贯，就是它在工作。",
    },
    {
        "id": "memory",
        "name": "记忆循环",
        "en": "Memory Loop",
        "scale": "跨会话（天级）",
        "status": "switch",
        "desc": "跨会话记忆：把重要事实写入 HERMES_HOME/memory，下次对话自动加载。默认关闭（保持无状态、可预期），可在下方开关启用。",
        "steps": [
            "会话开始时加载 memory 目录中的记忆文件",
            "对话中识别值得长期保存的事实",
            "把事实写入记忆文件",
            "下个会话自动带入，无需重复交代",
        ],
        "params": [
            {"key": "memory_enabled", "label": "启用记忆加载", "editable": True,
             "note": "开启后 build_agent 不再跳过记忆（skip_memory=False），重启新会话生效"},
        ],
        "usage": "希望 Agent 记住长期偏好（技术栈、代码风格、常用路径）时开启；追求每次干净上下文时保持关闭。",
    },
    {
        "id": "goal",
        "name": "目标循环",
        "en": "Ralph / Goal Loop",
        "scale": "多步目标（分钟级）",
        "status": "switch",
        "desc": "面向长目标的多轮推进：把大目标拆成多个 turn 连续执行（官方 goals.max_turns 默认 20）。本构建提供「目标上下文加载」开关（skip_context_files），完整 /goal 调度器属 Gateway 层。",
        "steps": [
            "登记目标（目标描述+完成标准）",
            "每个 turn 执行一段核心循环推进目标",
            "检查是否达成完成标准",
            "未达成且未超 max_turns → 继续下一 turn",
        ],
        "params": [
            {"key": "goal_enabled", "label": "启用目标上下文", "editable": True,
             "note": "开启后 build_agent 加载上下文文件（skip_context_files=False）"},
            {"key": "max_turns", "label": "最大轮数", "editable": False,
             "note": "官方默认 20，完整调度仅 Gateway 部署可调"},
        ],
        "usage": "跨多轮的大任务可开启目标上下文；单轮任务保持关闭即可。也可直接用下方「自定义循环」达到类似效果。",
    },
    {
        "id": "self_improvement",
        "name": "自我改进循环",
        "en": "Self-Improvement Loop",
        "scale": "任务完成后（按需）",
        "status": "ondemand",
        "runnable": True,
        "run_label": "沉淀技能",
        "run_hint": "输入一段任务描述，Agent 会提炼可复用的解法并写入技能库（SKILL.md）。",
        "desc": "任务完成后把可复用的解法沉淀为技能（skill），越用越聪明。网关版靠任务后钩子自动触发；本版改为按需执行——点「沉淀技能」即可把当前解法固化进技能库。",
        "steps": [
            "回顾待沉淀的任务/解法",
            "识别可复用的流程/命令/坑",
            "写成 SKILL.md 存入技能库",
            "后续任务自动匹配复用",
        ],
        "params": [],
        "usage": "点卡片上的「沉淀技能」按钮，输入任务描述，Agent 会自动生成 SKILL.md 写入技能库（设置中心 → 技能管理可查看/编辑）。",
    },
    {
        "id": "curator",
        "name": "技能管护循环",
        "en": "Curator Loop",
        "scale": "按需（手动触发）",
        "status": "ondemand",
        "runnable": True,
        "run_label": "整理技能库",
        "run_hint": "扫描技能库，识别重复/冗余项并归档，输出管护报告。",
        "desc": "整理技能库：归档重复/冗余技能、合并重叠项。网关版靠 7 天周期 cron 自动触发；本版改为按需执行——点「整理技能库」即扫描并归档建议项。",
        "steps": [
            "扫描技能库清单",
            "识别重复/冗余技能",
            "归档建议项（移入 _archive）",
            "生成管护报告",
        ],
        "params": [
            {"key": "interval", "label": "周期", "editable": False,
             "note": "网关版默认 7 天；本版按需手动触发"},
        ],
        "usage": "点「整理技能库」按钮，Agent 会列出技能并给出归档建议，确认后移入 skills/_archive 子目录（可在技能管理器中恢复）。",
    },
    {
        "id": "kanban",
        "name": "看板调度循环",
        "en": "Kanban Dispatcher Loop",
        "scale": "按需（手动触发）",
        "status": "ondemand",
        "runnable": True,
        "run_label": "派发看板任务",
        "run_hint": "扫描看板「待办/就绪」列，逐项派发给 Agent 执行并回写结果。",
        "desc": "看板调度：把待办任务分配给 Agent 执行并回写状态。网关版靠 60 秒常驻轮询触发；本版改为按需执行——点「派发看板任务」即扫描待办并逐项执行。数据读写走 Hermes 原生 kanban 工具集。",
        "steps": [
            "扫描看板待办/就绪列（原生 kanban_list）",
            "逐项派发给 Agent 执行",
            "回写执行结果（原生 kanban_comment）",
            "完成后标记已完成（原生 kanban_complete）",
        ],
        "params": [
            {"key": "interval", "label": "扫描间隔", "editable": False,
             "note": "网关版固定 60 秒；本版按需手动触发"},
        ],
        "usage": "点「派发看板任务」按钮，Agent 会依次执行看板中待办/就绪的任务，结果写入任务评论并标记完成。",
    },
    {
        "id": "subagent",
        "name": "子智能体循环",
        "en": "Sub-Agent Loop",
        "scale": "按需委派（并行）",
        "status": "ondemand",
        "runnable": True,
        "run_label": "委派子任务",
        "run_hint": "输入一个主目标，Agent 自动拆解为子任务并并行委派多个子 agent 执行后汇总。",
        "desc": "把子任务委派给并行的子 agent（官方 delegation.max_concurrent_children 默认 3）。本版进程内即可实现——点「委派子任务」输入主目标，Agent 拆解后经原生 delegate_task 并行执行并汇总。",
        "steps": [
            "主 agent 拆解出可并行的子任务",
            "经原生 delegate_task 批量派生子 agent",
            "子 agent 各自跑核心循环",
            "主 agent 汇总子结果继续",
        ],
        "params": [
            {"key": "max_concurrent_children", "label": "最大并发子代理", "editable": False,
             "note": "默认 3，见「委派」面板；由原生 delegation 配置执行"},
        ],
        "usage": "点「委派子任务」按钮，输入一个复合主目标（如「分别调研 A/B/C 三个方案并对比」），Agent 会拆成子任务并行执行后给出汇总。",
    },
]

STATUS_LABELS = {
    "active": "已激活",
    "embedded": "内嵌自动",
    "switch": "可开关",
    "ondemand": "按需执行",
    "gateway": "仅网关版",
}

# ── 循环设置读写（复用 agent_settings.json 的 loop 分组）────────────────────
def _settings_path():
    return get_hermes_home() / "agent_settings.json"

def _read_settings() -> dict:
    p = _settings_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")) or {}
        except Exception:
            pass
    return {}

def _write_settings(s: dict) -> None:
    _settings_path().write_text(
        json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8",
    )

def get_loop_flags() -> dict:
    """记忆/目标两个可开关循环的当前状态（默认均关闭，向后兼容）。"""
    lp = _read_settings().get("loop") or {}
    return {
        "memory_enabled": bool(lp.get("memory_enabled", False)),
        "goal_enabled": bool(lp.get("goal_enabled", False)),
    }

def save_builtin_loop_settings(payload: dict) -> dict:
    """保存内置循环可编辑参数：max_iterations / memory_enabled / goal_enabled。"""
    s = _read_settings()
    lp = dict(s.get("loop") or {})
    if payload.get("max_iterations") is not None:
        try:
            v = int(payload["max_iterations"])
            if 1 <= v <= 500:
                lp["max_iterations"] = v
        except (TypeError, ValueError):
            pass
    for k in ("memory_enabled", "goal_enabled"):
        if k in payload:
            lp[k] = bool(payload[k])
    s["loop"] = lp
    _write_settings(s)
    return lp

# ── 自定义循环 CRUD（持久化在 loop.custom）──────────────────────────────────
def list_custom_loops() -> list[dict]:
    lp = _read_settings().get("loop") or {}
    out = lp.get("custom")
    return out if isinstance(out, list) else []

def upsert_custom_loop(item: dict) -> dict:
    """新增/修改自定义循环。字段：id?、name、desc?、prompt、max_iterations?、enabled?。"""
    name = (item.get("name") or "").strip() or "未命名循环"
    prompt = (item.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("自定义循环必须提供目标提示词（prompt）")
    try:
        mi = int(item.get("max_iterations") or 30)
    except (TypeError, ValueError):
        mi = 30
    mi = max(1, min(mi, 200))
    rec = {
        "id": (item.get("id") or "").strip() or uuid.uuid4().hex[:8],
        "name": name,
        "desc": (item.get("desc") or "").strip(),
        "prompt": prompt,
        "max_iterations": mi,
        "enabled": bool(item.get("enabled", True)),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    s = _read_settings()
    lp = dict(s.get("loop") or {})
    custom = [c for c in (lp.get("custom") or []) if isinstance(c, dict)]
    for i, c in enumerate(custom):
        if c.get("id") == rec["id"]:
            rec["created_at"] = c.get("created_at", rec["updated_at"])
            custom[i] = rec
            break
    else:
        rec["created_at"] = rec["updated_at"]
        custom.append(rec)
    lp["custom"] = custom
    s["loop"] = lp
    _write_settings(s)
    return rec

def delete_custom_loop(loop_id: str) -> bool:
    s = _read_settings()
    lp = dict(s.get("loop") or {})
    custom = [c for c in (lp.get("custom") or []) if isinstance(c, dict)]
    kept = [c for c in custom if c.get("id") != loop_id]
    if len(kept) == len(custom):
        return False
    lp["custom"] = kept
    s["loop"] = lp
    _write_settings(s)
    return True

# ── 循环执行（后台线程跑完整 Core Agent Loop）───────────────────────────────
_RUNS: dict[str, dict] = {}
_RUNS_LOCK = threading.Lock()
_MAX_RUNS_KEPT = 20

def _prune_runs() -> None:
    if len(_RUNS) <= _MAX_RUNS_KEPT:
        return
    done = sorted(
        (r for r in _RUNS.values() if r["status"] in ("done", "error")),
        key=lambda r: r.get("finished_at") or "",
    )
    for r in done[: len(_RUNS) - _MAX_RUNS_KEPT]:
        _RUNS.pop(r["run_id"], None)

def _new_run(loop_id: str, loop_name: str) -> dict:
    rec = {
        "run_id": uuid.uuid4().hex[:12],
        "loop_id": loop_id,
        "loop_name": loop_name,
        "status": "running",
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "finished_at": None,
        "result": None,
        "error": None,
    }
    with _RUNS_LOCK:
        _RUNS[rec["run_id"]] = rec
        _prune_runs()
    return rec

def run_custom_loop(loop_id: str) -> dict:
    """后台执行自定义循环，立即返回 run 记录（含 run_id 供轮询）。"""
    target = next((c for c in list_custom_loops() if c.get("id") == loop_id), None)
    if not target:
        raise ValueError(f"自定义循环不存在：{loop_id}")
    if not target.get("enabled", True):
        raise ValueError(f"该循环已被停用：{target.get('name')}")
    rec = _new_run(loop_id, target.get("name"))

    def _worker():
        try:
            agent = _build_agent(
                get_active_model_cfg(),
                max_iterations=int(target.get("max_iterations") or 30),
            )
            prompt = (
                f"【自定义循环任务：{target.get('name')}】\n"
                f"{target.get('prompt')}\n\n"
                "请自主多步执行直至完成，完成后给出简明结果总结。"
            )
            rec["result"] = (agent.chat(prompt) or "")[:20000]
            rec["status"] = "done"
        except Exception as e:  # noqa: BLE001
            rec["error"] = str(e)[:2000]
            rec["status"] = "error"
        finally:
            rec["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    threading.Thread(target=_worker, name=f"loop-{loop_id}", daemon=True).start()
    return rec

def get_run(run_id: str) -> dict | None:
    return _RUNS.get(run_id)

def is_builtin_runnable(loop_id: str) -> bool:
    """判断一个内置循环是否支持「按需执行」。"""
    return any(d.get("id") == loop_id and d.get("runnable") for d in BUILTIN_LOOPS)

# ── 内置「按需执行」循环的实现 ──────────────────────────────────────────────
def _md_block(text: str) -> str:
    """从 agent 输出中提取 ```markdown 代码块正文；无则回退整段。"""
    if not text:
        return ""
    m = re.search(r"```(?:markdown|md)?\s*([\s\S]*?)```", text)
    return (m.group(1) if m else text).strip()

def _parse_skill_front(body: str):
    """从技能正文的 frontmatter 提取 (name, description)。"""
    name = desc = ""
    m = re.match(r"^---\s*\n(.*?)\n---", body, re.S)
    if m:
        fm = m.group(1)
        nm = re.search(r"^name:\s*(.+)$", fm, re.M)
        dm = re.search(r"^description:\s*(.+)$", fm, re.M)
        if nm:
            name = nm.group(1).strip()
        if dm:
            desc = dm.group(1).strip()
    return name, desc

def _run_self_improvement(agent, payload: dict) -> str:
    task = (payload.get("prompt") or "").strip()
    brief = task or "请基于近期协助用户完成的典型任务，提炼一个通用可复用的技能。"
    prompt = (
        brief + "\n\n"
        "请将其中可复用的解法沉淀为一个技能，并只输出如下格式的 Markdown 代码块：\n"
        "```markdown\n"
        "---\nname: <技能名称>\ndescription: <一句话说明何时使用该技能>\n---\n"
        "<技能正文：步骤、命令、注意事项、示例>\n```\n"
        "不要输出代码块以外的多余解释。"
    )
    body = _md_block(agent.chat(prompt))
    if not body:
        return "未能生成技能内容，请重试或补充任务描述。"
    name, desc = _parse_skill_front(body)
    if not name:
        name = (payload.get("name") or "沉淀技能").strip()
    created = create_skill(name, desc or "由自我改进循环自动沉淀", body)
    if created.get("ok"):
        return "✅ 已沉淀技能：" + created.get("name", name) + "\n\n" + body[:1200]
    return "技能写入失败：" + str(created.get("error", ""))

def _run_curator(agent) -> str:
    skills = list_skills()
    if not skills:
        return "技能库为空，无需管护。"
    catalog = "\n".join(
        f"- {s.get('name')}：{s.get('description', '')}" for s in skills
    )
    prompt = (
        "以下是当前技能库清单：\n" + catalog + "\n\n"
        "请识别其中重复、功能高度重叠或明显冗余的技能，给出需要归档的技能名称列表。"
        "只输出一个 JSON 数组，例如 [\"skill-a\",\"skill-b\"]，不要多余文字。"
    )
    out = agent.chat(prompt)
    names = _extract_json_list(out)
    if not names:
        return "未识别到需要归档的技能。\n\n（管护观察）\n" + (out or "")[:1000]
    skills_dir = get_hermes_home() / "skills"
    archive_dir = skills_dir / "_archive"
    archived = []
    for nm in names:
        src = skills_dir / nm
        if src.is_dir():
            try:
                archive_dir.mkdir(exist_ok=True)
                shutil.move(str(src), str(archive_dir / nm))
                archived.append(nm)
            except Exception:
                pass
    return ("🧹 已归档 " + str(len(archived)) + " 个技能：" + ", ".join(archived) +
            "\n（归档目录：skills/_archive，可在技能管理器中恢复）\n\n原始建议：\n"
            + (out or "")[:800])

def _kanban_call(tool_name: str, args: dict) -> dict:
    """调用 Hermes 原生 kanban 工具（经 registry），返回解析后的 dict。

    走原生工具而不是私有 DB 模块：看板数据结构由 Hermes 掌握，直连 sqlite 会在
    上游 schema 变更时静默损坏。
    """
    from tools.registry import registry
    handler = None
    try:
        handler = registry.get_handler(tool_name)
    except Exception:
        handler = None
    if handler is None:
        try:  # 触发注册后重试一次
            import tools.kanban_tools  # noqa: F401
            handler = registry.get_handler(tool_name)
        except Exception:
            return {"ok": False, "error": f"原生看板工具不可用：{tool_name}"}
    try:
        raw = handler(args or {})
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{tool_name} 执行异常：{e}"}
    try:
        d = json.loads(raw)
        return d if isinstance(d, dict) else {"ok": True, "raw": raw}
    except Exception:
        return {"ok": True, "raw": str(raw)}

def _run_kanban(agent) -> str:
    listed = _kanban_call("kanban_list", {"limit": 50})
    if listed.get("error"):
        return "看板不可用：" + str(listed["error"])
    tasks = listed.get("tasks") or listed.get("items") or []
    if not isinstance(tasks, list):
        tasks = []
    pending = [t for t in tasks if isinstance(t, dict)
               and str(t.get("status", "")).lower() in ("todo", "ready", "open")]
    if not pending:
        return "看板没有待办/就绪任务，无需派发。"
    # 按优先级降序、创建时间升序派发（对齐 Symphony 的优先级队列语义；
    # 内核 kanban_list 返回的任务含 priority / created_at 字段）
    pending.sort(key=lambda t: (-(int(t.get("priority") or 0)), str(t.get("created_at") or "")))
    done = 0
    lines: list[str] = []
    for t in pending:
        tid = t.get("id") or t.get("task_id")
        body = (t.get("description") or t.get("body") or t.get("title") or "").strip()
        if not tid or not body:
            continue
        try:
            res = agent.chat("请完成以下看板任务：\n" + body)
        except Exception as e:  # noqa: BLE001
            lines.append(f"- {t.get('title')}：执行出错 {e}")
            continue
        _kanban_call("kanban_comment", {
            "task_id": tid,
            "comment": "【看板调度循环】执行结果：\n" + (res or "")[:4000],
        })
        _kanban_call("kanban_complete", {"task_id": tid,
                                         "summary": (res or "")[:500]})
        done += 1
        lines.append(f"- {t.get('title')}：已完成")
    return f"🚀 已派发 {done} 个看板任务：\n" + "\n".join(lines)

def _run_subagent(agent, payload: dict) -> str:
    from .delegation import run_delegation

    goal = (payload.get("prompt") or "").strip() or "请完成一个需要多步拆解的复合任务。"
    try:
        return run_delegation(goal, parent_model_cfg=get_active_model_cfg())
    except Exception as e:  # noqa: BLE001
        return "子智能体委派失败：" + str(e)

def run_builtin_loop(loop_id: str, payload: dict | None = None) -> dict:
    """后台执行一个「按需执行」的内置循环，立即返回 run 记录（含 run_id 供轮询）。"""
    target = next((d for d in BUILTIN_LOOPS if d.get("id") == loop_id), None)
    if not target:
        raise ValueError(f"内置循环不存在：{loop_id}")
    if not target.get("runnable"):
        raise ValueError(f"该循环不可按需执行：{target.get('name')}")
    payload = payload or {}
    rec = _new_run(loop_id, target.get("name"))

    def _worker():
        try:
            agent = _build_agent(get_active_model_cfg(),
                                 max_iterations=get_loop_max_iterations() or 30)
            if loop_id == "self_improvement":
                res = _run_self_improvement(agent, payload)
            elif loop_id == "curator":
                res = _run_curator(agent)
            elif loop_id == "kanban":
                res = _run_kanban(agent)
            elif loop_id == "subagent":
                res = _run_subagent(agent, payload)
            else:
                res = "(未实现的循环)"
            rec["result"] = (res or "")[:20000]
            rec["status"] = "done"
        except Exception as e:  # noqa: BLE001
            rec["error"] = str(e)[:2000]
            rec["status"] = "error"
        finally:
            rec["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    threading.Thread(target=_worker, name=f"bloop-{loop_id}", daemon=True).start()
    return rec

def get_loops_payload() -> dict:
    """面板载荷：8 内置循环 + 实时参数 + 自定义循环。"""
    flags = get_loop_flags()
    mi = get_loop_max_iterations()
    builtins = []
    for d in BUILTIN_LOOPS:
        item = copy.deepcopy(d)  # deep copy
        item["status_label"] = STATUS_LABELS.get(d["status"], d["status"])
        for p in item.get("params", []):
            if p["key"] == "max_iterations":
                p["value"] = mi if mi is not None else 90
            elif p["key"] == "memory_enabled":
                p["value"] = flags["memory_enabled"]
            elif p["key"] == "goal_enabled":
                p["value"] = flags["goal_enabled"]
        builtins.append(item)
    return {
        "builtins": builtins,
        "custom": list_custom_loops(),
        "flags": flags,
        "max_iterations": mi if mi is not None else 90,
        "summary": {
            "total": len(BUILTIN_LOOPS),
            **{k: sum(1 for d in BUILTIN_LOOPS if d["status"] == k)
               for k in ("active", "embedded", "switch", "ondemand", "gateway")},
        },
    }