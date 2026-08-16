from __future__ import annotations

import copy
import json
import os
import re
import shutil
import sys
import threading
from pathlib import Path

from ._paths import DEFAULT_MODEL, DEFAULT_VENDOR, VENDOR_PRESETS, _DEFAULT_PROVIDER, _deep_merge, get_hermes_home, read_config_yaml, update_config_yaml



def write_model_routes(home: Path | None = None, cfg: dict | None = None) -> None:
    """把已配置模型的路由记录进 config.yaml（Library 模式下的中性记录）。

    Library 模式说明：Agent 由 agent_runtime.build_agent 直接把 provider/model/
    api_key/base_url 传给 AIAgent 构造器，**不再经 API Server 的 model_routes 选路**。
    这里写入的 model_routes 仅作「已配置模型」的持久化记录（审计/未来复用），
    不写 host/port/key/cors 等网关网络键（Library 模式无监听端口）。
    """
    h = home or get_hermes_home()
    models = get_models_list(cfg)
    model_routes: dict = {}
    for m in models:
        vendor = m.get("vendor") or DEFAULT_VENDOR
        preset = VENDOR_PRESETS.get(vendor, {})
        route = {"model": m.get("model") or m["id"],
                 "provider": preset.get("provider", vendor)}
        if m.get("api_key"):
            route["api_key"] = m["api_key"]
        if m.get("base_url"):
            route["base_url"] = m["base_url"]
        model_routes[m["id"]] = route
    update_config_yaml(h, {"platforms": {"api_server": {"extra": {
        "model_name": models[0]["id"], "model_routes": model_routes}}}})


# ── 联网搜索后端（Hermes Library 真实 schema，依据 hermes-llms-full.txt §Web Search Backends / Web Search Provider Plugins） ──
# 真实配置键（优先级从高到低）：
#   web_search  : web.search_backend  >  web.backend  >  按环境变量自动探测
#   web_extract : web.extract_backend >  web.backend  >  按环境变量自动探测
# 8 个内置后端（均随 hermes-agent 以插件形式内置，无需额外安装）：
#   firecrawl(默认,需 KEY) / searxng(免费,需 SEARXNG_URL 自托管地址) / brave-free(免费额度,需 BRAVE_SEARCH_API_KEY)
#   / ddgs(免费无需任何 Key,首次自动安装 SDK) / tavily / exa / parallel(均需 KEY) / xai(需 XAI_API_KEY,手动 opt-in)
#   - 未显式设置时 Hermes 按可用 Key 自动探测；xai 不参与自动探测，须显式 web.backend: xai。
#   - 唯一「零配置即免费」的后端是 ddgs（无需任何 Key/URL）；searxng 也免费但需自托管 SEARXNG_URL。
_WEB_BACKENDS = ("firecrawl", "searxng", "brave-free", "ddgs", "tavily", "exa", "parallel", "xai")
# 后端 -> 所需环境变量（None 表示零凭据：ddgs）
_WEB_BACKEND_KEY_ENV = {
    "firecrawl": "FIRECRAWL_API_KEY",   # 或 FIRECRAWL_API_URL（自托管时 Key 可省略）
    "searxng": "SEARXNG_URL",           # 自托管实例地址（非 API Key）
    "brave-free": "BRAVE_SEARCH_API_KEY",
    "tavily": "TAVILY_API_KEY",
    "exa": "EXA_API_KEY",
    "parallel": "PARALLEL_API_KEY",
    "xai": "XAI_API_KEY",
    "ddgs": None,
}
# 零凭据后端（无需任何 Key/URL）：ddgs
_WEB_NO_KEY_BACKENDS = {"ddgs"}
# 仅需「实例地址」(SEARXNG_URL) 而非 API Key 的后端
_WEB_URL_BACKENDS = {"searxng"}


def ensure_default_web_search_backend(home: Path | None = None) -> None:
    """保证开箱即用的免费联网搜索（零配置）。

    若用户未显式配置任何后端（web.search_backend / web.backend 均无），
    则默认写入 web.search_backend: ddgs——ddgs 是 Hermes 内置、无需任何
    API Key / URL 的后端（首次使用自动安装其 SDK），从而实现「零配置免费联网」。
    已配置任一后端的用户设置绝不覆盖（深合并，保留其它 web.* 键）。
    """
    h = home or get_hermes_home()
    cfg = read_config_yaml(h)
    web = cfg.get("web")
    if web is None:
        update_config_yaml(h, {"web": {"search_backend": "ddgs"}})
        return
    existing = (web.get("search_backend") or web.get("backend") or "").strip()
    if not existing:
        update_config_yaml(h, {"web": {"search_backend": "ddgs"}})


def get_web_search_status(home: Path | None = None) -> dict:
    """返回联网搜索后端真实状态：{ok, label, backend, needs_key, key_env, ready, message}。

    读取 Hermes 真实配置键 web.search_backend / web.backend（不再使用虚构的
    web.search_provider）。未配置时说明将自动探测（默认 firecrawl，需 Key），
    并提示零配置免费的 ddgs 方案。
    """
    cfg = read_config_yaml(home)
    web = (cfg.get("web") or {}) or {}
    backend = (web.get("search_backend") or web.get("backend") or "").strip()
    if not backend:
        return {"ok": True, "label": "未配置（自动探测）", "backend": "",
                "needs_key": True, "key_env": "FIRECRAWL_API_KEY", "ready": False,
                "message": "未配置后端：Hermes 将按可用 Key 自动选择（默认 firecrawl，"
                           "需 FIRECRAWL_API_KEY）。零配置免费方案：ddgs 无需任何 Key"
                           "（首次自动安装 SDK）；或自托管 SearXNG 并填 SEARXNG_URL。"}
    key_env = _WEB_BACKEND_KEY_ENV.get(backend)
    if key_env is None:
        # ddgs：零凭据
        ready = True
        needs_key = False
        label = backend
    elif key_env == "SEARXNG_URL":
        ready = bool(os.environ.get("SEARXNG_URL"))
        needs_key = False
        label = backend + ("" if ready else "（未就绪：需 SEARXNG_URL）")
    else:
        ready = bool(os.environ.get(key_env))
        needs_key = True
        label = backend + ("" if ready else f"（未就绪：需 {key_env}）")
    return {"ok": True, "label": label, "backend": backend,
            "needs_key": needs_key, "key_env": key_env or "", "ready": ready,
            "message": "" if ready else f"后端 {backend} 未就绪：需配置 {key_env}。"}


# ============================================================================
# 4) 模型管理（llm.json）
# ============================================================================
def get_llm_config() -> dict:
    """读取用户 LLM 配置；缺省返回默认厂商占位（无 key，原生 provider id）。"""
    p = get_hermes_home() / "llm.json"
    if p.exists():
        try:
            cfg = json.loads(p.read_text(encoding="utf-8"))
            vendor = cfg.get("vendor", DEFAULT_VENDOR)
            cfg.setdefault("vendor", vendor)
            cfg.setdefault("provider",
                           VENDOR_PRESETS.get(vendor, {}).get("provider", vendor))
            return cfg
        except Exception:
            pass
    preset = VENDOR_PRESETS.get(DEFAULT_VENDOR, {})
    return {
        "vendor": DEFAULT_VENDOR,
        "provider": preset.get("provider", DEFAULT_VENDOR),
        "base_url": preset.get("base_url", ""),
        "api_key": "",
        "model": DEFAULT_MODEL,
    }


def save_llm_config(cfg: dict) -> None:
    p = get_hermes_home() / "llm.json"
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _model_entry_id(m: dict) -> str:
    return (m.get("model") or m.get("id") or "").strip()


def get_models_list(cfg: dict | None = None) -> list[dict]:
    """返回已配置模型列表；兼容旧版单模型 llm.json（无 models 列表时用顶层字段构造）。"""
    if cfg is None:
        cfg = get_llm_config()
    models = cfg.get("models")
    if isinstance(models, list) and models:
        out: list[dict] = []
        for m in models:
            if not isinstance(m, dict):
                continue
            mid = _model_entry_id(m)
            if not mid:
                continue
            m = dict(m)
            m["id"] = mid
            m["model"] = mid
            m.setdefault("vendor", cfg.get("vendor", DEFAULT_VENDOR))
            if not m.get("base_url"):
                m["base_url"] = cfg.get("base_url", "")
            if not m.get("api_key"):
                m["api_key"] = cfg.get("api_key", "")
            out.append(m)
        if out:
            return out
    mid = _model_entry_id(cfg) or DEFAULT_MODEL
    return [{
        "id": mid,
        "vendor": cfg.get("vendor", DEFAULT_VENDOR),
        "base_url": cfg.get("base_url", ""),
        "api_key": cfg.get("api_key", ""),
        "model": mid,
    }]


def _normalize_model_entry(m: dict) -> dict:
    """把一条模型记录归一化为 llm.json 的持久化形态。

    固定保留 id/vendor/model/base_url/api_key；其余可选字段做类型校正后保留，
    使前端设置的逐模型参数（温度、Top-P、停止序列、输出格式、上下文长度、
    能力开关等）在「保存 → 重载」后原样往返，避免「设置后消失」的数据丢失。
    """
    mid = _model_entry_id(m) or DEFAULT_MODEL
    entry = {
        "id": mid,
        "vendor": m.get("vendor") or DEFAULT_VENDOR,
        "base_url": m.get("base_url") or "",
        "api_key": m.get("api_key") or "",
        "model": mid,
    }
    # 采样/格式类（经 AIAgent.request_overrides 透传给 provider）
    if m.get("max_tokens"):
        try:
            v = int(m["max_tokens"])
            if v > 0:
                entry["max_tokens"] = v
        except (TypeError, ValueError):
            pass
    if m.get("reasoning_effort"):
        entry["reasoning_effort"] = m["reasoning_effort"]
    if isinstance(m.get("reasoning_config"), dict):
        entry["reasoning_config"] = m["reasoning_config"]
    for f in ("temperature", "top_p"):
        v = m.get(f)
        if v not in (None, ""):
            try:
                entry[f] = float(v)
            except (TypeError, ValueError):
                pass
    if m.get("top_logprobs") not in (None, ""):
        try:
            entry["top_logprobs"] = int(m["top_logprobs"])
        except (TypeError, ValueError):
            pass
    if m.get("stop_sequences") not in (None, ""):
        entry["stop_sequences"] = str(m["stop_sequences"])
    if m.get("response_format") not in (None, ""):
        entry["response_format"] = str(m["response_format"])
    for f in ("input_max_tokens", "output_max_tokens"):
        v = m.get(f)
        if v not in (None, ""):
            try:
                entry[f] = int(v)
            except (TypeError, ValueError):
                pass
    # 能力/开关类（描述性元数据，仅持久化，不影响内核行为）
    for cap in ("tools", "vision", "thinking", "custom_protocol", "web_search"):
        if cap in m:
            entry[cap] = bool(m[cap])
    return entry


def save_models_list(models: list[dict], active_id: str | None = None) -> dict:
    """以 models 列表为唯一真相写入 llm.json，并镜像 active 条目到顶层字段。

    每条模型的逐模型配置（温度、Top-P、停止序列、输出格式、上下文长度、
    能力开关等）见 ``_normalize_model_entry`` —— 一并持久化，保存后重载不丢失。
    """
    models = [dict(m) for m in (models or []) if isinstance(m, dict)]
    norm = [_normalize_model_entry(m) for m in models]
    if not norm:
        norm = [{"id": DEFAULT_MODEL, "vendor": DEFAULT_VENDOR,
                 "base_url": VENDOR_PRESETS.get(DEFAULT_VENDOR, {}).get("base_url", ""),
                 "api_key": "", "model": DEFAULT_MODEL}]
    if active_id is None or not any(m["id"] == active_id for m in norm):
        active_id = norm[0]["id"]
    active = next((m for m in norm if m["id"] == active_id), norm[0])
    cfg = {
        "vendor": active.get("vendor", DEFAULT_VENDOR),
        "provider": VENDOR_PRESETS.get(active.get("vendor", DEFAULT_VENDOR), {}).get(
            "provider", active.get("vendor", DEFAULT_VENDOR)),
        "base_url": active.get("base_url", ""),
        "api_key": active.get("api_key", ""),
        "model": active.get("model", active["id"]),
        "models": norm,
    }
    save_llm_config(cfg)
    try:
        write_model_routes(cfg=cfg)
    except Exception:
        pass
    return cfg


def get_active_model_cfg(model_id: str | None = None) -> dict:
    """返回用于构造 AIAgent 的模型配置 dict。

    {vendor, provider, base_url, api_key, model, max_tokens?, reasoning_config?,
     温度/Top-P/停止序列/输出格式/上下文长度（透传 provider）, 能力开关（描述性元数据）}
    - model_id 指定时，从已配置模型列表中按 id / model 名匹配；
    - 未指定或匹配不到时，回退 llm.json 顶层 active 模型。
    provider 统一解析为厂商原生 Hermes provider id（VENDOR_PRESETS[vendor].provider）。
    """
    models = get_models_list()
    chosen: dict | None = None
    if model_id:
        _matches = [m for m in models
                    if m.get("id") == model_id or m.get("model") == model_id]
        if _matches:
            # 同 id 可能有多条（如默认空 key 条目 + 用户配置条目）：优先选带
            # api_key 的，避免「空 key 默认条目」遮蔽真实配置导致对话 401。
            chosen = next((m for m in _matches if m.get("api_key")), _matches[0])
    if chosen is None:
        active = get_llm_config()
        mid = (active.get("model") or "").strip()
        _matches = [m for m in models
                    if m.get("id") == mid or m.get("model") == mid]
        if _matches:
            chosen = next((m for m in _matches if m.get("api_key")), _matches[0])
        if chosen is None:
            chosen = {
                "vendor": active.get("vendor", DEFAULT_VENDOR),
                "base_url": active.get("base_url", ""),
                "api_key": active.get("api_key", ""),
                "model": mid or DEFAULT_MODEL,
            }
    vendor = chosen.get("vendor") or DEFAULT_VENDOR
    cfg = {
        "vendor": vendor,
        "provider": VENDOR_PRESETS.get(vendor, {}).get("provider", vendor or _DEFAULT_PROVIDER),
        "base_url": chosen.get("base_url") or "",
        "api_key": chosen.get("api_key") or "",
        "model": chosen.get("model") or chosen.get("id") or DEFAULT_MODEL,
    }
    if chosen.get("max_tokens"):
        try:
            cfg["max_tokens"] = int(chosen["max_tokens"])
        except (TypeError, ValueError):
            pass
    _rc = reasoning_effort_to_config(chosen)
    if _rc:
        cfg["reasoning_config"] = _rc
    # 逐模型采样/格式参数：供 build_agent 经 AIAgent.request_overrides 透传给 provider
    for f in ("temperature", "top_p", "top_logprobs", "stop_sequences", "response_format",
              "input_max_tokens", "output_max_tokens"):
        if chosen.get(f) not in (None, ""):
            cfg[f] = chosen[f]
    # 能力/开关类元数据（描述性，供 UI/客户端逻辑使用，不改变内核行为）
    for cap in ("tools", "vision", "thinking", "custom_protocol", "web_search"):
        if cap in chosen:
            cfg[cap] = chosen[cap]
    return cfg


def reasoning_effort_to_config(model: dict) -> "dict | None":
    """把模型的推理强度配置转换成 AIAgent 接受的 ``reasoning_config`` 字典。

    Hermes Library 的 ``AIAgent.__init__`` 只认 ``reasoning_config``（dict），
    而模型设置 UI 存的是 ``reasoning_effort``（字符串，如 ``"high"``）。
    本函数负责两者衔接，避免「推理强度」下拉框成为摆设：

    - 若模型已显式给出 ``reasoning_config``（dict），优先用它（更具体）；
    - 否则若设有 ``reasoning_effort`` 字符串，转成 ``{"effort": <level>}``；
    - 都没有则返回 ``None``（交给 Hermes 走默认 ``medium``）。

    返回的 dict 形状 ``{"effort": "<none|minimal|low|medium|high|xhigh|max|ultra>"}``
    与批量运行（``hermes_features.batch_run``）使用的约定一致。
    """
    rc = model.get("reasoning_config")
    if isinstance(rc, dict) and rc:
        return dict(rc)
    re_ = model.get("reasoning_effort")
    if re_:
        return {"effort": str(re_)}
    return None


# ── Agent 设置（HERMES_HOME/agent_settings.json） ─────────────────────────
def read_agent_settings(home: Path | None = None) -> dict:
    p = (home or get_hermes_home()) / "agent_settings.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def write_agent_settings(patch: dict, home: Path | None = None) -> dict:
    h = home or get_hermes_home()
    cur = read_agent_settings(h)
    merged = _deep_merge(cur, patch or {})
    (h / "agent_settings.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


def get_loop_max_iterations() -> int | None:
    """用户设置的 Agent Loop 最大迭代次数（未设置返回 None → Hermes 默认 90）。"""
    v = (read_agent_settings().get("loop") or {}).get("max_iterations")
    try:
        v = int(v)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None
