from __future__ import annotations

import copy
import json
import os
import re
import shutil
import sys
import threading
from pathlib import Path

from ._paths import DEFAULT_SKILLS_DIR, NO_BUNDLED_MARKER, _write_config_yaml_full, get_hermes_home, read_config_yaml



# ============================================================================
# 5) 技能（原生 SKILL.md 目录结构）
# ============================================================================
def ensure_default_skills(home: Path | None = None) -> Path:
    """确保 HERMES_HOME/skills 下存在内置默认技能（原生 SKILL.md 目录结构）。"""
    home = home or get_hermes_home()
    skills_dir = home / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    marker = home / NO_BUNDLED_MARKER
    if not marker.exists():
        try:
            marker.write_text("", encoding="utf-8")
        except Exception:
            pass
    if DEFAULT_SKILLS_DIR.exists():
        for d in sorted(DEFAULT_SKILLS_DIR.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                dest = skills_dir / d.name
                if not dest.exists():
                    shutil.copytree(d, dest)
    return skills_dir


def _skills_dir(home: Path | None = None) -> Path:
    return (home or get_hermes_home()) / "skills"


def _fm_scalar(val: str):
    """frontmatter 标量/内联列表归一：去引号；[a, b] 拆为列表。"""
    v = val.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_fm_scalar(x.strip()) for x in inner.split(",")]
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        return v[1:-1]
    return v


def _parse_simple_frontmatter(block: str) -> dict:
    """内建极简 frontmatter 解析（pyyaml 缺失时的防御性回退）。

    支持：标量、内联列表 [a, b]、块列表（- item）。
    wiki 的 frontmatter 由 _serialize_frontmatter 写入，本函数保证「写→读」闭环不丢元数据。
    """
    meta: dict = {}
    cur_key: str | None = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if cur_key is not None and line.lstrip().startswith("- "):
            item = line.lstrip()[2:].strip()
            if isinstance(meta.get(cur_key), list):
                meta[cur_key].append(_fm_scalar(item))  # type: ignore[arg-type]
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            cur_key = key
            meta.setdefault(key, [])
        else:
            cur_key = None
            meta[key] = _fm_scalar(val)
    return meta


def _parse_frontmatter(text: str):
    """解析 YAML frontmatter，返回 (meta:dict, body:str)。

    优先用 PyYAML（生产环境随 hermes-agent 安装）；若 pyyaml 缺失或解析异常，
    回退到内建轻量解析器，保证「写成功 → 读回」不丢元数据
    （消除无 yaml 运行时静默返回 {} 的隐患，防御 hermes-agent 版本/venv 变化）。
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    block, body = parts[1], parts[2].lstrip("\n")
    if yaml is not None:
        try:
            meta = yaml.safe_load(block)
            return (meta if isinstance(meta, dict) else {}), body
        except Exception:
            pass  # 解析失败也回退内建解析，避免整段元数据丢失
    return _parse_simple_frontmatter(block), body


def _dump_skill(meta: dict, body: str) -> str:
    head = "---\n" + "".join(f"{k}: {v}\n" for k, v in meta.items()) + "---\n"
    return head + body


def _serialize_frontmatter(meta: dict) -> str:
    """把 frontmatter dict 序列化回 YAML 头（与 _parse_frontmatter 互逆）。"""
    if yaml:
        import io
        buf = io.StringIO()
        yaml.safe_dump(meta, buf, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return "---\n" + buf.getvalue().rstrip("\n") + "\n---\n"
    # 退化路径：无 yaml 时手工拼（仅标量/列表）
    lines = []
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        else:
            lines.append(f"{k}: {v}")
    return "---\n" + "\n".join(lines) + "\n---\n"


def get_disabled_skills_set(home: Path | None = None, platform: str = "api_server") -> set:
    cfg = read_config_yaml(home)
    skills_cfg = cfg.get("skills") or {}
    disabled = set(skills_cfg.get("disabled") or [])
    disabled |= set((skills_cfg.get("platform_disabled") or {}).get(platform) or [])
    return disabled


def set_skill_enabled(name: str, enabled: bool, home: Path | None = None,
                      platform: str = "api_server") -> None:
    """启用/关闭某个技能（写 config.yaml，即时生效）。"""
    h = home or get_hermes_home()
    cfg = read_config_yaml(h)
    skills_cfg = dict(cfg.get("skills") or {})
    disabled = set(skills_cfg.get("disabled") or [])
    pd = dict(skills_cfg.get("platform_disabled") or {})
    plat_disabled = set(pd.get(platform) or [])
    if enabled:
        disabled.discard(name)
        plat_disabled.discard(name)
    else:
        plat_disabled.add(name)
    skills_cfg["disabled"] = sorted(disabled)
    pd[platform] = sorted(plat_disabled)
    skills_cfg["platform_disabled"] = pd
    cfg["skills"] = skills_cfg
    _write_config_yaml_full(h, cfg)
    # 让 Hermes 立刻重建技能系统提示词缓存
    try:
        from agent.prompt_builder import clear_skills_system_prompt_cache
        clear_skills_system_prompt_cache(clear_snapshot=True)
    except Exception:
        pass


def list_skills(home: Path | None = None) -> list[dict]:
    """读取 HERMES_HOME/skills 下所有原生技能（含 enabled 状态）。"""
    out: list[dict] = []
    skills_dir = _skills_dir(home)
    if skills_dir.exists():
        for d in sorted(skills_dir.iterdir()):
            skill_md = d / "SKILL.md"
            if d.is_dir() and skill_md.exists():
                try:
                    text = skill_md.read_text(encoding="utf-8")
                except Exception:
                    continue
                meta, body = _parse_frontmatter(text)
                name = meta.get("name") or d.name
                out.append({
                    "id": d.name, "name": name, "title": name,
                    "description": meta.get("description", ""),
                    "category": meta.get("category", ""),
                    "content": body, "path": str(skill_md),
                })
    disabled = get_disabled_skills_set(home, "api_server")
    for s in out:
        s["enabled"] = s["name"] not in disabled and s["id"] not in disabled
    return out


def read_skill(name: str, home: Path | None = None) -> dict | None:
    target = _skills_dir(home) / name / "SKILL.md"
    if not target.exists():
        return None
    meta, body = _parse_frontmatter(target.read_text(encoding="utf-8"))
    return {"id": name, "name": meta.get("name", name),
            "description": meta.get("description", ""),
            "category": meta.get("category", ""), "body": body}


def create_skill(name: str, description: str, body: str, category: str = "",
                 home: Path | None = None) -> dict:
    """新建一个原生技能目录 skills/<name>/SKILL.md。"""
    skills_dir = _skills_dir(home or get_hermes_home())
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", (name or "").strip().lower()) or "skill"
    target = skills_dir / safe
    target.mkdir(parents=True, exist_ok=True)
    meta = {"name": (name or "").strip(), "description": (description or "").strip()}
    if category:
        meta["category"] = category
    (target / "SKILL.md").write_text(_dump_skill(meta, body or ""), encoding="utf-8")
    return {"ok": True, "id": safe, "name": (name or "").strip()}


def update_skill(name: str, description: str | None = None, body: str | None = None,
                 category: str | None = None, home: Path | None = None) -> dict:
    target = _skills_dir(home) / name / "SKILL.md"
    if not target.exists():
        return {"ok": False, "error": "skill not found"}
    meta, old_body = _parse_frontmatter(target.read_text(encoding="utf-8"))
    if description is not None:
        meta["description"] = description.strip()
    if category is not None and category.strip():
        meta["category"] = category.strip()
    target.write_text(_dump_skill(meta, body if body is not None else old_body),
                      encoding="utf-8")
    return {"ok": True, "id": name}


def delete_skill(name: str, home: Path | None = None) -> dict:
    target = _skills_dir(home) / name
    if not target.exists():
        return {"ok": False, "error": "skill not found"}
    shutil.rmtree(target, ignore_errors=True)
    return {"ok": True, "id": name}
