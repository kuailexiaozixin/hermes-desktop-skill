import asyncio
import os
import sys

from pathlib import Path
from server import app
from ._helpers import _err, _guard, _ok
import agent_runtime as ar
import hermes_skills_client as hskills
import hermes_config as hc
import mcpstore_client as mstore
import skillhub_client as shub
import wiki_engine as we
import unified_skills_client as unified
# 设置中心 · 技能
# ---------------------------------------------------------------------------

@app.get("/api/skills")
def api_skills():
    return _guard(lambda: {"ok": True, "items": hc.list_skills()})

@app.get("/api/skills/{name}")
def api_skill_read(name: str):
    return _guard(lambda: {"ok": True, "item": hc.read_skill(name)})

@app.post("/api/skills")
async def api_skill_save(req):
    body = await req.json()
    name = body.get("name") or ""
    if not name:
        return _err("技能名不能为空")
    fn = hc.update_skill if body.get("exists") else hc.create_skill
    return _guard(fn, name, body.get("description") or "",
                  body.get("body") or "", body.get("category") or "")

@app.post("/api/skills/{name}/enabled")
async def api_skill_enabled(name: str, req):
    body = await req.json()
    return _guard(hc.set_skill_enabled, name, bool(body.get("enabled")))

@app.delete("/api/skills/{name}")
def api_skill_del(name: str):
    return _guard(hc.delete_skill, name)

@app.get("/api/skill-store/sources")
def skill_store_sources():
    return _ok(sources=[
        {"id": "skillhub", "name": "SkillHub（腾讯）", "needAuth": False,
         "desc": "国内最大 AI Skills 社区，公开列表接口无需鉴权"},
        {"id": "hermes", "name": "Hermes 官方", "needAuth": False,
         "desc": "Hermes skills-index 中的 official 可选技能（source=official / trust_level=builtin）"},
        {"id": "builtin", "name": "本地已安装", "needAuth": False,
         "desc": "本机 HERMES_HOME/skills 中的技能"},
    ])

@app.get("/api/skill-store/skills")
async def skill_store_search(req):
    """统一技能市场搜索（SkillHub + Hermes 各源，来源标注，按需查询不下载全量）。"""
    qp = req.query_params
    q = (qp.get("q") or "").strip()
    category = (qp.get("category") or "").strip()
    try:
        page = int(qp.get("page") or 1)
    except (TypeError, ValueError):
        page = 1
    try:
        pageSize = int(qp.get("pageSize") or 24)
    except (TypeError, ValueError):
        pageSize = 24
    # 市场过滤：逗号分隔的市场标识（如 community,skills.sh），空/缺省=全部
    sources = (qp.get("sources") or "").strip()
    # 排序模式：default / score / downloads / name / verified（详见 unified_skills_client.search_skills）
    sort = (qp.get("sort") or "default").strip()
    try:
        res = await asyncio.to_thread(
            unified.search_skills, q=q, category=category, page=page,
            pageSize=pageSize, sources=sources, sort=sort)
        return _ok(**res)
    except Exception as e:
        return _err(str(e), items=[], categories=[])

@app.get("/api/skill-store/categories")
async def skill_store_categories():
    """统一市场分类（SkillHub + Hermes 各源聚合）。"""
    try:
        cats = await asyncio.to_thread(unified.get_categories)
        return _ok(categories=cats)
    except Exception as e:
        return _err(str(e), categories=[])

@app.get("/api/skill-store/installed")
def skill_store_installed():
    """本机已安装技能列表。"""
    def _p() -> dict:
        items = []
        for s in hc.list_skills():
            p = s.get("path") or ""
            items.append({
                "id": s.get("id"), "name": s.get("name"),
                "description": s.get("description"), "category": s.get("category"),
                "path": p, "dir": os.path.dirname(p) if p else "",
                "enabled": s.get("enabled", True),
            })
        return {"ok": True, "items": items}
    return _guard(_p)

@app.post("/api/skill-store/installed/{sid}/enable")
async def skill_store_installed_enable(sid: str, req):
    """启用/关闭本机技能（写 config.yaml，即时生效）。"""
    body = await req.json()
    enabled = bool(body.get("enabled", True))
    hc.set_skill_enabled(sid, enabled)
    return _ok(id=sid, enabled=enabled)

@app.get("/api/skill-store/installed/{sid}/detail")
def skill_store_installed_detail(sid: str):
    """读取单个技能详情（用于修改）。"""
    d = hc.read_skill(sid)
    if not d:
        return _err("未找到技能")
    return _ok(**d)

@app.post("/api/skill-store/installed/{sid}/save")
async def skill_store_installed_save(sid: str, req):
    """保存对技能的修改（写回 SKILL.md）。"""
    body = await req.json()
    res = hc.update_skill(sid, body.get("description"), body.get("body"),
                          body.get("category"))
    if not res.get("ok"):
        return _err(res.get("error") or "保存失败")
    return _ok(**res)

@app.post("/api/skill-store/install")
async def skill_store_install(req):
    """统一市场安装（按来源走 SkillHub 或 Hermes 各源 fetch，隔离-扫描-落盘）。"""
    body = await req.json()
    identifier = (body.get("identifier") or body.get("slug") or "").strip()
    if not identifier:
        return _err("identifier 为必填")
    upstream = (body.get("upstream_url") or "").strip() or ""
    force = bool(body.get("force"))
    source = (body.get("source") or "").strip()
    res = await asyncio.to_thread(unified.install, identifier, upstream, force, source)
    if not res.get("ok"):
        return _err(res.get("error") or "安装失败")
    return _ok(**res)

# ---------------------------------------------------------------------------
# Hermes 官方 skills-index（official 可选技能，进程内 Library 安装）
# 前端组件：static/skillstore.js 的 "Hermes 官方" 子市场
# ---------------------------------------------------------------------------

@app.get("/api/skill-store/hermes/skills")
async def skill_store_hermes_skills(req):
    """浏览/搜索 Hermes 官方 skills-index（source=official）。"""
    qp = req.query_params
    q = (qp.get("q") or "").strip()
    category = (qp.get("category") or "").strip()
    try:
        page = int(qp.get("page") or 1)
    except (TypeError, ValueError):
        page = 1
    try:
        pageSize = int(qp.get("pageSize") or 24)
    except (TypeError, ValueError):
        pageSize = 24
    source_filter = (qp.get("source_filter") or "all").strip()
    try:
        res = await asyncio.to_thread(
            hskills.search_skills, q=q, category=category, page=page,
            pageSize=pageSize, source_filter=source_filter)
        return _ok(**res)
    except Exception as e:
        return _err(str(e), items=[], categories=[])

@app.get("/api/skill-store/hermes/categories")
async def skill_store_hermes_categories():
    """Hermes 官方技能分类列表。"""
    try:
        cats = await asyncio.to_thread(hskills.get_categories)
        return _ok(categories=cats)
    except Exception as e:
        return _err(str(e), categories=[])

@app.post("/api/skill-store/hermes/install")
async def skill_store_hermes_install(req):
    """从 Hermes skills-index 安装技能（identifier 形如 official/<category>/<skill>）。"""
    body = await req.json()
    identifier = (body.get("identifier") or "").strip()
    if not identifier:
        return _err("identifier 为必填（如 official/security/1password）")
    force = bool(body.get("force"))
    res = await asyncio.to_thread(hskills.install_skill, identifier, force=force)
    if not res.get("ok"):
        return _err(res.get("error") or "安装失败")
    return _ok(**res)

@app.delete("/api/skill-store/installed/{sid}")
def skill_store_uninstall(sid: str):
    """卸载本机技能（删除 HERMES_HOME/skills/<sid>）。"""
    return _guard(hc.delete_skill, sid)

@app.post("/api/skill-store/upload-local")
async def skill_store_upload_local(req):
    """上传本地 .zip 技能包安装到 HERMES_HOME/skills/<name>/（pywebview 上传的 HTTP 替代）。"""
    import io, re as _re, shutil, tempfile, zipfile
    try:
        form = await req.form()
    except Exception as e:
        return _err(f"表单解析失败：{e}")
    up = form.get("file")
    if up is None:
        return _err("未选择文件")
    filename = getattr(up, "filename", "") or ""
    if not filename.lower().endswith(".zip"):
        return _err("仅支持 .zip 技能包")
    try:
        raw = await up.read()
    except Exception as e:
        return _err(f"读取文件失败：{e}")
    if not raw:
        return _err("文件为空")
    tmp = Path(tempfile.mkdtemp(prefix="skillup_"))
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            zf.extractall(tmp)
        skill_dir = None
        if (tmp / "SKILL.md").exists():
            skill_dir = tmp
        else:
            for child in tmp.iterdir():
                if child.is_dir() and (child / "SKILL.md").exists():
                    skill_dir = child
                    break
        if skill_dir is None:
            return _err("压缩包内未找到 SKILL.md")
        meta, _body = hc._parse_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
        name = (meta.get("name") or skill_dir.name).strip()
        safe = _re.sub(r"[^A-Za-z0-9_-]", "-", name.lower()) or "skill"
        target = hc._skills_dir() / safe
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir, target)
        return _ok(id=safe, name=name)
    except Exception as e:
        return _err(f"安装失败：{e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@app.post("/api/skill-store/detail")
async def skill_store_detail(req):
    """按 identifier/source/upstream_url 拉取技能正文（best-effort，不落盘）。

    供详情弹窗使用：市场未安装技能点击时拉取 SKILL.md 正文展示；
    已安装技能走 /api/skill-store/installed/{id}/detail（本地读取）。
    """
    body = await req.json()
    identifier = (body.get("identifier") or body.get("slug") or "").strip()
    source = (body.get("source") or "").strip()
    upstream_url = (body.get("upstream_url") or "").strip()
    if not identifier:
        return _err("identifier 为必填")
    try:
        res = await asyncio.to_thread(
            unified.fetch_content, identifier, source, upstream_url)
        if res.get("ok"):
            return _ok(body=res.get("body", ""), name=res.get("name", identifier),
                       description=res.get("description", ""))
        return _err(res.get("error") or "无法获取详情")
    except Exception as e:
        return _err(f"{type(e).__name__}: {e}")
