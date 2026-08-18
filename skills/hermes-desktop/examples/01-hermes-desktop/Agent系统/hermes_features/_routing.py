from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any

from ._curator import _ensure_home_env


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
