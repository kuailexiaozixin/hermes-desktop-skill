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
from __future__ import annotations
import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 路径辅助
# ---------------------------------------------------------------------------
def _get_home() -> str:
    from hermes_config import get_hermes_home
    return get_hermes_home()

def _features_dir() -> Path:
    p = Path(_get_home()) / "features"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _read_json(path: Path) -> list | dict:
    if path.exists():
        try: return json.loads(path.read_text(encoding="utf-8"))
        except: pass
    return [] if path.suffix in (".json",) and "goals" not in str(path) else {}

def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ===================================================================
# 1. Goals — Hermes 按会话常驻目标 + 裁判循环
# ===================================================================
# 真实 Goals 机制（hermes_agent 0.19.0+，hermes_cli/goals.py 实证）：
#   - 每会话一个常驻目标，状态持久化于 HERMES_HOME/state.db 的 state_meta 表，
#     键为 f"goal:{session_id}"（不是独立 json 文件、也不是全局清单）；与同进程
#     Agent 写入同一 state.db（桌面 materialize_hermes_env() 已设 HERMES_HOME）。
#   - 没有配套 agent 工具集；循环完全由 CLI/Gateway 层驱动：每轮后用辅助(auxiliary)
#     裁判模型判断目标是否满足；未满足则把续跑提示词当 user 消息喂回同一 session
#     （Ralph loop）。失败开放：裁判连续 3 次解析失败 或 轮次预算(默认 20)耗尽 →
#     自动 status=paused，不卡死。
# 因此这里只做薄封装：复用内核 GoalManager，绝不手写 sqlite/json（早期玩具版手写
# goals.json 与内核语义错位、且 UI 谎称「每轮判断」，已废弃）。内核不可用时优雅降级。
def _goals_mod():
    """惰性导入内核 goals 模块；不可用返回 None。"""
    try:
        import hermes_cli.goals as _g
        return _g
    except Exception:  # noqa: BLE001
        return None


def _serialize_goal_state(s):
    """把内核 GoalState 安全转成 JSON 友好 dict（不依赖内核 to_json 的 asdict——
    GoalContract 非 dataclass，内核 to_json 对其会失败）。"""
    if s is None:
        return None
    contract = getattr(s, "contract", None)
    if contract is not None and hasattr(contract, "to_dict"):
        contract_dict = contract.to_dict()
    else:
        contract_dict = {}
    waiting_until = float(getattr(s, "waiting_until", 0.0) or 0.0)
    is_waiting = bool(
        getattr(s, "waiting_on_pid", None)
        or getattr(s, "waiting_on_session", None)
        or (waiting_until and time.time() < waiting_until)
    )
    has_contract = bool(contract_dict) and any((v or "").strip() for v in contract_dict.values())
    return {
        "goal": s.goal,
        "status": s.status,
        "turns_used": s.turns_used,
        "max_turns": s.max_turns,
        "created_at": s.created_at,
        "last_turn_at": s.last_turn_at,
        "last_verdict": s.last_verdict,
        "last_reason": s.last_reason,
        "paused_reason": s.paused_reason,
        "consecutive_parse_failures": s.consecutive_parse_failures,
        "subgoals": list(s.subgoals or []),
        "waiting_on_pid": getattr(s, "waiting_on_pid", None),
        "waiting_on_session": getattr(s, "waiting_on_session", None),
        "waiting_until": waiting_until,
        "waiting_reason": getattr(s, "waiting_reason", None),
        "waiting_since": float(getattr(s, "waiting_since", 0.0) or 0.0),
        "contract": contract_dict,
        "has_contract": has_contract,
        "is_waiting": is_waiting,
    }


def _goal_manager(conv_id):
    g = _goals_mod()
    if g is None:
        return None, "内核 hermes_cli.goals 不可用"
    try:
        return g.GoalManager(str(conv_id)), None
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def _goal_judge_available() -> bool:
    """探测裁判模型(goal_judge auxiliary)是否可用；不可用则 Goals 仅作记录、
    不烧轮次、不自动续跑。任何异常都按不可用处理（安全兜底）。"""
    try:
        from agent.auxiliary_client import get_text_auxiliary_client
        client, model = get_text_auxiliary_client("goal_judge")
        return client is not None and bool(model)
    except Exception:  # noqa: BLE001
        return False


# ---- 读取 ----
def goals_get(conv_id: str) -> dict:
    g = _goals_mod()
    if g is None:
        return {"ok": True, "available": False, "error": "内核 hermes_cli.goals 不可用",
                "judge_available": False, "state": None}
    try:
        gm, err = _goal_manager(conv_id)
        if gm is None:
            return {"ok": False, "error": err}
        st = gm.state
        # clear() 会保留 cleared 留痕；对前端而言 cleared == 无有效目标，
        # 返回 state=None 让面板显示「设定目标」表单（而非一个已清除的死目标）。
        if st is None or st.status == "cleared":
            return {"ok": True, "available": True, "judge_available": _goal_judge_available(),
                    "state": None}
        return {"ok": True, "available": True, "judge_available": _goal_judge_available(),
                "state": _serialize_goal_state(st)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---- 设定 ----
def goals_set(conv_id: str, text: str, max_turns=None, contract_text: str = None) -> dict:
    g = _goals_mod()
    if g is None:
        return {"ok": False, "error": "内核 hermes_cli.goals 不可用"}
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "目标内容不能为空"}
    try:
        headline, contract = g.parse_contract(text)
        if contract_text and contract_text.strip():
            _, c2 = g.parse_contract(contract_text)
            merged = {f: (c2.to_dict().get(f) or contract.to_dict().get(f) or "")
                      for f in ("outcome", "verification", "constraints", "boundaries", "stop_when")}
            contract = g.GoalContract(**merged)
        mt = int(max_turns) if max_turns else None
        gm, err = _goal_manager(conv_id)
        if gm is None:
            return {"ok": False, "error": err}
        st = gm.set(headline or text, max_turns=mt,
                    contract=(contract if (contract and not contract.is_empty()) else None))
        return {"ok": True, "state": _serialize_goal_state(st)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---- 暂停 / 继续 / 清除 / 标记完成 ----
def goals_pause(conv_id: str, reason: str = "user-paused") -> dict:
    g = _goals_mod()
    if g is None:
        return {"ok": False, "error": "内核 hermes_cli.goals 不可用"}
    try:
        gm, err = _goal_manager(conv_id)
        if gm is None:
            return {"ok": False, "error": err}
        st = gm.state
        if st is None or st.status == "cleared":
            return {"ok": False, "error": "当前没有有效目标可暂停"}
        st = gm.pause(reason or "user-paused")
        if st is None:
            return {"ok": False, "error": "当前没有目标可暂停"}
        return {"ok": True, "state": _serialize_goal_state(st)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def goals_resume(conv_id: str) -> dict:
    g = _goals_mod()
    if g is None:
        return {"ok": False, "error": "内核 hermes_cli.goals 不可用"}
    try:
        gm, err = _goal_manager(conv_id)
        if gm is None:
            return {"ok": False, "error": err}
        st = gm.state
        if st is None or st.status == "cleared":
            return {"ok": False, "error": "当前没有有效目标可继续"}
        st = gm.resume()
        if st is None:
            return {"ok": False, "error": "当前没有目标可继续"}
        return {"ok": True, "state": _serialize_goal_state(st)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def goals_clear(conv_id: str) -> dict:
    g = _goals_mod()
    if g is None:
        return {"ok": False, "error": "内核 hermes_cli.goals 不可用"}
    try:
        gm, err = _goal_manager(conv_id)
        if gm is None:
            return {"ok": False, "error": err}
        gm.clear()
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def goals_mark_done(conv_id: str, reason: str = "user marked done") -> dict:
    g = _goals_mod()
    if g is None:
        return {"ok": False, "error": "内核 hermes_cli.goals 不可用"}
    try:
        gm, err = _goal_manager(conv_id)
        if gm is None:
            return {"ok": False, "error": err}
        st = gm.state
        if st is None or st.status == "cleared":
            return {"ok": False, "error": "当前没有有效目标可标记完成"}
        gm.mark_done(reason or "user marked done")
        return {"ok": True, "state": _serialize_goal_state(gm.state)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---- 子目标 ----
def goals_add_subgoal(conv_id: str, text: str) -> dict:
    g = _goals_mod()
    if g is None:
        return {"ok": False, "error": "内核 hermes_cli.goals 不可用"}
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "子目标内容不能为空"}
    try:
        gm, err = _goal_manager(conv_id)
        if gm is None:
            return {"ok": False, "error": err}
        added = gm.add_subgoal(text)
        return {"ok": True, "text": added, "state": _serialize_goal_state(gm.state)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def goals_remove_subgoal(conv_id: str, index) -> dict:
    g = _goals_mod()
    if g is None:
        return {"ok": False, "error": "内核 hermes_cli.goals 不可用"}
    try:
        gm, err = _goal_manager(conv_id)
        if gm is None:
            return {"ok": False, "error": err}
        idx = int(index)
        removed = gm.remove_subgoal(idx)
        return {"ok": True, "removed": removed, "state": _serialize_goal_state(gm.state)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# ---- 每轮后裁判循环（由 api_chat 的 done 后处理调用） ----
def goals_evaluate(conv_id: str, last_response: str) -> dict:
    g = _goals_mod()
    if g is None:
        return {"ok": True, "available": False, "error": "内核 hermes_cli.goals 不可用",
                "active": False, "judge_available": False, "decision": None, "state": None}
    try:
        gm, err = _goal_manager(conv_id)
        if gm is None:
            return {"ok": False, "error": err, "active": False, "judge_available": False,
                    "decision": None, "state": None}
        if not gm.has_goal():
            return {"ok": True, "available": True, "active": False, "judge_available": True,
                    "decision": None, "state": None}
        # 裁判模型未配置：不烧轮次、不自动续跑，仅返回当前状态 + 提示手动判断
        if not _goal_judge_available():
            return {"ok": True, "available": True, "active": True, "judge_available": False,
                    "decision": {"verdict": "manual", "should_continue": False,
                                 "message": "裁判模型(goal_judge)未配置，目标仅作记录；完成与否需你手动判断。"},
                    "state": _serialize_goal_state(gm.state)}
        if not (last_response or "").strip():
            # 本轮无实质回复，不消耗轮次，仅返回当前状态
            return {"ok": True, "available": True, "active": True, "judge_available": True,
                    "decision": None, "state": _serialize_goal_state(gm.state)}
        dec = gm.evaluate_after_turn(last_response or "")
        return {"ok": True, "available": True, "active": True, "judge_available": True,
                "decision": dec, "state": _serialize_goal_state(gm.state)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "active": False,
                "judge_available": False, "decision": None, "state": None}

# ===================================================================
# 2. Context Compression — 对话上下文压缩
# ===================================================================
def compress_conversation(cid: str) -> dict:
    """压缩指定会话的上下文：将历史摘要化后替换原消息列表。
    返回 {ok, summary, compressed_count}。
    """
    try:
        import sessions as _sess
        msgs = _sess.get_messages(cid)
        if not msgs:
            return {"ok": False, "error": "会话为空"}
        # 保留 system 消息和最后 2 轮对话，其余摘要
        system_msgs = [m for m in msgs if m.get("role") == "system"]
        keep = msgs[-4:] if len(msgs) > 4 else msgs  # 保留最后 2 轮（4 条）
        compress_target = msgs[:-4] if len(msgs) > 4 else []
        if not compress_target:
            return {"ok": True, "summary": "无需压缩", "compressed_count": 0}
        summary_lines = []
        for m in compress_target:
            role = m.get("role", "unknown")
            content = str(m.get("content", ""))[:100]
            if content.strip():
                summary_lines.append(f"[{role}] {content}")
        summary = "上下文摘要（已压缩）：\n" + "\n".join(summary_lines[:20])
        if len(summary_lines) > 20:
            summary += f"\n... 共 {len(summary_lines)} 条压缩"
        new_msgs = system_msgs + [{"role": "system", "content": f"以下是之前对话的摘要：\n{summary}"}] + keep
        _sess.set_messages(cid, new_msgs)
        return {"ok": True, "summary": summary, "compressed_count": len(compress_target)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

# ===================================================================
# 3. Checkpoints — 对话快照
# ===================================================================
def _checkpoints_dir() -> Path:
    p = Path(_get_home()) / "checkpoints"
    p.mkdir(parents=True, exist_ok=True)
    return p

def checkpoints_list(cid: str) -> dict:
    """列出某会话的所有快照。"""
    d = _checkpoints_dir() / cid
    d.mkdir(parents=True, exist_ok=True)
    items = []
    for f in sorted(d.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                items.append({
                    "id": f.stem, "cid": cid,
                    "label": data.get("label", f.stem),
                    "created": data.get("created", datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()),
                    "msg_count": len(data.get("messages", [])),
                })
            except: pass
    return {"ok": True, "items": items}

def checkpoints_create(cid: str, label: str = "") -> dict:
    """创建当前会话的快照。"""
    try:
        import sessions as _sess
        msgs = _sess.get_messages(cid)
        if not msgs:
            return {"ok": False, "error": "会话为空"}
        cid_dir = _checkpoints_dir() / cid
        cid_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        cp_id = f"cp_{ts}"
        data = {
            "label": label or f"快照 {ts}",
            "created": datetime.datetime.now().isoformat(),
            "messages": msgs,
        }
        (cid_dir / f"{cp_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "id": cp_id, "label": data["label"], "created": data["created"]}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def checkpoints_restore(cid: str, cp_id: str) -> dict:
    """从快照恢复会话。"""
    try:
        import sessions as _sess
        p = _checkpoints_dir() / cid / f"{cp_id}.json"
        if not p.exists():
            return {"ok": False, "error": f"快照 {cp_id} 不存在"}
        data = json.loads(p.read_text(encoding="utf-8"))
        msgs = data.get("messages", [])
        if not msgs:
            return {"ok": False, "error": "快照无消息"}
        _sess.set_messages(cid, msgs)
        # 更新标题
        _sess.rename(cid, f"[恢复] {data.get('label', '')}")
        return {"ok": True, "label": data.get("label", ""), "msg_count": len(msgs)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def checkpoints_delete(cid: str, cp_id: str) -> dict:
    p = _checkpoints_dir() / cid / f"{cp_id}.json"
    if p.exists():
        p.unlink()
    return {"ok": True}

# ===================================================================
# 4. MOA — 多智能体混合（复用内核 hermes_cli.config + hermes_cli.moa_config）
# ===================================================================
# 真实机制（hermes_agent 0.19.0，agent/moa_loop.py + hermes_cli/moa_config.py 实证）：
#   - MOA 是 Hermes 的「虚拟 provider」：多个参考(顾问)模型(reference_models)各自对当前
#     任务给建议，再由一个聚合(执行)模型(aggregator)综合成最终回答。它不是一个独立命令，
#     而是当 AIAgent 的 provider=="moa" 且 model==<preset 名> 时，AIAgent.__init__
#     （agent/agent_init.py:816）自动构造 MoAClient 接管每次 LLM 调用，并通过
#     tool_progress_callback 把每个参考模型的回答以 "moa.reference" / "moa.aggregating"
#     事件透出（agent_init.py:827 的 _moa_reference_relay 转发到 tool_progress_callback）。
#   - 配置存在 HERMES_HOME/config.yaml 的 `moa` 键下，结构是「命名预设(presets)」：
#       moa:
#         default_preset: default
#         active_preset: ""          # 选中 moa 预设作为当前模型时由模型选择器/激活接口决定
#         presets:
#           default:
#             enabled: true
#             reference_models: [{provider, model}, ...]   # 参考/顾问模型（可多个）
#             aggregator: {provider, model}                # 聚合/执行模型（唯一）
#             reference_temperature: null
#             aggregator_temperature: null
#             max_tokens: 4096
#             reference_max_tokens: null   # 仅限顾问输出长度(降延迟)，聚合模型不被限
#             fanout: per_iteration        # per_iteration(每轮工具迭代重跑) | user_turn(每轮用户对话跑一次)
#   - 内核不可用时优雅降级（available:False）。绝不手写 schema——全部交给
#     hermes_cli.moa_config.normalize_moa_config / resolve_moa_preset / set_active_moa_preset
#     与 hermes_cli.config.load_config / save_config，保证与内核零漂移。
def _moa_cfg_mod():
    """惰性导入内核 moa_config + config 模块；不可用返回 (None, None)。"""
    try:
        import hermes_cli.config as _cfg
        import hermes_cli.moa_config as _moa
        return _cfg, _moa
    except Exception:  # noqa: BLE001
        return None, None

def _moa_home():
    """MOA 配置与 Hermes 其余状态同目录：复用 _get_home()（= hermes_config.get_hermes_home()），
    确保与 backup/snapshot 等落在【同一个】HERMES_HOME，不依赖 HERMES_HOME 环境变量是否被显式设置。"""
    return _get_home()

def moa_get() -> dict:
    cfg_mod, moa_mod = _moa_cfg_mod()
    if cfg_mod is None or moa_mod is None:
        return {"ok": True, "available": False,
                "error": "内核 hermes_cli.config / moa_config 不可用",
                "presets": {}, "default_preset": "", "active_preset": "",
                "reference_models": [], "aggregator": None, "fanout": "per_iteration",
                "enabled": False, "active_in_agent": False, "agent_model": ""}
    try:
        home = _moa_home()
        raw = cfg_mod.load_config()
        norm = moa_mod.normalize_moa_config(raw.get("moa") if isinstance(raw, dict) else None)
        # 当前是否真的以 moa 作为活动模型（从 llm.json 顶层 vendor 判断）
        try:
            from hermes_config import get_active_model_cfg
            _amc = get_active_model_cfg(None) or {}
            norm["agent_provider"] = _amc.get("provider", "")
            norm["agent_model"] = _amc.get("model", "")
            norm["active_in_agent"] = (_amc.get("provider") == "moa")
        except Exception:
            norm["active_in_agent"] = False
            norm["agent_model"] = ""
        return {"ok": True, "available": True, **norm}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "presets": {}}

def moa_save(config: dict) -> dict:
    """保存 MoA 预设（前端整体提交 presets + 可选 default_preset/active_preset）。
    与 config.yaml 现有 moa 合并后归一化落盘，绝不丢弃 active_preset 等字段。"""
    cfg_mod, moa_mod = _moa_cfg_mod()
    if cfg_mod is None or moa_mod is None:
        return {"ok": False, "error": "内核 hermes_cli.config / moa_config 不可用"}
    try:
        home = _moa_home()
        raw = cfg_mod.load_config()
        if not isinstance(raw, dict):
            raw = {}
        existing = raw.get("moa") or {}
        merged = dict(existing) if isinstance(existing, dict) else {}
        inc = config if isinstance(config, dict) else {}
        if isinstance(inc.get("presets"), dict):
            merged["presets"] = inc["presets"]
        for key in ("default_preset", "active_preset", "enabled"):
            if key in inc:
                merged[key] = inc[key]
        raw["moa"] = moa_mod.normalize_moa_config(merged)
        cfg_mod.save_config(raw)
        return moa_get()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def moa_set_active(preset_name: str = "") -> dict:
    """激活/取消激活一个 MoA 预设作为当前模型。
    name 非空 → ①config.yaml moa.active_preset 置该预设；②llm.json 顶层 vendor="moa"、
      model=<preset>，使 get_active_model_cfg 解析出 provider=="moa"，从而 AIAgent 自动
      走 MoAClient（agent_init.py:816）。
    name 为空 → 仅清空 config.yaml active_preset（切回普通模型由模型选择器负责，不动 llm.json）。"""
    cfg_mod, moa_mod = _moa_cfg_mod()
    if cfg_mod is None or moa_mod is None:
        return {"ok": False, "error": "内核 hermes_cli.config / moa_config 不可用"}
    name = (preset_name or "").strip()
    try:
        home = _moa_home()
        raw = cfg_mod.load_config()
        if not isinstance(raw, dict):
            raw = {}
        moa = raw.get("moa")
        if name:
            moa_mod.resolve_moa_preset(moa or {}, name)  # KeyError → 预设不存在
            raw["moa"] = moa_mod.set_active_moa_preset(moa, name)
        else:
            if isinstance(moa, dict):
                moa = dict(moa)
                moa["active_preset"] = ""
                raw["moa"] = moa
        cfg_mod.save_config(raw)
        # 同步 llm.json 顶层 active（仅激活时改；取消激活不动 llm.json，避免误清用户模型）
        if name:
            from hermes_config import get_llm_config, save_llm_config
            ll = get_llm_config()
            ll["vendor"] = "moa"
            ll["provider"] = "moa"
            ll["model"] = name
            ll["base_url"] = ""
            ll["api_key"] = ""
            save_llm_config(ll)
        return moa_get()
    except KeyError:
        return {"ok": False, "error": f"MoA 预设不存在：{name}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def moa_delete(preset_name: str) -> dict:
    cfg_mod, moa_mod = _moa_cfg_mod()
    if cfg_mod is None or moa_mod is None:
        return {"ok": False, "error": "内核 hermes_cli.config / moa_config 不可用"}
    name = (preset_name or "").strip()
    if not name:
        return {"ok": False, "error": "缺少 preset 名"}
    try:
        home = _moa_home()
        raw = cfg_mod.load_config()
        if not isinstance(raw, dict):
            raw = {}
        norm = moa_mod.normalize_moa_config(raw.get("moa") or {})
        if name not in norm["presets"]:
            return {"ok": False, "error": f"MoA 预设不存在：{name}"}
        if len(norm["presets"]) <= 1:
            return {"ok": False, "error": "至少保留一个 MoA 预设，无法删除最后一个"}
        del norm["presets"][name]
        if norm.get("default_preset") == name:
            norm["default_preset"] = next(iter(norm["presets"]))
        if norm.get("active_preset") == name:
            norm["active_preset"] = ""
        raw["moa"] = norm
        cfg_mod.save_config(raw)
        return moa_get()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def moa_encode_turn(prompt: str, preset: str = "") -> dict:
    """生成一次性 /moa 标记串（__HERMES_MOA_TURN_V1__...），供「只能发文本」的前端。
    把该串作为普通用户消息发送，conversation_loop 会自动解码并跑一次 MoA 单轮后恢复原模型。
    预设配置内嵌于标记中，无需切换活动模型即可单条试用 MOA。"""
    cfg_mod, moa_mod = _moa_cfg_mod()
    if cfg_mod is None or moa_mod is None:
        return {"ok": False, "error": "内核 hermes_cli.config / moa_config 不可用"}
    try:
        return {"ok": True, "encoded": moa_mod.encode_moa_turn(prompt, None, preset or None)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

# ===================================================================
# 5. Backup — 备份/恢复（复用内核 hermes_cli.backup._write_full_zip_backup）
# ===================================================================
# 真实机制（hermes_agent 0.19.0，hermes_cli/backup.py 实证）：
#   - 完整备份 = 将整个 HERMES_HOME 打包为 ZIP 归档（hermes backup / hermes import）。
#   - 内核 _write_full_zip_backup(out_path, hermes_root) 负责真正的归档：
#       · 相同的排除规则 _EXCLUDED_DIRS / _EXCLUDED_SUFFIXES / _EXCLUDED_NAMES
#         （hermes-agent/__pycache__/.git/node_modules/backups/checkpoints/.venv/venv/
#          site-packages/.cache/.tox/.nox/.pytest_cache/.mypy_cache/.ruff_cache +
#          .pyc/.pyo/.db-wal/.db-shm/.db-journal + gateway.pid/cron.pid）——
#          不排这些，单个插件 venv / MCP 安装 / pip·uv 缓存会被逐文件遍历，备份膨胀到
#          数十万条目、卡住数小时（官方注释原文：『backup stuck for days / 426543 files』）。
#       · .db 用 sqlite3.backup() 做 WAL 安全拷贝（对正在打开的库也能一致快照），
#         且不打包 .db-wal/.db-shm/.db-journal 等 sidecar（否则下次打开会 torn restore）。
#   - 因此这里只做薄封装：优先复用内核 _write_full_zip_backup；内核缺失时降级为
#     使用「与内核镜像一致」的本地排除集的手写 walk（保证排除规则不错）。
#   - 备份存储位置与状态快照保持一致：<HERMES_HOME>/backups/（内核 walk 天然排除
#     backups/，不会无限嵌套；恢复时整体覆盖 HERMES_HOME 也与快照语义一致）。
#   - 恢复前自动用内核 create_quick_snapshot 做一个轻量「恢复前快照」放到
#     <HERMES_HOME>/state-snapshots/，作为一键回滚安全网。

# 本地镜像内核排除集（仅在内核缺失时作为兜底 walk 使用；与 hermes_cli.backup 的
# _EXCLUDED_DIRS/_EXCLUDED_SUFFIXES/_EXCLUDED_NAMES 保持同步）。
_BACKUP_EXCLUDED_DIRS = {
    "hermes-agent", "__pycache__", ".git", "node_modules", "backups",
    "checkpoints", ".venv", "venv", "site-packages", ".cache", ".tox",
    ".nox", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}
_BACKUP_EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".db-wal", ".db-shm", ".db-journal")
_BACKUP_EXCLUDED_NAMES = {"gateway.pid", "cron.pid"}
# 镜像内核 _IMPORT_SKIP_NAMES / _SECRET_FILE_NAMES（恢复时不覆盖机器专属运行时状态、
# 机密文件收紧权限）。
_BACKUP_IMPORT_SKIP_NAMES = {
    "gateway_state.json", "gateway.pid", "cron.pid", "gateway.lock", "processes.json",
}
_BACKUP_SECRET_FILE_NAMES = {".env", "auth.json", "state.db"}


def _backup_mod():
    """惰性导入内核 backup 模块；不可用返回 None。"""
    try:
        import hermes_cli.backup as _bk
        return _bk
    except Exception:  # noqa: BLE001
        return None


def _backup_dir() -> Path:
    """完整备份存储目录：<HERMES_HOME>/backups/（与状态快照同属 HERMES_HOME，
    符合路径一致性红线；内核 walk 会排除 backups/ 防嵌套）。"""
    p = Path(_get_home()) / "backups"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _backup_search_dirs() -> list:
    """完整备份搜索目录：新位置 <HERMES_HOME>/backups/ 优先；若旧位置
    <HERMES_HOME>/features/backups/ 仍存在则一并纳入（向后兼容，避免丢备份）。"""
    home = Path(_get_home())
    dirs = [home / "backups"]
    legacy = home / "features" / "backups"
    if legacy.is_dir():
        dirs.append(legacy)
    for d in dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception:  # noqa: BLE001
            pass
    return dirs


def _find_backup(name: str):
    for d in _backup_search_dirs():
        p = d / name
        if p.is_file():
            return p
    return None


def _wal_copy_db(src: Path, dst: Path) -> bool:
    """WAL 安全拷贝 SQLite 库：优先复用内核 _safe_copy_db；不可用时回退 shutil.copy2。"""
    bk = _backup_mod()
    try:
        fn = getattr(bk, "_safe_copy_db", None) if bk is not None else None
        if fn is not None:
            return bool(fn(Path(src), Path(dst)))
    except Exception:  # noqa: BLE001
        pass
    try:
        shutil.copy2(str(src), str(dst))
        return True
    except Exception:  # noqa: BLE001
        return False


def _should_exclude_local(rel: Path) -> bool:
    """镜像内核 _should_exclude：hermes-agent 仅排除根级，其余排除集全级生效。"""
    parts = rel.parts
    for part in parts:
        if part not in _BACKUP_EXCLUDED_DIRS:
            continue
        if part == "hermes-agent" and part != parts[0]:
            continue
        return True
    name = rel.name
    if name in _BACKUP_EXCLUDED_NAMES:
        return True
    if name.endswith(_BACKUP_EXCLUDED_SUFFIXES):
        return True
    return False


def backup_create() -> dict:
    """将整个 HERMES_HOME 打包为 ZIP（完整归档备份）。

    优先复用内核 hermes_cli.backup._write_full_zip_backup（保证与 `hermes import`
    完全一致的排除规则 + WAL 安全 .db 拷贝 + 不打包 db sidecar）；内核缺失时降级为
    带「镜像排除集」的本地 walk（排除规则与内核一致，不会把 venv/cache 也打包进去）。"""
    try:
        home = Path(_get_home())
        if not home.is_dir():
            return {"ok": False, "error": f"HERMES_HOME 不存在：{home}"}
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"hermes_backup_{ts}.zip"
        dst = _backup_dir() / name
        bk = _backup_mod()
        # 优先内核
        if bk is not None and hasattr(bk, "_write_full_zip_backup"):
            try:
                res = bk._write_full_zip_backup(dst, home)
                if res is None:
                    return {"ok": False, "error": "没有可备份的文件（HERMES_HOME 为空）"}
                size_mb = dst.stat().st_size / (1024 * 1024)
                return {"ok": True, "name": name, "path": str(dst),
                        "size_mb": round(size_mb, 2), "via": "kernel"}
            except Exception:  # noqa: BLE001
                pass  # 落到本地兜底
        # 本地兜底 walk（镜像内核排除集）
        try:
            with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for root, dirs, files in os.walk(home):
                    dp = Path(root)
                    rel_dir = dp.relative_to(home)
                    is_root = rel_dir == Path(".")
                    dirs[:] = [
                        d for d in dirs
                        if d not in _BACKUP_EXCLUDED_DIRS
                        or (d == "hermes-agent" and not is_root)
                    ]
                    for f in files:
                        fp = dp / f
                        try:
                            rel = fp.relative_to(home)
                        except ValueError:
                            continue
                        if _should_exclude_local(rel):
                            continue
                        arcname = str(rel)
                        try:
                            if fp.suffix == ".db":
                                import tempfile as _tf
                                tmp = Path(_tf.mkdtemp()) / f
                                try:
                                    if _wal_copy_db(fp, tmp):
                                        zf.write(str(tmp), arcname)
                                    else:
                                        zf.write(str(fp), arcname)
                                finally:
                                    try:
                                        tmp.unlink(missing_ok=True)
                                    except Exception:  # noqa: BLE001
                                        pass
                                    try:
                                        tmp.parent.rmdir()
                                    except Exception:  # noqa: BLE001
                                        pass
                            else:
                                zf.write(str(fp), arcname)
                        except Exception:  # noqa: BLE001
                            continue
        except Exception as e:  # noqa: BLE001
            try:
                dst.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
        size_mb = dst.stat().st_size / (1024 * 1024)
        return {"ok": True, "name": name, "path": str(dst),
                "size_mb": round(size_mb, 2), "via": "fallback"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def backup_list() -> dict:
    items = []
    seen = set()
    for d in _backup_search_dirs():
        for f in sorted(d.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix == ".zip" and f.name not in seen:
                seen.add(f.name)
                items.append({
                    "name": f.name,
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    "created": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
    return {"ok": True, "items": items}


def backup_restore(name: str) -> dict:
    """从完整备份 ZIP 恢复（整体覆盖 HERMES_HOME）。

    恢复前用内核 create_quick_snapshot 做「恢复前快照」(放 <HERMES_HOME>/state-snapshots/)
    作为一键回滚安全网（诚实：这是核心状态快照，非完整副本）。恢复过程带 zip-slip 防护，
    绝不解压到 HERMES_HOME 之外；并镜像内核不覆盖机器专属运行时状态、机密文件收紧权限。"""
    try:
        p = _find_backup(name)
        if p is None:
            return {"ok": False, "error": f"备份文件 {name} 不存在"}
        home = Path(_get_home())
        home_res = home.resolve()
        # 恢复前快照（核心状态）作为安全网
        pre_snap_id = None
        bk = _backup_mod()
        skip_names = _BACKUP_IMPORT_SKIP_NAMES
        secret_names = _BACKUP_SECRET_FILE_NAMES
        if bk is not None:
            skip_names = getattr(bk, "_IMPORT_SKIP_NAMES", skip_names)
            secret_names = getattr(bk, "_SECRET_FILE_NAMES", secret_names)
            fn = getattr(bk, "create_quick_snapshot", None)
            if fn is not None:
                try:
                    pre_snap_id = fn(label=f"pre-restore-{name}", hermes_home=home_res)
                except Exception:  # noqa: BLE001
                    pre_snap_id = None
        restored = 0
        with zipfile.ZipFile(p, "r") as zf:
            for member in zf.namelist():
                # zip-slip 防护：解压路径必须落在 home 内，否则跳过（防越界写入）
                dest = (home_res / member).resolve()
                if dest != home_res and home_res not in dest.parents:
                    continue
                if member.endswith("/"):
                    dest.mkdir(parents=True, exist_ok=True)
                    continue
                # 不覆盖机器专属的运行时状态（镜像内核 _IMPORT_SKIP_NAMES）
                if Path(member).name in skip_names:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with zf.open(member) as src, open(str(dest), "wb") as out:
                        shutil.copyfileobj(src, out)
                    # 机密文件收紧权限（镜像内核 _SECRET_FILE_NAMES）
                    if Path(member).name in secret_names:
                        try:
                            os.chmod(str(dest), 0o600)
                        except OSError:
                            pass
                    restored += 1
                except Exception:  # noqa: BLE001
                    pass
        return {"ok": True, "restored_from": name, "restored": restored,
                "pre_restore_snapshot": pre_snap_id}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def backup_delete(name: str) -> dict:
    p = _find_backup(name)
    if p is not None:
        p.unlink()
    return {"ok": True}

# ===================================================================
# 5.1 State Snapshots — Hermes 原生状态快照（复用内核 hermes_cli.backup）
# ===================================================================
# 真实机制（hermes_agent 0.19.0，hermes_cli/backup.py 实证）：
#   - 快照 = 对 HERMES_HOME 下一组「关键状态文件」（state.db / config.yaml / .env /
#     auth.json / kanban.db / projects.db / response_store.db / memory_store.db /
#     verification_evidence.db / cron/jobs.json / channel_*.json / 配对存储等）做
#     一次文件系统级备份，存入 <HERMES_HOME>/state-snapshots/<时间戳[-标签]>/，并写
#     manifest.json（id/timestamp/label/file_count/total_size/files）。
#   - 与「对话快照」(checkpoints，单会话消息 JSON) 和「完整备份」(backup_*，全量 ZIP
#     归档) 都不同：它轻量、只备份核心状态、可一键回滚，且 .db 用 sqlite3.backup()
#     做 WAL 安全拷贝（即使数据库正被本应用打开也能拿到一致副本）。
#   - 因此这里只做薄封装：复用内核 create/list/restore/prune_quick_snapshot，绝不手写
#     文件拷贝 / sqlite 读取；内核不可用时优雅降级（available:False）。
def _backup_mod():
    """惰性导入内核 backup 模块；不可用返回 None。"""
    try:
        import hermes_cli.backup as _bk
        return _bk
    except Exception:  # noqa: BLE001
        return None

def _snapshot_home():
    """返回桌面冻结的 HERMES_HOME，与 backup_* 完全一致：复用 _get_home()
    （= hermes_config.get_hermes_home()，解析顺序 HERMES_DESKTOP_HOME →
    <exe>/hermes_data 冻结态 → <example>/.hermes_data 开发态）。

    关键：显式传给内核 hermes_cli.backup，确保快照与完整备份落在【同一个】
    数据目录，且不依赖 HERMES_HOME 环境变量是否被 materialize_hermes_env 显式
    设置（内核默认回退是 ~/.hermes，绝不能用错地方）。"""
    return _get_home()

def snapshots_list(limit: int = 50) -> dict:
    bk = _backup_mod()
    if bk is None:
        return {"ok": True, "available": False, "error": "内核 hermes_cli.backup 不可用",
                "snapshots": [], "home": None}
    try:
        home = _snapshot_home()
        snaps = bk.list_quick_snapshots(limit=int(limit or 50), hermes_home=home)
        items = []
        for s in snaps:
            items.append({
                "id": s.get("id"),
                "label": s.get("label") or "",
                "timestamp": s.get("timestamp") or "",
                "file_count": s.get("file_count", 0),
                "total_size": s.get("total_size", 0),
                "files": sorted((s.get("files") or {}).keys()),
            })
        return {"ok": True, "available": True, "home": str(home) if home else None,
                "snapshots": items}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "snapshots": []}

def snapshots_create(label: str = "") -> dict:
    bk = _backup_mod()
    if bk is None:
        return {"ok": False, "error": "内核 hermes_cli.backup 不可用"}
    try:
        home = _snapshot_home()
        lab = (label or "").strip() or None
        snap_id = bk.create_quick_snapshot(label=lab, hermes_home=home)
        if not snap_id:
            return {"ok": False, "error": "当前没有可快照的状态文件（应用可能尚未产生任何状态）"}
        return {"ok": True, "id": snap_id, "label": lab or "", "home": str(home) if home else None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def snapshots_restore(snap_id: str) -> dict:
    bk = _backup_mod()
    if bk is None:
        return {"ok": False, "error": "内核 hermes_cli.backup 不可用"}
    snap_id = (snap_id or "").strip()
    if not snap_id:
        return {"ok": False, "error": "缺少 snap_id"}
    try:
        home = _snapshot_home()
        ok = bk.restore_quick_snapshot(snap_id, hermes_home=home)
        if not ok:
            return {"ok": False, "error": f"快照 {snap_id} 不存在或恢复失败"
                                     f"（可能被本应用占用，请先关闭应用再试）"}
        # 内核对已打开的 .db 做原子替换；恢复后需重启应用才能让 state.db 等变更生效。
        return {"ok": True, "id": snap_id, "restart_required": True}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def snapshots_prune(keep: int = 20) -> dict:
    bk = _backup_mod()
    if bk is None:
        return {"ok": False, "error": "内核 hermes_cli.backup 不可用"}
    try:
        home = _snapshot_home()
        keep = int(keep) if keep else 20
        deleted = bk.prune_quick_snapshots(keep=keep, hermes_home=home)
        return {"ok": True, "deleted": deleted, "keep": keep}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

# ===================================================================
# 6. Profiles — 配置管理（复用 Hermes 原生 hermes_cli.profiles）
# ===================================================================
# 真实 Profiles 机制（hermes-agent 0.19.0+，hermes_cli/profiles.py 实证）：
#   Profile = 一个完全独立的 HERMES_HOME 目录，默认位于 <root>/profiles/<name>/；
#   "default" = <root> 本身（标准部署是 ~/.hermes；examples 冻结态是 <exe>/hermes_data），
#   向后兼容、零迁移。切换 = set_active_profile() 写 <root>/active_profile 文件
#   （下次启动生效），或运行时经 -p <name> 标志 / HERMES_HOME_OVERRIDE 改变
#   HERMES_HOME；内核【不识别】HERMES_PROFILE 这个环境变量名（旧版自造机制误用）。
#   每个 profile 自带 config.yaml/.env/memory/sessions/skills/gateway/cron/logs，
#   可选 profile.yaml 存描述。list_profiles() 返回丰富元信息
#   （gateway_running/model/provider/skill_count/alias/description…）。
#   路径锚点：profiles 根 = get_default_hermes_root()/"profiles"，而
#   get_default_hermes_root() 只读 os.environ["HERMES_HOME"]（不读 ContextVar
#   override）；examples 已在导入前设好该 env，故内核 profiles 与 examples 同落
#   <HERMES_HOME>/profiles，路径一致（_ensure_home_env 再幂等兜底，防双轨漂移）。
#   本封装复用内核，绝不手写目录 walk、不发明切换变量；内核缺失→available:False 降级。
def _profiles_mod():
    """惰性导入内核 profiles 模块；不可用返回 None。"""
    try:
        import hermes_cli.profiles as pm
        return pm
    except Exception:
        return None

def _ensure_home_env():
    """确保内核 profiles 看到的 HERMES_HOME 与 examples 一致。

    内核 get_default_hermes_root() 只读 os.environ['HERMES_HOME']（不读
    ContextVar override）。examples 虽已在启动早期设置，这里再幂等兜底一次，
    防止极端路径下内核把 profiles 落到 ~/.hermes/profiles 造成双轨漂移。
    """
    try:
        os.environ["HERMES_HOME"] = _get_home()
    except Exception:
        pass

def profiles_list() -> dict:
    pm = _profiles_mod()
    if pm is None:
        return {"ok": True, "available": False, "items": [], "current": "default",
                "note": "hermes_cli 不可用，Profiles 功能不可用"}
    try:
        _ensure_home_env()
        current = pm.get_active_profile()
        items = []
        for info in pm.list_profiles():
            items.append({
                "name": info.name,
                "is_current": info.name == current,
                "is_default": info.is_default,
                "path": str(info.path),
                "gateway_running": bool(info.gateway_running),
                "model": info.model,
                "provider": info.provider,
                "has_env": bool(info.has_env),
                "skill_count": int(info.skill_count or 0),
                "alias_name": info.alias_name,
                "description": info.description or "",
            })
        return {"ok": True, "available": True, "items": items, "current": current}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "available": True, "error": f"{type(e).__name__}: {e}"}

def profiles_create(name: str, clone_from: str = None) -> dict:
    pm = _profiles_mod()
    if pm is None:
        return {"ok": False, "available": False, "error": "hermes_cli 不可用，无法创建 Profile"}
    try:
        name = (name or "").strip()
        if not name:
            return {"ok": False, "error": "名称不能为空"}
        # 内核接受大小写/标题输入，这里先 normalize + validate 做友好校验
        # （正则 ^[a-z0-9][a-z0-9_-]{0,63}$，禁止 reserved 名与 hermes 子命令名）
        canon = pm.normalize_profile_name(name)
        pm.validate_profile_name(canon)
        _ensure_home_env()
        opts = {}
        if clone_from:
            clone_from = pm.normalize_profile_name(clone_from)
            pm.validate_profile_name(clone_from)
            opts["clone_from"] = clone_from
        # 内核 create_profile 会建完整独立 HERMES_HOME（8 个子目录 + 克隆
        # config/.env/SOUL.md/skills/memories + 写 .env(0600) + 注册 gateway
        # 服务[host 为 no-op]）；不自动 seed 技能（职责在 hermes update / dashboard）
        d = pm.create_profile(canon, **opts)
        return {"ok": True, "name": canon, "path": str(d),
                "note": "已创建独立 Profile 目录（完整 HERMES_HOME）。技能安装请在该 Profile 内执行 hermes skills install 或 hermes update。"}
    except (ValueError, FileExistsError) as e:
        return {"ok": False, "error": str(e)}

def profiles_switch(name: str) -> dict:
    pm = _profiles_mod()
    if pm is None:
        return {"ok": False, "available": False, "error": "hermes_cli 不可用，无法切换 Profile"}
    try:
        name = (name or "").strip()
        canon = pm.normalize_profile_name(name)
        _ensure_home_env()
        # 写 <root>/active_profile 文件；default 会删除该文件。下次启动生效。
        pm.set_active_profile(canon)
        return {"ok": True, "current": canon,
                "note": "已写入 active_profile，将在下次启动时生效（当前运行进程不会切换）。"}
    except (ValueError, FileNotFoundError) as e:
        return {"ok": False, "error": str(e)}

def profiles_delete(name: str) -> dict:
    pm = _profiles_mod()
    if pm is None:
        return {"ok": False, "available": False, "error": "hermes_cli 不可用，无法删除 Profile"}
    try:
        name = (name or "").strip()
        canon = pm.normalize_profile_name(name)
        _ensure_home_env()
        # 内核 delete_profile(yes=True) 会停 gateway / 停 profile 后端进程 /
        # 删 wrapper 脚本 / 清理服务 / retry rmtree，比裸 shutil.rmtree 安全得多
        pm.delete_profile(canon, yes=True)
        return {"ok": True, "name": canon}
    except (ValueError, FileNotFoundError) as e:
        return {"ok": False, "error": str(e)}

def profiles_export(name: str, output_path: str = "") -> dict:
    """导出 Profile 为 tar.gz 归档（复用内核 hermes_cli.profiles.export_profile）。"""
    pm = _profiles_mod()
    if pm is None:
        return {"ok": False, "available": False, "error": "hermes_cli 不可用，无法导出 Profile"}
    try:
        name = (name or "").strip()
        canon = pm.normalize_profile_name(name)
        _ensure_home_env()
        out = pm.export_profile(canon, (output_path or "").strip())
        return {"ok": True, "name": canon, "path": str(out)}
    except (ValueError, FileNotFoundError) as e:
        return {"ok": False, "error": str(e)}

def profiles_import(archive_path: str, name: str = "") -> dict:
    """导入 Profile 归档（复用内核 hermes_cli.profiles.import_profile）。"""
    pm = _profiles_mod()
    if pm is None:
        return {"ok": False, "available": False, "error": "hermes_cli 不可用，无法导入 Profile"}
    try:
        ap = (archive_path or "").strip()
        if not ap:
            return {"ok": False, "error": "归档路径不能为空"}
        out = pm.import_profile(ap, (name or "").strip() or None)
        return {"ok": True, "path": str(out)}
    except (ValueError, FileNotFoundError) as e:
        return {"ok": False, "error": str(e)}

def profiles_rename(old_name: str, new_name: str) -> dict:
    """重命名 Profile：目录/wrapper 脚本/服务/active_profile（复用内核 rename_profile）。"""
    pm = _profiles_mod()
    if pm is None:
        return {"ok": False, "available": False, "error": "hermes_cli 不可用，无法重命名 Profile"}
    try:
        old = pm.normalize_profile_name((old_name or "").strip())
        new = pm.normalize_profile_name((new_name or "").strip())
        _ensure_home_env()
        out = pm.rename_profile(old, new)
        return {"ok": True, "old": old, "new": new, "path": str(out)}
    except (ValueError, FileNotFoundError) as e:
        return {"ok": False, "error": str(e)}


# ===================================================================
# 7. Projects — 项目管理（Hermes 原生，复用内核 hermes_cli.projects_db）
# -------------------------------------------------------------------
# Hermes 真实机制（hermes-agent 0.19.0 实证，hermes_cli/projects_db.py）：
#   Project = 人类命名、跨多文件夹的工作区，per-profile 存于 $HERMES_HOME/projects.db
#   （SQLite，与 sessions/config/cron/kanban 同目录）。表：projects(id/slug/name/
#   description/icon/color/board_slug/primary_path/created_at/archived)、
#   project_folders(project_id,path,label,is_primary,added_at)、
#   project_meta(key/value，存 active_id 活动项目指针)、
#   discovered_repos(root,label,last_seen，文件系统扫描缓存)。
#   关键语义：① 桌面会话分组——会话 cwd 落在某项目文件夹下即归属该项目（最长前缀匹配）；
#   ② 可绑定 kanban board(board_slug)→ 任务 worktree 用确定性分支 <slug>/<task-id>；
#   ③ 活动项目指针(set_active/get_active_id)。Agent 侧有 project 工具集
#   （project_list/project_create/project_switch），切换时经 set_project_workspace_callback
#   重锚会话 cwd + 侧栏跟随。
#   本封装复用内核 projects_db，绝不手写 schema / 不落独立 JSON；内核不可用时 available:False。
def _projects_db_mod():
    """惰性导入内核 projects_db 模块；不可用返回 None。"""
    try:
        import hermes_cli.projects_db as _pdb
        return _pdb
    except Exception:  # noqa: BLE001
        return None


def _proj_to_ui(p, active_id):
    return {
        "id": p.id, "slug": p.slug, "name": p.name,
        "description": p.description, "icon": p.icon, "color": p.color,
        "board_slug": p.board_slug, "primary_path": p.primary_path,
        "archived": bool(p.archived), "created_at": p.created_at,
        "folders": [{"path": f.path, "label": f.label, "is_primary": bool(f.is_primary)}
                    for f in (p.folders or [])],
        "active": (p.id == active_id),
    }


def projects_list(include_archived: bool = False) -> dict:
    pdb = _projects_db_mod()
    if pdb is None:
        return {"ok": True, "available": False,
                "error": "内核 hermes_cli.projects_db 不可用",
                "items": [], "active_id": None}
    try:
        with pdb.connect_closing() as conn:
            active = pdb.get_active_id(conn)
            projs = pdb.list_projects(conn, include_archived=include_archived)
        return {"ok": True, "available": True, "active_id": active,
                "items": [_proj_to_ui(p, active) for p in projs]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "items": [], "active_id": None}


def projects_create(payload: dict) -> dict:
    pdb = _projects_db_mod()
    if pdb is None:
        return {"ok": False, "error": "内核 hermes_cli.projects_db 不可用"}
    name = (payload.get("name") or "").strip()
    if not name:
        return {"ok": False, "error": "name 必填"}
    folders = [str(x).strip() for x in (payload.get("folders") or []) if str(x).strip()]
    try:
        with pdb.connect_closing() as conn:
            pid = pdb.create_project(
                conn, name=name, slug=payload.get("slug") or None,
                folders=folders, primary_path=payload.get("primary_path") or None,
                description=payload.get("description") or None,
                icon=payload.get("icon") or None, color=payload.get("color") or None,
                board_slug=payload.get("board_slug") or None)
            if payload.get("set_active"):
                pdb.set_active(conn, pid)
            p = pdb.get_project(conn, pid)
        return {"ok": True, "project": _proj_to_ui(p, pid)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def projects_update(pid: str, payload: dict) -> dict:
    pdb = _projects_db_mod()
    if pdb is None:
        return {"ok": False, "error": "内核 hermes_cli.projects_db 不可用"}
    try:
        with pdb.connect_closing() as conn:
            ok = pdb.update_project(
                conn, pid, name=payload.get("name"), description=payload.get("description"),
                icon=payload.get("icon"), color=payload.get("color"),
                board_slug=payload.get("board_slug"))
            if not ok:
                return {"ok": False, "error": f"项目 {pid} 不存在"}
            p = pdb.get_project(conn, pid)
            active = pdb.get_active_id(conn)
        return {"ok": True, "project": _proj_to_ui(p, active)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def projects_delete(pid: str) -> dict:
    pdb = _projects_db_mod()
    if pdb is None:
        return {"ok": False, "error": "内核 hermes_cli.projects_db 不可用"}
    try:
        with pdb.connect_closing() as conn:
            ok = pdb.delete_project(conn, pid)
        return {"ok": bool(ok), "error": None if ok else f"项目 {pid} 不存在"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def projects_activate(pid: str = "") -> dict:
    """设置/清除活动项目指针（pid 为空则清除）。"""
    pdb = _projects_db_mod()
    if pdb is None:
        return {"ok": False, "error": "内核 hermes_cli.projects_db 不可用"}
    try:
        with pdb.connect_closing() as conn:
            pdb.set_active(conn, pid or None)
            active = pdb.get_active_id(conn)
        return {"ok": True, "active_id": active}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def projects_add_folder(pid: str, path: str, primary: bool = False) -> dict:
    pdb = _projects_db_mod()
    if pdb is None:
        return {"ok": False, "error": "内核 hermes_cli.projects_db 不可用"}
    try:
        with pdb.connect_closing() as conn:
            pdb.add_folder(conn, pid, path, is_primary=bool(primary))
            p = pdb.get_project(conn, pid)
            active = pdb.get_active_id(conn)
        return {"ok": True, "project": _proj_to_ui(p, active)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def projects_remove_folder(pid: str, path: str) -> dict:
    pdb = _projects_db_mod()
    if pdb is None:
        return {"ok": False, "error": "内核 hermes_cli.projects_db 不可用"}
    try:
        with pdb.connect_closing() as conn:
            ok = pdb.remove_folder(conn, pid, path)
            p = pdb.get_project(conn, pid)
            active = pdb.get_active_id(conn)
        return {"ok": bool(ok), "project": _proj_to_ui(p, active) if p else None}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

# ===================================================================
# 8. Blueprints — 自动化蓝图（Automation Blueprints，Hermes 原生内核）
# ===================================================================
# 真实机制（hermes_agent 0.19.0，cron/blueprint_catalog.py + hermes_cli/blueprint_cmd.py 实证）：
#   - Blueprint = 参数化「自动化模板」，单一事实来源是 cron.blueprint_catalog.CATALOG
#     （内置、只读目录，无用户自定义蓝图 API）。每个蓝图含：
#       key/title/description/category/tags + schedule_template(cron 占位符)
#       + prompt_template(可含 {slot}) + slots[](BlueprintSlot: name/type[time|enum|
#       text|weekdays]/label/default/options/optional/help/strict)。
#   - 桌面端接入范式（与原生 dashboard/GUI 一致）：选蓝图 → 按 slots 渲染表单 →
#     提交 fill_blueprint(blueprint, values, origin=None) → cron.jobs.create_job(**spec)
#     得到一个真实定时任务，落入 HERMES_HOME/cron/jobs.json，由本应用 cron 调度线程
#     到期触发执行（与「定时任务中心」共用同一存储与调度器，绝不另起一套）。
#   - 内核不可用时 available:False 降级；fill 校验失败（BlueprintFillError）返回
#     kind='validation' 的错误，供表单逐字段提示。
# 反模式红线：旧版把 Blueprint 当成「对话提示词模板」自己写 {name,prompt,category}
# 存 blueprints.json —— 完全脱离内核、永不执行。已废弃。
def _blueprint_catalog_mod():
    """惰性导入内核 blueprint_catalog 模块；不可用返回 None（降级 available:False）。"""
    try:
        import cron.blueprint_catalog as m
        return m
    except Exception:  # noqa: BLE001
        return None


def _cron_jobs_mod():
    """惰性导入内核 cron.jobs 模块；不可用返回 None。"""
    try:
        import cron.jobs as m
        return m
    except Exception:  # noqa: BLE001
        return None


def blueprints_list() -> dict:
    """列出 Hermes 原生自动化蓝图目录（只读、内置）。"""
    mod = _blueprint_catalog_mod()
    if mod is None:
        return {"ok": True, "available": False, "items": [],
                "error": "Blueprint 模块不可用（cron 未安装？）"}
    try:
        items = [mod.blueprint_catalog_entry(b) for b in mod.CATALOG]
        return {"ok": True, "available": True, "items": items}
    except Exception as e:  # noqa: BLE001
        return {"ok": True, "available": False, "items": [],
                "error": f"{type(e).__name__}: {e}"}


def blueprints_fill(key: str, values: dict | None = None) -> dict:
    """按蓝图 key + 用户填写的 slot 值，创建真实定时任务。

    返回 {ok, job:{id,name,schedule_display,deliver,next_run_at}} 或
    {ok:False, kind:'validation'|'notfound'|'create', error}。
    """
    values = values or {}
    cat = _blueprint_catalog_mod()
    if cat is None:
        return {"ok": False, "available": False,
                "error": "Blueprint 模块不可用（cron 未安装？）"}
    bp = cat.get_blueprint(key)
    if bp is None:
        return {"ok": False, "kind": "notfound", "error": f"未找到蓝图：{key}"}
    # 校验 + 翻译为 create_job 参数（内核保证无第二套作业引擎）
    try:
        spec = cat.fill_blueprint(bp, values, origin=None)
    except cat.BlueprintFillError as e:
        return {"ok": False, "kind": "validation", "error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "kind": "validation", "error": f"{type(e).__name__}: {e}"}
    jobs = _cron_jobs_mod()
    if jobs is None:
        return {"ok": False, "available": False,
                "error": "cron.jobs 模块不可用（无法创建定时任务）"}
    try:
        job = jobs.create_job(**spec)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "kind": "create", "error": f"创建定时任务失败：{type(e).__name__}: {e}"}
    return {"ok": True, "job": {
        "id": job.get("id"),
        "name": job.get("name"),
        "schedule_display": job.get("schedule_display"),
        "deliver": job.get("deliver"),
        "next_run_at": job.get("next_run_at"),
    }}

# ===================================================================
# 9. Bundles — 捆绑包（复用内核 agent.skill_bundles，绝不手写 JSON/分家）
# ===================================================================
def _bundles_mod():
    """惰性导入内核 skill_bundles 模块；不可用时返回 None（降级 available:False）。"""
    try:
        import agent.skill_bundles as m
        return m
    except Exception:
        return None

def bundles_list() -> dict:
    """列出已安装的技能捆绑包（内核原生 skill-bundles/*.yaml）。"""
    m = _bundles_mod()
    if m is None:
        return {"ok": True, "available": False, "error": "内核 skill_bundles 不可用", "items": []}
    try:
        items = []
        for info in m.list_bundles():
            items.append({
                "name": info.get("name"),
                "slug": info.get("slug"),
                "description": info.get("description") or "",
                "skills": info.get("skills") or [],
                "instruction": info.get("instruction") or "",
                "path": info.get("path"),
            })
        return {"ok": True, "available": True, "items": items}
    except Exception as e:
        return {"ok": True, "available": False, "error": f"{type(e).__name__}: {e}", "items": []}

def bundles_get(name: str) -> dict:
    """获取单个捆绑包详情（供编辑/校验）。"""
    m = _bundles_mod()
    if m is None:
        return {"ok": False, "available": False, "error": "内核 skill_bundles 不可用"}
    try:
        info = m.get_bundle(name)
        if not info:
            return {"ok": False, "error": "未找到该捆绑包"}
        return {"ok": True, "available": True, "item": {
            "name": info.get("name"), "slug": info.get("slug"),
            "description": info.get("description") or "", "skills": info.get("skills") or [],
            "instruction": info.get("instruction") or "", "path": info.get("path"),
        }}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def bundles_install(name: str, skills: list, description: str = "", instruction: str = "", overwrite: bool = False) -> dict:
    """创建/覆盖一个技能捆绑包（写内核 skill-bundles/<slug>.yaml 并刷新内核缓存）。"""
    m = _bundles_mod()
    if m is None:
        return {"ok": False, "available": False, "error": "内核 skill_bundles 不可用"}
    try:
        skills = [str(s).strip() for s in (skills or []) if str(s).strip()]
        path = m.save_bundle(name, skills, description or "", instruction or "", bool(overwrite))
        return {"ok": True, "name": name, "path": str(path), "skills_count": len(skills)}
    except FileExistsError as e:
        return {"ok": False, "exists": True, "error": f"捆绑包已存在（可传 overwrite=true 覆盖）：{e}"}
    except ValueError as e:
        return {"ok": False, "error": f"参数无效：{e}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def bundles_uninstall(name: str) -> dict:
    """卸载一个技能捆绑包（删除 skill-bundles/<slug>.yaml）。"""
    m = _bundles_mod()
    if m is None:
        return {"ok": False, "available": False, "error": "内核 skill_bundles 不可用"}
    try:
        path = m.delete_bundle(name)
        return {"ok": True, "path": str(path)}
    except FileNotFoundError:
        return {"ok": True, "missing": True, "error": "捆绑包不存在"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def bundles_reload() -> dict:
    """重新扫描 skill-bundles 目录（内核缓存与磁盘同步）。"""
    m = _bundles_mod()
    if m is None:
        return {"ok": False, "available": False, "error": "内核 skill_bundles 不可用"}
    try:
        diff = m.reload_bundles()
        return {"ok": True, "available": True, "diff": diff}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

# ===================================================================
# 10. Curator — 策展（复用内核 agent.curator + tools.skill_usage + agent.curator_backup）
# -------------------------------------------------------------------
# 真实机制（hermes_agent 0.19.0 实证）：
#   Curator 是 Hermes 对「agent 创建的技能」的后台维护通道——按 查看/使用/打补丁 频率，
#   把长期不用的技能从 active → stale → archived 流转，并可（可选、默认关）跑一轮 aux 模型
#   审查做合并/归并。数据落点全部走 get_hermes_home()：
#     · 使用记录   <HERMES_HOME>/skills/.usage.json          (tools.skill_usage)
#     · 归档技能   <HERMES_HOME>/skills/.archive/            (archive_skill 物理移动目录)
#     · 策展状态   <HERMES_HOME>/skills/.curator_state       (agent.curator.load_state)
#     · 技能树快照 <HERMES_HOME>/skills/.curator_backups/    (agent.curator_backup)
#   核心 API：
#     · agent.curator：load_state/set_paused/is_paused/is_enabled/get_interval_hours/
#       get_stale_after_days/get_archive_after_days/get_consolidate/get_prune_builtins/
#       apply_automatic_transitions(now) -> {checked,marked_stale,archived,reactivated,seeded}
#       （确定性、无 LLM、不烧 token；LLM 合并 pass 在 run_curator_review，默认不接以免烧 token）
#     · tools.skill_usage：usage_report()(全量技能+provenance) / agent_created_report()(仅 agent 创建) /
#       list_archived_skill_names() / is_agent_created(name) / get_record(name) / set_pinned(name,bool) /
#       archive_skill(name)->(ok,msg) / restore_skill(name)->(ok,msg) / STATE_ACTIVE/STALE/ARCHIVED
#     · agent.curator_backup：is_enabled() / snapshot_skills(reason)->Path|None / list_backups()->[dict] /
#       rollback(backup_id=None)->(ok,msg,path)
#   注意：内核「enabled」读 config.yaml 的 curator.enabled（默认 True），运行时只能用 set_paused 暂停；
#   本面板「启用策展」复选框映射到 set_paused(not enabled)（诚实：暂停自动整理，使用记录仍照常追踪）。
# ===================================================================
def _curator_mods():
    """惰性导入内核 Curator 相关模块；任一缺失返回 None 表示不可用（降级 available:False）。"""
    try:
        from agent import curator as _cur
        from tools import skill_usage as _su
        from agent import curator_backup as _cb
        return _cur, _su, _cb
    except Exception:
        return None

def _ensure_home_env():
    """幂等兜底：确保进程内 HERMES_HOME 与 examples 数据目录一致（防内核双轨漂移）。"""
    try:
        os.environ["HERMES_HOME"] = _get_home()
    except Exception:
        pass

def _curator_idle_days(rec: dict):
    """距上次活动（查看/使用/打补丁）的天数；无时间戳则回退 created_at。"""
    from datetime import datetime, timezone
    ts = rec.get("last_activity_at") or rec.get("created_at")
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - dt).days)

def curator_get() -> dict:
    """读取真实策展状态 + 全量技能使用遥测 + 归档列表。内核缺失 → available:False 降级。"""
    mods = _curator_mods()
    if mods is None:
        return {"ok": True, "available": False, "error": "内核 Curator 模块不可用"}
    try:
        _cur, _su, _cb = mods
        _ensure_home_env()
        state = _cur.load_state()
        usage = _su.usage_report()  # 全量技能（含 provenance: agent/bundled/hub）
        agent_rows = _su.agent_created_report()  # 仅 agent 创建的技能
        by_state = {"active": 0, "stale": 0, "archived": 0}
        pinned = []
        for r in agent_rows:
            s = r.get("state", "active")
            if s in by_state:
                by_state[s] += 1
            if r.get("pinned"):
                pinned.append(r["name"])
        archived = _su.list_archived_skill_names()
        return {
            "ok": True, "available": True,
            "enabled": _cur.is_enabled(),
            "paused": _cur.is_paused(),
            "interval_hours": _cur.get_interval_hours(),
            "stale_after_days": _cur.get_stale_after_days(),
            "archive_after_days": _cur.get_archive_after_days(),
            "consolidate": _cur.get_consolidate(),
            "prune_builtins": _cur.get_prune_builtins(),
            "last_run_at": state.get("last_run_at"),
            "run_count": state.get("run_count", 0),
            "usage": usage,
            "agent_created_total": len(agent_rows),
            "by_state": by_state,
            "pinned": pinned,
            "archived": archived,
        }
    except Exception as e:
        return {"ok": False, "available": True, "error": f"{type(e).__name__}: {e}"}

def curator_toggle(enabled: bool) -> dict:
    """「启用策展」复选框 → 运行时暂停/恢复自动整理（内核 enabled 读 config，运行时只能 pause）。"""
    mods = _curator_mods()
    if mods is None:
        return {"ok": False, "available": False, "error": "内核 Curator 模块不可用"}
    try:
        _cur, _su, _cb = mods
        _ensure_home_env()
        _cur.set_paused(not bool(enabled))
        return {"ok": True, "available": True, "enabled": bool(enabled), "paused": _cur.is_paused()}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def curator_apply(dry_run: bool = False) -> dict:
    """运行确定性自动整理（active→stale→archived），无 LLM、不烧 token。"""
    mods = _curator_mods()
    if mods is None:
        return {"ok": False, "available": False, "error": "内核 Curator 模块不可用"}
    try:
        _cur, _su, _cb = mods
        _ensure_home_env()
        if dry_run:
            # 内核 apply_automatic_transitions 无 dry 参数；这里返回当前将受影响候选的预览
            candidates = []
            for r in _su.agent_created_report():
                if r.get("pinned"):
                    continue
                if r.get("state") == _su.STATE_ARCHIVED:
                    continue
                candidates.append({"name": r["name"], "state": r.get("state"),
                                   "idle_days": _curator_idle_days(r)})
            return {"ok": True, "available": True, "dry_run": True, "candidates": candidates}
        counts = _cur.apply_automatic_transitions()
        return {"ok": True, "available": True, "dry_run": False, "counts": counts}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def curator_archive(name: str) -> dict:
    """手动归档一个 agent 创建的技能（固定中的技能拒绝）。"""
    mods = _curator_mods()
    if mods is None:
        return {"ok": False, "available": False, "error": "内核 Curator 模块不可用"}
    try:
        _cur, _su, _cb = mods
        _ensure_home_env()
        name = (name or "").strip()
        if not name:
            return {"ok": False, "error": "名称不能为空"}
        if _su.get_record(name).get("pinned"):
            return {"ok": False, "error": f"「{name}」已固定(pinned)，请先取消固定再归档"}
        ok, msg = _su.archive_skill(name)
        return {"ok": ok, "available": True, "message": msg}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def curator_restore(name: str) -> dict:
    """把归档的技能恢复回活跃。"""
    mods = _curator_mods()
    if mods is None:
        return {"ok": False, "available": False, "error": "内核 Curator 模块不可用"}
    try:
        _cur, _su, _cb = mods
        _ensure_home_env()
        name = (name or "").strip()
        if not name:
            return {"ok": False, "error": "名称不能为空"}
        ok, msg = _su.restore_skill(name)
        return {"ok": ok, "available": True, "message": msg}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def curator_pin(name: str, pinned: bool) -> dict:
    """固定/取消固定一个 agent 创建的技能（固定后永不自动流转）。"""
    mods = _curator_mods()
    if mods is None:
        return {"ok": False, "available": False, "error": "内核 Curator 模块不可用"}
    try:
        _cur, _su, _cb = mods
        _ensure_home_env()
        name = (name or "").strip()
        if not name:
            return {"ok": False, "error": "名称不能为空"}
        if not _su.is_agent_created(name):
            return {"ok": False, "error": f"「{name}」不是 agent 创建的技能（策展只管理 agent 创建的技能）"}
        _su.set_pinned(name, bool(pinned))
        return {"ok": True, "available": True, "name": name, "pinned": bool(pinned)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def curator_prune(days: int = 90, dry_run: bool = True) -> dict:
    """批量归档空闲 >= N 天的 agent 创建技能（默认 90）。dry_run 仅列出候选、不修改。"""
    mods = _curator_mods()
    if mods is None:
        return {"ok": False, "available": False, "error": "内核 Curator 模块不可用"}
    try:
        _cur, _su, _cb = mods
        _ensure_home_env()
        days = int(days or 90)
        if days < 1:
            return {"ok": False, "error": "days 必须 >= 1"}
        candidates = []
        for r in _su.agent_created_report():
            if r.get("pinned"):
                continue
            if r.get("state") == _su.STATE_ARCHIVED:
                continue
            idle = _curator_idle_days(r)
            if idle is None or idle < days:
                continue
            candidates.append({"name": r["name"], "idle_days": idle, "state": r.get("state")})
        if dry_run:
            return {"ok": True, "available": True, "dry_run": True, "count": len(candidates), "candidates": candidates}
        archived = 0
        failures = []
        for c in candidates:
            ok, msg = _su.archive_skill(c["name"])
            if ok:
                archived += 1
            else:
                failures.append({"name": c["name"], "error": msg})
        return {"ok": True, "available": True, "dry_run": False, "archived": archived,
                "total": len(candidates), "failures": failures}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def curator_backup(reason: str = "manual") -> dict:
    """手动给技能树做一次快照（curator 每次真实运行前也会自动做）。"""
    mods = _curator_mods()
    if mods is None:
        return {"ok": False, "available": False, "error": "内核 Curator 模块不可用"}
    try:
        _cur, _su, _cb = mods
        _ensure_home_env()
        if not _cb.is_enabled():
            return {"ok": False, "available": True, "error": "策展备份未启用（curator.backup.enabled: false）"}
        snap = _cb.snapshot_skills(reason=reason or "manual")
        if snap is None:
            return {"ok": False, "available": True, "error": "快照失败（备份未启用或 IO 错误）"}
        return {"ok": True, "available": True, "name": snap.name, "path": str(snap)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def curator_backups() -> dict:
    """列出已有的技能树快照。"""
    mods = _curator_mods()
    if mods is None:
        return {"ok": False, "available": False, "error": "内核 Curator 模块不可用"}
    try:
        _cur, _su, _cb = mods
        _ensure_home_env()
        rows = _cb.list_backups()
        return {"ok": True, "available": True, "backups": rows}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def curator_rollback(backup_id: str = None, yes: bool = False) -> dict:
    """从快照恢复技能树（默认最新）。需显式确认（yes=true）。"""
    mods = _curator_mods()
    if mods is None:
        return {"ok": False, "available": False, "error": "内核 Curator 模块不可用"}
    try:
        _cur, _su, _cb = mods
        _ensure_home_env()
        if not yes:
            return {"ok": False, "available": True, "need_confirm": True,
                    "error": "恢复会替换当前技能树，请传 yes=true 确认"}
        ok, msg, _ = _cb.rollback(backup_id=backup_id)
        return {"ok": ok, "available": True, "message": msg}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

# ===================================================================
# 11. Journey — 旅程/学习图谱
# ===================================================================
# 真实机制（hermes_agent 0.19.0+，hermes_cli/journey.py + agent/learning_graph.py 实证）：
#   - `hermes journey` 调用 agent.learning_graph.build_learning_graph() 组装「学到什么」图谱：
#       * nodes：学到的技能（非 base、agent 创建或曾使用）+ 记忆卡片（MEMORY.md/USER.md § 分块），
#         每节点含 id / kind(skill|memory) / label / timestamp / category / useCount / state /
#         createdBy / pinned（memory 节点另有 memorySource）；
#       * edges：技能 related_skills 边 + 记忆→技能的词汇重叠边；
#       * clusters：按 category 聚合计数；
#       * memory：记忆卡片原文（source / timestamp / title / body）；
#       * stats：密度统计（nodes / related_edges / edges_per_node / linked_nodes / isolated_pct /
#         categories / agent_created / used / top_categories + memory_nodes / memory_skill_edges /
#         learned_skills）。
#   - `hermes journey list|delete|edit <node>` 复用 agent.learning_mutations
#     （node_detail / delete_node / edit_node）；删除技能=归档（可 hermes curator restore 恢复），
#     删除记忆=重写其文件；删除/编辑走内核，绝不手写。
#   - 内核从 HERMES_HOME 读取（skills/ + memories/），与桌面 materialize 的 HERMES_HOME 一致，
#     路径不分裂（不在此手写 json / 不编造事件）。
# 因此这里只做薄封装：复用内核 build_learning_graph + learning_mutations，绝不伪造数据/手写存储。
# 内核模块不可用时优雅降级 available:False（绝不编造「首次对话」之类的假事件）。
def _journey_mod():
    """惰性导入内核 learning_graph 模块；不可用返回 None（降级 available:False）。"""
    try:
        import agent.learning_graph as m
        return m
    except Exception:
        return None

def _journey_mutations_mod():
    """惰性导入内核 learning_mutations 模块；不可用返回 None（降级 available:False）。"""
    try:
        import agent.learning_mutations as m
        return m
    except Exception:
        return None

def journey_get() -> dict:
    """获取学习旅程（真实 Hermes 学习图谱）。"""
    mod = _journey_mod()
    if mod is None:
        return {"ok": True, "available": False,
                "error": "内核 agent.learning_graph 不可用（hermes-agent 未安装？）",
                "nodes": [], "edges": [], "clusters": [], "memory": [], "stats": {}}
    try:
        payload = mod.build_learning_graph()
        return {
            "ok": True,
            "available": True,
            "nodes": payload.get("nodes", []),
            "edges": payload.get("edges", []),
            "clusters": payload.get("clusters", []),
            "memory": payload.get("memory", []),
            "stats": payload.get("stats", {}),
        }
    except Exception as e:
        return {"ok": True, "available": False,
                "error": f"{type(e).__name__}: {e}",
                "nodes": [], "edges": [], "clusters": [], "memory": [], "stats": {}}

def journey_node_detail(node_id: str) -> dict:
    """获取节点详情（供编辑预填）。内核不可用/节点不存在均返回 ok:False，绝不谎报。"""
    mod = _journey_mutations_mod()
    if mod is None:
        return {"ok": False, "available": False, "message": "内核 agent.learning_mutations 不可用"}
    return mod.node_detail(node_id)

def journey_delete(node_id: str) -> dict:
    """删除/归档学习节点（技能=归档可恢复；记忆=重写文件）。复用内核，绝不手写。"""
    mod = _journey_mutations_mod()
    if mod is None:
        return {"ok": False, "available": False, "message": "内核 agent.learning_mutations 不可用"}
    return mod.delete_node(node_id)

def journey_edit(node_id: str, content: str) -> dict:
    """编辑学习节点内容（技能=改 SKILL.md；记忆=改 § 分块）。复用内核，绝不手写。"""
    mod = _journey_mutations_mod()
    if mod is None:
        return {"ok": False, "available": False, "message": "内核 agent.learning_mutations 不可用"}
    return mod.edit_node(node_id, content)

# ===================================================================
# 12. Security Audit — 安全审计
# ===================================================================
def _security_audit_mod():
    """惰性导入内核 security_audit 模块；不可用时返回 None（降级 available:False）。"""
    try:
        import hermes_cli.security_audit as m
        return m
    except Exception:
        return None

def _security_advisories_mod():
    """惰性导入内核 security_advisories 模块；不可用时返回 None（投毒包检测降级空列表）。"""
    try:
        import hermes_cli.security_advisories as m
        return m
    except Exception:
        return None

_SEVERITY_LABELS = {
    "CRITICAL": "严重", "HIGH": "高", "MEDIUM": "中", "MODERATE": "中",
    "LOW": "低", "UNKNOWN": "未知",
}

def security_audit_run(*, skip_venv: bool = False, skip_plugins: bool = False, skip_mcp: bool = False) -> dict:
    """运行 Hermes 原生供应链安全审计（hermes security audit）。

    复用内核 hermes_cli.security_audit.run_audit：对三个攻击面
    （venv 已装 PyPI 包 / 插件声明的依赖 / config.yaml 钉版本号的 MCP 服务器）
    比对 OSV.dev 已知漏洞；并叠加 security_advisories 的已知投毒包检测
    （hermes doctor 同源，纯 metadata 查询、无需联网）。前端严格按内核结构映射。
    """
    sa = _security_audit_mod()
    sv = _security_advisories_mod()
    if sa is None:
        return {"ok": False, "available": False, "error": "内核 security_audit 不可用",
                "findings": [], "advisories": [], "total_components_scanned": 0, "finding_count": 0}
    home = Path(_get_home())
    # 1) OSV.dev 供应链审计（需联网；失败宽容降级，绝不谎报"通过"）
    findings: list = []
    total_components = 0
    osv_error = None
    try:
        total_components = sa._count_components(
            skip_venv=skip_venv, skip_plugins=skip_plugins, skip_mcp=skip_mcp, hermes_home=home
        )
        raw = sa.run_audit(
            skip_venv=skip_venv, skip_plugins=skip_plugins, skip_mcp=skip_mcp, hermes_home=home
        )
    except RuntimeError as exc:
        osv_error = f"无法连接 OSV.dev（需要联网）：{exc}"
        raw = []
    except Exception as exc:
        osv_error = f"审计失败：{exc}"
        raw = []
    for f in raw:
        comp = f.component
        vuln = f.vuln
        findings.append({
            "package": comp.name,
            "version": comp.version,
            "ecosystem": comp.ecosystem,
            "source": comp.source,
            "vuln_id": vuln.osv_id,
            "severity": vuln.severity,
            "severity_label": _SEVERITY_LABELS.get(vuln.severity, vuln.severity),
            "summary": vuln.summary,
            "fixed_versions": vuln.fixed_versions,
        })
    # 2) 已知投毒包检测（hermes doctor 同源，纯 metadata，无需联网）
    advisories: list = []
    if sv is not None:
        try:
            hits = sv.filter_unacked(sv.detect_compromised())
            for h in hits:
                a = h.advisory
                advisories.append({
                    "id": a.id,
                    "title": a.title,
                    "severity": a.severity,
                    "severity_label": _SEVERITY_LABELS.get(a.severity, a.severity),
                    "package": h.package,
                    "installed_version": h.installed_version,
                    "summary": a.summary,
                    "url": a.url,
                    "remediation": list(a.remediation),
                })
        except Exception:
            pass
    return {
        "ok": True,
        "available": True,
        "total_components_scanned": total_components,
        "finding_count": len(findings),
        "findings": findings,
        "advisories": advisories,
        "osv_error": osv_error,
    }

# ===================================================================
# 13. Provider Routing — 提供者路由（OpenRouter provider_routing 块，落 config.yaml）
# ===================================================================
def _routing_mods():
    """惰性导入内核 config 模块；任一缺失返回 None → available:False 降级。"""
    try:
        from hermes_cli import config as _cfg
        return _cfg
    except Exception:
        return None

# 内核 provider_routing 真实字段（见 hermes-agent docs：OpenRouter Provider Routing）
_ROUTING_SORT_VALUES = ("price", "throughput", "latency")  # sort 取值；price 为默认
_ROUTING_LIST_KEYS = ("only", "ignore", "order")           # 列表型：允许的/排除的/顺序
_ROUTING_DATA_COLLECTION_VALUES = ("allow", "deny")        # data_collection 取值

def routing_get() -> dict:
    """读取真实 Provider Routing 配置（OpenRouter provider_routing 块 + openrouter.min_coding_score）。
    内核缺失 → available:False 降级。"""
    mods = _routing_mods()
    if mods is None:
        return {"ok": True, "available": False, "error": "内核 config 模块不可用（Provider Routing 功能不可用）"}
    try:
        _ensure_home_env()
        cfg = mods.load_config()
        pr = mods.cfg_get(cfg, "provider_routing")
        if not isinstance(pr, dict):
            pr = {}
        min_score = mods.cfg_get(cfg, "openrouter", "min_coding_score")
        provider = mods.cfg_get(cfg, "model", "provider")
        return {
            "ok": True, "available": True,
            "provider": provider,
            "is_openrouter": (provider == "openrouter"),
            "sort": pr.get("sort", "price"),
            "only": pr.get("only") or [],
            "ignore": pr.get("ignore") or [],
            "order": pr.get("order") or [],
            "require_parameters": bool(pr.get("require_parameters", False)),
            "data_collection": pr.get("data_collection"),  # "allow" | "deny" | None
            "min_coding_score": min_score,  # 0.0–1.0（默认 0.65）或 None（被清空）
            "note": ("Provider Routing 仅对 OpenRouter 生效；当前 provider 非 openrouter，这些设置当前无作用。"
                     if provider != "openrouter" else
                     "提示：模型名追加 :nitro=按吞吐排序、:floor=按价格排序 可快速切换 sort。"),
        }
    except Exception as e:
        return {"ok": False, "available": True, "error": f"{type(e).__name__}: {e}"}

def routing_save(payload: dict) -> dict:
    """写入真实 Provider Routing 配置到 config.yaml 的 provider_routing 段 + openrouter.min_coding_score。
    内核缺失 → available:False 降级；字段严格按内核 schema 校验。"""
    mods = _routing_mods()
    if mods is None:
        return {"ok": False, "available": False, "error": "内核 config 模块不可用（无法保存 Provider Routing）"}
    try:
        _ensure_home_env()
        if not isinstance(payload, dict):
            return {"ok": False, "error": "payload 必须是对象"}
        cfg = mods.load_config()
        pr = {}
        sort_v = (payload.get("sort") or "price")
        if sort_v not in _ROUTING_SORT_VALUES:
            return {"ok": False, "error": f"sort 必须是 {_ROUTING_SORT_VALUES} 之一"}
        pr["sort"] = sort_v
        for k in _ROUTING_LIST_KEYS:  # only / ignore / order
            v = payload.get(k)
            if isinstance(v, str):
                v = [s.strip() for s in v.split(",") if s.strip()]
            if not isinstance(v, list):
                v = []
            if v:
                pr[k] = v
        if payload.get("require_parameters"):
            pr["require_parameters"] = True
        dc = payload.get("data_collection")
        if dc in _ROUTING_DATA_COLLECTION_VALUES:
            pr["data_collection"] = dc
        if pr:
            cfg["provider_routing"] = pr
        else:
            cfg.pop("provider_routing", None)
        # openrouter.min_coding_score：仅 openrouter/pareto-code 用；空/None 清除（回退默认 0.65）
        if "min_coding_score" in payload:
            mcs = payload.get("min_coding_score")
            if mcs in ("", None):
                mods.cfg_get(cfg, "openrouter")  # noqa: 确保 openrouter 段存在再 pop
                oc = cfg.setdefault("openrouter", {})
                oc.pop("min_coding_score", None)
            else:
                try:
                    f = float(mcs)
                except (TypeError, ValueError):
                    return {"ok": False, "error": "min_coding_score 必须是 0.0–1.0 的数字"}
                if not (0.0 <= f <= 1.0):
                    return {"ok": False, "error": "min_coding_score 必须在 0.0–1.0 之间"}
                cfg.setdefault("openrouter", {})["min_coding_score"] = f
        mods.save_config(cfg)
        return routing_get()
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

# ===================================================================
# 14. Batch Processing — 批量处理（Hermes 原生 batch_runner）
# -------------------------------------------------------------------
# 真实机制（hermes-agent 0.19.0）：batch_runner.py 是顶层可导入模块（不是
# hermes_cli 子模块）。它把 JSONL 数据集（每行 {"prompt": ...}）的每条 prompt
# 送进一个隔离的 AIAgent 会话（默认本地；仅当数据行含 image/docker_image 且
# TERMINAL_ENV=docker 才用容器），按 toolset distribution 采样工具集，产出
# ShareGPT 轨迹（training / eval 数据）。BatchRunner.run() 用多进程
# multiprocessing.Pool(num_workers)，在冻结 Windows EXE 里子进程脆弱——
# 桌面端改用本进程 worker 线程串行驱动内核的 _process_single_prompt，复用其
# 真实的 Agent 运行逻辑与轨迹 schema，避免多进程，且尊重「单进程」铁律。
# ===================================================================
_BATCH_RUNS: dict = {}
_BATCH_LOCK = threading.Lock()


def _batch_runner_mod():
    try:
        import batch_runner as m
        return m
    except Exception:
        return None


def batch_list_distributions() -> dict:
    """返回 Hermes 原生 batch_runner 的 toolset distribution 列表。"""
    mod = _batch_runner_mod()
    if mod is None:
        return {"ok": True, "available": False, "items": [],
                "error": "batch_runner 模块不可用（hermes-agent 未安装？）"}
    try:
        dists = mod.list_distributions()
        items = []
        for k, v in dists.items():
            if isinstance(v, dict):
                items.append({
                    "key": k,
                    "description": v.get("description", ""),
                    "toolsets": list(v.get("toolsets", {}).keys()),
                })
            else:
                items.append({"key": k, "description": "", "toolsets": []})
        return {"ok": True, "available": True, "items": items}
    except Exception as e:
        return {"ok": True, "available": False, "items": [],
                "error": f"{type(e).__name__}: {e}"}


def batch_run(rows: list, opts: dict | None = None) -> dict:
    """启动一次批量处理（后台线程，立即返回 run_id 供轮询）。

    rows: 数据集。每项可为字符串，或 {"prompt": ...} / {"text": ...}。
    opts: run_name / model / base_url / api_key / max_iterations / distribution /
          reasoning_effort / max_tokens / verbose / providers_allowed|ignored|
          order / provider_sort / ephemeral_system_prompt。
    模型默认走 OpenRouter 免费模型（遵循项目铁律），distribution 默认 safe
    （不含 terminal，桌面端安全）。
    """
    mod = _batch_runner_mod()
    if mod is None:
        return {"ok": False, "available": False, "error": "batch_runner 模块不可用"}
    opts = opts or {}

    # 归一化为真实数据集：每条 {"prompt": ...}
    dataset = []
    for r in rows:
        if isinstance(r, dict):
            p = r.get("prompt") or r.get("text") or ""
        else:
            p = str(r)
        p = (p or "").strip()
        if p:
            dataset.append({"prompt": p})
    if not dataset:
        return {"ok": False, "kind": "empty",
                "error": "数据集为空（每条需含 prompt 或 text）"}

    run_name = opts.get("run_name") or f"desktop_batch_{int(time.time())}"
    re = opts.get("reasoning_effort")
    reasoning_config = {"effort": re} if re else None
    config = {
        "distribution": opts.get("distribution") or "safe",
        "model": opts.get("model") or "inclusionai/ling-3.0-flash:free",
        "max_iterations": int(opts.get("max_iterations") or 10),
        "base_url": opts.get("base_url") or "https://openrouter.ai/api/v1",
        "api_key": opts.get("api_key") or None,
        "verbose": bool(opts.get("verbose")),
        "ephemeral_system_prompt": opts.get("ephemeral_system_prompt") or None,
        "log_prefix_chars": 100,
        "providers_allowed": opts.get("providers_allowed"),
        "providers_ignored": opts.get("providers_ignored"),
        "providers_order": opts.get("providers_order"),
        "provider_sort": opts.get("provider_sort"),
        "openrouter_min_coding_score": opts.get("openrouter_min_coding_score"),
        "max_tokens": int(opts["max_tokens"]) if opts.get("max_tokens") else None,
        "reasoning_config": reasoning_config,
        "prefill_messages": None,
    }

    with _BATCH_LOCK:
        run_id = f"run_{int(time.time() * 1000)}_{len(_BATCH_RUNS)}"
        state = {
            "run_id": run_id,
            "run_name": run_name,
            "status": "running",
            "total": len(dataset),
            "processed": 0,
            "results": [],
            "statistics": {
                "tool_stats": {},
                "reasoning_stats": {"total_assistant_turns": 0,
                                    "turns_with_reasoning": 0,
                                    "turns_without_reasoning": 0},
                "discarded_no_reasoning": 0,
                "failed": 0,
            },
            "output_dir": None,
            "error": None,
            "started_at": time.time(),
        }
        _BATCH_RUNS[run_id] = state

    t = threading.Thread(
        target=_batch_run_worker,
        args=(mod, run_id, dataset, config, run_name),
        daemon=True,
    )
    t.start()
    return {"ok": True, "run_id": run_id, "run_name": run_name, "total": len(dataset)}


def _batch_item(idx: int, entry: dict, res: dict, discarded: bool = False,
                failed: bool = False) -> dict:
    traj = res.get("trajectory") or []
    out = ""
    for m in reversed(traj):
        if m.get("from") == "gpt":
            out = m.get("value", "")
            break
    success = bool(res.get("success")) and not failed and not discarded
    status = ("discarded" if discarded else
              "failed" if failed else
              "partial" if res.get("partial") else "completed")
    return {
        "prompt_index": idx,
        "prompt": (entry.get("prompt") or "")[:200],
        "status": status,
        "success": success,
        "output": out[:2000],
        "api_calls": res.get("api_calls"),
        "toolsets_used": res.get("toolsets_used", []),
        "tool_stats": (res.get("tool_stats") or {}),
        "error": (res.get("error") if not success else None),
    }


def _batch_run_worker(mod, run_id: str, dataset: list, config: dict, run_name: str):
    """后台线程：串行驱动内核 _process_single_prompt，累积真实轨迹与统计。"""
    state = _BATCH_RUNS.get(run_id)
    if state is None:
        return
    try:
        out_dir = Path(os.getcwd()) / "data" / run_name
        out_dir.mkdir(parents=True, exist_ok=True)
        traj_file = out_dir / "trajectories.jsonl"
        batch_file = out_dir / "batch_0.jsonl"
        with _BATCH_LOCK:
            state["output_dir"] = str(out_dir)

        total_tool_stats: dict = {}
        total_reasoning = {"total_assistant_turns": 0,
                           "turns_with_reasoning": 0,
                           "turns_without_reasoning": 0}
        discarded = 0
        failed = 0

        for idx, entry in enumerate(dataset):
            res = mod._process_single_prompt(idx, entry, 0, config)
            with _BATCH_LOCK:
                state["processed"] = idx + 1
            if res.get("success") and res.get("trajectory"):
                reasoning = res.get("reasoning_stats", {})
                if not reasoning.get("has_any_reasoning", True):
                    discarded += 1
                    with _BATCH_LOCK:
                        state["results"].append(_batch_item(idx, entry, res, discarded=True))
                    continue
                raw = res.get("tool_stats", {})
                norm = (mod._normalize_tool_stats(raw)
                        if hasattr(mod, "_normalize_tool_stats") else raw)
                err_counts = (mod._normalize_tool_error_counts(
                    {t: s.get("failure", 0) for t, s in raw.items()})
                    if hasattr(mod, "_normalize_tool_error_counts") else {})
                traj_entry = {
                    "prompt_index": idx,
                    "conversations": res["trajectory"],
                    "metadata": res.get("metadata", {}),
                    "completed": res.get("completed"),
                    "partial": res.get("partial", False),
                    "api_calls": res.get("api_calls"),
                    "toolsets_used": res.get("toolsets_used", []),
                    "tool_stats": norm,
                    "tool_error_counts": err_counts,
                }
                line = json.dumps(traj_entry, ensure_ascii=False)
                with open(batch_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                with open(traj_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                for tn, ts in raw.items():
                    d = total_tool_stats.setdefault(
                        tn, {"count": 0, "success": 0, "failure": 0})
                    d["count"] += ts.get("count", 0)
                    d["success"] += ts.get("success", 0)
                    d["failure"] += ts.get("failure", 0)
                for k in total_reasoning:
                    total_reasoning[k] += reasoning.get(k, 0)
                with _BATCH_LOCK:
                    state["results"].append(_batch_item(idx, entry, res))
            else:
                failed += 1
                with _BATCH_LOCK:
                    state["results"].append(_batch_item(idx, entry, res, failed=True))

        checkpoint = {
            "run_name": run_name,
            "completed_prompts": [r["prompt_index"] for r in state["results"]
                                  if r.get("success")],
            "batch_stats": {},
            "last_updated": datetime.datetime.now().isoformat(),
        }
        (out_dir / "checkpoint.json").write_text(
            json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
        statistics = {
            "tool_stats": total_tool_stats,
            "reasoning_stats": total_reasoning,
            "discarded_no_reasoning": discarded,
            "failed": failed,
            "total": len(dataset),
            "duration_sec": round(time.time() - state["started_at"], 2),
        }
        (out_dir / "statistics.json").write_text(
            json.dumps(statistics, ensure_ascii=False, indent=2), encoding="utf-8")
        with _BATCH_LOCK:
            state["statistics"] = statistics
            state["status"] = "done"
    except Exception as e:
        with _BATCH_LOCK:
            state["status"] = "error"
            state["error"] = f"{type(e).__name__}: {e}"


def batch_status(run_id: str) -> dict:
    """轮询某次批量处理的进度与结果。"""
    with _BATCH_LOCK:
        st = _BATCH_RUNS.get(run_id)
        if st is None:
            return {"ok": False, "kind": "notfound",
                    "error": f"未找到批量任务：{run_id}"}
        snap = {k: st[k] for k in ("run_name", "status", "total", "processed",
                                   "results", "statistics", "output_dir", "error")}
    return {"ok": True, "run_id": run_id, **snap}