# -*- coding: utf-8 -*-
"""上下文管理：context.engine 选择 + 压缩状态 + token 跟踪（对照 13 §2.1 上下文压缩引擎）。

* 引擎选择：读写 config.yaml 的 ``context.engine``（hermes 默认内置 "compressor"），
  并列出可用引擎（内置 compressor + plugins.context_engine 发现的第三方引擎）。
* 压缩状态：基于模型 context_window 估算 threshold_tokens，结合会话 token 水位给出
  usage_percent 与 should_compress 判定；若当前引擎可加载实例，则补充其真实
  compression_count / last_prompt_tokens 等运行时字段。
* token 跟踪：对接 sessions 会话 usage_input/usage_output，展示单会话上下文水位。

全部走 hermes 原生能力；任一能力不可用时优雅降级返回 error 而非抛异常。
"""
from __future__ import annotations

import hermes_config as hc

_DEFAULT_ENGINE = "compressor"
_THRESHOLD_PERCENT = 0.75


def get_active_engine(home=None) -> str:
    """读取 config.yaml 的 context.engine；未配置时返回 hermes 默认 compressor。"""
    try:
        cfg = hc.read_config_yaml(home) or {}
        eng = (cfg.get("context") or {}).get("engine")
        return eng or _DEFAULT_ENGINE
    except Exception:
        return _DEFAULT_ENGINE


def list_engines(home=None) -> dict:
    """列出可用上下文引擎 + 当前启用。内置 compressor 始终在列，附第三方发现结果。"""
    current = get_active_engine(home)
    engines = [{
        "id": _DEFAULT_ENGINE,
        "desc": "内置上下文压缩引擎 (ContextCompressor)",
        "builtin": True,
        "available": True,
    }]
    try:
        from plugins.context_engine import discover_context_engines
        for name, desc, avail in discover_context_engines():
            engines.append({
                "id": name, "desc": desc or "", "builtin": False,
                "available": bool(avail),
            })
    except Exception:
        pass
    # 去重（若 discover 也返回 compressor）
    seen, uniq = set(), []
    for e in engines:
        if e["id"] not in seen:
            seen.add(e["id"])
            uniq.append(e)
    for e in uniq:
        e["active"] = (e["id"] == current)
    return {"current": current, "default": _DEFAULT_ENGINE, "engines": uniq}


def switch_engine(engine_id, home=None) -> dict:
    """切换 context.engine（写 config.yaml 的 context.engine），返回新状态。"""
    if not engine_id or not isinstance(engine_id, str):
        return {"ok": False, "error": "engine_id 不能为空"}
    avail = [e["id"] for e in list_engines(home).get("engines", [])]
    if engine_id not in avail:
        return {"ok": False, "error": f"未知上下文引擎: {engine_id}", "available": avail}
    try:
        hc.update_config_yaml(home, {"context": {"engine": engine_id}})
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"写入配置失败: {type(e).__name__}: {e}"}
    return {"ok": True, **list_engines(home)}


def _model_context_window() -> int:
    """用 models.dev 查当前活动模型的 context_window。"""
    try:
        from agent.models_dev import get_model_capabilities
        cfg = hc.get_active_model_cfg()
        prov = (cfg.get("provider") or "").strip()
        model = (cfg.get("model") or "").strip()
        if not prov or not model:
            return 0
        caps = get_model_capabilities(prov, model)
        return int(getattr(caps, "context_window", 0) or 0)
    except Exception:  # noqa: BLE001
        return 0


def _load_engine_instance(name):
    """加载引擎实例（第三方走 plugins.context_engine；compressor 为内置）。"""
    try:
        from plugins.context_engine import load_context_engine
        inst = load_context_engine(name)
        if inst is not None:
            return inst
    except Exception:  # noqa: BLE001
        pass
    if name == _DEFAULT_ENGINE:
        try:
            from agent.context_compressor import ContextCompressor
            return ContextCompressor()
        except Exception:  # noqa: BLE001
            return None
    return None


def _session_tokens(cid=None) -> dict:
    """读取会话 token 用量（sessions conversations 表 usage_input/usage_output）。"""
    if not cid:
        return {"input": 0, "output": 0}
    try:
        from routes import sessions
        s = sessions.get(cid) or {}
        u = s.get("usage") or {}
        return {"input": int(u.get("input") or 0), "output": int(u.get("output") or 0)}
    except Exception:  # noqa: BLE001
        try:
            import sessions as _s
            s = _s.get(cid) or {}
            u = s.get("usage") or {}
            return {"input": int(u.get("input") or 0), "output": int(u.get("output") or 0)}
        except Exception:  # noqa: BLE001
            return {"input": 0, "output": 0}


def get_context_status(home=None, cid=None) -> dict:
    """压缩状态 + token 跟踪汇总（修正口径：真实优先 + N/A 语义 + 诊断）。

    返回：active_engine / context_window / threshold_tokens / usage_percent /
    should_compress / compression_count / session_tokens / diagnostics；
    引擎可加载实例时以其真实运行时字段优先（engine_live=True），否则用推算值并
    明确标出 N/A（None）而非伪 0，避免误导。
    """
    active = get_active_engine(home)
    diag = {"engine_loaded": False, "model_known": True, "reason": ""}
    ctx_len = _model_context_window()
    if not ctx_len:
        diag["model_known"] = False
        diag["reason"] = ("当前模型未在 models.dev 收录，无法推算上下文窗口；"
                           "引擎实例可提供真实值时不受影响")
    threshold = int(ctx_len * _THRESHOLD_PERCENT) if ctx_len else None
    tok = _session_tokens(cid) if cid else None
    last_prompt = int(tok["input"]) if tok else None

    status = {
        "active_engine": active,
        "default_engine": _DEFAULT_ENGINE,
        "context_window": ctx_len or None,
        "threshold_tokens": threshold,
        "threshold_percent": _THRESHOLD_PERCENT,
        "last_prompt_tokens": last_prompt,
        "usage_percent": round(last_prompt / ctx_len * 100, 1)
                         if (ctx_len and last_prompt is not None) else None,
        "should_compress": None,
        "compression_count": None,
        "session_tokens": tok,
        "diagnostics": diag,
    }

    inst = _load_engine_instance(active)
    if inst is not None:
        diag["engine_loaded"] = True
        try:
            gs = inst.get_status() or {}
            live = False
            for k in ("last_prompt_tokens", "threshold_tokens", "context_length",
                      "usage_percent", "compression_count"):
                if gs.get(k) is not None:
                    status[k] = gs[k]
            if gs.get("threshold_tokens") or gs.get("context_length"):
                status["engine_live"] = True
                live = True
            # 优先用引擎真实窗口/水位判定，其次用推算值
            lp = status.get("last_prompt_tokens")
            thr = status.get("threshold_tokens")
            if live and lp is not None and thr is not None:
                status["should_compress"] = bool(lp >= thr)
            elif lp is not None and threshold is not None:
                status["should_compress"] = bool(lp >= threshold)
        except Exception:  # noqa: BLE001
            pass
    return status

# ============================================================================
# 压缩历史（内存级，keyed by cid；示例应用足够，重启清空）
# ============================================================================
_HISTORY: dict[str, list] = {}
_HISTORY_MAX = 50


def record_compression(cid, *, original_count, compressed_count, reason="") -> None:
    """记录一次压缩事件，供前端「压缩历史」展示。"""
    import time
    _HISTORY.setdefault(cid, []).append({
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "original_count": original_count,
        "compressed_count": compressed_count,
        "saved": max(0, original_count - compressed_count),
        "reason": reason,
    })
    if len(_HISTORY[cid]) > _HISTORY_MAX:
        _HISTORY[cid] = _HISTORY[cid][-_HISTORY_MAX:]


def get_compression_history(cid) -> list:
    """取某会话的压缩历史（最近 N 条，按时间倒序）。"""
    return list(reversed(_HISTORY.get(cid, [])))
