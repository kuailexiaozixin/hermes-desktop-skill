from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any



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
