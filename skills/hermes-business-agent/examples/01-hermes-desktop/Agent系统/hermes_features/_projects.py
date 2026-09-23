from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any




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
