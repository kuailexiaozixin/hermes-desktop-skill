from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any

from ._base import _get_home


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
