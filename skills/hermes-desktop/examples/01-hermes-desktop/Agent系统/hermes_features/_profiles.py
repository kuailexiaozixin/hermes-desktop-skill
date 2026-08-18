from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any

from ._base import _get_home


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
