from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any



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
