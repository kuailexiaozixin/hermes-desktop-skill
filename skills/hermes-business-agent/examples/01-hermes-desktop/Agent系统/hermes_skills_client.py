"""hermes_skills_client.py — Hermes 官方 skills-index / Skills Hub 接入

职责：
  1. 列表：从 Hermes 官方 skills-index（hermes-agent.nousresearch.com/docs/api/skills-index.json）
     拉取技能，默认 source_filter="all"（官方 104 条 + 各社区源，约 9 万条），按
     分类/搜索/分页返回；卡片带 type 字段（official/trusted/github/community）供前端显示
     类型徽标。官方 104 条天然排在索引最前，故默认首页即见官方；前端可在「仅官方 / 全部（含社区）」
     间切换。字段形状与 SkillHub 市场一致，供前端同一套卡片渲染。
  2. 安装：通过 tools.skills_hub + tools.skills_guard 的隔离-扫描-落盘流程，
     把官方技能安装到 HERMES_HOME/skills/<name>/（扁平），与 `hermes skills add`
     走同一条代码路径（进程内 Library 调用，不 spawn CLI）。

依赖：全部来自已安装的 hermes-agent（tools.skills_hub / tools.skills_guard / agent.prompt_builder），
无新增第三方包。

已对 hermes-agent 0.19.0 实测核实的关键事实（避免幻觉）：
  - HermesIndexSource.search(query, limit) 是「截断式」：结果按 limit 截断。空查询返回
    索引前 limit 条；带查询时按评分返回前 limit 条匹配。官方 104 条恰好处在索引前 500，
    故 limit=500 空查也能命中，但「带查询」时官方条目可能被埋到 500 名之后而丢失。
    → 本模块改用「拉全量 + 本地过滤」策略：src.search("", limit=2_000_000) 取全量，
      再按 source/trust_level 与查询/分类在内存过滤，查询永不丢官方结果。
  - 官方条目形如 identifier="official/security/1password", source="official",
    trust_level="builtin", repo="NousResearch/hermes-agent",
    path="optional-skills/security/1password"。安装时 fetch 回退到 GitHubSource
    拉取 NousResearch/hermes-agent 仓库的 optional-skills/ 目录 → 需要 GitHub API。
    未鉴权仅 60 req/hr，故有概率被限流（与 `hermes skills add` 同一限制，非本实现缺陷）。
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from tools.skills_guard import (
    format_scan_report,
    scan_skill,
    should_allow_install,
)
from tools.skills_hub import (
    GitHubAuth,
    HermesIndexSource,
    SkillBundle,
    SkillMeta,
    SkillSource,
    create_source_router,
    ensure_hub_dirs,
    install_from_quarantine,
    quarantine_bundle,
)
from tools.skills_hub import HUB_DIR

from agent.prompt_builder import clear_skills_system_prompt_cache

import hermes_config as _hc

_GET_HOME = lambda: _hc.get_hermes_home()

# ── 全量索引缓存 ───────────────────────────────────────────────
# skills-index 本身由 HermesIndexSource 缓存 6h；这里再包一层内存缓存，
# 避免前端每次分页/分类/搜索都重建 9 万条 SkillMeta（实测全量转换约 0.2s，
# 缓存 15min 足够平滑，且查询过滤只在 104 条官方子集上做，极快）。
_CACHE_TTL = 60 * 15  # 15 分钟
_CACHE_LOCK = threading.Lock()
_ALL_METAS: list[SkillMeta] | None = None
_ALL_METAS_TS = 0.0
_HERMES_SOURCE: HermesIndexSource | None = None
_HERMES_SOURCE_TS = 0.0


def _get_hermes_source() -> HermesIndexSource:
    """返回带本地缓冲的 HermesIndexSource 单例。"""
    global _HERMES_SOURCE, _HERMES_SOURCE_TS
    with _CACHE_LOCK:
        now = time.time()
        if _HERMES_SOURCE is None or now - _HERMES_SOURCE_TS > _CACHE_TTL:
            _HERMES_SOURCE = HermesIndexSource(auth=GitHubAuth())
            _HERMES_SOURCE_TS = now
        return _HERMES_SOURCE


def _all_metas() -> list[SkillMeta]:
    """全量索引 SkillMeta（缓存 15min）。空查询 + 超大 limit 取全量，再本地过滤。"""
    global _ALL_METAS, _ALL_METAS_TS
    with _CACHE_LOCK:
        now = time.time()
        if _ALL_METAS is None or now - _ALL_METAS_TS > _CACHE_TTL:
            src = _get_hermes_source()
            _ALL_METAS = (
                src.search("", limit=2_000_000) if src.is_available else []
            )
            _ALL_METAS_TS = now
        return _ALL_METAS


def _official_metas() -> list[SkillMeta]:
    """官方可选技能（source=official & trust_level=builtin）。当前索引固定 104 条。"""
    return [
        m for m in _all_metas()
        if m.source == "official" and m.trust_level == "builtin"
    ]


def _trusted_metas() -> list[SkillMeta]:
    """builtin + trusted 级别（官方 + 社区受信任）。"""
    return [m for m in _all_metas() if m.trust_level in ("builtin", "trusted")]


def _type_label(meta: SkillMeta) -> str:
    """前端类型徽标用的归一化分类：official / trusted / github / community。

    实测 source 取值分布（0.19.0 索引 90605 条）：
      official=104 / skills.sh=19967 / clawhub=69150 / lobehub=505 /
      browse-sh=440 / github=438 / claude-marketplace=1
    trust_level 取值：builtin=104（全部来自 official）/ trusted=478 / community=90023。
    → official 永远 builtin；trusted 是社区里被标记为受信任的子集；其余按 source 归为社区/GitHub。
    """
    if meta.source == "official":
        return "official"
    if meta.trust_level == "trusted":
        return "trusted"
    if meta.source == "github":
        return "github"
    return "community"


def _derive_category(identifier: str) -> str:
    """从 official/<category>/<skill> 提取分类段。"""
    if not identifier:
        return ""
    parts = identifier.split("/")
    if parts[0] == "official" and len(parts) >= 3:
        return "/".join(parts[1:-1])
    return ""


def _meta_to_item(meta: SkillMeta) -> dict:
    """把 SkillMeta 归一化成前端 skillstore.js 认识的卡片字段。"""
    category = _derive_category(meta.identifier)
    extra = dict(meta.extra or {})
    provider = extra.get("provider", "")
    downloads = extra.get("downloads") or extra.get("installCount") or 0
    return {
        "slug": meta.identifier,
        "name": meta.name or meta.identifier.rsplit("/", 1)[-1],
        "description": meta.description or "",
        "category": category,
        "iconUrl": "",
        "downloads": int(downloads) if isinstance(downloads, (int, float, str)) and downloads else 0,
        "owner": provider or "Nous Research",
        "namespace": meta.source,
        "upstream_url": meta.repo or "",
        "homepage": "",
        "verified": meta.trust_level == "builtin",
        "source": meta.source,
        "trust_level": meta.trust_level,
        "type": _type_label(meta),
        "identifier": meta.identifier,
        "tags": list(meta.tags or []),
    }


def _match_query(meta: SkillMeta, q: str) -> bool:
    """子串匹配：name / description / identifier / tags（与 HermesIndexSource 的匹配面一致）。"""
    hay = " ".join([
        (meta.name or "").lower(),
        (meta.description or "").lower(),
        (meta.identifier or "").lower(),
        " ".join(str(t).lower() for t in (meta.tags or [])),
    ])
    return q in hay


def search_skills(
    q: str = "",
    category: str = "",
    page: int = 1,
    pageSize: int = 24,
    source_filter: str = "all",
) -> dict:
    """搜索 Hermes skills-index，返回与 SkillHub 市场兼容的分页结构。

    source_filter:
      - "official"：仅 source=official / trust_level=builtin（104 个官方可选技能）。
      - "trusted"：trust_level 为 trusted 或 builtin 的条目。
      - "all"（默认）：全部索引（约 9 万条，含 clawhub/skills.sh/lobehub/github 等社区源）。
        官方 104 条天然排在索引最前，故默认首页即见官方；卡片按 source/trust_level
        显示类型徽标（官方 / 受信任 / GitHub / 社区）区分。
    """
    src = _get_hermes_source()
    available = src.is_available

    if not available:
        return {
            "ok": True,
            "items": [],
            "categories": [],
            "total": 0,
            "page": page,
            "pageSize": pageSize,
            "pages": 0,
            "cached": False,
            "source": source_filter,
        }

    # 选定基础集合（官方/受信任为小子集，检索极快；all 为全量）
    if source_filter == "official":
        base = _official_metas()
    elif source_filter == "trusted":
        base = _trusted_metas()
    else:
        base = _all_metas()

    q = (q or "").strip().lower()
    if q:
        base = [m for m in base if _match_query(m, q)]

    if category:
        cat = category.strip().lower()
        base = [m for m in base if _derive_category(m.identifier).lower() == cat]

    total = len(base)
    page = max(1, page)
    pageSize = max(1, min(pageSize, 100))
    start = (page - 1) * pageSize
    end = start + pageSize
    pages = (total + pageSize - 1) // pageSize if total else 0

    return {
        "ok": True,
        "items": [_meta_to_item(m) for m in base[start:end]],
        # 分类条永远基于官方子集，与「官方市场」语义一致
        "categories": sorted({_derive_category(m.identifier) for m in _official_metas()}),
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "pages": pages,
        "cached": True,
        "source": source_filter,
    }


def get_categories() -> list[str]:
    """返回官方技能分类列表（去重、排序）。"""
    return sorted({_derive_category(m.identifier) for m in _official_metas()})


def _resolve_meta_and_bundle(identifier: str, sources: list[SkillSource]):
    """复刻 hermes_cli.skills_hub._resolve_source_meta_and_bundle（该函数为 CLI 私有）。

    依次询问各源 inspect/fetch，拿到第一个能 fetch 出 bundle 的源即止。
    官方条目因 resolved_github_id=None，HermesIndexSource.fetch 会回退到
    GitHubSource 拉取 NousResearch/hermes-agent 的 optional-skills/，需 GitHub API。
    """
    meta: SkillMeta | None = None
    bundle: SkillBundle | None = None
    for src in sources:
        if meta is None:
            try:
                meta = src.inspect(identifier)
                if meta:
                    _ = src  # 命中源，继续尝试 fetch
            except Exception:
                meta = None
        try:
            bundle = src.fetch(identifier)
        except Exception:
            bundle = None
        if bundle:
            if meta is None:
                try:
                    meta = src.inspect(identifier)
                except Exception:
                    meta = None
            break
    return meta, bundle


def _install_flow(identifier: str, sources: list, force: bool = False) -> dict:
    """安装技能（隔离-扫描-落盘流水线）；sources 为用于 resolve/fetch 的源适配器。"""
    if not identifier or not identifier.strip():
        return {"ok": False, "error": "identifier 不能为空"}
    identifier = identifier.strip()
    try:
        ensure_hub_dirs()
        meta, bundle = _resolve_meta_and_bundle(identifier, sources)
        if not bundle:
            return {"ok": False, "error": (
                f"无法从任何源获取 '{identifier}'。"
                "若索引命中，多半是 GitHub 未鉴权限流（未鉴权仅 60 req/hr）；"
                "请设置 GITHUB_TOKEN 或执行 `gh auth login` 后重试。"
            )}
        category = ""
        if bundle.source == "official" and bundle.identifier.startswith("official/"):
            parts = bundle.identifier.split("/")
            if len(parts) >= 3:
                category = "/".join(parts[1:-1])
        q_path = quarantine_bundle(bundle)
        scan_result = scan_skill(q_path, source=bundle.source)
        allowed, reason = should_allow_install(scan_result, force=force)
        if not allowed:
            import shutil as _shutil
            _shutil.rmtree(q_path, ignore_errors=True)
            return {"ok": False, "error": f"安全扫描未通过：{reason}\n{format_scan_report(scan_result)}"}
        install_dir = install_from_quarantine(
            q_path, bundle.name, "", bundle, scan_result
        )
        try:
            clear_skills_system_prompt_cache(clear_snapshot=True)
        except Exception:
            pass
        return {"ok": True, "name": bundle.name, "identifier": bundle.identifier,
                "category": category, "path": str(install_dir)}
    except ValueError as exc:
        return {"ok": False, "error": f"安装被阻止：{exc}"}
    except Exception as exc:
        return {"ok": False, "error": f"安装失败：{type(exc).__name__}: {exc}"}


def install_skill(identifier: str, force: bool = False) -> dict:
    """安装 Hermes 官方/索引技能（create_source_router 全源，含全量索引）。"""
    ensure_hub_dirs()
    return _install_flow(identifier, create_source_router(auth=GitHubAuth()), force)


def _sources_no_index():
    """create_source_router 的源，排除 HermesIndexSource（35MB 全量索引）。"""
    return [s for s in create_source_router(auth=GitHubAuth())
            if not isinstance(s, HermesIndexSource)]


def install_from_sources(identifier: str, force: bool = False) -> dict:
    """用排除全量索引的源安装（统一技能市场用），不触发 35MB 索引下载。"""
    return _install_flow(identifier, _sources_no_index(), force)


def warm_cache() -> None:
    """后台预热：预加载 Hermes skills-index，使用户打开官方市场时秒开。"""
    try:
        _ = _all_metas()
    except Exception:
        pass

def install_bundle_files(identifier, name, files, source, trust_level='community', metadata=None, force=False):
    """From a constructed files dict, run the quarantine-scan-install pipeline.

    Used by new market sources (official/skillsmp/lobehub) that build a
    SkillBundle directly instead of going through Hermes adapters.
    """
    if not files:
        return {'ok': False, 'error': '技能内容为空'}
    try:
        ensure_hub_dirs()
        bundle = SkillBundle(
            name=name or identifier,
            files=files,
            source=source,
            identifier=identifier,
            trust_level=trust_level,
            metadata=dict(metadata or {}),
        )
        q_path = quarantine_bundle(bundle)
        scan_result = scan_skill(q_path, source=bundle.source)
        allowed, reason = should_allow_install(scan_result, force=force)
        if not allowed:
            import shutil as _shutil
            _shutil.rmtree(q_path, ignore_errors=True)
            return {'ok': False, 'error': f'安全扫描未通过：{reason}\n{format_scan_report(scan_result)}'}
        install_dir = install_from_quarantine(
            q_path, bundle.name, '', bundle, scan_result
        )
        try:
            clear_skills_system_prompt_cache(clear_snapshot=True)
        except Exception:
            pass
        return {'ok': True, 'name': bundle.name, 'identifier': bundle.identifier,
                'category': '', 'path': str(install_dir)}
    except ValueError as exc:
        return {'ok': False, 'error': f'安装被阻止：{exc}'}
    except Exception as exc:
        return {'ok': False, 'error': f'安装失败：{type(exc).__name__}: {exc}'}
