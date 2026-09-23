from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any

from ._base import _get_home


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
