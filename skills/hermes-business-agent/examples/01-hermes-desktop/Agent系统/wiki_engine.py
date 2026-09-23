"""wiki_engine.py — LLM Wiki 引擎（进程内，纯标准库 + 懒加载 AIAgent）

参照 Karpathy 的 LLM Wiki 范式（Hermes 亦以 bundled skill `research/llm-wiki` v2.1.0 内置同一范式）；本文件为从零自研实现，并非加载/复用该 bundled skill。
  - 三层目录：raw/（不可变源）· entities/concepts/comparisons/queries/（编译页）· root（summary）
  - 元文件：SCHEMA.md（分类法）· index.md（带摘要的导航骨架）· log.md（append-only 动作日志）
  - 索引文件：_backlinks.json（反向链接）· _absorb_log.json（已吸收 raw 记录，增量编译用）
  - [[wikilinks]] 互联 + 自动反向链接 + 自动 index 维护
  - Ingest（raw→LLM 编译）· Query（导航+综合+cite）· Lint（13 项健康）· Graph（图导出）

设计：
  - 不含任何 GUI / HTTP 依赖；AIAgent 调用全部函数内懒加载（符合打包 hidden-import 铁律）。
  - 落盘位置：HERMES_HOME/wiki（本引擎自行管理，**不读取**官方 `WIKI_PATH` 环境变量——
    官方默认 `~/wiki`，与本路径不同）。本引擎**不加载** Hermes 内置 `research/llm-wiki` skill：
    该 bundled skill 未随本机 hermes-agent 发行（本机 `.hermes_data/skills` 下无此 skill 文件，
    无论是否启用 bundled skills 均不可用）；example01 的 Wiki 完全由本文件自行读写。
    二者是同一 Karpathy 范式的**两套独立实现**，目录约定存在 intentional 差异
    （官方 `SKILL.md` 用 `WIKI_PATH`→`~/wiki` 且 raw 分 `articles/papers/...` 子目录；
    本引擎用 `HERMES_HOME/wiki`、raw 平铺；双方 raw 均带源 frontmatter
    （source_url/ingested/sha256），本引擎另在 `_absorb_log.json` 记 sha256）。
  - 所有 LLM 往返都需有效 API Key，缺失时抛清晰错误，UI 显式提示。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from types import SimpleNamespace

WIKI_TYPES = ["entity", "concept", "comparison", "query", "summary"]
TYPE_DIRS = {
    "entity": "entities",
    "concept": "concepts",
    "comparison": "comparisons",
    "query": "queries",
}
_WIKI_RESERVED = {"SCHEMA.md", "index.md", "log.md", "_backlinks.json", "_absorb_log.json"}

# ── 路径与结构 ────────────────────────────────────────────────────────────
def _home(home: Path | None = None) -> Path:
    if home is not None:
        return Path(home)
    from hermes_config import get_hermes_home
    return get_hermes_home()


def wiki_dir(home: Path | None = None) -> Path:
    return _home(home) / "wiki"


def ensure_structure(home: Path | None = None) -> dict:
    """幂等创建三层目录与元文件。已存在则跳过。"""
    d = wiki_dir(home)
    for sub in ("raw", "entities", "concepts", "comparisons", "queries"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    bl = d / "_backlinks.json"
    if not bl.exists():
        bl.write_text("{}", encoding="utf-8")
    al = d / "_absorb_log.json"
    if not al.exists():
        al.write_text("{}", encoding="utf-8")
    schema = d / "SCHEMA.md"
    if not schema.exists():
        schema.write_text(_DEFAULT_SCHEMA(), encoding="utf-8")
    index = d / "index.md"
    if not index.exists():
        index.write_text("# Wiki Index\n\n_（自动维护；首次摄入或保存页面后生成）_\n", encoding="utf-8")
    log = d / "log.md"
    if not log.exists():
        log.write_text("# Wiki Log\n\n", encoding="utf-8")
    return {"ok": True, "dir": str(d)}


def _DEFAULT_SCHEMA() -> str:
    return (
        "# Wiki SCHEMA\n\n"
        "本知识库的分类法与写作约定（参考 Hermes `llm-wiki` skill）。可手改。\n\n"
        "## 页面类型 (type)\n"
        "- `entity`：人 / 组织 / 产品 / 模型等具体对象 → `entities/`\n"
        "- `concept`：抽象概念 / 方法 → `concepts/`\n"
        "- `comparison`：对比分析 → `comparisons/`\n"
        "- `query`：归档的问答结果 → `queries/`\n"
        "- `summary`：综述 / 索引型（默认，落在根目录）\n\n"
        "## 写作规则\n"
        "- 每页 ≥2 个 `[[wikilinks]]` 出站链接（互联是 Wiki 的灵魂）。\n"
        "- frontmatter 必填：title / type / tags；选填：sources / confidence / contested / contradictions。\n"
        "- 源材料放 `raw/`，页面由 Ingest 编译产生，亦可手动新建。\n"
    )


# ── frontmatter 工具 ───────────────────────────────────────────────────────
def _parse_frontmatter(text: str):
    from hermes_config import _parse_frontmatter
    return _parse_frontmatter(text)


def _serialize_frontmatter(meta: dict) -> str:
    from hermes_config import _serialize_frontmatter
    return _serialize_frontmatter(meta)


def slugify(title: str, used: set[str] | None = None) -> str:
    s = re.sub(r"[\\/:*?\"<>|]", "", title or "").strip()
    s = re.sub(r"\s+", "-", s).strip("-.")
    s = s[:80] or f"page-{int(time.time())}"
    if used is None:
        return s
    base, i = s, 1
    while s in used:
        s = f"{base}-{i}"; i += 1
    return s


# ── 安全路径 ──────────────────────────────────────────────────────────────
def page_path(home: Path | None, name: str) -> Path:
    d = wiki_dir(home).resolve()
    p = (d / (name or "").replace("..", "")).resolve()
    if str(p) != str(d) and not str(p).startswith(str(d) + os.sep):
        raise ValueError("非法页面路径")
    if p.is_dir():
        raise ValueError("目标是目录")
    return p


# ── 单遍加载器（W1 / W2 / W3 的核心） ────────────────────────────────────────
def _resolve_slug_loaded(lower_index: dict, target: str) -> str | None:
    """用 {lower_slug: slug} 字典解析 wikilink 目标。

    以 O(1)~O(N) 内存查表替代 _resolve_slug 的 `d.rglob('*.md')` 全树磁盘遍历（W2）。
    语义与原 _resolve_slug 的「精确匹配 + 短名(叶子)匹配」完全一致。
    """
    t = (target or "").strip().lower()
    if t.endswith(".md"):
        t = t[:-3]
    if t in lower_index:                         # 精确匹配（含类型子目录）
        return lower_index[t]
    want = t.split("/")[-1]                      # 短名（叶子）匹配
    for s in lower_index.values():
        sl = s.lower()
        if sl == want or sl.endswith("/" + want):
            return s
    return None


def _load_all(home: Path | None = None) -> dict:
    """单遍加载全部页面：只遍历 + 解析一次整个知识库，返回 {slug: _Page}。

    _Page（types.SimpleNamespace）字段：
        slug / meta / body / lower(slug 小写) / mtime / size / outbound(已解析出链集合)
    顺带构建 lower_index = {slug.lower(): slug}，供 _resolve_slug_loaded 查表（W2）。

    收益（W1 / W3）：原本 list_pages()+get_page() 每页读两遍、save_page 每次触发 ~3 次
    全库读；引入本加载器后，单次操作只遍历解析一次，后续全部走内存 O(1) 访问。
    功能丝毫不减。
    """
    d = wiki_dir(home)
    loaded: dict[str, "SimpleNamespace"] = {}
    lower_index: dict[str, str] = {}
    if not d.exists():
        return loaded
    for f in sorted(d.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        rel = str(f.relative_to(d)).replace("\\", "/")
        if rel in _WIKI_RESERVED or rel.startswith("raw/"):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        meta, body = _parse_frontmatter(text)
        slug = rel[:-3]
        lower = slug.lower()
        loaded[slug] = SimpleNamespace(
            slug=slug, meta=meta, body=body, lower=lower,
            mtime=f.stat().st_mtime, size=f.stat().st_size, outbound=set())
        lower_index[lower] = slug
    # 一轮解析出链（内存 O(N) + 字典 O(1) 查表，替代逐页 get_page + rglob）
    for pg in loaded.values():
        pg.outbound = {r for t in parse_wikilinks(pg.body)
                       if (r := _resolve_slug_loaded(lower_index, t))}
    return loaded


def _pages_meta(loaded: dict, _bl: dict) -> list[dict]:
    """把 _load_all 结果转成 list_pages 原有形态的元信息列表（按 mtime 倒序）。"""
    out = []
    for pg in sorted(loaded.values(), key=lambda p: p.mtime, reverse=True):
        slug = pg.slug
        out.append({
            "slug": slug,
            "title": pg.meta.get("title") or slug,
            "type": pg.meta.get("type") or "summary",
            "category": pg.meta.get("category") or (pg.meta.get("type") or "通用"),
            "tags": pg.meta.get("tags") or [],
            "sources": pg.meta.get("sources") or [],
            "confidence": pg.meta.get("confidence") or "",
            "updated": pg.meta.get("updated", ""),
            "contested": pg.meta.get("contested", False),
            "contradictions": pg.meta.get("contradictions") or [],
            "size": pg.size,
            "backlinks": len(_bl.get(slug) or []),
        })
    return out


def _page_dict(loaded: dict, slug: str, _bl: dict) -> "dict | None":
    """把 _load_all 中某个 _Page 转成 get_page 原有形态的富字典（不重新读盘）。"""
    pg = loaded.get(slug)
    if pg is None:
        return None
    inbound = _bl.get(slug) or []
    return {
        "ok": True,
        "slug": pg.slug,
        "name": pg.slug + ".md",
        "title": pg.meta.get("title") or pg.slug,
        "type": pg.meta.get("type") or "summary",
        "category": pg.meta.get("category") or (pg.meta.get("type") or "通用"),
        "tags": pg.meta.get("tags") or [],
        "sources": pg.meta.get("sources") or [],
        "confidence": pg.meta.get("confidence") or "",
        "updated": pg.meta.get("updated", ""),
        "contested": pg.meta.get("contested", False),
        "contradictions": pg.meta.get("contradictions") or [],
        "body": pg.body,
        "outbound": sorted(pg.outbound),
        "inbound": sorted(inbound),
    }


def list_pages(home: Path | None = None, _loaded: dict | None = None) -> list[dict]:
    """列出全部页面（含 frontmatter 摘要 + 反向链接数）。兼容旧 flat 条目。

    W1 优化：若调用方已持有 _load_all(home) 结果，通过 _loaded 传入即可复用，
    避免在此再次全库遍历解析。
    """
    if _loaded is None:
        _loaded = _load_all(home)
    d = wiki_dir(home)
    bl = _read_json(d / "_backlinks.json")
    return _pages_meta(_loaded, bl)


def get_page(home: Path | None, slug: str, _loaded: dict | None = None,
             _bl: dict | None = None) -> dict | None:
    """读取单页（含出/入链）。W1/W3 优化：若调用方已持有 _load_all 结果与
    _backlinks.json，通过 _loaded / _bl 传入即可复用，避免再次读盘。
    """
    if _loaded is None:
        _loaded = _load_all(home)
    d = wiki_dir(home)
    if _bl is None:
        _bl = _read_json(d / "_backlinks.json")
    return _page_dict(_loaded, slug, _bl)


def save_page(home: Path | None, *, slug: str | None = None, title: str,
              type_: str = "summary", tags: list | None = None,
              sources: list | None = None, confidence: str = "",
              category: str = "", text: str = "",
              model_cfg: dict | None = None,
              contested: bool = False,
              contradictions: list | None = None,
              _loaded: dict | None = None) -> dict:
    """保存/新建页面。type 决定落盘目录；写入后重算反链 + 更新 index。

    W1 优化：调用方（如 ingest）可传入共享的 _loaded 模型，避免每页重读整库；
    内部在写入后会把新页并入 _loaded，供 recompute/update_index 复用（仅 1 次全库读）。
    """
    ensure_structure(home)
    d = wiki_dir(home)
    if _loaded is None:
        _loaded = _load_all(home)
    lower_index = {pg.lower: s for s, pg in _loaded.items()}
    tags = [t.strip() for t in (tags or []) if t.strip()]
    sources = [s.strip() for s in (sources or []) if s.strip()]
    sub = TYPE_DIRS.get(type_, "")
    used = set(_loaded.keys())
    if not slug:
        base = slugify(title, used)
        if sub:
            base = f"{sub}/{base}"
    else:
        base = slug.replace("..", "").strip("/")
        if sub and "/" not in base:
            base = f"{sub}/{base}"
    if not base.lower().endswith(".md"):
        base += ".md"
    p = page_path(home, base)
    meta = {
        "title": title or base[:-3],
        "created": _now_date(),
        "updated": _now_date(),
        "type": type_,
        "tags": tags,
    }
    if category:
        meta["category"] = category
    if sources:
        meta["sources"] = sources
    if confidence:
        meta["confidence"] = confidence
    if contested:
        meta["contested"] = True
    if contradictions:
        meta["contradictions"] = contradictions
    body = (text or "").lstrip("\n")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_serialize_frontmatter(meta) + "\n\n" + body + "\n", encoding="utf-8")
    # W1：把刚写入的页并入已加载模型，避免为 recompute/update_index 再读整库
    text_new = p.read_text(encoding="utf-8")
    meta_new, body_new = _parse_frontmatter(text_new)
    slug_new = base[:-3]
    new_pg = SimpleNamespace(slug=slug_new, meta=meta_new, body=body_new,
                             lower=slug_new.lower(), mtime=p.stat().st_mtime,
                             size=p.stat().st_size, outbound=set())
    new_pg.outbound = {r for t in parse_wikilinks(body_new)
                       if (r := _resolve_slug_loaded(lower_index, t))}
    _loaded[slug_new] = new_pg
    lower_index[slug_new.lower()] = slug_new
    recompute_backlinks(home, _loaded)
    update_index(home, _loaded)
    # B3：写时断链检测——保存后立即报告指向不存在页面的 [[wikilinks]]
    broken = _broken_of(home, slug_new, _loaded) if slug_new else []
    return {"ok": True, "slug": slug_new, "name": base, "broken": broken}


def delete_page(home: Path | None, slug: str, _loaded: dict | None = None) -> dict:
    p = page_path(home, slug + ".md")
    if not p.exists() or not p.is_file():
        return {"ok": False, "error": "页面不存在"}
    p.unlink()
    # W1：删除后一次性重载（仅 1 次），供 recompute/update_index 复用
    if _loaded is None:
        _loaded = _load_all(home)
    _loaded.pop(slug, None)
    recompute_backlinks(home, _loaded)
    update_index(home, _loaded)
    return {"ok": True}


# ── wikilinks / 反向链接 ────────────────────────────────────────────────────
_WLINK = re.compile(r"\[\[([^\]|#]+)")


def parse_wikilinks(body: str) -> set[str]:
    return {m.group(1).strip().lower() for m in _WLINK.finditer(body or "")}


def _resolve_slug(d: Path, target: str, _lower_index: dict | None = None) -> str | None:
    """把 wikilink 目标（可能带/或不带目录、带 .md）解析为实际存在的 slug。

    W2 优化：若调用方已构建 {lower_slug: slug} 字典，通过 _lower_index 传入即可
    走字典查表，避免 `d.rglob('*.md')` 全树磁盘遍历（热路径如 recompute 不再触发）。
    """
    if _lower_index is not None:
        return _resolve_slug_loaded(_lower_index, target)
    t = target.strip().lower()
    if t.endswith(".md"):
        t = t[:-3]
    candidates = [t, t + ".md"]
    # 同时尝试各 type 子目录与根
    for c in candidates:
        p = (d / c)
        if p.is_file():
            return str(p.relative_to(d)).replace("\\", "/")[:-3]
    # 大小写/扩展名不敏感兜底
    want = t.split("/")[-1]
    for f in d.rglob("*.md"):
        rel = str(f.relative_to(d)).replace("\\", "/")[:-3].lower()
        if rel == t or rel.endswith("/" + want) or rel == want:
            return rel
    return None


def _compute_backlinks(home: Path | None = None, _loaded: dict | None = None) -> dict:
    """内存计算反链映射（slug -> [inbound slugs]），**不写盘**。供 lint 只读核对。

    W1/W3 优化：若调用方已持有 _load_all 结果，通过 _loaded 传入即可复用，
    不再逐页 read_text + _resolve_slug(rglob)。
    """
    if _loaded is None:
        _loaded = _load_all(home)
    slugs = {pg.lower for pg in _loaded.values()}
    outbound_map: dict[str, set[str]] = {slug: set() for slug in _loaded}
    for slug, pg in _loaded.items():
        for tgt in pg.outbound:
            if tgt.lower() in slugs and tgt.lower() != slug.lower():
                outbound_map[slug].add(tgt)
    inv: dict[str, list[str]] = {}
    for src, tgts in outbound_map.items():
        for t in tgts:
            inv.setdefault(t, [])
            if src not in inv[t]:
                inv[t].append(src)
    return inv


def recompute_backlinks(home: Path | None = None, _loaded: dict | None = None) -> dict:
    """扫描全部页面正文，重算并写盘 _backlinks.json（slug -> [inbound slugs]）。"""
    inv = _compute_backlinks(home, _loaded)
    d = wiki_dir(home)
    (d / "_backlinks.json").write_text(
        json.dumps({k: sorted(v) for k, v in inv.items()}, ensure_ascii=False, indent=0),
        encoding="utf-8")
    return {"ok": True, "links": sum(len(v) for v in inv.values())}


def _backlinks_consistent(computed: dict, ondisk: dict) -> bool:
    """比对内存重算结果与磁盘 _backlinks.json 是否一致（忽略列表顺序）。"""
    for k, v in computed.items():
        if sorted(ondisk.get(k, [])) != sorted(v):
            return False
    for k in ondisk:
        if k not in computed:
            return False
    return True


# ── index.md 自动维护 ───────────────────────────────────────────────────────
def _summarize(body: str, n: int = 90) -> str:
    body = re.sub(r"^---.*?---\s*", "", body, flags=re.S)
    body = re.sub(r"\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]", r"\1", body)
    body = re.sub(r"[#*`>_~>-]", " ", body)
    line = re.sub(r"\s+", " ", body).strip()
    if len(line) <= n:
        return line
    return line[:n].rstrip() + "…"


def update_index(home: Path | None = None, _loaded: dict | None = None) -> dict:
    if _loaded is None:
        _loaded = _load_all(home)
    d = wiki_dir(home)
    by_type: dict[str, list] = {t: [] for t in WIKI_TYPES}
    for pg in _loaded.values():
        by_type.setdefault(pg.meta.get("type") or "summary", []).append(pg)
    lines = ["# Wiki Index", "",
             f"_自动维护 · 共 {len(_loaded)} 页 · 更新于 {_now_date()}_", ""]
    labels = {"entity": "实体 Entities", "concept": "概念 Concepts",
              "comparison": "对比 Comparisons", "query": "问答 Queries",
              "summary": "综述 Summaries"}
    for t in WIKI_TYPES:
        items = by_type.get(t) or []
        if not items:
            continue
        lines.append(f"## {labels.get(t, t)}")
        for pg in sorted(items, key=lambda x: x.meta.get("title") or x.slug):
            # W3：直接用已加载的正文生成摘要，不再为每页重新读盘
            lines.append(f"- [[{pg.slug}]] — {_summarize(pg.body, 70) or (pg.meta.get('title') or pg.slug)}")
        lines.append("")
    (d / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "count": len(_loaded)}


def append_log(home: Path | None, action: str) -> None:
    d = wiki_dir(home)
    log = d / "log.md"
    stamp = _now_date()
    with log.open("a", encoding="utf-8") as f:
        f.write(f"- `{stamp}` {action}\n")


# ── raw 源材料 ──────────────────────────────────────────────────────────────
def add_raw(home: Path | None, name: str, text: str, source_url: str = "") -> dict:
    ensure_structure(home)
    d = wiki_dir(home)
    safe = re.sub(r"[\\/:*?\"<>|]", "-", name or "").strip().strip(".")
    if not safe.lower().endswith(".md"):
        safe += ".md"
    sha = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    front = (
        "---\n"
        f"source_url: \"{source_url}\"\n"
        f"ingested: {_now_date()}\n"
        f"sha256: {sha}\n"
        "---\n\n"
    )
    p = d / "raw" / safe
    p.write_text(front + (text or ""), encoding="utf-8")
    al = _read_json(d / "_absorb_log.json")
    al.pop(safe, None)  # 新版本未吸收
    (d / "_absorb_log.json").write_text(json.dumps(al, ensure_ascii=False, indent=0), encoding="utf-8")
    append_log(home, f"add_raw `{safe}` (sha256:{sha[:8]})" + (f" src:{source_url}" if source_url else ""))
    return {"ok": True, "name": safe, "sha256": sha, "size": len(text or "")}


def list_raw(home: Path | None = None) -> list[dict]:
    d = wiki_dir(home)
    raw = d / "raw"
    al = _read_json(d / "_absorb_log.json")
    out = []
    if raw.exists():
        for f in sorted(raw.glob("*.md")):
            out.append({
                "name": f.name,
                "size": f.stat().st_size,
                "absorbed": bool(al.get(f.name)),
                "pages": al.get(f.name) or [],
            })
    return out


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {}


def _now_date() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def _strip_frontmatter(text: str) -> str:
    """去掉 Markdown 文件开头的 YAML frontmatter（--- ... ---），用于把 raw 源喂给 LLM 前清洗。"""
    if text.startswith("---"):
        m = re.match(r"^---\s*\n.*?\n---\s*(\n|$)", text, re.S)
        if m:
            return text[m.end():]
    return text


# ── AIAgent 单次调用（懒加载） ─────────────────────────────────────────────
def _ask_agent(prompt: str, system: str | None = None, model_cfg: dict | None = None) -> str:
    """进程内单次问答。需有效 API Key。无 hermes-agent / 无 key 时抛清晰错误。"""
    if model_cfg is None:
        from hermes_config import get_active_model_cfg
        model_cfg = get_active_model_cfg()
    if not model_cfg or not model_cfg.get("api_key"):
        raise RuntimeError("未配置 API Key：请在「模型」设置中配置后重试（构建/查询是有成本的 LLM 往返）")
    from agent_runtime import build_agent
    agent = build_agent(model_cfg, web_search=False)
    result = agent.run_conversation(
        user_message=prompt,
        system_message=system or None,
    )
    if isinstance(result, dict):
        return result.get("final_response") or ""
    return str(result or "")


_WIKI_SYSTEM = (
    "你是 Karpathy 式 LLM Wiki 的编译引擎。把原始资料编译成互联的 Markdown 知识页。"
    "每页必须含 frontmatter 与正文，正文至少 2 个 [[wikilinks]] 指向其它页（用 slug，"
    "如 concepts/attention）。只输出我要求的 JSON，不要多余文字。"
)


# ── P2 Ingest（构建） ───────────────────────────────────────────────────────
def ingest(home: Path | None = None, raw_names: list[str] | None = None,
           model_cfg: dict | None = None) -> dict:
    """对指定/全部未吸收的 raw 跑编译流水线。返回报告。"""
    ensure_structure(home)
    d = wiki_dir(home)
    al = _read_json(d / "_absorb_log.json")
    raws = list_raw(home)
    targets = [r for r in raws if (raw_names is None) or (r["name"] in raw_names)]
    if raw_names is None:
        targets = [r for r in raws if not r["absorbed"]]
    if not targets:
        return {"ok": True, "created": 0, "updated": 0, "pages": [], "note": "无待吸收源材料"}

    created = updated = 0
    made_pages: list[str] = []
    loaded = _load_all(home)           # W1：全程共享一个已加载模型
    used = set(loaded.keys())
    for r in targets:
        rp = d / "raw" / r["name"]
        src = _strip_frontmatter(rp.read_text(encoding="utf-8"))
        try:
            resp = _ask_agent(_INGEST_PROMPT(src, used), system=_WIKI_SYSTEM, model_cfg=model_cfg)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"编译 {r['name']} 失败：{e}", "pages": made_pages}
        pages = _extract_pages(resp)
        for pg in pages:
            try:
                res = save_page(home, slug=pg.get("slug"), title=pg["title"],
                                type_=pg.get("type", "concept"),
                                tags=pg.get("tags", []), sources=[f"raw/{r['name']}"],
                                confidence=pg.get("confidence", ""), text=pg["body"],
                                model_cfg=model_cfg, _loaded=loaded)
                if res["ok"]:
                    made_pages.append(res["slug"])
                    if pg.get("_existed"):
                        updated += 1
                    else:
                        created += 1
                    used.add(res["slug"])
            except Exception:
                continue
        al[r["name"]] = made_pages
        (d / "_absorb_log.json").write_text(
            json.dumps(al, ensure_ascii=False, indent=0), encoding="utf-8")
        append_log(home, f"ingest `{r['name']}` → {len(pages)} 页")
    recompute_backlinks(home, loaded)
    update_index(home, loaded)
    return {"ok": True, "created": created, "updated": updated,
            "pages": made_pages, "note": f"已吸收 {len(targets)} 个源"}


def _INGEST_PROMPT(src: str, used: set[str]) -> str:
    return (
        "以下是一段源材料。请编译成知识页（拆成若干关联概念/实体页，避免堆砌）。\n"
        "已存在页面 slug（勿重复，除非要更新）：\n"
        + (", ".join(sorted(used)) if used else "（无）") + "\n\n"
        "源材料：\n```\n" + src[:12000] + "\n```\n\n"
        "输出 JSON 数组，每项为：\n"
        '{"slug":"concepts/xxx","title":"...","type":"entity|concept|comparison",'
        '"tags":["..."],"confidence":"high|medium|low","body":"# 标题\\n正文含 [[其它slug]]"}'
        "\n只输出 JSON 数组。"
    )


def _extract_pages(resp: str) -> list[dict]:
    m = re.search(r"\[.*\]", resp, flags=re.S)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return []
    out = []
    for it in arr if isinstance(arr, list) else []:
        if not isinstance(it, dict) or not it.get("title") or not it.get("body"):
            continue
        out.append({
            "slug": (it.get("slug") or "").strip("/") or None,
            "title": it["title"],
            "type": it.get("type", "concept"),
            "tags": it.get("tags", []) or [],
            "confidence": it.get("confidence", ""),
            "body": it["body"],
        })
    return out


# ── P3 Query（查询） ────────────────────────────────────────────────────────
def query(home: Path | None = None, question: str = "", model_cfg: dict | None = None,
          _loaded: dict | None = None) -> dict:
    d = wiki_dir(home)
    if not d.exists():
        return {"ok": False, "error": "知识库为空，请先摄入资料"}
    if _loaded is None:
        _loaded = _load_all(home)
    bl = _read_json(d / "_backlinks.json")
    pages = _pages_meta(_loaded, bl)
    if not pages:
        return {"ok": False, "error": "知识库为空，请先摄入资料"}
    index_text = (d / "index.md").read_text(encoding="utf-8")
    # 简易相关页选择：问题词命中 title/tag/slug
    qwords = re.findall(r"[\w\u4e00-\u9fff]{2,}", question or "")
    scored = []
    for p in pages:
        blob = (p["title"] + " " + " ".join(p["tags"]) + " " + p["slug"]).lower()
        score = sum(1 for w in qwords if w.lower() in blob)
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    relevant = [p["slug"] for _, p in scored[:8]] or [p["slug"] for p in pages[:5]]
    ctx = ""
    for slug in relevant:
        pg = _loaded.get(slug)          # W3：直接用已加载正文，不再 get_page 重读
        if pg:
            ctx += f"\n## {pg.meta.get('title') or slug} ({slug})\n{pg.body[:1500]}\n"
    prompt = (
        f"问题：{question}\n\n以下是知识库相关页面内容：\n{ctx}\n\n"
        "请基于上述内容回答（若知识库不足请说明）。用 [[slug]] 形式引用你参考的页面，"
        "例如 [[concepts/attention]]。最后用一行 `CITED: slug1, slug2` 列出引用页。"
    )
    try:
        answer = _ask_agent(prompt, system="你是知识库问答助手，严格基于给定内容作答并标注引用。",
                            model_cfg=model_cfg)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"查询失败：{e}"}
    cited = []
    m = re.search(r"CITED:\s*(.+)", answer)
    if m:
        cited = [s.strip().lower() for s in m.group(1).split(",") if s.strip()]
        answer = answer[:m.start()].strip()
    append_log(home, f"query \"{question[:40]}\" → {len(cited)} cited")
    return {"ok": True, "answer": answer, "cited": cited, "retrieved": relevant}


# ── P4 Lint（13 项健康） ────────────────────────────────────────────────────
def lint(home: Path | None = None, _loaded: dict | None = None) -> dict:
    d = wiki_dir(home)
    issues: list[dict] = []
    if not d.exists():
        return {"ok": True, "checks": 13, "issues": [{"check": "structure", "level": "error",
                "msg": "wiki 目录不存在"}], "counts": {}}
    if _loaded is None:
        _loaded = _load_all(home)
    bl = _read_json(d / "_backlinks.json")
    pages = _pages_meta(_loaded, bl)
    slugs = {p["slug"].lower() for p in pages}
    al = _read_json(d / "_absorb_log.json")
    index_text = (d / "index.md").read_text(encoding="utf-8") if (d / "index.md").exists() else ""

    # 1 孤儿页（零入站链接，且非 index 唯一页）
    for p in pages:
        if not (bl.get(p["slug"]) or []):
            issues.append({"check": "orphan", "level": "warn",
                           "msg": f"孤儿页（无入站链接）：[[{p['slug']}]]"})
    # 2 断链（W3：直接用已加载模型的出链，不再 get_page 重读）
    for p in pages:
        pg = _loaded.get(p["slug"])
        if not pg:
            continue
        for tgt in pg.outbound:
            if tgt.lower() not in slugs:
                issues.append({"check": "broken", "level": "error",
                               "msg": f"[[{p['slug']}]] → 断链 [[{tgt}]]"})
    # 3 索引完整性
    for p in pages:
        if f"[[{p['slug']}]]" not in index_text:
            issues.append({"check": "index", "level": "warn",
                           "msg": f"页面未在 index.md 出现：[[{p['slug']}]]"})
    # 4 frontmatter 校验
    for p in pages:
        if p["type"] not in WIKI_TYPES:
            issues.append({"check": "frontmatter", "level": "warn",
                           "msg": f"type 非法：{p['slug']} = {p['type']}"})
        if not p["tags"]:
            issues.append({"check": "frontmatter", "level": "info",
                           "msg": f"缺标签：[[{p['slug']}]]"})
    # 5 陈旧内容（>90 天）
    now = time.time()
    for p in pages:
        if p["updated"]:
            try:
                ts = time.mktime(time.strptime(p["updated"].split(" ")[0], "%Y-%m-%d"))
                if (now - ts) > 90 * 86400:
                    issues.append({"check": "stale", "level": "info",
                                   "msg": f"内容陈旧(>90天)：[[{p['slug']}]] ({p['updated']})"})
            except Exception:
                pass
    # 6 矛盾标记（W3）
    for p in pages:
        pg = _loaded.get(p["slug"])
        if pg and (pg.meta.get("contested") or pg.meta.get("contradictions")):
            issues.append({"check": "contradiction", "level": "warn",
                           "msg": f"标记矛盾：[[{p['slug']}]]"})
    # 7 质量信号（正文过短）（W3）
    for p in pages:
        pg = _loaded.get(p["slug"])
        if pg and len(pg.body.split()) < 30:
            issues.append({"check": "quality", "level": "info",
                           "msg": f"正文过短(<30词)：[[{p['slug']}]]"})
    # 8 源漂移（有 sources 但 raw 缺失）（W3）
    for p in pages:
        pg = _loaded.get(p["slug"])
        if not pg:
            continue
        for s in (pg.meta.get("sources") or []):
            rawname = s.replace("raw/", "")
            if not (d / "raw" / rawname).exists():
                issues.append({"check": "source_drift", "level": "warn",
                               "msg": f"源丢失：[[{p['slug']}]] → raw/{rawname}"})
    # 9 页大小（>2000 词）（W3）
    for p in pages:
        pg = _loaded.get(p["slug"])
        if pg and len(pg.body.split()) > 2000:
            issues.append({"check": "size", "level": "info",
                           "msg": f"页过大(>2000词)：[[{p['slug']}]]"})
    # 10 标签审计（已在 4 覆盖空标签；此处审计未归类 type=summary 的堆积）
    summary_pile = [p for p in pages if p["type"] == "summary"]
    if len(summary_pile) > 15:
        issues.append({"check": "tag_audit", "level": "info",
                       "msg": f"summary 类堆积过多({len(summary_pile)})，建议归类到 concepts/entities"})
    # 11 日志轮转（>500 行）
    log = d / "log.md"
    if log.exists() and len(log.read_text(encoding="utf-8").splitlines()) > 500:
        issues.append({"check": "log_rotation", "level": "info", "msg": "log.md 超过 500 行，建议归档"})
    # 12 schema 存在
    if not (d / "SCHEMA.md").exists():
        issues.append({"check": "schema", "level": "warn", "msg": "缺少 SCHEMA.md"})
    # 13 反链索引一致性（只读：内存重算与磁盘比对，不回写 _backlinks.json）
    computed = _compute_backlinks(home, _loaded)
    ondisk = _read_json(d / "_backlinks.json")
    if not _backlinks_consistent(computed, ondisk):
        issues.append({"check": "backlinks", "level": "warn",
                       "msg": "_backlinks.json 与正文不一致，建议运行修复/重算"})

    counts = {"error": 0, "warn": 0, "info": 0}
    for it in issues:
        counts[it["level"]] = counts.get(it["level"], 0) + 1
    return {"ok": True, "checks": 13, "issues": issues, "counts": counts,
            "total_pages": len(pages)}


# ── Graph（图视图） ─────────────────────────────────────────────────────────
def graph(home: Path | None = None, _loaded: dict | None = None) -> dict:
    if _loaded is None:
        _loaded = _load_all(home)
    bl = _read_json(wiki_dir(home) / "_backlinks.json")
    pages = _pages_meta(_loaded, bl)
    nodes = [{"id": p["slug"], "title": p["title"], "type": p["type"],
              "backlinks": p["backlinks"]} for p in pages]
    edges = []
    seen = set()
    for p in pages:
        pg = _loaded.get(p["slug"])
        if not pg:
            continue
        for t in pg.outbound:          # W3：直接用已加载出链
            key = (p["slug"], t)
            if key in seen:
                continue
            seen.add(key)
            edges.append({"source": p["slug"], "target": t})
    return {"ok": True, "nodes": nodes, "edges": edges}


# ── B8 改名联动（rename cascade） ───────────────────────────────────────────
def _replace_wikilink(body: str, old: str, new: str):
    """把正文里所有 [[old]] / [[old|别名]] / [[old#锚]] 的链接目标替换为 new。

    链接在正文里既可能以「全称 slug」（如 concepts/page_b）也可能以「短名」
    （如 page_b，去掉类型子目录后的叶子名）书写——两种写法都要替换，
    否则改名会留下指向已删除页面的断链。
    """
    old_l = old.lower()
    new_l = new.lower()
    old_leaf = old_l.rsplit("/", 1)[-1]
    new_leaf = new_l.rsplit("/", 1)[-1]
    # group2 必须贪婪吞掉整个链接目标（遇 |/#/] 才停），否则惰性 +? 只会捕获首字符
    pat = re.compile(r"(\[\[)([^\]|#]+)([^\]]*)(\]\])")
    count = 0

    def repl(mm: re.Match) -> str:
        nonlocal count
        target = mm.group(2).strip().lower()
        if target == old_l:
            count += 1
            return mm.group(1) + new + mm.group(3) + mm.group(4)
        if target == old_leaf:
            count += 1
            return mm.group(1) + new_leaf + mm.group(3) + mm.group(4)
        return mm.group(0)

    return pat.sub(repl, body), count


def rename_page(home: Path | None, old_slug: str, new_slug: str,
               _loaded: dict | None = None) -> dict:
    """改名一页：移动文件 + 全库更新指向它的 [[wikilinks]] + 重算反链 + 更新索引。"""
    old_slug = (old_slug or "").strip().lower().replace("..", "").strip("/")
    new_slug = (new_slug or "").strip().lower().replace("..", "").strip("/")
    if not old_slug or not new_slug:
        return {"ok": False, "error": "slug 不能为空"}
    if old_slug == new_slug:
        return {"ok": False, "error": "新旧 slug 相同"}
    # 用户若只填短名（无类型子目录），则沿用旧页面的子目录，避免链接错落目录
    if "/" not in new_slug and "/" in old_slug:
        new_slug = old_slug.rsplit("/", 1)[0] + "/" + new_slug
    op = page_path(home, old_slug + ".md")
    if not op.exists() or not op.is_file():
        return {"ok": False, "error": "源页面不存在"}
    np = page_path(home, new_slug + ".md")
    if np.exists():
        return {"ok": False, "error": "目标 slug 已存在"}
    np.parent.mkdir(parents=True, exist_ok=True)
    op.rename(np)
    # W1：改名 + 改内容后一次性重载（仅 1 次），供循环改写与 recompute/update_index 复用
    if _loaded is None:
        _loaded = _load_all(home)
    lower_index = {pg.lower: s for s, pg in _loaded.items()}
    updated: list[dict] = []
    for slug, pg in _loaded.items():
        new_body, n = _replace_wikilink(pg.body, old_slug, new_slug)
        if n:
            page_path(home, slug + ".md").write_text(new_body, encoding="utf-8")
            pg.body = new_body
            pg.outbound = {r for t in parse_wikilinks(new_body)
                           if (r := _resolve_slug_loaded(lower_index, t))}
            updated.append({"slug": slug, "count": n})
    recompute_backlinks(home, _loaded)
    update_index(home, _loaded)
    append_log(home, f"rename [[{old_slug}]] → [[{new_slug}]]（更新 {len(updated)} 页引用）")
    return {"ok": True, "old": old_slug, "new": new_slug, "updated": updated}


# ── C2 全文搜索 ────────────────────────────────────────────────────────────
def _snippet(body: str, qwords: list[str], n: int = 120) -> str:
    low = body.lower()
    pos = -1
    for w in qwords:
        i = low.find(w)
        if i >= 0 and (pos < 0 or i < pos):
            pos = i
    if pos < 0:
        return body[:n]
    start = max(0, pos - 40)
    end = min(len(body), pos + n)
    return ("…" if start > 0 else "") + body[start:end] + ("…" if end < len(body) else "")


def search(home: Path | None, q: str, limit: int = 30, _loaded: dict | None = None) -> list[dict]:
    """跨页面（标题/标签/slug/正文）与 raw 源做全文检索，返回带摘要的结果。"""
    d = wiki_dir(home)
    if not d.exists() or not q or not q.strip():
        return []
    qwords = re.findall(r"[\w\u4e00-\u9fff]+", q.lower())
    if not qwords:
        return []
    if _loaded is None:
        _loaded = _load_all(home)
    bl = _read_json(d / "_backlinks.json")
    pages = _pages_meta(_loaded, bl)
    results: list[dict] = []
    for p in pages:
        pg = _loaded.get(p["slug"])          # W3：直接用已加载正文，不再 get_page 重读
        body = pg.body if pg else ""
        hay = (p["title"] + " " + " ".join(p["tags"]) + " " + p["slug"] + " " + body).lower()
        score = sum(hay.count(w) for w in qwords)
        if score:
            results.append({"kind": "page", "slug": p["slug"], "title": p["title"],
                            "type": p["type"], "score": score,
                            "snippet": _snippet(body, qwords)})
    for r in list_raw(home):
        rp = d / "raw" / r["name"]
        try:
            txt = rp.read_text(encoding="utf-8")
        except Exception:
            continue
        hay = (r["name"] + " " + txt).lower()
        score = sum(hay.count(w) for w in qwords)
        if score:
            results.append({"kind": "raw", "slug": None, "title": r["name"],
                            "type": "raw", "score": score,
                            "snippet": _snippet(txt, qwords)})
    results.sort(key=lambda x: -x["score"])
    return results[:limit]


# ── B3 写时断链 + E2 一键修复 ───────────────────────────────────────────────
def _broken_of(home: Path | None, slug: str, _loaded: dict | None = None) -> list[str]:
    if _loaded is None:
        _loaded = _load_all(home)
    pg = _loaded.get(slug)
    if pg is None:
        return []
    slugs = {pg.lower for pg in _loaded.values()}
    # 注意：outbound 只含已解析链接，断链已被过滤；须直接从正文 wikilinks 计算
    return sorted(t for t in parse_wikilinks(pg.body) if t.lower() not in slugs)


def fix_broken_links(home: Path | None = None, _loaded: dict | None = None) -> dict:
    """E2：为全部断链目标自动生成占位页，使链接可解析（一键修复）。"""
    d = wiki_dir(home)
    if not d.exists():
        return {"ok": True, "created": []}
    if _loaded is None:
        _loaded = _load_all(home)
    created: list[str] = []
    slugs = {pg.lower for pg in _loaded.values()}
    for slug, pg in list(_loaded.items()):
        for tgt in _broken_of(home, slug, _loaded):
            if tgt.lower() in slugs:
                continue
            title = tgt.split("/")[-1].replace("-", " ").title()
            res = save_page(home, slug=tgt, title=title, type_="summary",
                            text=f"# {title}\n\n_（由「修复断链」自动生成的占位页，待补充内容）_\n",
                            model_cfg=None)
            if res.get("ok"):
                created.append(tgt)
                slugs.add(tgt.lower())
    # 生成占位页后一次性重载（仅 1 次），供 recompute/update_index 复用
    loaded = _load_all(home)
    recompute_backlinks(home, loaded)
    update_index(home, loaded)
    append_log(home, f"fix_broken_links 生成 {len(created)} 个占位页")
    return {"ok": True, "created": created}


# ── G2/G3 导出 / 导入（无损 JSON 包） ───────────────────────────────────────
def export_wiki(home: Path | None = None, _loaded: dict | None = None) -> dict:
    if _loaded is None:
        _loaded = _load_all(home)
    bl = _read_json(wiki_dir(home) / "_backlinks.json")
    pages = _pages_meta(_loaded, bl)
    out_pages = []
    for p in pages:
        pg = _loaded.get(p["slug"])          # W3：直接用已加载正文，不再 get_page 重读
        if pg:
            out_pages.append({"slug": p["slug"], "title": pg.meta.get("title") or p["slug"],
                              "type": pg.meta.get("type") or "summary",
                              "tags": pg.meta.get("tags") or [],
                              "sources": pg.meta.get("sources") or [],
                              "confidence": pg.meta.get("confidence") or "",
                              "contested": pg.meta.get("contested", False),
                              "contradictions": pg.meta.get("contradictions") or [],
                              "body": pg.body})
    raws = []
    for r in list_raw(home):
        rp = wiki_dir(home) / "raw" / r["name"]
        try:
            raws.append({"name": r["name"], "text": rp.read_text(encoding="utf-8")})
        except Exception:
            continue
    schema = ""
    sp = wiki_dir(home) / "SCHEMA.md"
    if sp.exists():
        schema = sp.read_text(encoding="utf-8")
    return {"ok": True, "pages": out_pages, "raw": raws, "schema": schema,
            "exported_at": _now_date()}


def import_wiki(home: Path | None, data: dict, _loaded: dict | None = None) -> dict:
    ensure_structure(home)
    if _loaded is None:
        _loaded = _load_all(home)
    created = updated = 0
    for pg in (data or {}).get("pages", []):
        slug = (pg.get("slug") or "").strip()
        if not slug:
            continue
        existing = get_page(home, slug, _loaded=_loaded)
        res = save_page(home, slug=slug, title=pg.get("title") or slug,
                        type_=pg.get("type", "summary"), tags=pg.get("tags", []),
                        sources=pg.get("sources", []), confidence=pg.get("confidence", ""),
                        text=pg.get("body", ""), model_cfg=None,
                        contested=pg.get("contested", False),
                        contradictions=pg.get("contradictions") or [],
                        _loaded=_loaded)
        if res.get("ok"):
            if existing:
                updated += 1
            else:
                created += 1
    for r in (data or {}).get("raw", []):
        add_raw(home, r.get("name", "source.md"), _strip_frontmatter(r.get("text", "")))
    recompute_backlinks(home, _loaded)
    update_index(home, _loaded)
    return {"ok": True, "created": created, "updated": updated}


# ── SCHEMA 生成 ─────────────────────────────────────────────────────────────
def generate_schema(home: Path | None = None, domain: str = "", model_cfg: dict | None = None) -> dict:
    ensure_structure(home)
    prompt = (
        f"为{domain or '通用'}领域的 LLM Wiki 生成 SCHEMA.md：定义 3-6 个核心概念类型、"
        "写作约定、必填 frontmatter 字段。用 Markdown 输出，控制在 400 字内。"
    )
    try:
        txt = _ask_agent(prompt, system="你是知识库架构师。", model_cfg=model_cfg)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"生成失败：{e}"}
    (wiki_dir(home) / "SCHEMA.md").write_text(txt.strip() + "\n", encoding="utf-8")
    append_log(home, "generate_schema")
    return {"ok": True, "schema": txt}
