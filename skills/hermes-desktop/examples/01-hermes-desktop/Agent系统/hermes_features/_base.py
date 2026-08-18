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
