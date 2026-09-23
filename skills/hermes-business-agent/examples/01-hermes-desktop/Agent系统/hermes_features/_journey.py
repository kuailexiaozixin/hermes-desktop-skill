from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any



# ===================================================================
# 11. Journey — 旅程/学习图谱
# ===================================================================
# 真实机制（hermes_agent 0.19.0+，hermes_cli/journey.py + agent/learning_graph.py 实证）：
#   - `hermes journey` 调用 agent.learning_graph.build_learning_graph() 组装「学到什么」图谱：
#       * nodes：学到的技能（非 base、agent 创建或曾使用）+ 记忆卡片（MEMORY.md/USER.md § 分块），
#         每节点含 id / kind(skill|memory) / label / timestamp / category / useCount / state /
#         createdBy / pinned（memory 节点另有 memorySource）；
#       * edges：技能 related_skills 边 + 记忆→技能的词汇重叠边；
#       * clusters：按 category 聚合计数；
#       * memory：记忆卡片原文（source / timestamp / title / body）；
#       * stats：密度统计（nodes / related_edges / edges_per_node / linked_nodes / isolated_pct /
#         categories / agent_created / used / top_categories + memory_nodes / memory_skill_edges /
#         learned_skills）。
#   - `hermes journey list|delete|edit <node>` 复用 agent.learning_mutations
#     （node_detail / delete_node / edit_node）；删除技能=归档（可 hermes curator restore 恢复），
#     删除记忆=重写其文件；删除/编辑走内核，绝不手写。
#   - 内核从 HERMES_HOME 读取（skills/ + memories/），与桌面 materialize 的 HERMES_HOME 一致，
#     路径不分裂（不在此手写 json / 不编造事件）。
# 因此这里只做薄封装：复用内核 build_learning_graph + learning_mutations，绝不伪造数据/手写存储。
# 内核模块不可用时优雅降级 available:False（绝不编造「首次对话」之类的假事件）。
def _journey_mod():
    """惰性导入内核 learning_graph 模块；不可用返回 None（降级 available:False）。"""
    try:
        import agent.learning_graph as m
        return m
    except Exception:
        return None

def _journey_mutations_mod():
    """惰性导入内核 learning_mutations 模块；不可用返回 None（降级 available:False）。"""
    try:
        import agent.learning_mutations as m
        return m
    except Exception:
        return None

def journey_get() -> dict:
    """获取学习旅程（真实 Hermes 学习图谱）。"""
    mod = _journey_mod()
    if mod is None:
        return {"ok": True, "available": False,
                "error": "内核 agent.learning_graph 不可用（hermes-agent 未安装？）",
                "nodes": [], "edges": [], "clusters": [], "memory": [], "stats": {}}
    try:
        payload = mod.build_learning_graph()
        return {
            "ok": True,
            "available": True,
            "nodes": payload.get("nodes", []),
            "edges": payload.get("edges", []),
            "clusters": payload.get("clusters", []),
            "memory": payload.get("memory", []),
            "stats": payload.get("stats", {}),
        }
    except Exception as e:
        return {"ok": True, "available": False,
                "error": f"{type(e).__name__}: {e}",
                "nodes": [], "edges": [], "clusters": [], "memory": [], "stats": {}}

def journey_node_detail(node_id: str) -> dict:
    """获取节点详情（供编辑预填）。内核不可用/节点不存在均返回 ok:False，绝不谎报。"""
    mod = _journey_mutations_mod()
    if mod is None:
        return {"ok": False, "available": False, "message": "内核 agent.learning_mutations 不可用"}
    return mod.node_detail(node_id)

def journey_delete(node_id: str) -> dict:
    """删除/归档学习节点（技能=归档可恢复；记忆=重写文件）。复用内核，绝不手写。"""
    mod = _journey_mutations_mod()
    if mod is None:
        return {"ok": False, "available": False, "message": "内核 agent.learning_mutations 不可用"}
    return mod.delete_node(node_id)

def journey_edit(node_id: str, content: str) -> dict:
    """编辑学习节点内容（技能=改 SKILL.md；记忆=改 § 分块）。复用内核，绝不手写。"""
    mod = _journey_mutations_mod()
    if mod is None:
        return {"ok": False, "available": False, "message": "内核 agent.learning_mutations 不可用"}
    return mod.edit_node(node_id, content)
