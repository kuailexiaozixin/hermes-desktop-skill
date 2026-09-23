## Security Audit 安全审计 — 示例落地清单（from examples/01-hermes-desktop，实际改动）

> 本文件从 `references/08-capability-integration.md#security-audit` 抽出：该旗舰示例对 Security Audit 的实际落地（后端薄封装 `hermes_features.py` §12 / 路由 `routes/features.py` / 前端 `renderSecurityPanel` / 样式 `app.css`）。属示例耦合内容，不进入技能核心骨干（通用内核范式与反模式红线见 `references/08-capability-integration.md#security-audit`）。

---

## 3. 集成范式（examples 怎么做）

### 3.1 后端薄封装（`hermes_features.py` §12 `security_audit_run`）

```python
def _security_audit_mod():
    try:
        import hermes_cli.security_audit as m
        return m
    except Exception:
        return None          # 内核不可用 → 降级 available:False

def _security_advisories_mod():
    try:
        import hermes_cli.security_advisories as m
        return m
    except Exception:
        return None          # 投毒包检测降级为空列表

_SEVERITY_LABELS = {"CRITICAL":"严重","HIGH":"高","MEDIUM":"中","MODERATE":"中",
                    "LOW":"低","UNKNOWN":"未知"}

def security_audit_run(*, skip_venv=False, skip_plugins=False, skip_mcp=False) -> dict:
    sa = _security_audit_mod(); sv = _security_advisories_mod()
    if sa is None:
        return {"ok": False, "available": False, "error": "内核 security_audit 不可用",
                "findings": [], "advisories": [], "total_components_scanned": 0, "finding_count": 0}
    home = Path(_get_home())
    findings = []; total_components = 0; osv_error = None
    try:
        total_components = sa._count_components(skip_venv=..., skip_plugins=..., skip_mcp=..., hermes_home=home)
        raw = sa.run_audit(skip_venv=..., skip_plugins=..., skip_mcp=..., hermes_home=home)
    except RuntimeError as exc:
        osv_error = f"无法连接 OSV.dev（需要联网）：{exc}"; raw = []   # 宽容降级，绝不谎报
    except Exception as exc:
        osv_error = f"审计失败：{exc}"; raw = []
    for f in raw:                       # 严格按 Finding 真实结构映射
        comp = f.component; vuln = f.vuln
        findings.append({"package": comp.name, "version": comp.version,
            "ecosystem": comp.ecosystem, "source": comp.source,
            "vuln_id": vuln.osv_id, "severity": vuln.severity,
            "severity_label": _SEVERITY_LABELS.get(vuln.severity, vuln.severity),
            "summary": vuln.summary, "fixed_versions": vuln.fixed_versions})
    advisories = []
    if sv is not None:
        try:
            for h in sv.filter_unacked(sv.detect_compromised()):
                a = h.advisory
                advisories.append({"id": a.id, "title": a.title, "severity": a.severity,
                    "severity_label": _SEVERITY_LABELS.get(a.severity, a.severity),
                    "package": h.package, "installed_version": h.installed_version,
                    "summary": a.summary, "url": a.url, "remediation": list(a.remediation)})
        except Exception:
            pass
    return {"ok": True, "available": True, "total_components_scanned": total_components,
            "finding_count": len(findings), "findings": findings,
            "advisories": advisories, "osv_error": osv_error}
```

**要点**：
- 内核不可用 → `available:False` + 空 findings/advisories（前端降级提示）。
- OSV.dev 联网失败（`RuntimeError`）→ 记 `osv_error`、findings 清空，**但仍返回投毒包检测结果**（投毒包纯 metadata 无需联网）。
- 严重度按 `SEVERITY_ORDER` 降序展示（CRITICAL 在最上）。

### 3.2 路由（`routes/features.py`）

```python
@app.post('/api/features/security-audit')
async def api_security_audit(req):
    try:
        b = await req.json()
    except Exception:
        b = {}
    if not isinstance(b, dict):
        b = {}
    return hf.security_audit_run(
        skip_venv=bool(b.get('skip_venv', False)),
        skip_plugins=bool(b.get('skip_plugins', False)),
        skip_mcp=bool(b.get('skip_mcp', False)),
    )
```

### 3.3 前端面板（`static/src/panels/other.js` `renderSecurityPanel`）

- 标题「安全审计（Hermes 原生）」；说明三个攻击面 + 投毒包检测、需联网。
- 三个勾选：`跳过 venv` / `跳过插件` / `跳过 MCP` → POST 体 `skip_*` 布尔。
- 渲染：
  - `osv_error` 存在 → `tag warn`（⚠ 联网失败），仍展示投毒包。
  - findings：严重度徽章 `tag sev-<lowercase severity>`，行 = `package==version (ecosystem · source)` / `vuln_id — summary` / `修复版本：...`。
  - advisories：投毒包 `tag sev-critical` + 标题 + url + 处置（`remediation`）。
  - 空 findings 且无 osv_error → `tag ok`「未发现已知漏洞 ✅（已扫描 N 个组件）」；无投毒包 → `tag ok`「未发现已知投毒包 ✅」。
  - `available===false` → 降级「安全审计不可用：<error>」。

### 3.4 样式（`static/app.css`）

```css
.tag.sev-critical { background: rgba(224,108,117,.28); color: #e06c75; font-weight: 700; }
.tag.sev-high     { background: rgba(224,108,117,.18); color: #e06c75; }
.tag.sev-medium, .tag.sev-moderate { background: rgba(229,192,123,.22); color: #e5c07b; }
.tag.sev-low      { background: rgba(152,195,121,.2);  color: #98c379; }
.tag.sev-unknown  { background: rgba(150,150,150,.22); color: #9aa0a6; }
```
