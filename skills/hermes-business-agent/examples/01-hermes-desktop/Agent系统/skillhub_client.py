"""skillhub_client.py — SkillHub 技能市场接入

职责：
  1. 列表代理：把 SkillHub 公开列表接口（api.skillhub.cn/api/skills，无需鉴权）转发
     并归一化为本项目前端可用的字段。
  2. 源解析：SkillHub 社区技能的 upstream_url 多为 clawhub.ai/<owner>/<repo>，
     clawhub 页面内嵌 GitHub 仓库地址 → 解析出 github.com/<owner>/<repo>。
  3. 安装：从 GitHub codeload 下载仓库 zip（无需 git 运行时），解压并扁平化顶层
     目录后写入 HERMES_HOME/skills/<slug>/，供 Hermes Library 模式自动发现。

全部使用标准库（urllib / zipfile / shutil），不引入第三方依赖，确保冻结态 EXE
（零 Python 运行时）亦可联网安装技能。
"""
from __future__ import annotations

import io
import json
import re
import shutil
import threading
import time
import zipfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import hermes_config as _hc
_GET_HOME = lambda: _hc.get_hermes_home()

SKILLHUB_API = "https://api.skillhub.cn/api/skills"
SKILLHUB_DOWNLOAD_API = "https://api.skillhub.cn/api/v1/download"
_UA = {"User-Agent": "Mozilla/5.0 (Hermes Desktop SkillHub client)"}
_GITHUB_RE = re.compile(r"github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/|$)")
_CLAWHUB_RE = re.compile(r"clawhub\.ai/([\w.-]+)/([\w.-]+)")

# ── 缓存（TTL 内存 + 磁盘）─────────────────────────────────────────────
# 解决"长时间加载中"：首次联网拉取后写入缓存，应用启动后后台预热，
# 用户打开商店前缓存已就绪 → 秒开；且列表接口不再阻塞事件循环。
_CACHE_TTL = 30 * 60          # 列表缓存 30 分钟
_CATEGORY_TTL = 24 * 60 * 60  # 分类缓存 1 天（分类极稳定）
_DISK_PRUNE_TTL = 24 * 60 * 60  # 磁盘缓存中超过 1 天的条目清理
_STALE_TTL = _CACHE_TTL * 1000  # 过期缓存仍可回退的窗口（约 20 天）
_CACHE_LOCK = threading.Lock()
_MEM_CACHE: dict = {}          # key -> (ts, value)
_DISK_CACHE_PATH: Path | None = None

# 兜底分类表：即便预热/网络失败，分类 chips 也始终可渲染
_BASE_CATEGORIES = [
    "ai-agent", "dev-programming", "office-efficiency", "knowledge-management",
    "design-media", "data-analysis", "content-creation", "professional",
    "business-ops", "it-ops-security", "life-service", "education",
]


def _cache_path() -> Path:
    global _DISK_CACHE_PATH
    if _DISK_CACHE_PATH is None:
        _DISK_CACHE_PATH = _GET_HOME() / "skillhub_cache.json"
    return _DISK_CACHE_PATH


def _load_disk_cache() -> dict:
    # Disk cache disabled (in-memory only) to respect 1MB disk cap.
    return {}


def _save_disk_cache(data: dict) -> None:
    # Disk cache disabled (in-memory only) to respect 1MB disk cap.
    pass


def _cache_get(key: str, ttl: int):
    now = time.time()
    with _CACHE_LOCK:
        if key in _MEM_CACHE:
            ts, val = _MEM_CACHE[key]
            if now - ts < ttl:
                return val
        disk = _load_disk_cache()
        if key in disk:
            ts, val = disk[key]
            if now - ts < ttl:
                _MEM_CACHE[key] = (ts, val)
                return val
    return None


def _cache_put(key: str, val, ttl: int) -> None:
    now = time.time()
    with _CACHE_LOCK:
        _MEM_CACHE[key] = (now, val)
        disk = _load_disk_cache()
        # 清理过期条目，避免磁盘缓存无限增长
        disk = {k: (t, v) for k, (t, v) in disk.items() if now - t < _DISK_PRUNE_TTL}
        disk[key] = (now, val)
    _save_disk_cache(disk)


def _http_json(url: str, params: dict | None = None, timeout: int = 25):
    if params:
        url = url + ("&" if "?" in url else "?") + urlencode(params)
    req = Request(url, headers=_UA)
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def search_skills(q: str = "", category: str = "", page: int = 1,
                  pageSize: int = 24, sort: str = "score", use_cache: bool = True) -> dict:
    """代理 SkillHub 列表搜索，归一化返回。

    命中缓存（TTL）即直接返回，避免联网阻塞。缓存未命中才联网，
    成功写入缓存；若联网失败且有（过期）缓存则回退缓存，再失败才抛错。

    返回：{"items":[...], "categories":[...], "total":int,
           "page":int, "pageSize":int, "pages":int|None, "cached":bool}
    """
    params = {
        "keyword": q or "",
        "category": category or "",
        "sortBy": sort or "score",
        "page": page,
        "pageSize": pageSize,
    }
    cache_key = f"s:{q}|{category}|{page}|{pageSize}|{sort}"
    if use_cache:
        hit = _cache_get(cache_key, _CACHE_TTL)
        if hit is not None:
            hit = dict(hit)
            hit["cached"] = True
            return hit
    try:
        data = _http_json(SKILLHUB_API, params)
    except Exception:
        if use_cache:
            stale = _cache_get(cache_key, _STALE_TTL)  # 允许回退到过期缓存
            if stale is not None:
                stale = dict(stale)
                stale["cached"] = True
                return stale
        raise
    payload = data.get("data", {}) if isinstance(data, dict) else {}
    skills = payload.get("skills", []) if isinstance(payload, dict) else []
    items: list[dict] = []
    cats: set[str] = set()
    for s in skills:
        ns = s.get("namespace") or {}
        items.append({
            "slug": s.get("slug"),
            "name": s.get("name"),
            "description": s.get("description_zh") or s.get("description") or "",
            "category": s.get("category") or "",
            "iconUrl": s.get("iconUrl") or "",
            "downloads": s.get("downloads") or 0,
            "owner": s.get("ownerName") or (ns.get("displayName") if isinstance(ns, dict) else ""),
            "namespace": ns.get("canonicalName") if isinstance(ns, dict) else "",
            "upstream_url": s.get("upstream_url") or "",
            "homepage": s.get("homepage") or "",
            "verified": bool(s.get("verified")),
            "source": s.get("source") or "community",
            "version": s.get("version") or "",
        })
        if s.get("category"):
            cats.add(s.get("category"))
    total = payload.get("total") if isinstance(payload, dict) else None
    pages = None
    if isinstance(total, int) and total > 0 and pageSize > 0:
        pages = (total + pageSize - 1) // pageSize
    result = {
        "items": items,
        "categories": sorted(cats),
        "total": total,
        "page": page,
        "pageSize": pageSize,
        "pages": pages,
        "cached": False,
    }
    if use_cache:
        _cache_put(cache_key, result, _CACHE_TTL)
    return result


def get_categories(use_cache: bool = True, sample_pages: int = 4) -> list[str]:
    """聚合全部顶层分类。

    SkillHub 列表接口不返回全量分类（仅当前页），且无独立分类端点（/api/categories 405）。
    做法：以兜底分类表 _BASE_CATEGORIES（已覆盖全部已知顶层类目）为保底，再轻量拉取
    若干页（按下载量排序）聚合 distinct 顶层 category 作为补充，避免遗漏新类目；
    结果缓存 1 天。联网失败则回退兜底表，保证 chips 始终可渲染、且首屏秒开。
    """
    cache_key = "categories"
    if use_cache:
        hit = _cache_get(cache_key, _CATEGORY_TTL)
        if hit is not None:
            return hit
    cats: set[str] = set(_BASE_CATEGORIES)
    try:
        for page in range(1, sample_pages + 1):
            params = {"sortBy": "downloads", "page": page, "pageSize": 100}
            data = _http_json(SKILLHUB_API, params, timeout=20)
            payload = data.get("data", {}) if isinstance(data, dict) else {}
            skills = payload.get("skills", []) if isinstance(payload, dict) else []
            if not skills:
                break
            for s in skills:
                c = s.get("category")
                if c:
                    cats.add(c)
    except Exception:
        pass  # 失败则用兜底表（已覆盖全部已知类目）
    result = sorted(cats)
    if use_cache:
        _cache_put(cache_key, result, _CATEGORY_TTL)
    return result


def warm_cache() -> None:
    """后台预热：拉默认市场首页 + 全部分类写入缓存，使商店打开即秒开。

    应在独立 daemon 线程中调用，不阻塞事件循环。与前端默认参数保持一致
    （q='' / category='' / sort='score' / page=1 / pageSize=24）以确保首屏命中缓存。
    """
    try:
        search_skills(q="", category="", page=1, pageSize=24, sort="score", use_cache=True)
    except Exception:
        pass
    try:
        get_categories(use_cache=True)
    except Exception:
        pass


def resolve_github_repo(upstream_url: str):
    """从 upstream_url 解析 (owner, repo)。

    - 直接 github.com/<owner>/<repo> → 直接取。
    - clawhub.ai/<owner>/<repo> → 拉取页面 HTML，提取内嵌的 github 仓库地址。
    - 其它 / 解析失败 → None。
    """
    if not upstream_url:
        return None
    m = _GITHUB_RE.search(upstream_url)
    if m:
        return (m.group(1), m.group(2))
    cm = _CLAWHUB_RE.search(upstream_url)
    if cm:
        page_url = f"https://clawhub.ai/{cm.group(1)}/{cm.group(2)}"
        try:
            req = Request(page_url, headers=_UA)
            with urlopen(req, timeout=25) as r:
                html = r.read().decode("utf-8", "ignore")
            gm = _GITHUB_RE.search(html)
            if gm:
                return (gm.group(1), gm.group(2))
        except Exception:
            return None
    return None


def _download_bytes(url: str, timeout: int = 60) -> bytes:
    req = Request(url, headers=_UA)
    with urlopen(req, timeout=timeout) as r:
        return r.read()


def download_and_install(upstream_url: str | None, slug: str, name: str | None = None,
                         version: str | None = None) -> dict:
    """安装技能：优先解析 GitHub/ClawHub 仓库；无 upstream_url 则回退 SkillHub 官方下载。

    兼容单技能仓库与含多技能的 monorepo（GitHub zip 内按 SKILL.md 定位子目录）；
    SkillHub 官方 zip 结构为平铺，直接落盘到 HERMES_HOME/skills/<slug>/。
    返回 {"ok": bool, ...}。
    """
    if upstream_url:
        repo = resolve_github_repo(upstream_url)
        if repo:
            return _install_from_github(repo, slug, name)
        # upstream_url 非空但解析失败 → 也允许回退到 SkillHub 下载
    return _install_from_skillhub(slug, name, version)


def _install_from_github(repo: tuple[str, str], slug: str, name: str | None = None) -> dict:
    owner, repo_name = repo
    skills_dir = _GET_HOME() / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    dest = skills_dir / (slug or repo_name)
    last_err = ""
    for branch in ("main", "master"):
        url = f"https://github.com/{owner}/{repo_name}/archive/refs/heads/{branch}.zip"
        try:
            raw = _download_bytes(url)
            if not raw or raw[:2] != b"PK":
                last_err = f"分支 {branch} 返回非 zip（可能不存在）"
                continue
            return _install_from_zip(raw, slug or repo_name, name, dest)
        except Exception as e:
            last_err = str(e)
    return {"ok": False, "error": f"GitHub 下载/解压失败：{last_err}"}


def _install_from_skillhub(slug: str, name: str | None = None,
                           version: str | None = None) -> dict:
    """从 SkillHub 官方 /api/v1/download 下载 zip 并安装（无需鉴权）。"""
    params = {"slug": slug}
    if version:
        params["version"] = version
    url = SKILLHUB_DOWNLOAD_API + ("&" if "?" in SKILLHUB_DOWNLOAD_API else "?") + urlencode(params)
    try:
        raw = _download_bytes(url, timeout=60)
        if not raw or raw[:2] != b"PK":
            return {"ok": False, "error": "SkillHub 下载返回非 zip 数据"}
    except Exception as e:
        return {"ok": False, "error": f"SkillHub 下载失败：{e}"}
    skills_dir = _GET_HOME() / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    dest = skills_dir / slug
    return _install_from_zip(raw, slug, name, dest, flatten=True)


def _install_from_zip(raw: bytes, slug: str, name: str | None = None,
                      dest: Path | None = None, flatten: bool = False) -> dict:
    """将 zip 原始字节安装到 dest/skills/<slug>/。

    flatten=True 表示 zip 内为平铺结构（SkillHub 官方包），直接解压到 dest；
    flatten=False 表示 zip 内为 GitHub archive（含顶层仓库目录），需先定位技能子目录。
    """
    skills_dir = _GET_HOME() / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    if dest is None:
        dest = skills_dir / slug
    tmp = skills_dir / f"._{slug}_dl"
    if tmp.exists():
        shutil.rmtree(tmp)
    try:
        zipfile.ZipFile(io.BytesIO(raw)).extractall(tmp)
        if flatten:
            chosen = tmp
            if not any(p.name == "SKILL.md" for p in chosen.iterdir() if p.is_file()):
                # 少数 zip 仍可能有一层顶层目录
                candidates = [p for p in chosen.iterdir() if p.is_dir() and (p / "SKILL.md").exists()]
                chosen = candidates[0] if candidates else chosen
        else:
            candidates = [p.parent for p in Path(tmp).rglob("SKILL.md") if p.parent.is_dir()]
            chosen = _select_skill_dir(candidates, slug)
            if not chosen:
                shutil.rmtree(tmp, ignore_errors=True)
                return {"ok": False, "error": "zip 中未找到 SKILL.md（可能非技能包）"}
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for item in chosen.iterdir():
            tgt = dest / item.name
            if item.is_dir():
                shutil.copytree(item, tgt)
            else:
                shutil.copy2(item, tgt)
        if not (dest / "SKILL.md").exists():
            shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "error": "安装目录缺少 SKILL.md"}
        shutil.rmtree(tmp, ignore_errors=True)
        return {"ok": True, "path": str(dest), "name": name or slug}
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return {"ok": False, "error": f"解压/安装失败：{e}"}


def _select_skill_dir(candidates: list[Path], slug: str) -> Path | None:
    """从候选技能目录里挑最匹配 slug 的一个。

    匹配优先级：① 目录名精确等于 slug；② 互相包含；③ 词元重叠度最高
    （去掉 agent/skill 等后缀噪声后比较，处理 monorepo 子目录名与 slug 不完全一致，
    如 slug=self-improving-agent 对应子目录 self-improvement）；④ 路径最浅兜底。
    """
    if not candidates:
        return None
    slug_l = slug.lower()
    for d in candidates:
        if d.name.lower() == slug_l:
            return d
    for d in candidates:
        n = d.name.lower()
        if slug_l in n or n in slug_l:
            return d
    _stop = {"agent", "skill", "pro", "ai", "tool", "plugin", "app", "bot"}
    st = {t for t in re.split(r"[-\s_]+", slug_l) if t and t not in _stop}
    best, best_score = None, -1
    for d in candidates:
        dt = {t for t in re.split(r"[-\s_]+", d.name.lower()) if t}
        score = len(st & dt)
        if score > best_score:
            best_score, best = score, d
    if best_score > 0:
        return best
    return min(candidates, key=lambda d: len(d.parts))
