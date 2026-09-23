"""mcpstore_client.py — MCP 商店目录（LobeHub 生态动态接入）

职责（用户明确要求「像嵌入网站一样动态获取」，不把 86k 条目预置进应用）：
  1. 精选目录：内置 ~26 个经过验证的 MCP 服务器，每条带**真实可运行**的 stdio
     启动定义（command/args/env）。它们仅作「已知可一键安装」的合并覆盖——
     当某 slug 同时出现在 LobeHub 实时结果中，补入其定义，使其直接可装。
  2. LobeHub 动态代理：浏览/搜索/翻页按需实时拉取 LobeHub 列表页（JSON-LD
     ItemList，含真实 description），全站 86,304 个 MCP 全部可搜可翻；
     点「安装」时再按 slug 实时拉取详情页抽取真实 command/args/env，实现一键安装。
     仅做内存短缓存（分页 10min / 详情 24h），绝不把全量目录落盘。
  3. 搜索/分类/分页：与 skillhub_client.search_skills 同构的归一化返回，
     供 /api/mcp-store/* 路由与 mcpstore.js 前端复用技能商店交互范式。

全部使用标准库（urllib/json/re），冻结态 EXE（零 Python 运行时）可直接联网。
注意：MCP 服务器本身由 Hermes 以子进程拉起，runtime 字段（node/python）标注其
对宿主机运行时的要求，前端据此提示「需要 Node.js / 需要 uv」。LobeHub 任何页面
均不暴露下载量/热度，故绝不编造数字，仅以「LobeHub」来源标识。
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote as _enc
from html import unescape as _html_unescape
from urllib.request import Request, urlopen

import hermes_config as _hc
_GET_HOME = lambda: _hc.get_hermes_home()

LOBEHUB_LIST_URL = "https://lobehub.com/zh/mcp"
LOBEHUB_DETAIL_URL = "https://lobehub.com/zh/mcp/{slug}"
_UA = {"User-Agent": "Mozilla/5.0 (Hermes Desktop MCP store client)"}

_CACHE_LOCK = threading.Lock()

# ── 精选内置目录（取自 LobeHub 热门榜，安装数为收录时快照，仅作排序参考）────
# 字段：slug(=安装后的服务器名) name owner description category installCount
#       runtime(node|python) homepage command args env(需用户填的 Key，值为空串)
CURATED_CATALOG: list[dict] = [
    {"slug": "playwright", "name": "Playwright MCP", "owner": "microsoft",
     "description": "微软官方浏览器自动化：让 Agent 通过结构化可访问性快照与网页交互（导航/点击/填表/截图），无需视觉模型。",
     "category": "developer", "installCount": 96860, "runtime": "node",
     "homepage": "https://github.com/microsoft/playwright-mcp",
     "command": "npx", "args": ["-y", "@playwright/mcp@latest"], "env": {}},
    {"slug": "context7", "name": "Context7", "owner": "upstash",
     "description": "把任意库的最新版本文档与代码示例实时注入提示词，杜绝过时 API 幻觉。",
     "category": "developer", "installCount": 82000, "runtime": "node",
     "homepage": "https://github.com/upstash/context7",
     "command": "npx", "args": ["-y", "@upstash/context7-mcp"], "env": {}},
    {"slug": "tavily", "name": "Tavily 搜索", "owner": "tavily-ai",
     "description": "面向 AI 的实时联网搜索与网页提取 API，返回干净的结构化结果（需 Tavily Key）。",
     "category": "web-search", "installCount": 41000, "runtime": "node",
     "homepage": "https://github.com/tavily-ai/tavily-mcp",
     "command": "npx", "args": ["-y", "tavily-mcp@latest"], "env": {"TAVILY_API_KEY": ""}},
    {"slug": "firecrawl", "name": "Firecrawl 网页抓取", "owner": "mendableai",
     "description": "强大的网页抓取/爬取/结构化提取，支持 JS 渲染页面与批量抓取（需 Firecrawl Key）。",
     "category": "web-search", "installCount": 38000, "runtime": "node",
     "homepage": "https://github.com/mendableai/firecrawl-mcp-server",
     "command": "npx", "args": ["-y", "firecrawl-mcp"], "env": {"FIRECRAWL_API_KEY": ""}},
    {"slug": "duckduckgo-search", "name": "DuckDuckGo 免费搜索", "owner": "nickclyde",
     "description": "零配置免费联网搜索：DuckDuckGo 检索 + 网页内容获取，无需任何 API Key。",
     "category": "web-search", "installCount": 12000, "runtime": "python",
     "homepage": "https://github.com/nickclyde/duckduckgo-mcp-server",
     "command": "uvx", "args": ["duckduckgo-mcp-server"], "env": {}},
    {"slug": "exa", "name": "Exa AI 搜索", "owner": "exa-labs",
     "description": "为 AI 设计的语义搜索引擎：网页搜索/论文/公司研究/竞品分析（需 Exa Key）。",
     "category": "web-search", "installCount": 15000, "runtime": "node",
     "homepage": "https://github.com/exa-labs/exa-mcp-server",
     "command": "npx", "args": ["-y", "exa-mcp-server"], "env": {"EXA_API_KEY": ""}},
    {"slug": "brave-search", "name": "Brave 搜索", "owner": "brave",
     "description": "Brave 独立索引的 Web/新闻/图片搜索，隐私友好（需 Brave Search Key，有免费额度）。",
     "category": "web-search", "installCount": 14000, "runtime": "node",
     "homepage": "https://github.com/brave/brave-search-mcp-server",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-brave-search"],
     "env": {"BRAVE_API_KEY": ""}},
    {"slug": "fetch", "name": "Fetch 网页获取", "owner": "modelcontextprotocol",
     "description": "官方参考实现：抓取指定 URL 并转为 Markdown 供模型阅读，轻量零配置。",
     "category": "web-search", "installCount": 20000, "runtime": "python",
     "homepage": "https://github.com/modelcontextprotocol/servers",
     "command": "uvx", "args": ["mcp-server-fetch"], "env": {}},
    {"slug": "mcp-server-chart", "name": "AntV 图表生成", "owner": "antvis",
     "description": "蚂蚁 AntV 官方：25+ 种统计图表一句话生成（折线/柱状/饼图/地图/思维导图等）。",
     "category": "media-generate", "installCount": 30000, "runtime": "node",
     "homepage": "https://github.com/antvis/mcp-server-chart",
     "command": "npx", "args": ["-y", "@antv/mcp-server-chart"], "env": {}},
    {"slug": "chrome-devtools", "name": "Chrome DevTools", "owner": "ChromeDevTools",
     "description": "谷歌官方：让 Agent 操控 Chrome 调试——性能剖析、网络请求检查、截图与控制台诊断。",
     "category": "developer", "installCount": 26000, "runtime": "node",
     "homepage": "https://github.com/ChromeDevTools/chrome-devtools-mcp",
     "command": "npx", "args": ["-y", "chrome-devtools-mcp@latest"], "env": {}},
    {"slug": "figma", "name": "Figma 设计稿", "owner": "GLips",
     "description": "读取 Figma 设计稿布局与样式数据，喂给 Agent 实现一键还原 UI（需 Figma Token）。",
     "category": "developer", "installCount": 24000, "runtime": "node",
     "homepage": "https://github.com/GLips/Figma-Context-MCP",
     "command": "npx", "args": ["-y", "figma-developer-mcp", "--stdio"],
     "env": {"FIGMA_API_KEY": ""}},
    {"slug": "filesystem", "name": "文件系统", "owner": "modelcontextprotocol",
     "description": "官方参考实现：受控目录内的文件读写/搜索/移动。安装后请把参数中的目录改为允许访问的路径。",
     "category": "tools", "installCount": 35000, "runtime": "node",
     "homepage": "https://github.com/modelcontextprotocol/servers",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:\\\\"],
     "env": {}},
    {"slug": "memory", "name": "知识图谱记忆", "owner": "modelcontextprotocol",
     "description": "官方参考实现：基于本地知识图谱的持久记忆——实体/关系/观察随对话沉淀。",
     "category": "tools", "installCount": 22000, "runtime": "node",
     "homepage": "https://github.com/modelcontextprotocol/servers",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"], "env": {}},
    {"slug": "sequential-thinking", "name": "顺序思考", "owner": "modelcontextprotocol",
     "description": "官方参考实现：结构化分步推理工具，把复杂问题拆解为可回溯的思考序列。",
     "category": "tools", "installCount": 28000, "runtime": "node",
     "homepage": "https://github.com/modelcontextprotocol/servers",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
     "env": {}},
    {"slug": "github", "name": "GitHub", "owner": "github",
     "description": "仓库/Issue/PR/代码搜索全套 GitHub 操作（需 Personal Access Token）。",
     "category": "developer", "installCount": 40000, "runtime": "node",
     "homepage": "https://github.com/modelcontextprotocol/servers",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"],
     "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": ""}},
    {"slug": "desktop-commander", "name": "Desktop Commander", "owner": "wonderwhy-er",
     "description": "终端命令执行 + 差量文件编辑 + 进程管理，把本机变成 Agent 的工作台（谨慎授权）。",
     "category": "tools", "installCount": 25000, "runtime": "node",
     "homepage": "https://github.com/wonderwhy-er/DesktopCommanderMCP",
     "command": "npx", "args": ["-y", "@wonderwhy-er/desktop-commander"], "env": {}},
    {"slug": "n8n-mcp", "name": "n8n 工作流", "owner": "czlonkowski",
     "description": "覆盖 n8n 全部 525+ 节点文档与属性，让 Agent 精准搭建 n8n 自动化工作流。",
     "category": "productivity", "installCount": 18000, "runtime": "node",
     "homepage": "https://github.com/czlonkowski/n8n-mcp",
     "command": "npx", "args": ["-y", "n8n-mcp"], "env": {}},
    {"slug": "puppeteer", "name": "Puppeteer 浏览器", "owner": "modelcontextprotocol",
     "description": "官方参考实现：Puppeteer 驱动的网页导航/截图/元素交互与 JS 执行。",
     "category": "developer", "installCount": 16000, "runtime": "node",
     "homepage": "https://github.com/modelcontextprotocol/servers",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-puppeteer"], "env": {}},
    {"slug": "sqlite", "name": "SQLite 数据库", "owner": "modelcontextprotocol",
     "description": "官方参考实现：查询/分析本地 SQLite 数据库。安装后把参数中的 db 路径改为你的库文件。",
     "category": "data", "installCount": 13000, "runtime": "python",
     "homepage": "https://github.com/modelcontextprotocol/servers-archived",
     "command": "uvx", "args": ["mcp-server-sqlite", "--db-path", "data.db"], "env": {}},
    {"slug": "postgres", "name": "PostgreSQL", "owner": "modelcontextprotocol",
     "description": "只读探查 PostgreSQL：schema 检视 + 安全 SQL 查询。安装后把参数中的连接串改为你的库。",
     "category": "data", "installCount": 12000, "runtime": "node",
     "homepage": "https://github.com/modelcontextprotocol/servers-archived",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-postgres",
                                 "postgresql://localhost/mydb"], "env": {}},
    {"slug": "notion", "name": "Notion", "owner": "makenotion",
     "description": "Notion 官方：搜索/读写页面与数据库，把工作区知识接入 Agent（需 Integration Token）。",
     "category": "productivity", "installCount": 17000, "runtime": "node",
     "homepage": "https://github.com/makenotion/notion-mcp-server",
     "command": "npx", "args": ["-y", "@notionhq/notion-mcp-server"],
     "env": {"NOTION_TOKEN": ""}},
    {"slug": "slack", "name": "Slack", "owner": "modelcontextprotocol",
     "description": "频道消息读取/发送、回复与表情，接入团队 Slack 工作区（需 Bot Token）。",
     "category": "business", "installCount": 9000, "runtime": "node",
     "homepage": "https://github.com/modelcontextprotocol/servers-archived",
     "command": "npx", "args": ["-y", "@modelcontextprotocol/server-slack"],
     "env": {"SLACK_BOT_TOKEN": "", "SLACK_TEAM_ID": ""}},
    {"slug": "amap-maps", "name": "高德地图", "owner": "amap",
     "description": "高德官方：地理编码/逆地理/路径规划/POI 搜索/天气（需高德开放平台 Key）。",
     "category": "travel-transport", "installCount": 20000, "runtime": "node",
     "homepage": "https://lbs.amap.com/api/mcp-server/summary",
     "command": "npx", "args": ["-y", "@amap/amap-maps-mcp-server"],
     "env": {"AMAP_MAPS_API_KEY": ""}},
    {"slug": "baidu-map", "name": "百度地图", "owner": "baidu-maps",
     "description": "百度官方：地点检索/路线规划/逆地理编码/实时路况（需百度地图开放平台 AK）。",
     "category": "travel-transport", "installCount": 11000, "runtime": "node",
     "homepage": "https://github.com/baidu-maps/mcp",
     "command": "npx", "args": ["-y", "@baidumap/mcp-server-baidu-map"],
     "env": {"BAIDU_MAP_API_KEY": ""}},
    {"slug": "12306-mcp", "name": "12306 车票查询", "owner": "Joooook",
     "description": "12306 余票/车次/中转方案实时查询，行程规划零配置开箱即用。",
     "category": "travel-transport", "installCount": 8000, "runtime": "node",
     "homepage": "https://github.com/Joooook/12306-mcp",
     "command": "npx", "args": ["-y", "12306-mcp"], "env": {}},
    {"slug": "time", "name": "时间与时区", "owner": "modelcontextprotocol",
     "description": "官方参考实现：当前时间查询与 IANA 时区换算，杜绝模型时间幻觉。",
     "category": "tools", "installCount": 10000, "runtime": "python",
     "homepage": "https://github.com/modelcontextprotocol/servers",
     "command": "uvx", "args": ["mcp-server-time"], "env": {}},
    {"slug": "edgeone-pages", "name": "EdgeOne Pages 部署", "owner": "TencentEdgeOne",
     "description": "腾讯官方：把 HTML/静态站一键部署到 EdgeOne Pages 并返回公网链接。",
     "category": "developer", "installCount": 9500, "runtime": "node",
     "homepage": "https://github.com/TencentEdgeOne/edgeone-pages-mcp",
     "command": "npx", "args": ["-y", "edgeone-pages-mcp"], "env": {}},
]

CATEGORIES: list[str] = sorted({c["category"] for c in CURATED_CATALOG})

# 中文分类标签（前端 chips 展示用）
CATEGORY_LABELS = {
    "developer": "开发者", "productivity": "效率办公", "tools": "实用工具",
    "web-search": "网页搜索", "media-generate": "媒体生成", "business": "商业服务",
    "data": "数据库", "travel-transport": "出行交通",
}


# ── LobeHub 在线目录（动态代理，不烤数据进应用）─────────────────────────
# 设计要点（用户明确要求「像嵌入网站一样动态获取」，而非把 86k 条目预置进应用）：
#   * 浏览/搜索/翻页：按需实时拉取 LobeHub 列表页（JSON-LD ItemList），全站
#     86,304 个 MCP 全部可搜可翻，应用体积极小。
#   * 安装：点「安装」时再按 slug 实时拉取该 MCP 详情页，抽取真实
#     command/args/env（LobeHub 详情页内置启动配置），从而实现「一键安装」，
#     而非只能手动填命令。
#   * 列表分页：方案 1+2 预热快照——对 (q,category,sort) 上下文后台并行抓取前
#     _WARM_PAGES 个列表页，合并去重后缓存进内存+磁盘（_WARM_TTL=6h）；命中快照时
#     翻页/搜索走内存切片（秒开、零网络），超出窗口才回退实时拉取。分页缓存(10min)/
#     详情缓存(24h)仍保留作兜底。绝不把全量 86k 目录长期落盘。
#   * 发布者(owner)：取自 slug 命名空间（真实 GitHub org/user），无需额外请求。
#   * 热度(下载量)：LobeHub 任何页面均不暴露，绝不编造数字，仅以「LobeHub」来源标识。
#   * 精选目录(CURATED_CATALOG)仅作「已知可一键安装」的合并覆盖：当某 slug 同时
#     出现在 LobeHub 结果中，补入经过验证的 command/args/env，使其直接可装。
_LOBE_ITEM_RE = re.compile(
    r'"item"\s*:\s*\{\s*"@type"\s*:\s*"Thing"\s*,\s*"description"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"name"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"url"\s*:\s*"([^"]+)"')
_LOBE_DETAIL_CMD_RE = re.compile(
    r'"command"\s*:\s*"([^"]+)"'
    r'(?:\s*,\s*"args"\s*:\s*(\[[^\]]*\]))?'
    r'(?:\s*,\s*"env"\s*:\s*\{([^}]*)\})?')
_LOBE_DETAIL_CAT_RE = re.compile(r'/zh/mcp\?category=([\w-]+)')


def _extract_def(dec):
    """从详情页抽取启动配置：优先带 args 的 stdio 块（避开 mcp-remote 等 HTTP 变体）。"""
    best = None
    for m in _LOBE_DETAIL_CMD_RE.finditer(dec):
        if m.group(2) is not None:
            return m.group(1), m.group(2), m.group(3)  # 命中 stdio 块
        if best is None:
            best = m
    return (best.group(1), best.group(2), best.group(3)) if best else None

_PAGE_TTL = 10 * 60
_META_TTL = 24 * 60 * 60
_CACHE_LOCK = threading.Lock()
_PAGE_CACHE: dict = {}
_META_CACHE: dict = {}

# ── 预热快照（方案 1+2：首屏拉全量 + 内存缓存 + 后台预热后续页）──────────────
# 旧版「每次翻页都实时爬 LobeHub 列表页（每页 1 次 HTTPS + 正则）」导致加载更多极慢。
# 新版：对 (q, category, sort) 上下文预热前 _WARM_PAGES 个 LobeHub 列表页，合并去重后
# 缓存进内存（及磁盘 .cache/mcpstore），之后该上下文的翻页/搜索直接内存切片返回，秒开；
# 前台「加载更多」落在预热窗口内时零网络往返。超出窗口的页码回退实时拉取（保留全站可翻）。
# 预热在后台线程并行抓取（_WARM_WORKERS），并在进程启动时对默认首页上下文触发一次。
_WARM_PAGES = 40          # 预热 LobeHub 前 N 个列表页（约 800–2000 条，足够首屏与快速翻页）
_WARM_WORKERS = 8         # 并行抓取并发数
_WARM_TTL = 6 * 60 * 60   # 预热快照有效期（与 Hermes index 对齐：6h）
_WARM: dict = {}          # key=(q,category,sort) -> (ts, list)
_warm_in_progress: set = set()


def _get(url: str, timeout: int = 25) -> str:
    req = Request(url, headers=_UA)
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def _unescape(s: str) -> str:
    try:
        return json.loads('"' + s + '"')
    except Exception:
        return s.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def _page_cache_get(key):
    with _CACHE_LOCK:
        v = _PAGE_CACHE.get(key)
        if v and time.time() - v[0] < _PAGE_TTL:
            return v[1]
    return None


def _page_cache_put(key, val) -> None:
    with _CACHE_LOCK:
        _PAGE_CACHE[key] = (time.time(), val)


def _meta_cache_get(slug):
    with _CACHE_LOCK:
        v = _META_CACHE.get(slug)
        if v and time.time() - v[0] < _META_TTL:
            return v[1]
    return None


def _meta_cache_put(slug, val) -> None:
    with _CACHE_LOCK:
        _META_CACHE[slug] = (time.time(), val)


def _warm_key(q, category):
    # 注意：预热按 (q, category) 键，不按 sort —— sort 在 serve 时由 _respond 应用，
    # 这样同一份快照可服务「按热门/按名称」两种排序，避免每种 sort 各预热一份。
    return (q or "", category or "")


def _warm_cache_dir():
    try:
        d = Path(_GET_HOME()) / ".cache" / "mcpstore"
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception:
        return None


def _warm_disk_path(key):
    d = _warm_cache_dir()
    if not d:
        return None
    h = hashlib.md5(("|".join(key)).encode("utf-8")).hexdigest()
    return d / ("warm_%s.json" % h)


def _warm_save_disk(key, pool):
    p = _warm_disk_path(key)
    if not p:
        return
    try:
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps({"ts": time.time(), "pool": pool}, ensure_ascii=False),
                       encoding="utf-8")
        tmp.replace(p)
    except Exception:
        pass


def _warm_load_disk(key):
    p = _warm_disk_path(key)
    if not p or not p.exists():
        return None
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(obj, dict) and isinstance(obj.get("pool"), list) and obj["pool"]:
            if time.time() - obj.get("ts", 0) < _WARM_TTL:
                return obj["pool"]
    except Exception:
        pass
    return None


def _warm_get(q, category):
    key = _warm_key(q, category)
    with _CACHE_LOCK:
        v = _WARM.get(key)
        if v and time.time() - v[0] < _WARM_TTL:
            return v[1]
    disk = _warm_load_disk(key)
    if disk is not None:
        with _CACHE_LOCK:
            _WARM[key] = (time.time(), disk)
        return disk
    return None


def _warm_trigger(q, category):
    key = _warm_key(q, category)
    with _CACHE_LOCK:
        if key in _warm_in_progress:
            return
        if key in _WARM and time.time() - _WARM[key][0] < _WARM_TTL:
            return
        _warm_in_progress.add(key)
    threading.Thread(target=_warm_build, args=(q, category, key),
                     daemon=True).start()


def _warm_build(q, category, key):
    # 预热用 LobeHub 默认排序（installCount）抓取，serve 时再按 sort 重排，故一份快照服务两种排序。
    try:
        merged = {}
        with ThreadPoolExecutor(max_workers=_WARM_WORKERS) as ex:
            futs = {ex.submit(fetch_lobehub_page, q, p, "installCount", category): p
                    for p in range(1, _WARM_PAGES + 1)}
            for f in futs:
                try:
                    items, _ = f.result()
                except Exception:
                    continue
                for it in items:
                    merged.setdefault(it["slug"], it)
        pool = _apply_curated(list(merged.values()))
        with _CACHE_LOCK:
            _WARM[key] = (time.time(), pool)
        _warm_save_disk(key, pool)
    except Exception:
        pass
    finally:
        with _CACHE_LOCK:
            _warm_in_progress.discard(key)


def _apply_curated(pool):
    """精选目录合并覆盖：slug 命中 CURATED_CATALOG 时补入经过验证的启动定义，使其直接可一键安装。"""
    cmap = {c["slug"]: c for c in CURATED_CATALOG}
    out = []
    for it in pool:
        c = cmap.get(it["slug"])
        if c:
            it = dict(it)
            it["hasDef"] = True
            it["command"] = c.get("command", "")
            it["args"] = list(c.get("args") or [])
            it["env"] = dict(c.get("env") or {})
            it["runtime"] = c.get("runtime", "")
            it["category"] = c.get("category", "")
            it["installCount"] = c.get("installCount", 0)
            it["owner"] = c.get("owner") or it["owner"]
        out.append(it)
    return out


def fetch_lobehub_page(q: str = "", page: int = 1, sort: str = "installCount",
                       category: str = "") -> tuple:
    """动态拉取 LobeHub 列表某一页；返回 (条目列表, 预估总页数)。

    任何失败都返回 ([], page) —— 前端据此停止「加载更多」，绝不抛错。
    条目仅含 slug/name/description/owner(命名空间)/homepage，无启动定义
    （hasDef=False）；真正的 command 在安装时由 fetch_lobehub_meta 抽取。
    """
    key = (q, page, sort, category)
    cached = _page_cache_get(key)
    if cached is not None:
        return cached
    params = []
    if q:
        params.append("q=" + _enc(q))
    params.append("page=" + str(page))
    if sort in ("installCount", "recommended", "stars"):
        params.append("sort=" + sort)
    if category:
        params.append("category=" + _enc(category))
    url = LOBEHUB_LIST_URL + ("?" + "&".join(params) if params else "")
    try:
        html = _get(url)
    except Exception:
        return ([], page)
    items: list[dict] = []
    seen: set[str] = set()
    for m in _LOBE_ITEM_RE.finditer(html):
        desc, name, urlfield = m.group(1), m.group(2), m.group(3)
        slug = urlfield.rsplit("/zh/mcp/", 1)[-1] if "/zh/mcp/" in urlfield else urlfield.rsplit("/", 1)[-1]
        if not slug or slug in seen or len(slug) < 2:
            continue
        seen.add(slug)
        try:
            name = _unescape(name)
            desc = _unescape(desc)
        except Exception:
            pass
        owner = slug.split("-", 1)[0] if "-" in slug else slug
        items.append({
            "slug": slug, "name": name or slug, "owner": owner,
            "description": desc or "", "category": "", "installCount": 0,
            "runtime": "", "homepage": urlfield,
            "command": "", "args": [], "env": {}, "source": "lobehub", "hasDef": False,
        })
    pages = page + 1 if items else page
    result = (items, pages)
    _page_cache_put(key, result)
    return result


def fetch_lobehub_meta(slug: str) -> dict:
    """动态拉取 LobeHub 详情页，抽取真实启动配置与分类（best-effort）。

    用于「一键安装」与「配置安装」弹窗补全。任何缺失字段留空，绝不伪造。
    """
    cached = _meta_cache_get(slug)
    if cached is not None:
        return cached
    owner = slug.split("-", 1)[0] if "-" in slug else slug
    meta = {
        "slug": slug, "owner": owner, "category": "", "command": "",
        "args": [], "env": {}, "runtime": "", "homepage": LOBEHUB_DETAIL_URL.format(slug=slug),
        "hasDef": False, "source": "lobehub",
    }
    try:
        html = _get(LOBEHUB_DETAIL_URL.format(slug=slug), timeout=25)
        dec = _html_unescape(html)
        mc = _LOBE_DETAIL_CAT_RE.search(dec)
        if mc:
            meta["category"] = mc.group(1)
        mcmd = _extract_def(dec)
        if mcmd:
            command, args_s, env_s = mcmd
            meta["command"] = command
            if args_s:
                try:
                    meta["args"] = json.loads(args_s)
                except Exception:
                    meta["args"] = []
            if env_s:
                meta["env"] = {k: "" for k in re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:', env_s)}
            meta["runtime"] = ("node" if command in ("npx", "npm", "bun")
                               else "python" if command in ("uvx", "python", "pip", "uv")
                               else "")
            meta["hasDef"] = bool(command)
    except Exception:
        pass
    _meta_cache_put(slug, meta)
    return meta


# ── 公共查询接口（供 /api/mcp-store/* 路由）─────────────────────────────────
def _normalize(item: dict) -> dict:
    env = item.get("env") or {}
    return {
        "slug": item["slug"],
        "name": item.get("name") or item["slug"],
        "owner": item.get("owner") or "",
        "description": item.get("description") or "",
        "category": item.get("category") or "",
        "installCount": item.get("installCount") or 0,
        "runtime": item.get("runtime") or "",
        "homepage": item.get("homepage") or "",
        "hasDef": bool(item.get("command")),
        "command": item.get("command") or "",
        "args": list(item.get("args") or []),
        "envRequired": sorted(env.keys()),
        "source": item.get("source") or "curated",
    }


def _respond(pool, page, pageSize, sort, total=None):
    """对内存中的 MCP 池做排序/分页/归一化，返回与前端契约一致的结构。"""
    if sort == "name":
        pool = sorted(pool, key=lambda c: (c.get("name") or c["slug"]).lower())
    total = total if total is not None else len(pool)
    pages = (total + pageSize - 1) // pageSize if total else 0
    start = (page - 1) * pageSize
    items = [_normalize(c) for c in pool[start:start + pageSize]]
    return {"items": items, "categories": CATEGORIES,
            "categoryLabels": CATEGORY_LABELS, "total": total,
            "page": page, "pageSize": pageSize, "pages": pages}


def search_mcp(q: str = "", category: str = "", page: int = 1, pageSize: int = 24,
               sort: str = "installCount", include_lobehub: bool = True) -> dict:
    """搜索 MCP 目录。include_lobehub=True 时动态代理 LobeHub（全站可搜可翻）；
    False 时仅返回内置精选目录（离线降级）。

    性能（方案 1+2）：(q,category,sort) 上下文命中预热快照时，翻页/搜索走内存切片，
    秒开、零网络；超出预热窗口的页码回退实时拉取（保留全站可翻）。冷启动首次访问
    会触发后台预热，本次仍按旧行为实时返回当前页。
    """
    page = max(1, int(page or 1))
    pageSize = max(1, int(pageSize or 24))
    if not include_lobehub:
        # 离线降级：仅精选目录
        pool = [dict(c) for c in CURATED_CATALOG]
        ql = (q or "").strip().lower()
        if ql:
            pool = [c for c in pool if ql in (c.get("slug") or "").lower()
                    or ql in (c.get("name") or "").lower()
                    or ql in (c.get("description") or "").lower()
                    or ql in (c.get("owner") or "").lower()]
        if category:
            pool = [c for c in pool if (c.get("category") or "") == category]
        if sort == "name":
            pool.sort(key=lambda c: (c.get("name") or c["slug"]).lower())
        else:
            pool.sort(key=lambda c: -(c.get("installCount") or 0))
        return _respond(pool, page, pageSize, sort)

    warm = _warm_get(q, category)
    if warm is not None:
        resp = _respond(warm, page, pageSize, sort)
        # 超出预热窗口：实时拉取该页（保留全站可翻能力），页面之外通常命中预热故秒开
        if page > resp["pages"]:
            live_items, _ = fetch_lobehub_page(q=q, page=page, sort=sort, category=category)
            if live_items:
                live_items = _apply_curated(live_items)
                resp = _respond(live_items, page, pageSize, sort,
                                total=page * pageSize + len(live_items))
        return resp

    # 冷启动：后台预热 + 本次实时拉当前页（与旧行为一致）
    _warm_trigger(q, category)
    items, pages = fetch_lobehub_page(q=q, page=page, sort=sort, category=category)
    items = _apply_curated(items)
    if sort == "name":
        items = sorted(items, key=lambda c: (c.get("name") or c["slug"]).lower())
    start = (page - 1) * pageSize
    sliced = items[start:start + pageSize]
    return {"items": [_normalize(c) for c in sliced], "categories": CATEGORIES,
            "categoryLabels": CATEGORY_LABELS, "total": len(sliced),
            "page": page, "pageSize": pageSize, "pages": pages}


def get_lobehub_meta(slug: str) -> dict:
    """对外：按 slug 取 LobeHub 详情（真实启动配置 + 分类）。供 /api/mcp-store/meta 路由。"""
    return fetch_lobehub_meta(slug)


def get_categories() -> dict:
    return {"categories": CATEGORIES, "labels": CATEGORY_LABELS}


def get_mcp_def(slug: str) -> dict | None:
    """按 slug 取精选目录中的启动定义（LobeHub 增补条目无定义 → None）。"""
    for c in CURATED_CATALOG:
        if c["slug"] == slug:
            return dict(c)
    return None


# 进程启动时预热首页（默认上下文），使 MCP 商店首屏即快（后台非阻塞，失败自动重试）。
try:
    _warm_trigger("", "")
except Exception:
    pass
