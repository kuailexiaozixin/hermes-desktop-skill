from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any

from ._base import _get_home


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
