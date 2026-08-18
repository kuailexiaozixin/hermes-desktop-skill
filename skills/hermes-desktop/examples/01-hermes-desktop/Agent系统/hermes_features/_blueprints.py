from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any



# ===================================================================
# 8. Blueprints — 自动化蓝图（Automation Blueprints，Hermes 原生内核）
# ===================================================================
# 真实机制（hermes_agent 0.19.0，cron/blueprint_catalog.py + hermes_cli/blueprint_cmd.py 实证）：
#   - Blueprint = 参数化「自动化模板」，单一事实来源是 cron.blueprint_catalog.CATALOG
#     （内置、只读目录，无用户自定义蓝图 API）。每个蓝图含：
#       key/title/description/category/tags + schedule_template(cron 占位符)
#       + prompt_template(可含 {slot}) + slots[](BlueprintSlot: name/type[time|enum|
#       text|weekdays]/label/default/options/optional/help/strict)。
#   - 桌面端接入范式（与原生 dashboard/GUI 一致）：选蓝图 → 按 slots 渲染表单 →
#     提交 fill_blueprint(blueprint, values, origin=None) → cron.jobs.create_job(**spec)
#     得到一个真实定时任务，落入 HERMES_HOME/cron/jobs.json，由本应用 cron 调度线程
#     到期触发执行（与「定时任务中心」共用同一存储与调度器，绝不另起一套）。
#   - 内核不可用时 available:False 降级；fill 校验失败（BlueprintFillError）返回
#     kind='validation' 的错误，供表单逐字段提示。
# 反模式红线：旧版把 Blueprint 当成「对话提示词模板」自己写 {name,prompt,category}
# 存 blueprints.json —— 完全脱离内核、永不执行。已废弃。
def _blueprint_catalog_mod():
    """惰性导入内核 blueprint_catalog 模块；不可用返回 None（降级 available:False）。"""
    try:
        import cron.blueprint_catalog as m
        return m
    except Exception:  # noqa: BLE001
        return None


def _cron_jobs_mod():
    """惰性导入内核 cron.jobs 模块；不可用返回 None。"""
    try:
        import cron.jobs as m
        return m
    except Exception:  # noqa: BLE001
        return None


def blueprints_list() -> dict:
    """列出 Hermes 原生自动化蓝图目录（只读、内置）。"""
    mod = _blueprint_catalog_mod()
    if mod is None:
        return {"ok": True, "available": False, "items": [],
                "error": "Blueprint 模块不可用（cron 未安装？）"}
    try:
        items = [mod.blueprint_catalog_entry(b) for b in mod.CATALOG]
        return {"ok": True, "available": True, "items": items}
    except Exception as e:  # noqa: BLE001
        return {"ok": True, "available": False, "items": [],
                "error": f"{type(e).__name__}: {e}"}


def blueprints_fill(key: str, values: dict | None = None) -> dict:
    """按蓝图 key + 用户填写的 slot 值，创建真实定时任务。

    返回 {ok, job:{id,name,schedule_display,deliver,next_run_at}} 或
    {ok:False, kind:'validation'|'notfound'|'create', error}。
    """
    values = values or {}
    cat = _blueprint_catalog_mod()
    if cat is None:
        return {"ok": False, "available": False,
                "error": "Blueprint 模块不可用（cron 未安装？）"}
    bp = cat.get_blueprint(key)
    if bp is None:
        return {"ok": False, "kind": "notfound", "error": f"未找到蓝图：{key}"}
    # 校验 + 翻译为 create_job 参数（内核保证无第二套作业引擎）
    try:
        spec = cat.fill_blueprint(bp, values, origin=None)
    except cat.BlueprintFillError as e:
        return {"ok": False, "kind": "validation", "error": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "kind": "validation", "error": f"{type(e).__name__}: {e}"}
    jobs = _cron_jobs_mod()
    if jobs is None:
        return {"ok": False, "available": False,
                "error": "cron.jobs 模块不可用（无法创建定时任务）"}
    try:
        job = jobs.create_job(**spec)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "kind": "create", "error": f"创建定时任务失败：{type(e).__name__}: {e}"}
    return {"ok": True, "job": {
        "id": job.get("id"),
        "name": job.get("name"),
        "schedule_display": job.get("schedule_display"),
        "deliver": job.get("deliver"),
        "next_run_at": job.get("next_run_at"),
    }}
