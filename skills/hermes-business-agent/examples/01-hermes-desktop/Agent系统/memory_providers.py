# -*- coding: utf-8 -*-
"""记忆增强：provider 切换 + 向量检索 + 分层查看（对照 13 §2.2 分层记忆系统）。

* Provider 切换：列出可用 memory provider（hermes 原生 plugins.memory 发现机制）+ 当前启用
  （config.yaml 的 ``memory.provider`` 键，经 hermes_config 深合并写，不抹其它键）。
* 向量检索：holographic MemoryStore + FactRetriever 混合检索（FTS5 + Jaccard + HRR 向量）。
* 分层查看：①记忆文件（MEMORY.md / USER.md）②holographic facts（按 category 分组）③active provider。

全部走 hermes 原生能力；任一能力不可用时优雅降级返回 error 而非抛异常。
"""
from __future__ import annotations

import hermes_config as hc

_DEFAULT_PROVIDER = "holographic"


def get_active_provider(home=None) -> str:
    """读取 config.yaml 的 memory.provider；未配置时返回 hermes 默认 holographic。"""
    try:
        cfg = hc.read_config_yaml(home) or {}
        mem = (cfg.get("memory") or {}).get("provider")
        return mem or _DEFAULT_PROVIDER
    except Exception:
        return _DEFAULT_PROVIDER


def list_providers(home=None) -> dict:
    """列出可用 provider + 当前启用。用轻量目录扫描，避免逐个 import。"""
    current = get_active_provider(home)
    names = []
    try:
        from plugins.memory import list_memory_provider_names
        names = list_memory_provider_names()
    except Exception:
        names = [current]
    if not names:
        names = [current]
    return {
        "current": current,
        "default": _DEFAULT_PROVIDER,
        "providers": [
            {"id": n, "active": (n == current)}
            for n in sorted(set(names))
        ],
    }


def switch_provider(provider_id: str, home=None) -> dict:
    """切换 memory.provider（写 config.yaml），返回新状态。"""
    if not provider_id or not isinstance(provider_id, str):
        return {"ok": False, "error": "provider_id 不能为空"}
    # 校验存在性
    try:
        from plugins.memory import list_memory_provider_names
        names = list_memory_provider_names()
        if provider_id not in names:
            return {
                "ok": False,
                "error": f"未知记忆 provider: {provider_id}",
                "available": sorted(names),
            }
    except Exception:
        pass
    try:
        hc.update_config_yaml(home, {"memory": {"provider": provider_id}})
    except Exception as e:
        return {"ok": False, "error": f"写入配置失败: {type(e).__name__}: {e}"}
    return {"ok": True, **list_providers(home)}


def search_memory(query: str, category=None, limit: int = 10) -> dict:
    """向量/语义检索：holographic MemoryStore + FactRetriever 混合检索。

    返回按 score 降序的记忆条目（fact_id/content/category/score/trust_score）。
    """
    if not query or not query.strip():
        return {"ok": True, "engine": "holographic", "items": []}
    try:
        from plugins.memory.holographic.store import MemoryStore
        from plugins.memory.holographic.retrieval import FactRetriever

        store = MemoryStore()
        retriever = FactRetriever(store)
        results = retriever.search(query.strip(), category=category, limit=int(limit))
        return {
            "ok": True,
            "engine": "holographic (FTS5 + Jaccard + HRR 向量)",
            "items": [
                {
                    "fact_id": r.get("fact_id"),
                    "content": r.get("content"),
                    "category": r.get("category"),
                    "score": round(float(r["score"]), 4) if r.get("score") is not None else None,
                    "trust_score": r.get("trust_score"),
                }
                for r in results
            ],
        }
    except Exception as e:
        return {"ok": False, "error": f"holographic 检索不可用: {type(e).__name__}: {e}"}


def memory_layers(home=None) -> dict:
    """分层查看：①记忆文件 ②holographic facts（按 category）③active provider。"""
    layers = {
        "active_provider": get_active_provider(home),
        "default": _DEFAULT_PROVIDER,
    }
    # 层 1：记忆文件（MEMORY.md / USER.md）
    try:
        layers["memory_files"] = hc.list_memory(home)
    except Exception as e:
        layers["memory_files"] = {"error": str(e)}
    # 层 2：holographic facts，按 category 分组
    try:
        from plugins.memory.holographic.store import MemoryStore

        store = MemoryStore()
        facts = store.list_facts(limit=500)
        by_cat = {}
        for f in facts:
            c = f.get("category") or "uncategorized"
            by_cat.setdefault(c, []).append({
                "fact_id": f.get("fact_id"),
                "content": f.get("content"),
                "trust_score": f.get("trust_score"),
                "updated_at": f.get("updated_at"),
            })
        layers["facts_by_category"] = by_cat
        layers["fact_count"] = len(facts)
    except Exception as e:
        layers["facts_by_category"] = {"error": f"holographic 记忆库不可用: {type(e).__name__}: {e}"}
    return layers
