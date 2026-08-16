from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any

from ._base import _get_home


# ===================================================================
# 4. MOA — 多智能体混合（复用内核 hermes_cli.config + hermes_cli.moa_config）
# ===================================================================
# 真实机制（hermes_agent 0.19.0，agent/moa_loop.py + hermes_cli/moa_config.py 实证）：
#   - MOA 是 Hermes 的「虚拟 provider」：多个参考(顾问)模型(reference_models)各自对当前
#     任务给建议，再由一个聚合(执行)模型(aggregator)综合成最终回答。它不是一个独立命令，
#     而是当 AIAgent 的 provider=="moa" 且 model==<preset 名> 时，AIAgent.__init__
#     （agent/agent_init.py:816）自动构造 MoAClient 接管每次 LLM 调用，并通过
#     tool_progress_callback 把每个参考模型的回答以 "moa.reference" / "moa.aggregating"
#     事件透出（agent_init.py:827 的 _moa_reference_relay 转发到 tool_progress_callback）。
#   - 配置存在 HERMES_HOME/config.yaml 的 `moa` 键下，结构是「命名预设(presets)」：
#       moa:
#         default_preset: default
#         active_preset: ""          # 选中 moa 预设作为当前模型时由模型选择器/激活接口决定
#         presets:
#           default:
#             enabled: true
#             reference_models: [{provider, model}, ...]   # 参考/顾问模型（可多个）
#             aggregator: {provider, model}                # 聚合/执行模型（唯一）
#             reference_temperature: null
#             aggregator_temperature: null
#             max_tokens: 4096
#             reference_max_tokens: null   # 仅限顾问输出长度(降延迟)，聚合模型不被限
#             fanout: per_iteration        # per_iteration(每轮工具迭代重跑) | user_turn(每轮用户对话跑一次)
#   - 内核不可用时优雅降级（available:False）。绝不手写 schema——全部交给
#     hermes_cli.moa_config.normalize_moa_config / resolve_moa_preset / set_active_moa_preset
#     与 hermes_cli.config.load_config / save_config，保证与内核零漂移。
def _moa_cfg_mod():
    """惰性导入内核 moa_config + config 模块；不可用返回 (None, None)。"""
    try:
        import hermes_cli.config as _cfg
        import hermes_cli.moa_config as _moa
        return _cfg, _moa
    except Exception:  # noqa: BLE001
        return None, None

def _moa_home():
    """MOA 配置与 Hermes 其余状态同目录：复用 _get_home()（= hermes_config.get_hermes_home()），
    确保与 backup/snapshot 等落在【同一个】HERMES_HOME，不依赖 HERMES_HOME 环境变量是否被显式设置。"""
    return _get_home()

def moa_get() -> dict:
    cfg_mod, moa_mod = _moa_cfg_mod()
    if cfg_mod is None or moa_mod is None:
        return {"ok": True, "available": False,
                "error": "内核 hermes_cli.config / moa_config 不可用",
                "presets": {}, "default_preset": "", "active_preset": "",
                "reference_models": [], "aggregator": None, "fanout": "per_iteration",
                "enabled": False, "active_in_agent": False, "agent_model": ""}
    try:
        home = _moa_home()
        raw = cfg_mod.load_config()
        norm = moa_mod.normalize_moa_config(raw.get("moa") if isinstance(raw, dict) else None)
        # 当前是否真的以 moa 作为活动模型（从 llm.json 顶层 vendor 判断）
        try:
            from hermes_config import get_active_model_cfg
            _amc = get_active_model_cfg(None) or {}
            norm["agent_provider"] = _amc.get("provider", "")
            norm["agent_model"] = _amc.get("model", "")
            norm["active_in_agent"] = (_amc.get("provider") == "moa")
        except Exception:
            norm["active_in_agent"] = False
            norm["agent_model"] = ""
        return {"ok": True, "available": True, **norm}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "presets": {}}

def moa_save(config: dict) -> dict:
    """保存 MoA 预设（前端整体提交 presets + 可选 default_preset/active_preset）。
    与 config.yaml 现有 moa 合并后归一化落盘，绝不丢弃 active_preset 等字段。"""
    cfg_mod, moa_mod = _moa_cfg_mod()
    if cfg_mod is None or moa_mod is None:
        return {"ok": False, "error": "内核 hermes_cli.config / moa_config 不可用"}
    try:
        home = _moa_home()
        raw = cfg_mod.load_config()
        if not isinstance(raw, dict):
            raw = {}
        existing = raw.get("moa") or {}
        merged = dict(existing) if isinstance(existing, dict) else {}
        inc = config if isinstance(config, dict) else {}
        if isinstance(inc.get("presets"), dict):
            merged["presets"] = inc["presets"]
        for key in ("default_preset", "active_preset", "enabled"):
            if key in inc:
                merged[key] = inc[key]
        raw["moa"] = moa_mod.normalize_moa_config(merged)
        cfg_mod.save_config(raw)
        return moa_get()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def moa_set_active(preset_name: str = "") -> dict:
    """激活/取消激活一个 MoA 预设作为当前模型。
    name 非空 → ①config.yaml moa.active_preset 置该预设；②llm.json 顶层 vendor="moa"、
      model=<preset>，使 get_active_model_cfg 解析出 provider=="moa"，从而 AIAgent 自动
      走 MoAClient（agent_init.py:816）。
    name 为空 → 仅清空 config.yaml active_preset（切回普通模型由模型选择器负责，不动 llm.json）。"""
    cfg_mod, moa_mod = _moa_cfg_mod()
    if cfg_mod is None or moa_mod is None:
        return {"ok": False, "error": "内核 hermes_cli.config / moa_config 不可用"}
    name = (preset_name or "").strip()
    try:
        home = _moa_home()
        raw = cfg_mod.load_config()
        if not isinstance(raw, dict):
            raw = {}
        moa = raw.get("moa")
        if name:
            moa_mod.resolve_moa_preset(moa or {}, name)  # KeyError → 预设不存在
            raw["moa"] = moa_mod.set_active_moa_preset(moa, name)
        else:
            if isinstance(moa, dict):
                moa = dict(moa)
                moa["active_preset"] = ""
                raw["moa"] = moa
        cfg_mod.save_config(raw)
        # 同步 llm.json 顶层 active（仅激活时改；取消激活不动 llm.json，避免误清用户模型）
        if name:
            from hermes_config import get_llm_config, save_llm_config
            ll = get_llm_config()
            ll["vendor"] = "moa"
            ll["provider"] = "moa"
            ll["model"] = name
            ll["base_url"] = ""
            ll["api_key"] = ""
            save_llm_config(ll)
        return moa_get()
    except KeyError:
        return {"ok": False, "error": f"MoA 预设不存在：{name}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def moa_delete(preset_name: str) -> dict:
    cfg_mod, moa_mod = _moa_cfg_mod()
    if cfg_mod is None or moa_mod is None:
        return {"ok": False, "error": "内核 hermes_cli.config / moa_config 不可用"}
    name = (preset_name or "").strip()
    if not name:
        return {"ok": False, "error": "缺少 preset 名"}
    try:
        home = _moa_home()
        raw = cfg_mod.load_config()
        if not isinstance(raw, dict):
            raw = {}
        norm = moa_mod.normalize_moa_config(raw.get("moa") or {})
        if name not in norm["presets"]:
            return {"ok": False, "error": f"MoA 预设不存在：{name}"}
        if len(norm["presets"]) <= 1:
            return {"ok": False, "error": "至少保留一个 MoA 预设，无法删除最后一个"}
        del norm["presets"][name]
        if norm.get("default_preset") == name:
            norm["default_preset"] = next(iter(norm["presets"]))
        if norm.get("active_preset") == name:
            norm["active_preset"] = ""
        raw["moa"] = norm
        cfg_mod.save_config(raw)
        return moa_get()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

def moa_encode_turn(prompt: str, preset: str = "") -> dict:
    """生成一次性 /moa 标记串（__HERMES_MOA_TURN_V1__...），供「只能发文本」的前端。
    把该串作为普通用户消息发送，conversation_loop 会自动解码并跑一次 MoA 单轮后恢复原模型。
    预设配置内嵌于标记中，无需切换活动模型即可单条试用 MOA。"""
    cfg_mod, moa_mod = _moa_cfg_mod()
    if cfg_mod is None or moa_mod is None:
        return {"ok": False, "error": "内核 hermes_cli.config / moa_config 不可用"}
    try:
        return {"ok": True, "encoded": moa_mod.encode_moa_turn(prompt, None, preset or None)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
