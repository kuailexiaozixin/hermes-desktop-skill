"""Part 2 — 子智能体委派（原生 tools.delegate_tool 桥接）

为什么是「桥接」而不是自研并行引擎：
  Hermes 自带原生 tools/delegate_tool.py（delegate_task，toolset=delegation），
  且模型自主调用路径本来就走原生（AIAgent._dispatch_delegate_task(parent_agent=self)）。
  若再自研一套并行编排，会出现双轨：配置脱节（原生读 config.yaml delegation.*，
  自研读别处）、监控盲区（自研子 agent 不进原生 _active_subagents registry）。
  因此本层只做三件事：配置统一、执行转发、监控合并。

诚实约束（与原生一致）：
  - 深度限制由原生 delegation.max_spawn_depth（默认 1=扁平）执行；
  - 子 agent 非持久，超时由 delegation.child_timeout_seconds 控制；
  - 子默认继承父凭据/工具集；delegation.model 配值时子用该模型（主强子快）。
"""
from __future__ import annotations

import io
import json
import os
import threading
import time
import uuid
from typing import Any

try:
    from hermes_config import (
        get_hermes_home, get_active_model_cfg, read_config_yaml, update_config_yaml,
    )
except ImportError:  # pragma: no cover - 冻结态兜底
    from hermes_config import (  # type: ignore
        get_hermes_home, get_active_model_cfg, read_config_yaml, update_config_yaml,
    )

from ._utils import _build_agent, _extract_json_list

DELEGATION_DEFAULTS: dict[str, Any] = {
    "enabled": True,                  # App 级：是否启用子智能体委托
    "orchestrator_enabled": True,     # App 级：是否允许自动拆解编排
    "max_concurrent_children": 3,     # 原生 delegation.max_concurrent_children
    "max_iterations": 50,             # 原生 delegation.max_iterations
    "child_timeout_seconds": 300,     # 原生 delegation.child_timeout_seconds
    "max_spawn_depth": 1,             # 原生 delegation.max_spawn_depth（1=扁平）
    "child_model": "",                # 映射原生 delegation.model（留空=继承父）
    "child_provider": "",             # 映射原生 delegation.provider（留空=继承父）
    "child_role": "leaf",             # 子 agent role：leaf/orchestrator（原生 delegate_task 透传）
    "inherit_mcp_toolsets": True,     # 原生 delegation.inherit_mcp_toolsets
    "subagent_auto_approve": False,   # 原生 delegation.subagent_auto_approve
    "expected_output": "",            # App 级：预期输出格式约束（原生无此参数，并入 context）
    "context_share": [],              # App 级：共享上下文文件列表（原生无此参数，并入 context）
}

_DELEG_LOCK = threading.Lock()
_DELS: dict[str, dict] = {}

_CURRENT_PARENT: dict | None = None
_PARENT_AGENT: Any = None
_PARENT_LOCK = threading.Lock()

# ── 配置读写 ─────────────────────────────────────────────────────────────────

def get_delegation_config() -> dict:
    """返回委派配置（config.yaml delegation.* + 默认值回退 + 数值合法性收敛）。

    UI 键 ``child_model`` 映射原生键 ``delegation.model``。
    """
    sec = read_config_yaml(get_hermes_home()).get("delegation")
    s = sec if isinstance(sec, dict) else {}
    if not isinstance(s, dict):
        s = {}
    cfg = dict(DELEGATION_DEFAULTS)
    for k in DELEGATION_DEFAULTS:
        if k in s:
            cfg[k] = s[k]
    if "model" in s and str(s.get("model") or "").strip():
        cfg["child_model"] = str(s["model"]).strip()
    if "provider" in s and str(s.get("provider") or "").strip():
        cfg["child_provider"] = str(s["provider"]).strip()

    def _clamp(key: str, lo: int, hi: int, default: int) -> None:
        try:
            cfg[key] = max(lo, min(int(cfg[key]), hi))
        except (TypeError, ValueError):
            cfg[key] = default

    _clamp("max_concurrent_children", 1, 12, 3)
    _clamp("max_iterations", 1, 200, 50)
    _clamp("child_timeout_seconds", 10, 3600, 300)
    _clamp("max_spawn_depth", 1, 5, 1)
    for b in ("enabled", "orchestrator_enabled", "inherit_mcp_toolsets", "subagent_auto_approve"):
        if not isinstance(cfg[b], bool):
            cfg[b] = True
    if not isinstance(cfg["child_model"], str):
        cfg["child_model"] = ""
    if not isinstance(cfg["child_provider"], str):
        cfg["child_provider"] = ""
    if cfg.get("child_role") not in ("leaf", "orchestrator"):
        cfg["child_role"] = "leaf"
    if not isinstance(cfg.get("expected_output"), str):
        cfg["expected_output"] = ""
    if not isinstance(cfg.get("context_share"), list):
        cfg["context_share"] = []
    return cfg

def save_delegation_config(payload: dict) -> dict:
    """保存委派配置到 config.yaml delegation.*（深合并，保留其它键）。

    ``child_model`` 同时写原生键 ``model``，使原生凭据解析直接生效（主强子快）。
    """
    payload = payload or {}
    patch: dict[str, Any] = {k: payload[k] for k in DELEGATION_DEFAULTS if k in payload}
    if "child_model" in patch:
        cm = str(patch.get("child_model") or "").strip()
        patch["child_model"] = cm
        patch["model"] = cm  # 原生消费键
    if "child_provider" in patch:
        cp = str(patch.get("child_provider") or "").strip()
        patch["child_provider"] = cp
        patch["provider"] = cp  # 原生消费键
    if patch:
        update_config_yaml(get_hermes_home(), {"delegation": patch})
    return get_delegation_config()

# ── 父 agent 上下文 ──────────────────────────────────────────────────────────

def set_parent_model_cfg(cfg: dict | None) -> None:
    """由对话工作线程写入当前父模型配置，供无实时对话时构造父 agent。"""
    global _CURRENT_PARENT
    with _PARENT_LOCK:
        _CURRENT_PARENT = cfg

def set_parent_agent(agent: Any) -> None:
    """由对话工作线程写入当前父 agent（registry 兜底路径与诊断用途）。

    模型自主调用路径不依赖此值（AIAgent._dispatch_delegate_task 自带 self）。
    """
    global _PARENT_AGENT
    with _PARENT_LOCK:
        _PARENT_AGENT = agent

def _effective_parent_cfg() -> dict:
    with _PARENT_LOCK:
        p = _CURRENT_PARENT
    return p if p else get_active_model_cfg()

# ── 原生委托桥接 ─────────────────────────────────────────────────────────────

def _native_delegate():
    """延迟导入原生 delegate_tool（冻结 EXE 内同样可用）。

    若导入失败（运行环境缺少 hermes_agent 自带的 tools 包），抛出清晰中文异常，
    便于定位——多 Agent 委派依赖该原生工具，与 AIAgent 同源。
    """
    try:
        import tools.delegate_tool as dt
        return dt
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "无法加载 Hermes 原生委派工具（tools.delegate_tool）。多 Agent 委派需要 "
            "hermes_agent 自带的 tools 包（与 AIAgent 同源）。请确认运行环境已正确安装 "
            "hermes-agent 且 tools 包可导入。"
        ) from e

def _parse_native_result(raw: str) -> dict:
    try:
        d = json.loads(raw)
        return d if isinstance(d, dict) else {"raw": raw}
    except Exception:
        return {"raw": raw}

def _results_to_texts(parsed: dict, n: int) -> list[str]:
    """从原生结果 dict 提取按 task_index 排列的文本（成功摘要或失败原因）。

    原生 ``delegate_task`` 在不同调用形态下返回结构并不完全一致，这里做宽容解析，
    核心目标：**成功结果绝不误报为失败**。

    - 明确带 ``error``（且无 ``results``）时，才判定为失败；
    - 没有 ``results`` 但有 ``raw`` 文本（同步单任务常直接返回摘要文本）时，当作成功结果；
    - 有 ``results`` 列表时逐条提取；只有 ``status`` 明确为失败才标红，
      其余（含无 ``status`` / ``completed`` / ``ok`` / ``done``）一律当作成功，
      优先取 ``summary``，回退 ``output`` / ``result`` / ``text`` / ``content``，
      再回退整条 entry 字符串，避免把成功误报为失败。
    """
    texts = ["（未返回结果）"] * n
    if not isinstance(parsed, dict):
        return texts

    results = parsed.get("results")
    if not isinstance(results, list):
        # 同步单任务常直接返回纯文本摘要；只有明确 error 才判失败
        err = parsed.get("error")
        raw = parsed.get("raw")
        if err:
            return [f"（委派失败：{err}）"] * n
        if isinstance(raw, str) and raw.strip():
            return [raw.strip()] * n
        return texts

    _TEXT_KEYS = ("summary", "output", "result", "text", "content")
    for entry in results:
        if not isinstance(entry, dict):
            continue
        idx = entry.get("task_index")
        if not isinstance(idx, int) or not (0 <= idx < n):
            continue
        status = str(entry.get("status") or "").lower()
        if status in ("failed", "error", "cancelled", "canceled"):
            texts[idx] = ("（子任务失败：" + str(entry.get("error")
                         or entry.get("summary") or "无详情") + "）")
            continue
        # 成功：优先 summary，回退其它常见文本键
        val = None
        for k in _TEXT_KEYS:
            v = entry.get(k)
            if isinstance(v, str) and v.strip():
                val = v.strip()
                break
        if val is None:
            val = str(entry) if entry else "（子任务完成但无输出）"
        texts[idx] = val
    return texts

def run_delegation(goal: str, parent_model_cfg: dict | None = None,
                   options: dict | None = None) -> str:
    """同步执行委派（阻塞直到完成）。返回最终结果文本。"""
    del_id = _run_delegation_async(goal, parent_model_cfg, options)
    # 等待后台线程完成
    while True:
        with _DELEG_LOCK:
            rec = _DELS.get(del_id)
        if rec and rec["status"] != "running":
            return rec.get("result") or rec.get("error") or "（无结果）"
        time.sleep(2)

def run_delegation_async(goal: str, parent_model_cfg: dict | None = None,
                         options: dict | None = None) -> dict:
    """异步启动委派（后台线程执行），立即返回 {ok, id, status}。"""
    del_id = _run_delegation_async(goal, parent_model_cfg, options)
    return {"ok": True, "id": del_id, "status": "running"}

def _run_delegation_async(goal: str, parent_model_cfg: dict | None = None,
                          options: dict | None = None) -> str:
    """启动委派后台线程，返回 delegation_id。"""
    options = options or {}
    config = get_delegation_config()
    parent_cfg = parent_model_cfg or _effective_parent_cfg()
    mi = max(1, min(int(options.get("max_iterations")
                        or config.get("max_iterations") or 50), 200))
    maxc = int(config.get("max_concurrent_children") or 3)

    # 创建编排记录
    del_id = uuid.uuid4().hex[:12]
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with _DELEG_LOCK:
        rec = {
            "id": del_id, "goal": goal, "status": "running", "engine": "native",
            "started_at": now, "finished_at": None,
            "subtasks": [], "result": None, "error": None,
        }
        _DELS[del_id] = rec
        if len(_DELS) > 50:
            for k in sorted(_DELS.keys())[:len(_DELS) - 50]:
                _DELS.pop(k, None)

    def _worker():
        try:
            if not config.get("enabled"):
                agent = _build_agent(parent_cfg, max_iterations=mi)
                result = "（子智能体委派未启用，已降级为单次执行）\n\n" + (agent.chat(goal) or "")
                with _DELEG_LOCK:
                    rec["result"] = result
                    rec["status"] = "done"
                    rec["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                return

            # 1) 拆解
            subtasks: list[str] = []
            if config.get("orchestrator_enabled"):
                try:
                    planner = _build_agent(parent_cfg, max_iterations=max(5, mi // 2))
                    plan_prompt = (
                        "请把以下主目标拆解为 2-" + str(min(4, maxc)) + " 个可并行执行的子任务，"
                        "每个子任务独立、可单独完成。"
                        "重要：子 agent 从空白上下文起步、对背景一无所知，"
                        "因此每个子任务描述必须自带足够上下文。"
                        "只输出 JSON 数组，每个元素是一个字符串子任务描述，不要多余文字：\n" + goal
                    )
                    subtasks = _extract_json_list(planner.chat(plan_prompt))
                except Exception:
                    subtasks = []
            subtasks = [s for s in subtasks if isinstance(s, str) and s.strip()][:maxc]

            task_list = subtasks if subtasks else [goal]
            with _DELEG_LOCK:
                rec["subtasks"] = [
                    {"index": i + 1, "task": t, "status": "running",
                     "started_at": now, "finished_at": None, "result": None}
                    for i, t in enumerate(task_list)
                ]

            # 2) 构造父 agent 并执行委派
            parent = _build_agent(parent_cfg, max_iterations=mi)
            dt = _native_delegate()
            # role 透传（原生 leaf/orchestrator；leaf 阻止 clarify/send_message/execute_code 等）
            child_role = str(config.get("child_role") or "leaf")
            _role_kw = {"role": child_role} if child_role in ("leaf", "orchestrator") else {}
            # expectedOutput / contextShare：原生 delegate_task 无此参数，并入 context
            _ctx_extra = ""
            try:
                _share_parts = []
                for _p in (config.get("context_share") or []):
                    _fp = str(_p).strip()
                    if _fp and os.path.exists(_fp):
                        with io.open(_fp, "r", encoding="utf-8", errors="replace") as _f:
                            _share_parts.append("### 共享文件：" + _fp + "\n" + _f.read()[:8000])
                _ctx_extra = "\n\n".join(_share_parts)
            except Exception:
                _ctx_extra = ""
            _expected = str(config.get("expected_output") or "").strip()
            if _expected:
                _ctx_extra += ("\n" if _ctx_extra else "") + "【预期输出格式】" + _expected

            def _mk_context(base: str) -> str:
                return (base + ("\n\n" + _ctx_extra if _ctx_extra else ""))

            if len(task_list) == 1:
                raw = dt.delegate_task(
                    goal=task_list[0],
                    context=_mk_context(("主目标：" + goal) if subtasks else ""),
                    background=False, parent_agent=parent, **_role_kw,
                )
            else:
                raw = dt.delegate_task(
                    tasks=[{"goal": t, "context": _mk_context("主目标：" + goal), **_role_kw} for t in task_list],
                    background=False, parent_agent=parent,
                )
            texts = _results_to_texts(_parse_native_result(raw), len(task_list))

            fin = time.strftime("%Y-%m-%d %H:%M:%S")
            with _DELEG_LOCK:
                for i, t in enumerate(texts):
                    rec["subtasks"][i].update({"result": t, "status": "done",
                                               "finished_at": fin})

            # 3) 汇总
            if len(task_list) == 1:
                prefix = ("未能自动拆解，已作为单任务委派子 agent 执行：\n\n" if not subtasks
                          else "🧩 已委派 1 个子任务（原生 delegate_task）：\n\n")
                out = prefix + texts[0]
            else:
                parts = [f"### 子任务 {i + 1}：{t}\n{texts[i]}" for i, t in enumerate(task_list)]
                try:
                    summary_agent = _build_agent(parent_cfg, max_iterations=mi)
                    final = summary_agent.chat(
                        "以下是多个子 agent 并行执行的结果，请汇总成一份连贯的最终回答：\n\n"
                        + "\n\n".join(parts)
                    )
                except Exception as e:
                    final = "（汇总失败：" + str(e) + "）\n\n" + "\n\n".join(parts)
                out = ("🧩 已并行委派 " + str(len(task_list)) + " 个子任务（原生 delegate_task，"
                       + "并发上限 " + str(maxc) + "，子模型："
                       + (config.get("child_model") or "继承父模型") + "）：\n"
                       + "\n".join("- " + s for s in task_list)
                       + "\n\n【汇总】\n" + (final or ""))

            with _DELEG_LOCK:
                # 单任务时 out 已含「委派执行」说明前缀 + 结果文本；多任务时含
                # 并行说明 + 汇总。统一存 out，避免单任务丢失说明前缀。
                rec["result"] = out
                rec["status"] = "done"
                rec["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            with _DELEG_LOCK:
                rec["error"] = f"{type(e).__name__}: {e}"
                rec["status"] = "error"
                rec["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    threading.Thread(target=_worker, name=f"deleg-{del_id[:8]}", daemon=True).start()
    return del_id

# ── 查询与取消 ───────────────────────────────────────────────────────────────

def list_native_subagents() -> list[dict]:
    """直读原生 registry 的活跃子 agent 快照（模型路径派生的子 agent 也在内）。"""
    try:
        items = _native_delegate().list_active_subagents()
        return items if isinstance(items, list) else []
    except Exception:
        return []

def list_delegations() -> list[dict]:
    """编排级历史记录（run_delegation 的拆解/汇总，进程内非持久）。"""
    with _DELEG_LOCK:
        return [dict(v) for v in _DELS.values()]

def get_delegation(did: str) -> dict | None:
    with _DELEG_LOCK:
        return dict(_DELS[did]) if did in _DELS else None

def cancel_delegation(did: str) -> bool:
    """取消：优先按原生 subagent_id 请求中断；否则标记编排记录取消。"""
    try:
        if _native_delegate().interrupt_subagent(did):
            return True
    except Exception:
        pass
    with _DELEG_LOCK:
        if did in _DELS:
            if _DELS[did]["status"] == "running":
                _DELS[did]["status"] = "cancelling"
            return True
    return False


def restart_branch(did: str, idx: int) -> dict:
    """重启单个子分支：重新构造父 agent 并执行该子任务（原生 delegate_task）。

    用于卡死/失败子任务的可控重启；后台线程执行，不阻塞调用方。
    """
    with _DELEG_LOCK:
        rec = _DELS.get(did)
        if not rec:
            return {"ok": False, "error": "委派不存在"}
        subs = rec.get("subtasks") or []
        if not (0 <= idx < len(subs)):
            return {"ok": False, "error": "子任务序号无效"}
        task = subs[idx].get("task")
        if not task:
            return {"ok": False, "error": "子任务无描述，无法重启"}
        subs[idx].update({"status": "restarting", "result": None,
                          "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                          "finished_at": None})
        main_goal = rec.get("goal") or ""

    def _worker():
        try:
            config = get_delegation_config()
            parent_cfg = _effective_parent_cfg()
            mi = int(config.get("max_iterations") or 50)
            child_role = str(config.get("child_role") or "leaf")
            _role_kw = {"role": child_role} if child_role in ("leaf", "orchestrator") else {}
            parent = _build_agent(parent_cfg, max_iterations=mi)
            dt = _native_delegate()
            raw = dt.delegate_task(
                goal=task,
                context=("主目标：" + main_goal) if main_goal else "",
                background=False, parent_agent=parent, **_role_kw,
            )
            texts = _results_to_texts(_parse_native_result(raw), 1)
            with _DELEG_LOCK:
                subs[idx].update({"result": texts[0], "status": "done",
                                  "finished_at": time.strftime("%Y-%m-%d %H:%M:%S")})
        except Exception as e:  # noqa: BLE001
            with _DELEG_LOCK:
                subs[idx].update({"result": "（重启失败：" + str(e) + "）", "status": "error",
                                  "finished_at": time.strftime("%Y-%m-%d %H:%M:%S")})

    threading.Thread(target=_worker, name=f"restart-{did[:8]}-{idx}", daemon=True).start()
    return {"ok": True, "id": did, "idx": idx, "status": "restarting"}


def restart_delegation(did: str) -> dict:
    """整体重启一条委派（重新拆解+并行执行）。"""
    with _DELEG_LOCK:
        rec = _DELS.get(did)
        if not rec:
            return {"ok": False, "error": "委派不存在"}
        goal = rec.get("goal")
    if not goal:
        return {"ok": False, "error": "无目标，无法重启"}
    new_id = _run_delegation_async(goal)
    return {"ok": True, "id": new_id, "status": "running"}
