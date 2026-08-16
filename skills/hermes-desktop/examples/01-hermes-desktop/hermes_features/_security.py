from __future__ import annotations

import json, os, shutil, threading, datetime, subprocess, zipfile, io, time
from pathlib import Path
from typing import Any

from ._base import _get_home


# ===================================================================
# 12. Security Audit — 安全审计
# ===================================================================
def _security_audit_mod():
    """惰性导入内核 security_audit 模块；不可用时返回 None（降级 available:False）。"""
    try:
        import hermes_cli.security_audit as m
        return m
    except Exception:
        return None

def _security_advisories_mod():
    """惰性导入内核 security_advisories 模块；不可用时返回 None（投毒包检测降级空列表）。"""
    try:
        import hermes_cli.security_advisories as m
        return m
    except Exception:
        return None

_SEVERITY_LABELS = {
    "CRITICAL": "严重", "HIGH": "高", "MEDIUM": "中", "MODERATE": "中",
    "LOW": "低", "UNKNOWN": "未知",
}

def security_audit_run(*, skip_venv: bool = False, skip_plugins: bool = False, skip_mcp: bool = False) -> dict:
    """运行 Hermes 原生供应链安全审计（hermes security audit）。

    复用内核 hermes_cli.security_audit.run_audit：对三个攻击面
    （venv 已装 PyPI 包 / 插件声明的依赖 / config.yaml 钉版本号的 MCP 服务器）
    比对 OSV.dev 已知漏洞；并叠加 security_advisories 的已知投毒包检测
    （hermes doctor 同源，纯 metadata 查询、无需联网）。前端严格按内核结构映射。
    """
    sa = _security_audit_mod()
    sv = _security_advisories_mod()
    if sa is None:
        return {"ok": False, "available": False, "error": "内核 security_audit 不可用",
                "findings": [], "advisories": [], "total_components_scanned": 0, "finding_count": 0}
    home = Path(_get_home())
    # 1) OSV.dev 供应链审计（需联网；失败宽容降级，绝不谎报"通过"）
    findings: list = []
    total_components = 0
    osv_error = None
    try:
        total_components = sa._count_components(
            skip_venv=skip_venv, skip_plugins=skip_plugins, skip_mcp=skip_mcp, hermes_home=home
        )
        raw = sa.run_audit(
            skip_venv=skip_venv, skip_plugins=skip_plugins, skip_mcp=skip_mcp, hermes_home=home
        )
    except RuntimeError as exc:
        osv_error = f"无法连接 OSV.dev（需要联网）：{exc}"
        raw = []
    except Exception as exc:
        osv_error = f"审计失败：{exc}"
        raw = []
    for f in raw:
        comp = f.component
        vuln = f.vuln
        findings.append({
            "package": comp.name,
            "version": comp.version,
            "ecosystem": comp.ecosystem,
            "source": comp.source,
            "vuln_id": vuln.osv_id,
            "severity": vuln.severity,
            "severity_label": _SEVERITY_LABELS.get(vuln.severity, vuln.severity),
            "summary": vuln.summary,
            "fixed_versions": vuln.fixed_versions,
        })
    # 2) 已知投毒包检测（hermes doctor 同源，纯 metadata，无需联网）
    advisories: list = []
    if sv is not None:
        try:
            hits = sv.filter_unacked(sv.detect_compromised())
            for h in hits:
                a = h.advisory
                advisories.append({
                    "id": a.id,
                    "title": a.title,
                    "severity": a.severity,
                    "severity_label": _SEVERITY_LABELS.get(a.severity, a.severity),
                    "package": h.package,
                    "installed_version": h.installed_version,
                    "summary": a.summary,
                    "url": a.url,
                    "remediation": list(a.remediation),
                })
        except Exception:
            pass
    return {
        "ok": True,
        "available": True,
        "total_components_scanned": total_components,
        "finding_count": len(findings),
        "findings": findings,
        "advisories": advisories,
        "osv_error": osv_error,
    }
