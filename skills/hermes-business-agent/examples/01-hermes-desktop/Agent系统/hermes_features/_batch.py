from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any



# ===================================================================
# 14. Batch Processing — 批量处理（Hermes 原生 batch_runner）
# -------------------------------------------------------------------
# 真实机制（hermes-agent 0.19.0）：batch_runner.py 是顶层可导入模块（不是
# hermes_cli 子模块）。它把 JSONL 数据集（每行 {"prompt": ...}）的每条 prompt
# 送进一个隔离的 AIAgent 会话（默认本地；仅当数据行含 image/docker_image 且
# TERMINAL_ENV=docker 才用容器），按 toolset distribution 采样工具集，产出
# ShareGPT 轨迹（training / eval 数据）。BatchRunner.run() 用多进程
# multiprocessing.Pool(num_workers)，在冻结 Windows EXE 里子进程脆弱——
# 桌面端改用本进程 worker 线程串行驱动内核的 _process_single_prompt，复用其
# 真实的 Agent 运行逻辑与轨迹 schema，避免多进程，且尊重「单进程」铁律。
# ===================================================================
_BATCH_RUNS: dict = {}
_BATCH_LOCK = threading.Lock()


def _batch_runner_mod():
    try:
        import batch_runner as m
        return m
    except Exception:
        return None


def batch_list_distributions() -> dict:
    """返回 Hermes 原生 batch_runner 的 toolset distribution 列表。"""
    mod = _batch_runner_mod()
    if mod is None:
        return {"ok": True, "available": False, "items": [],
                "error": "batch_runner 模块不可用（hermes-agent 未安装？）"}
    try:
        dists = mod.list_distributions()
        items = []
        for k, v in dists.items():
            if isinstance(v, dict):
                items.append({
                    "key": k,
                    "description": v.get("description", ""),
                    "toolsets": list(v.get("toolsets", {}).keys()),
                })
            else:
                items.append({"key": k, "description": "", "toolsets": []})
        return {"ok": True, "available": True, "items": items}
    except Exception as e:
        return {"ok": True, "available": False, "items": [],
                "error": f"{type(e).__name__}: {e}"}


def batch_run(rows: list, opts: dict | None = None) -> dict:
    """启动一次批量处理（后台线程，立即返回 run_id 供轮询）。

    rows: 数据集。每项可为字符串，或 {"prompt": ...} / {"text": ...}。
    opts: run_name / model / base_url / api_key / max_iterations / distribution /
          reasoning_effort / max_tokens / verbose / providers_allowed|ignored|
          order / provider_sort / ephemeral_system_prompt。
    模型默认走 OpenRouter 免费模型（遵循项目铁律），distribution 默认 safe
    （不含 terminal，桌面端安全）。
    """
    mod = _batch_runner_mod()
    if mod is None:
        return {"ok": False, "available": False, "error": "batch_runner 模块不可用"}
    opts = opts or {}

    # 归一化为真实数据集：每条 {"prompt": ...}
    dataset = []
    for r in rows:
        if isinstance(r, dict):
            p = r.get("prompt") or r.get("text") or ""
        else:
            p = str(r)
        p = (p or "").strip()
        if p:
            dataset.append({"prompt": p})
    if not dataset:
        return {"ok": False, "kind": "empty",
                "error": "数据集为空（每条需含 prompt 或 text）"}

    run_name = opts.get("run_name") or f"desktop_batch_{int(time.time())}"
    re = opts.get("reasoning_effort")
    reasoning_config = {"effort": re} if re else None
    config = {
        "distribution": opts.get("distribution") or "safe",
        "model": opts.get("model") or "inclusionai/ling-3.0-flash:free",
        "max_iterations": int(opts.get("max_iterations") or 10),
        "base_url": opts.get("base_url") or "https://openrouter.ai/api/v1",
        "api_key": opts.get("api_key") or None,
        "verbose": bool(opts.get("verbose")),
        "ephemeral_system_prompt": opts.get("ephemeral_system_prompt") or None,
        "log_prefix_chars": 100,
        "providers_allowed": opts.get("providers_allowed"),
        "providers_ignored": opts.get("providers_ignored"),
        "providers_order": opts.get("providers_order"),
        "provider_sort": opts.get("provider_sort"),
        "openrouter_min_coding_score": opts.get("openrouter_min_coding_score"),
        "max_tokens": int(opts["max_tokens"]) if opts.get("max_tokens") else None,
        "reasoning_config": reasoning_config,
        "prefill_messages": None,
    }

    with _BATCH_LOCK:
        run_id = f"run_{int(time.time() * 1000)}_{len(_BATCH_RUNS)}"
        state = {
            "run_id": run_id,
            "run_name": run_name,
            "status": "running",
            "total": len(dataset),
            "processed": 0,
            "results": [],
            "statistics": {
                "tool_stats": {},
                "reasoning_stats": {"total_assistant_turns": 0,
                                    "turns_with_reasoning": 0,
                                    "turns_without_reasoning": 0},
                "discarded_no_reasoning": 0,
                "failed": 0,
            },
            "output_dir": None,
            "error": None,
            "started_at": time.time(),
        }
        _BATCH_RUNS[run_id] = state

    t = threading.Thread(
        target=_batch_run_worker,
        args=(mod, run_id, dataset, config, run_name),
        daemon=True,
    )
    t.start()
    return {"ok": True, "run_id": run_id, "run_name": run_name, "total": len(dataset)}


def _batch_item(idx: int, entry: dict, res: dict, discarded: bool = False,
                failed: bool = False) -> dict:
    traj = res.get("trajectory") or []
    out = ""
    for m in reversed(traj):
        if m.get("from") == "gpt":
            out = m.get("value", "")
            break
    success = bool(res.get("success")) and not failed and not discarded
    status = ("discarded" if discarded else
              "failed" if failed else
              "partial" if res.get("partial") else "completed")
    return {
        "prompt_index": idx,
        "prompt": (entry.get("prompt") or "")[:200],
        "status": status,
        "success": success,
        "output": out[:2000],
        "api_calls": res.get("api_calls"),
        "toolsets_used": res.get("toolsets_used", []),
        "tool_stats": (res.get("tool_stats") or {}),
        "error": (res.get("error") if not success else None),
    }


def _batch_run_worker(mod, run_id: str, dataset: list, config: dict, run_name: str):
    """后台线程：串行驱动内核 _process_single_prompt，累积真实轨迹与统计。"""
    state = _BATCH_RUNS.get(run_id)
    if state is None:
        return
    try:
        out_dir = Path(os.getcwd()) / "data" / run_name
        out_dir.mkdir(parents=True, exist_ok=True)
        traj_file = out_dir / "trajectories.jsonl"
        batch_file = out_dir / "batch_0.jsonl"
        with _BATCH_LOCK:
            state["output_dir"] = str(out_dir)

        total_tool_stats: dict = {}
        total_reasoning = {"total_assistant_turns": 0,
                           "turns_with_reasoning": 0,
                           "turns_without_reasoning": 0}
        discarded = 0
        failed = 0

        for idx, entry in enumerate(dataset):
            res = mod._process_single_prompt(idx, entry, 0, config)
            with _BATCH_LOCK:
                state["processed"] = idx + 1
            if res.get("success") and res.get("trajectory"):
                reasoning = res.get("reasoning_stats", {})
                if not reasoning.get("has_any_reasoning", True):
                    discarded += 1
                    with _BATCH_LOCK:
                        state["results"].append(_batch_item(idx, entry, res, discarded=True))
                    continue
                raw = res.get("tool_stats", {})
                norm = (mod._normalize_tool_stats(raw)
                        if hasattr(mod, "_normalize_tool_stats") else raw)
                err_counts = (mod._normalize_tool_error_counts(
                    {t: s.get("failure", 0) for t, s in raw.items()})
                    if hasattr(mod, "_normalize_tool_error_counts") else {})
                traj_entry = {
                    "prompt_index": idx,
                    "conversations": res["trajectory"],
                    "metadata": res.get("metadata", {}),
                    "completed": res.get("completed"),
                    "partial": res.get("partial", False),
                    "api_calls": res.get("api_calls"),
                    "toolsets_used": res.get("toolsets_used", []),
                    "tool_stats": norm,
                    "tool_error_counts": err_counts,
                }
                line = json.dumps(traj_entry, ensure_ascii=False)
                with open(batch_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                with open(traj_file, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                for tn, ts in raw.items():
                    d = total_tool_stats.setdefault(
                        tn, {"count": 0, "success": 0, "failure": 0})
                    d["count"] += ts.get("count", 0)
                    d["success"] += ts.get("success", 0)
                    d["failure"] += ts.get("failure", 0)
                for k in total_reasoning:
                    total_reasoning[k] += reasoning.get(k, 0)
                with _BATCH_LOCK:
                    state["results"].append(_batch_item(idx, entry, res))
            else:
                failed += 1
                with _BATCH_LOCK:
                    state["results"].append(_batch_item(idx, entry, res, failed=True))

        checkpoint = {
            "run_name": run_name,
            "completed_prompts": [r["prompt_index"] for r in state["results"]
                                  if r.get("success")],
            "batch_stats": {},
            "last_updated": datetime.datetime.now().isoformat(),
        }
        (out_dir / "checkpoint.json").write_text(
            json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
        statistics = {
            "tool_stats": total_tool_stats,
            "reasoning_stats": total_reasoning,
            "discarded_no_reasoning": discarded,
            "failed": failed,
            "total": len(dataset),
            "duration_sec": round(time.time() - state["started_at"], 2),
        }
        (out_dir / "statistics.json").write_text(
            json.dumps(statistics, ensure_ascii=False, indent=2), encoding="utf-8")
        with _BATCH_LOCK:
            state["statistics"] = statistics
            state["status"] = "done"
    except Exception as e:
        with _BATCH_LOCK:
            state["status"] = "error"
            state["error"] = f"{type(e).__name__}: {e}"


def batch_status(run_id: str) -> dict:
    """轮询某次批量处理的进度与结果。"""
    with _BATCH_LOCK:
        st = _BATCH_RUNS.get(run_id)
        if st is None:
            return {"ok": False, "kind": "notfound",
                    "error": f"未找到批量任务：{run_id}"}
        snap = {k: st[k] for k in ("run_name", "status", "total", "processed",
                                   "results", "statistics", "output_dir", "error")}
    return {"ok": True, "run_id": run_id, **snap}