import json
import os
import shutil
import threading

from starlette.responses import FileResponse, JSONResponse, StreamingResponse

from typing import Iterator
from pathlib import Path
from server import app
from ._helpers import _err, _msg_text, _ok, render_markdown
import agent_runtime as ar
import hermes_config as hc
import hermes_features as hf
import sessions
import wiki_engine as we


# ---------------------------------------------------------------------------
# 安全防御纵深（复用 hermes Library，对齐官方 8 层安全模型第③层「File write safety」
# 与凭据脱敏）。Library 文档明确声明 file_safety「NOT a security boundary」——属 OS
# 权限之外的二次拦截 + 审计。本应用已用 _ws_resolve 根约束做主边界，这里补充：
#   * 读端点阻断 .env / Hermes 凭据库等敏感文件（file_safety.get_read_block_error）
#   * 写端点阻断 OS 主目录敏感前缀（.ssh/.aws/.kube/.config/gh…）与 HERMES_HOME 的
#     sessions/state.db（file_safety.get_write_denied_error）
# 任一调用失败都「放行」（不阻断正常功能），仅作 best-effort 二次防护。
# ---------------------------------------------------------------------------
def _file_safety_read_block(path) -> "str | None":
    """读取前咨询 Library file_safety；返回阻断原因（应 403）或 None。"""
    try:
        from agent.file_safety import get_read_block_error
        return get_read_block_error(str(path)) or None
    except Exception:
        return None


def _file_safety_write_denied(path) -> "str | None":
    """写入前咨询 Library file_safety；返回阻断原因（应 403）或 None。"""
    try:
        from agent.file_safety import get_write_denied_error
        return get_write_denied_error(str(path), verb="Write") or None
    except Exception:
        return None


def _safe_redact(text):
    """对可能外泄到前端/传输的文本做密钥脱敏（best-effort；失败则原样返回）。"""
    if not text:
        return text
    try:
        from agent.redact import redact_sensitive_text
        return redact_sensitive_text(text, force=True, redact_url_credentials=True)
    except Exception:
        return text


# 健康自检
# ---------------------------------------------------------------------------
@app.get("/healthz")
def healthz():
    """进程内自检（替代网关 /health）。前端据此显示右下角状态灯。"""
    info = ar.runtime_ready()
    try:
        info["home"] = str(hc.get_hermes_home())
        info["output"] = str(hc.output_dir())
        info["model"] = (hc.get_active_model_cfg() or {}).get("model")
        info["has_key"] = bool((hc.get_active_model_cfg() or {}).get("api_key"))
    except Exception as e:  # noqa: BLE001
        info["config_error"] = f"{type(e).__name__}: {e}"
    return info


@app.get("/api/context-files")
async def api_context_files(req):
    """报告当前/指定工作目录下 Hermes 原生上下文文件的发现情况（可见性，便于调试与 QA）。

    仅报告不注入；真正注入由 Hermes 原生 ``build_context_files_prompt(cwd=resolve_context_cwd())``
    在构造 agent 时完成（受 config.yaml 的 agent.context_files / soul_enabled 控制）。
    """
    import agent.prompt_builder as _pb
    raw = (req.query_params.get("dir") or "").strip()
    if not raw:
        raw = os.environ.get("TERMINAL_CWD") or os.getcwd()
    cwd_path = Path(raw).resolve()

    # 优先级顺序（首匹配胜出，对齐 Library build_context_files_prompt）
    _PRIORITY = (".hermes.md", "HERMES.md", "AGENTS.md", "CLAUDE.md", ".cursorrules")
    found_names: list[str] = []
    for name in _PRIORITY:
        if (cwd_path / name).is_file():
            found_names.append(name)
    mdc_dir = cwd_path / ".cursor" / "rules"
    mdc_names: list[str] = []
    if mdc_dir.is_dir():
        mdc_names = [str(m.relative_to(cwd_path)) for m in sorted(mdc_dir.glob("*.mdc"))]
    all_names = found_names + mdc_names
    winner = all_names[0] if all_names else None

    files = []
    for name in all_names:
        p = cwd_path / name
        entry = {"name": name, "path": str(p),
                 "selected": name == winner, "blocked": False}
        try:
            entry["bytes"] = p.stat().st_size
        except Exception:
            pass
        # 注入威胁扫描：仅 winner 会被 Library 真正加载；若其内容含提示注入，
        # Library 会拦截为 [BLOCKED:]（不注入）。superseded 文件不会被加载，
        # 这里仍扫描并报知（仅供参考，不影响注入决策）。
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            scanned = _pb._scan_context_content(content, name)
            if scanned.startswith("[BLOCKED:"):
                entry["blocked"] = True
        except Exception:
            pass
        files.append(entry)

    soul = {"loaded": False, "path": None}
    try:
        from hermes_cli.config import get_hermes_home
        sp = get_hermes_home() / "SOUL.md"
        soul = {"path": str(sp),
                "loaded": sp.is_file() and bool(sp.read_text(encoding="utf-8", errors="ignore").strip())}
    except Exception:
        pass
    # 实跑库函数确认注入文本（非空的 "Project Context" 段即表示会被注入）
    injected = ""
    try:
        injected = _pb.build_context_files_prompt(cwd=str(cwd_path)) or ""
    except Exception:
        injected = ""
    return _ok(cwd=str(cwd_path), context_files=files, winner=winner, soul=soul,
              will_inject=bool(injected.strip()),
              snippet=(injected[:600] if injected else ""))


# ---------------------------------------------------------------------------
# 对话流（SSE）
# ---------------------------------------------------------------------------
# conv_id -> threading.Event：置位表示「用户点了停止」。
# 行为（诚实标注）：
#  - 前端立即停止接收（SSE 转发循环 break）且本轮结果不落盘；
#  - run_conversation() 没有原生 cancel，但我们把 cancel 事件传入流式内核，在
#    on_delta / on_tool_* / on_reasoning 回调里最佳努力抛 _CancelRequested 中断
#    worker，避免长时间工具循环继续烧 token / 写文件（非 100% 保证，取决于 provider
#    是否在回调之间让出执行）。
_CANCEL: dict[str, threading.Event] = {}
_CANCEL_LOCK = threading.Lock()


def _cancel_event(cid: str) -> threading.Event:
    with _CANCEL_LOCK:
        ev = _CANCEL.get(cid)
        if ev is None:
            ev = threading.Event()
            _CANCEL[cid] = ev
        ev.clear()
        return ev


_TEXT_ATTACH_EXT = {".txt", ".md", ".csv", ".json", ".py", ".js", ".html", ".css",
                    ".log", ".xml", ".yaml", ".yml", ".toml", ".ini", ".sql"}

# ⑤ 附件体量预算：总字数上限（与固定文件夹共享预算，防止单轮注入撑爆上下文）
_ATTACH_MAX_TOTAL_CHARS = 120000

def _read_attachments_text(items: list) -> str:
    """把上传附件读成可注入上下文的文本（文本类读内容，其余给路径）。
    有体量预算：总字数不超过 _ATTACH_MAX_TOTAL_CHARS，超限截断。"""
    from pathlib import Path as _P
    chunks = []
    total_chars = 0
    for it in (items or []):
        if total_chars >= _ATTACH_MAX_TOTAL_CHARS:
            chunks.append("…(附件总字数已达上限，其余附件已跳过)")
            break
        p = it.get("path") or it.get("name")
        name = it.get("name") or _P(p).name
        try:
            pp = _P(p)
            if not pp.exists():
                chunks.append(f"### {name}\n（文件不存在）"); continue
            ext = pp.suffix.lower()
            if ext in _TEXT_ATTACH_EXT:
                data = pp.read_text(encoding="utf-8", errors="replace")
                if len(data) > 6000:
                    data = data[:6000] + "\n…(截断)"
                # ⑤ 累计总字数，超限截断
                if total_chars + len(data) > _ATTACH_MAX_TOTAL_CHARS:
                    remain = _ATTACH_MAX_TOTAL_CHARS - total_chars
                    if remain > 0:
                        data = data[:remain] + "\n…(附件总字数已达上限)"
                    else:
                        continue
                total_chars += len(data)
                chunks.append(f"### 附件 {name}\n{data}")
            else:
                chunks.append(f"### 附件 {name}\n（二进制/非文本文件，路径 {pp}）")
        except Exception as e:  # noqa: BLE001
            chunks.append(f"### {name}\n（读取失败：{e}）")
    return "\n\n".join(chunks)


# 图片扩展名白名单：仅这些视为可经 vision_analyze 分析的图片附件。
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".avif"}


def _is_image_attachment(item: dict) -> bool:
    """判断一个附件是否为图片（按扩展名；无扩展名时退化为按名称片段判断）。"""
    if not isinstance(item, dict):
        return False
    p = item.get("path") or item.get("name") or ""
    ext = os.path.splitext(p)[1].lower()
    if ext in _IMAGE_EXT:
        return True
    return ext == "" and "image" in (item.get("type") or "").lower()

# 会话固定文件夹上下文（G6）：把绑定目录递归读成可注入上下文的文本。
# 安全：复用 _ws_resolve 与 _WS_SKIP_DIRS，路径必须落在授权根内、跳过 node_modules/.git 等；
# 限额：最多下钻 8 层、最多 80 个文本文件、单文件 ≤20KB、总字符 ≤120KB，防超大目录拖垮注入。
_CTX_MAX_DEPTH = 8
_CTX_MAX_FILES = 80
_CTX_MAX_FILE_CHARS = 20000
_CTX_MAX_TOTAL_CHARS = 120000


def _read_context_folder(root: str, rel: str) -> dict:
    """受限递归读取绑定目录；返回 {text, files, chars, truncated, error}。

    text 为空表示无需注入（目录不存在/无文本文件/越界）。text 头部自带目录说明，
    供模型区分「这是固定背景」与「这是用户本轮附件」。"""
    info: dict = {"text": "", "files": 0, "chars": 0, "truncated": False, "error": None}
    try:
        base, rel_clean = _ws_resolve(root, rel)
    except ValueError as e:
        info["error"] = str(e)
        return info
    if not base.is_dir():
        info["error"] = "目录不存在"
        return info
    parts: list[str] = []
    base_str = str(base)
    # 复用 Library 的注入扫描与截断（惰性导入，失败则退化为朴素截断）
    try:
        from agent.prompt_builder import _scan_context_content, _truncate_content
    except Exception:
        _scan_context_content = _truncate_content = None
    try:
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            # 不进入跳过目录，避免 node_modules/.git 等巨量/无关内容
            dirnames[:] = [d for d in dirnames if d not in _WS_SKIP_DIRS]
            rel_to_base = os.path.relpath(dirpath, base_str)
            depth = 0 if rel_to_base == "." else len(rel_to_base.split(os.sep))
            if depth > _CTX_MAX_DEPTH:
                dirnames[:] = []  # 不再下钻
                continue
            for fn in sorted(filenames):
                if info["files"] >= _CTX_MAX_FILES or info["chars"] >= _CTX_MAX_TOTAL_CHARS:
                    info["truncated"] = True
                    break
                ext = (os.path.splitext(fn)[1] or "").lower()
                if ext not in _TEXT_ATTACH_EXT:
                    continue  # 仅取文本类文件，二进制不读
                info["files"] += 1
                fp = Path(dirpath) / fn
                # 防御纵深：跳过受保护凭据文件（不注入上下文，避免密钥泄漏）
                if _file_safety_read_block(fp):
                    continue
                try:
                    data = fp.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    parts.append("\n# " + os.path.relpath(fp, base_str) + "\n（读取失败）")
                    continue
                # 注入前威胁扫描：对齐 Hermes Library 的 _scan_context_content 守卫。
                # 命中提示注入则返回 "[BLOCKED: ...]" 标记——不注入该文件内容，
                # 仅记入 blocked_files 供前端/调试可见，绝不污染对话上下文。
                if _scan_context_content is not None:
                    try:
                        scanned = _scan_context_content(data, fn)
                    except Exception:
                        scanned = data
                else:
                    scanned = data
                if scanned.startswith("[BLOCKED:"):
                    info.setdefault("blocked_files", []).append(os.path.relpath(fp, base_str))
                    continue
                data = scanned
                # 单文件超过上限：标记 truncated 并复用 Library 的 70/20/10 头尾截断
                # （直接复用，避免自行实现比例漂移）；truncated 供前端「上下文已截断」指示。
                if len(data) > _CTX_MAX_FILE_CHARS:
                    info["truncated"] = True
                    if _truncate_content is not None:
                        try:
                            data = _truncate_content(data, fn, max_chars=_CTX_MAX_FILE_CHARS)
                        except Exception:
                            data = data[:_CTX_MAX_FILE_CHARS] + "\n…(文件截断)"
                    else:
                        data = data[:_CTX_MAX_FILE_CHARS] + "\n…(文件截断)"
                parts.append("\n# " + os.path.relpath(fp, base_str) + "\n" + data)
                info["chars"] += len(data)
                if info["chars"] >= _CTX_MAX_TOTAL_CHARS:
                    info["truncated"] = True
                    break
            if info["truncated"]:
                break
    except Exception as e:  # noqa: BLE001
        info["error"] = f"读取异常：{e}"
        return info
    if not parts:
        return info
    head = "# 固定文件夹：" + base_str + "\n# 文本文件数：" + str(info["files"])
    if info["truncated"]:
        head += "（已达上限，仅取部分内容）"
    head += "\n"
    info["text"] = head + "\n".join(parts)
    return info


def _read_context_folder_text(root: str, rel: str) -> str:
    """_read_context_folder 的薄封装，仅返回可注入文本（空串表示无需注入）。"""
    return _read_context_folder(root, rel).get("text") or ""


@app.post("/api/upload")
async def api_upload(req):
    """上传文件作为对话附件（存 HERMES_HOME/uploads，供 /api/chat 注入上下文）。
    支持普通多文件与「文件夹上传」：文件夹上传时附带 relpaths（相对路径列表，与 files 顺序一致），
    服务端按相对路径落盘并保留目录结构；任何越界/非法路径一律回退为仅取文件名，杜绝目录穿越。"""
    form = await req.form()
    files = form.getlist("files")
    rel_raw = form.get("relpaths")
    relpaths = []
    if rel_raw:
        try:
            relpaths = json.loads(rel_raw) or []
        except Exception:
            relpaths = []
    up_dir = Path(hc.get_hermes_home()) / "uploads"
    up_dir.mkdir(parents=True, exist_ok=True)
    up_root = up_dir.resolve()
    items = []
    for i, f in enumerate(files):
        try:
            data = await f.read()
        except Exception:
            continue
        rel = relpaths[i] if i < len(relpaths) else None
        name, target = _resolve_upload_target(up_root, f.filename, rel)
        target.write_bytes(data)
        items.append({"name": name, "path": str(target), "size": len(data)})
    return _ok(attachments=items)


def _resolve_upload_target(up_root: Path, filename: str, rel) -> tuple:
    """根据原始文件名与（可选）相对路径，算出上传落盘目标；隔离目录穿越。
    返回清洗后的相对名称（去掉 .. 与空段），杜绝向上逃逸与展示脏路径。"""
    if rel:
        parts = [p for p in str(rel).replace("\\", "/").split("/") if p not in ("", ".", "..")]
        if parts:
            cand = (up_root / "/".join(parts)).resolve()
            if str(cand).startswith(str(up_root) + os.sep):
                cand.parent.mkdir(parents=True, exist_ok=True)
                return "/".join(parts), cand
    base = (filename or "file").replace("\\", "/").split("/")[-1] or "file"
    return base, up_root / base


@app.post("/api/attachments/from-path")
async def api_attach_from_path(req):
    """把已有文件（output/ 产物或 uploads 上传件）按路径登记为对话附件，免去重新上传。
    仅允许应用自有目录：output_dir 与 HERMES_HOME/uploads；拒绝越界/非文件。"""
    body = await req.json()
    raw = (body.get("path") or "").strip()
    if not raw:
        return _err("缺少 path")
    root = Path(hc.output_dir()).resolve()
    up_root = (Path(hc.get_hermes_home()) / "uploads").resolve()
    cand = Path(raw)
    target = (root / raw).resolve() if not cand.is_absolute() else cand.resolve()
    if not str(target).startswith(str(root)) and not str(target).startswith(str(up_root)):
        return JSONResponse(_err("路径越界，仅允许 output/ 与 uploads 目录"), status_code=403)
    if not target.is_file():
        return JSONResponse(_err("文件不存在"), status_code=404)
    item = {"name": target.name, "path": str(target), "size": target.stat().st_size}
    return _ok(attachment=item)


# ============================================================================
# 工作区文件浏览器（G4）：受限目录浏览 + 编辑 + 附件化
#   安全模型：仅允许浏览「已授权根目录」(config.yaml: workspace.roots 合并默认根)，
#   默认含应用目录与用户主目录及常见用户目录；任意路径必须严格落在某根之内，
#   否则一律 403，杜绝目录穿越。所有写操作（写/建/改名/删）同样受根约束。
# ============================================================================
_WS_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
                 ".hermes_data", ".workbuddy", ".idea", ".vscode", ".tox"}


def _ws_default_roots() -> list[dict]:
    """默认授权根：应用目录 + 用户主目录；常见用户目录存在才列。"""
    home = Path.home()
    roots = [
        {"label": "应用目录", "path": str(Path(__file__).resolve().parent)},
        {"label": "我的主目录", "path": str(home)},
    ]
    for label, sub in (("桌面", "Desktop"), ("文档", "Documents"),
                       ("下载", "Downloads"), ("图片", "Pictures")):
        p = home / sub
        if p.is_dir():
            roots.append({"label": label, "path": str(p)})
    return roots


def _ws_roots() -> list[dict]:
    """合并默认根 + 用户在 config.yaml 自定义的根（按路径去重）。
    custom=True 表示用户自定义（可移除），默认根 custom=False（不可移除）。"""
    cfg = hc.read_config_yaml(hc.get_hermes_home())
    custom = (cfg.get("workspace", {}) or {}).get("roots", []) or []
    custom_paths = {str(r.get("path", "")).rstrip(os.sep) for r in custom}
    merged, seen = [], set()
    for r in _ws_default_roots() + list(custom):
        p = str(r.get("path") or "").rstrip(os.sep)
        if not p or p in seen:
            continue
        seen.add(p)
        merged.append({"label": r.get("label") or (Path(p).name or p),
                       "path": p, "custom": p in custom_paths})
    return merged


def _ws_resolve(root_path: str, rel: str) -> tuple[Path, str]:
    """把（已授权）根路径 + 相对路径解析为绝对落盘路径；隔离穿越。
    返回 (abs_path, rel_clean)；根不在授权列表或越界则抛 ValueError。
    算法：先 normpath 规范化用户输入，再用 os.path.commonpath 检查前缀，
    确保任何符号链接解析后仍落在授权根内。"""
    roots = _ws_roots()
    # 根路径匹配：先 normpath 标准化
    root_norm = os.path.normpath(str(root_path))
    match = next((r["path"] for r in roots
                  if os.path.normpath(r["path"]) == root_norm), None)
    if not match:
        raise ValueError("根目录不在授权列表中")
    base = Path(match).resolve()
    # 相对路径：用 normpath 规范化，然后检查是否试图跳出
    rel_norm = os.path.normpath(str(rel).replace("\\", "/")) if rel else ""
    if not rel_norm or rel_norm == ".":
        return base, ""
    # 用 commonpath 检查越界：拼接后的路径必须落在 base 内
    cand = Path(os.path.normpath(str(base) + os.sep + rel_norm)).resolve()
    if os.path.commonpath([str(cand), str(base)]) != str(base):
        raise ValueError("路径越界（试图跳出授权根）")
    # 相对路径保持干净（去掉前导 ./ 等）
    rel_clean = os.path.relpath(str(cand), str(base)).replace("\\", "/")
    return cand, rel_clean


@app.get("/api/workspace/roots")
async def api_ws_roots():
    """返回当前授权根列表（含默认与自定义）。"""
    return _ok(roots=_ws_roots())


@app.post("/api/workspace/roots")
async def api_ws_add_root(req):
    """把一个真实目录加入授权根（持久化到 config.yaml: workspace.roots）。"""
    body = await req.json()
    raw = (body.get("path") or "").strip()
    label = (body.get("label") or "").strip()
    if not raw:
        return _err("缺少 path")
    p = Path(raw).expanduser()
    if not p.is_absolute():
        return _err("请使用绝对路径")
    if not p.is_dir():
        return _err("路径不存在或不是目录")
    p = str(p.resolve())
    cfg = hc.read_config_yaml(hc.get_hermes_home())
    ws = cfg.get("workspace", {}) or {}
    existing = list(ws.get("roots", []) or [])
    if any(str(r.get("path", "")).rstrip(os.sep) == p for r in existing):
        return _err("该目录已在授权列表中")
    existing.append({"label": label or p, "path": p})
    hc.update_config_yaml(hc.get_hermes_home(), {"workspace": {"roots": existing}})
    return _ok(roots=_ws_roots())


@app.delete("/api/workspace/roots")
async def api_ws_del_root(req):
    """从授权根移除一个自定义目录（默认根不可移除）。path 支持 query 或 body。"""
    raw = (req.query_params.get("path") or "").strip()
    try:
        body = await req.json()
        raw = (body.get("path") or raw).strip()
    except Exception:
        pass
    raw = raw.rstrip(os.sep)
    if not raw:
        return _err("缺少 path")
    cfg = hc.read_config_yaml(hc.get_hermes_home())
    ws = cfg.get("workspace", {}) or {}
    existing = [r for r in (ws.get("roots", []) or [])
                if str(r.get("path", "")).rstrip(os.sep) != raw]
    ws["roots"] = existing
    hc.update_config_yaml(hc.get_hermes_home(), {"workspace": ws})
    return _ok(roots=_ws_roots())


@app.get("/api/workspace/list")
async def api_ws_list(root: str, path: str = "", sort_by: str = "name"):
    """列出某授权根下某相对目录的条目。
    sort_by: name(默认)|size|time，按名称/大小/修改时间排序，目录始终排在文件前。"""
    try:
        abs_p, rel = _ws_resolve(root, path)
    except ValueError as e:
        return JSONResponse(_err(str(e)), status_code=403)
    if not abs_p.is_dir():
        return JSONResponse(_err("目录不存在"), status_code=404)
    try:
        with os.scandir(abs_p) as it:
            items = list(it)
            _sort_key = {"name": lambda e: (not e.is_dir(), e.name.lower()),
                          "size": lambda e: (not e.is_dir(), -(e.stat().st_size if e.stat() else 0)),
                          "time": lambda e: (not e.is_dir(), -(e.stat().st_mtime if e.stat() else 0))}
            items.sort(key=_sort_key.get(sort_by, _sort_key["name"]))
    except PermissionError:
        return JSONResponse(_err("无权限读取该目录"), status_code=403)
    entries = []
    for e in items:
        if e.is_dir() and e.name in _WS_SKIP_DIRS:
            continue
        try:
            st = e.stat()
        except Exception:
            st = None
        is_dir = e.is_dir()
        ext = (Path(e.name).suffix or "").lower()
        entry = {
            "name": e.name + ("/" if is_dir else ""),
            "is_dir": is_dir,
            "size": st.st_size if st else None,
            "mtime": st.st_mtime if st else None,
            "is_text": (not is_dir) and (ext in _TEXT_ATTACH_EXT),
            "rel": (rel + "/" + e.name) if rel else e.name,
        }
        if is_dir:
            # Git 检测：目录自身是否为 git 仓库根（廉价 exists 判断）
            entry["is_git"] = os.path.isdir(os.path.join(abs_p, e.name, ".git"))
        entries.append(entry)
    return _ok(path=rel, root=root, entries=entries)


@app.get("/api/workspace/read")
async def api_ws_read(root: str, path: str = ""):
    """读取文本文件内容（>2MB 标 too_large；二进制标 binary）。"""
    try:
        abs_p, rel = _ws_resolve(root, path)
    except ValueError as e:
        return JSONResponse(_err(str(e)), status_code=403)
    if not abs_p.is_file():
        return JSONResponse(_err("文件不存在"), status_code=404)
    # 防御纵深：凭据/敏感文件读阻断（.env / Hermes 凭据库等）
    _rb = _file_safety_read_block(abs_p)
    if _rb:
        return JSONResponse(_err(_rb), status_code=403)
    try:
        size = abs_p.stat().st_size
    except Exception:
        size = None
    if size is not None and size > 2_000_000:
        return _ok(path=rel, is_text=False, too_large=True, size=size)
    try:
        data = abs_p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return _ok(path=rel, is_text=False, binary=True, size=size)
    if len(data) > 500_000:
        data = data[:500_000] + "\n…(已截断，文件过大)"
    return _ok(path=rel, is_text=True, content=data, size=size)


@app.post("/api/workspace/write")
async def api_ws_write(req):
    """写入文本文件（创建/覆盖），路径受根约束。"""
    body = await req.json()
    try:
        abs_p, rel = _ws_resolve(body.get("root", ""), body.get("path", ""))
    except ValueError as e:
        return JSONResponse(_err(str(e)), status_code=403)
    if abs_p.is_dir():
        return _err("目标已是目录")
    # 防御纵深：受保护系统/凭据文件写阻断（OS 主目录 .ssh/.aws/.kube 等）
    _wd = _file_safety_write_denied(abs_p)
    if _wd:
        return JSONResponse(_err(_wd), status_code=403)
    try:
        abs_p.parent.mkdir(parents=True, exist_ok=True)
        abs_p.write_text(body.get("content", "") or "", encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"写入失败：{e}"), status_code=500)
    return _ok(path=rel, size=abs_p.stat().st_size)


@app.post("/api/workspace/mkdir")
async def api_ws_mkdir(req):
    """新建目录（路径受根约束）。"""
    body = await req.json()
    try:
        abs_p, rel = _ws_resolve(body.get("root", ""), body.get("path", ""))
    except ValueError as e:
        return JSONResponse(_err(str(e)), status_code=403)
    if abs_p.exists():
        return _err("已存在")
    try:
        abs_p.mkdir(parents=True, exist_ok=True)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"创建失败：{e}"), status_code=500)
    return _ok(path=rel)


@app.post("/api/workspace/rename")
async def api_ws_rename(req):
    """重命名/移动（仅在同根内），路径受根约束。"""
    body = await req.json()
    try:
        a_src, rel_src = _ws_resolve(body.get("root", ""), body.get("src", ""))
        a_dst, rel_dst = _ws_resolve(body.get("root", ""), body.get("dst", ""))
    except ValueError as e:
        return JSONResponse(_err(str(e)), status_code=403)
    if not a_src.exists():
        return _err("源不存在")
    if a_dst.exists():
        return _err("目标已存在")
    try:
        a_dst.parent.mkdir(parents=True, exist_ok=True)
        a_src.rename(a_dst)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"重命名失败：{e}"), status_code=500)
    return _ok(src=rel_src, dst=rel_dst)


@app.post("/api/workspace/delete")
async def api_ws_delete(req):
    """删除文件或目录（递归），根目录本身不可删，路径受根约束。"""
    body = await req.json()
    try:
        abs_p, rel = _ws_resolve(body.get("root", ""), body.get("path", ""))
    except ValueError as e:
        return JSONResponse(_err(str(e)), status_code=403)
    if abs_p == Path(body.get("root", "")).resolve():
        return _err("不能删除根目录本身")
    if not abs_p.exists():
        return _err("不存在")
    try:
        if abs_p.is_dir():
            shutil.rmtree(abs_p)
        else:
            abs_p.unlink()
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"删除失败：{e}"), status_code=500)
    return _ok(path=rel)


@app.get("/api/workspace/download")
async def api_ws_download(root: str, path: str = ""):
    """下载文件（二进制安全），路径受根约束。"""
    try:
        abs_p, rel = _ws_resolve(root, path)
    except ValueError as e:
        return JSONResponse(_err(str(e)), status_code=403)
    if not abs_p.is_file():
        return JSONResponse(_err("文件不存在"), status_code=404)
    # 防御纵深：凭据文件禁止下载
    _rb = _file_safety_read_block(abs_p)
    if _rb:
        return JSONResponse(_err(_rb), status_code=403)
    return FileResponse(str(abs_p), filename=abs_p.name)


@app.post("/api/workspace/attach")
async def api_ws_attach(req):
    """把工作区文件复制进 HERMES_HOME/uploads 并登记为对话附件（复用注入逻辑）。"""
    body = await req.json()
    try:
        abs_p, rel = _ws_resolve(body.get("root", ""), body.get("path", ""))
    except ValueError as e:
        return JSONResponse(_err(str(e)), status_code=403)
    if not abs_p.is_file():
        return _err("文件不存在")
    # 防御纵深：凭据文件禁止作为附件注入上下文
    _rb = _file_safety_read_block(abs_p)
    if _rb:
        return JSONResponse(_err("该文件受保护，禁止附加：" + _rb), status_code=403)
    up_root = (Path(hc.get_hermes_home()) / "uploads").resolve()
    up_root.mkdir(parents=True, exist_ok=True)
    name, target = _resolve_upload_target(up_root, abs_p.name, rel)
    try:
        target.write_bytes(abs_p.read_bytes())
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"附加失败：{e}"), status_code=500)
    return _ok(attachment={"name": name, "path": str(target),
                           "size": target.stat().st_size})


# ============================================================================
# 会话固定文件夹上下文（G6）：把工作区内某文件夹绑定到单个会话，作为长期背景
#   每轮对话自动注入该文件夹（受限递归）的文本；路径必须经 _ws_resolve 校验落在
#   授权根内，杜绝目录穿越。与「工作区授权根」复用同一套安全边界。
# ============================================================================
@app.get("/api/context-folder")
def api_ctx_folder_get(conv_id: str = ""):
    """返回某会话当前绑定的固定文件夹及读取统计（文件数/字符数/是否截断）。"""
    if not conv_id:
        return _err("缺少 conv_id")
    cf = sessions.get_context_folder(conv_id)
    if not cf:
        return _ok(context_folder=None, stats={"files": 0, "chars": 0, "truncated": False})
    r = _read_context_folder(cf["root"], cf["rel"])
    return _ok(context_folder=cf, stats={"files": r["files"], "chars": r["chars"],
                                         "truncated": r["truncated"], "error": r["error"]})


@app.post("/api/context-folder")
async def api_ctx_folder_post(req):
    """绑定某文件夹为会话固定上下文。root 必须落在授权根内（防穿越/未授权）。"""
    body = await req.json()
    cid = (body.get("conv_id") or "").strip()
    if sessions.get(cid) is None:
        cid = sessions.ensure(None)
    root = (body.get("root") or "").strip()
    rel = (body.get("rel") or "").strip()
    if not root:
        return _err("缺少 root")
    try:
        abs_base, rel_clean = _ws_resolve(root, rel)
    except ValueError as e:
        return JSONResponse(_err(str(e)), status_code=403)
    if not abs_base.is_dir():
        return JSONResponse(_err("目录不存在"), status_code=404)
    value = {"root": root, "rel": rel_clean, "display": str(abs_base)}
    r = sessions.set_context_folder(cid, value)
    if not r.get("ok"):
        return JSONResponse(r, status_code=400)
    rr = _read_context_folder(root, rel_clean)
    return _ok(context_folder=value, stats={"files": rr["files"], "chars": rr["chars"],
                                            "truncated": rr["truncated"], "error": rr["error"]})


@app.delete("/api/context-folder")
async def api_ctx_folder_del(req):
    """解绑某会话的固定文件夹上下文。conv_id 支持 query 或 body。"""
    raw = (req.query_params.get("conv_id") or "").strip()
    try:
        body = await req.json()
        raw = (body.get("conv_id") or raw).strip()
    except Exception:
        pass
    if not raw:
        return _err("缺少 conv_id")
    r = sessions.set_context_folder(raw, None)
    if not r.get("ok"):
        return JSONResponse(r, status_code=400)
    return _ok(context_folder=None)


# ============================================================================
# 上下文 / 压缩（对齐官方 tips 文档：token 跟踪 + 主动压缩端点）
#   说明：token 用量来自会话 usage（sessions.usage_input/output）；若某会话从未被
#   写入 usage，则 usage_percent=0、should_compress=False（仍返回有效状态，不报错）。
# ===========================================================================
@app.get("/api/context/status")
def api_ctx_status(conv_id: str = ""):
    """实时上下文水位：active_engine / context_window / threshold_tokens /
    usage_percent / should_compress / compression_count / session_tokens。"""
    import context_provider as cp
    try:
        return _ok(**cp.get_context_status(cid=conv_id))
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"获取上下文状态失败：{e}"), status_code=500)


@app.get("/api/context/engines")
def api_ctx_engines():
    """列出可用上下文压缩引擎 + 当前启用。"""
    import context_provider as cp
    try:
        return _ok(**cp.list_engines())
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"获取引擎列表失败：{e}"), status_code=500)


@app.post("/api/context/engine")
async def api_ctx_engine(req):
    """切换 context.engine（写 config.yaml: context.engine）。"""
    import context_provider as cp
    try:
        body = await req.json()
    except Exception:
        body = {}
    engine_id = (body.get("engine_id") or "").strip()
    if not engine_id:
        return _err("缺少 engine_id")
    try:
        r = cp.switch_engine(engine_id)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"切换失败：{e}"), status_code=500)
    if not r.get("ok"):
        return JSONResponse(_err(r.get("error") or "切换失败"), status_code=400)
    return _ok(**r)


@app.post("/api/context/compress")
async def api_ctx_compress(req):
    """对指定会话历史主动跑 ContextCompressor 压缩（tips: /compress 的进程内等价）。
    保真校验：压缩后不得丢失 user 消息，否则拒绝覆盖（避免丢历史）；未实际压缩
    （消息数不足/已最简）则不写回，仅报告原因。"""
    try:
        body = await req.json()
    except Exception:
        body = {}
    cid = (body.get("conv_id") or "").strip()
    if not cid:
        return _err("缺少 conv_id")
    if sessions.get(cid) is None:
        return JSONResponse(_err("会话不存在"), status_code=404)
    msgs = sessions.get_messages(cid)
    if not msgs:
        return _ok(conv_id=cid, compressed=False, reason="空会话无需压缩",
                   original_count=0, compressed_count=0)
    try:
        from agent.context_compressor import ContextCompressor
        model = (hc.get_active_model_cfg() or {}).get("model") or "compressor"
        comp = ContextCompressor(model)
        compressed = comp.compress(msgs, current_tokens=None, force=True)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"压缩失败：{type(e).__name__}: {e}"), status_code=500)
    if not isinstance(compressed, list) or not compressed:
        return _ok(conv_id=cid, compressed=False, reason="引擎未返回有效压缩结果",
                   original_count=len(msgs), compressed_count=len(msgs))
    # 保真校验：原始含 user 消息则压缩后也必须含，否则拒绝覆盖
    orig_users = sum(1 for m in msgs if isinstance(m, dict) and m.get("role") == "user")
    new_users = sum(1 for m in compressed if isinstance(m, dict) and m.get("role") == "user")
    if orig_users and new_users < orig_users:
        return JSONResponse(_err("压缩后用户消息丢失，已拒绝覆盖（保真校验失败）"), status_code=422)
    if len(compressed) >= len(msgs):
        # 未实际压缩（消息数不足或已最简），不覆盖写回
        return _ok(conv_id=cid, compressed=False,
                   reason=("已最简，无需压缩" if len(compressed) == len(msgs)
                           else "压缩后未减少"),
                   original_count=len(msgs), compressed_count=len(compressed))
    try:
        sessions.set_messages(cid, compressed)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"写回压缩结果失败：{e}"), status_code=500)
    return _ok(conv_id=cid, compressed=True,
               original_count=len(msgs), compressed_count=len(compressed))


@app.post("/api/chat")
async def api_chat(req):
    """一轮对话：读会话历史 → 跑 Agent → SSE 流式回吐 → done 时落盘。"""
    body = await req.json()
    text = (body.get("text") or "").strip()
    cid = sessions.ensure(body.get("conv_id"))
    # ① 保存原始提问（不含上下文注入块），落盘历史只存纯提问
    text_original = text
    # 构建上下文块（只本轮注入，不写进历史）
    context_parts = []
    # G6：会话固定文件夹上下文——绑定目录递归注入为长期背景（先于附件，作为背景）
    ctx_folder = sessions.get_context_folder(cid)
    if ctx_folder:
        try:
            cf_text = _read_context_folder_text(ctx_folder["root"], ctx_folder["rel"])
        except Exception as e:  # noqa: BLE001
            cf_text = f"（固定文件夹读取失败：{e}）"
        if cf_text:
            label = ctx_folder.get("display") or ctx_folder.get("rel") or ctx_folder.get("root") or "固定文件夹"
            context_parts.append(f"[会话固定文件夹上下文：{label}]\n{cf_text}")
    attachments = body.get("attachments") or []
    if attachments:
        extra = _read_attachments_text(attachments)
        context_parts.append(f"[附件内容]\n{extra}")
        # 多模态：图片附件经 vision_analyze 工具交给模型查看。
        # 约束背景：本应用走 Library 的 run_conversation(user_message: str)，该接口只接受
        # 字符串（见 references/01-library-api.md:263-277），无法以像素内容块直传图片；
        # 因此图片以本地绝对路径登记，并显式引导模型调用 vision_analyze——该工具对视觉模型
        # 返回原生像素、对纯文本模型降级为辅助视觉模型的描述（hermes-llms-full.txt 视觉章节）。
        # 仅在有图片附件时追加此指令，避免污染纯文本对话。
        _img_paths = [ (a.get("path") or a.get("name")) for a in attachments
                       if _is_image_attachment(a) ]
        if _img_paths:
            _hint = ("[多模态图片] 用户附上了 %d 张图片，本地绝对路径：%s。"
                     "请调用 vision_analyze 工具逐一查看这些图片，再结合图片内容回答用户的问题。"
                     % (len(_img_paths), "、".join(_img_paths)))
            context_parts.append(_hint)
    skill_id = body.get("skill_id") or None
    if skill_id:
        sk = hc.read_skill(skill_id)
        if sk and (sk.get("body") or "").strip():
            context_parts.append(f"[已启用技能：{skill_id}]\n{sk['body']}")
    if not text_original and not context_parts:
        return JSONResponse(_err("消息为空"), status_code=400)

    model_id = body.get("model_id") or None
    deep_think = bool(body.get("deep_think"))
    web_search = body.get("web_search")
    web_search = True if web_search is None else bool(web_search)

    try:
        model_cfg = hc.get_active_model_cfg(model_id)
    except Exception as e:  # noqa: BLE001
        return JSONResponse(_err(f"读取模型配置失败：{e}"), status_code=500)

    history = sessions.get_messages(cid)

    # B1：重生成 / 编辑语义——丢弃「第 replace_index 条 user 消息」及其之后的全部历史，
    # 再追加本轮 user。等价于「从所选用户消息起重跑」，对工具消息也安全（按 user 边界切割，
    # 不会留下孤立的 tool 消息）；队首 system 设定永不丢弃。
    ri = body.get("replace_index")
    if ri is not None:
        try:
            ri = int(ri)
        except (TypeError, ValueError):
            ri = None
    if ri is not None and ri >= 0:
        user_positions = [i for i, m in enumerate(history)
                          if isinstance(m, dict) and m.get("role") == "user"]
        if ri < len(user_positions):
            cut = user_positions[ri]
            if history and history[0].get("role") == "system" and cut == 0:
                cut = 1  # 不丢 system 设定
            history = history[:cut]
            sessions.set_messages(cid, history)
        # else：找不到目标 user，兜底保持原 history 不变

    # ① 落盘只存纯提问（不包含固定文件夹/附件/技能正文）
    sessions.append(cid, "user", text_original, title_hint=text_original, attachments=attachments)
    # ① 构造发给模型的消息：纯提问，上下文块注入到 system 消息（只本轮注入，不写进历史）
    messages = history + [{"role": "user", "content": text_original}]
    if context_parts:
        ctx_block = "\n\n".join(context_parts)
        if messages and messages[0].get("role") == "system":
            messages[0] = {"role": "system", "content": messages[0]["content"] + "\n\n" + ctx_block}
        else:
            messages.insert(0, {"role": "system", "content": "以下为本次对话的上下文背景信息：\n\n" + ctx_block})
    # 原生上下文文件发现目录：会话绑定文件夹优先（让 Hermes 原生发现扫用户项目），
    # 无绑定则不设（build_agent 回退到启动目录）。与下方自定义「固定文件夹上下文」
    # （整目录文本注入）是两件互补的事：前者走原生 .hermes.md/AGENTS.md/SOUL.md 发现+安全扫描。
    _ctx_cwd = None
    if ctx_folder and (ctx_folder.get("root") or "").strip() and os.path.isdir(ctx_folder["root"]):
        _ctx_cwd = ctx_folder["root"]
    cancel = _cancel_event(cid)

    def wrapped() -> Iterator[bytes]:
        # 先告诉前端本轮归属哪个会话（新建会话时前端据此对齐 conv_id）
        yield ("data: " + json.dumps(
            {"type": "meta", "conv_id": cid,
             "model": model_cfg.get("model"),
             "vendor": model_cfg.get("vendor")}, ensure_ascii=False) + "\n\n").encode()
        final_payload: dict | None = None
        try:
            for chunk in ar.stream_agent_chat(
                messages, model_cfg,
                max_iterations=hc.get_loop_max_iterations(),
                approval_check=ar.extract_approval,
                deep_think=deep_think, web_search=web_search,
                working_dir=_ctx_cwd,
                cancel_event=cancel,
            ):
                if cancel.is_set():
                    yield ("data: " + json.dumps(
                        {"type": "cancelled"}, ensure_ascii=False) + "\n\n").encode()
                    break
                # 嗅探 done 事件以便落盘 + 补一份渲染好的 HTML
                if chunk.startswith(b"data: "):
                    try:
                        obj = json.loads(chunk[6:].decode("utf-8").strip())
                    except Exception:
                        obj = None
                    if isinstance(obj, dict) and obj.get("type") == "done":
                        final_payload = obj
                        continue                      # 换成下面加料后的版本再发
                yield chunk
        except Exception as e:  # noqa: BLE001
            yield ("data: " + json.dumps(
                {"error": {"message": f"{type(e).__name__}: {e}"}},
                ensure_ascii=False) + "\n\n").encode()

        if final_payload is not None and not cancel.is_set():
            final_text = final_payload.get("final") or ""
            msgs = final_payload.get("messages")
            if isinstance(msgs, list) and msgs:
                # B2：防御性校验——仅当 agent 回传的 messages 确实包含本轮刚发的 user
                # 消息时才整体覆盖；否则某些 provider/路径只回传 assistant 增量，整体
                # 覆盖会丢失此前全部历史。不符时改为「本地已追加历史 + 新 assistant」合并。
                # ① 用 text_original（纯提问）匹配 Agent 回传的用户消息
                last_user_ok = any(
                    m.get("role") == "user" and (m.get("content") or "") == text_original
                    for m in msgs[-4:]
                )
                # ④ 额外完整性校验：仅当回传 messages 含 system 或达到预期长度才整体覆盖
                if last_user_ok:
                    has_system = any(m.get("role") == "system" for m in msgs[:2])
                    if not has_system and len(msgs) < 3:
                        last_user_ok = False
                    # 附件元数据不来自 Agent 回传，需在整体覆盖前回填到本轮用户消息，
                    # 否则刚落盘的附件会在此被冲掉（导致重开会话芯片丢失）。
                    if attachments:
                        for _m in reversed(msgs):
                            if _m.get("role") == "user" and (_m.get("content") or "") == text_original:
                                _m["attachments"] = attachments
                                break
                    sessions.set_messages(cid, msgs, title_hint=text_original)
                else:
                    sessions.append(cid, "assistant", final_text)
            else:
                # 某些路径不回 messages：自己补一条 assistant，保住多轮上下文
                sessions.append(cid, "assistant", final_text)
            out = {
                "type": "done", "conv_id": cid,
                "final": _safe_redact(final_text),
                "html": render_markdown(_safe_redact(final_text)),
                "approval": ar.extract_approval(final_text),
                "title": sessions.summary(cid)["title"],
                "changed_files": (final_payload or {}).get("changed_files") or [],
            }
            # Goals：若本会话有常驻目标，每轮完成后跑裁判循环（透明可控——
            # 仅返回判定结果，是否「继续目标」由用户在前端点「继续目标」显式驱动，
            # 绝不自动连跑）。任何异常都隔离，绝不影响对话落盘与前端渲染。
            try:
                goal_eval = hf.goals_evaluate(cid, final_text)
                if isinstance(goal_eval, dict):
                    out["goal"] = goal_eval
            except Exception:  # noqa: BLE001
                pass
            yield ("data: " + json.dumps(out, ensure_ascii=False) + "\n\n").encode()

    return StreamingResponse(
        wrapped(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat/stop")
async def api_chat_stop(req):
    body = await req.json()
    cid = body.get("conv_id") or ""
    with _CANCEL_LOCK:
        ev = _CANCEL.get(cid)
    if ev:
        ev.set()
    return _ok(conv_id=cid, stopped=bool(ev))


# ---------------------------------------------------------------------------
# 会话管理
# ---------------------------------------------------------------------------
@app.get("/api/conversations")
def api_convs(q: str = "", include_archived: str = "true"):
    inc = str(include_archived).lower() != "false"
    return _ok(items=sessions.list_sessions(include_archived=inc, q=q))


@app.get("/api/conversations/search")
def api_convs_search(q: str = ""):
    """A2：跨会话对消息正文做全文检索（对标 hermes-studio Ctrl+K）。"""
    return _ok(items=sessions.search_messages(q))

# ---------------------------------------------------------------------------
# 统一搜索入口（A6：跨所有内容源搜索）
# ---------------------------------------------------------------------------
@app.get("/api/search/all")
def api_search_all(q: str = ""):
    """跨所有内容源搜索：会话 + Wiki + 记忆 + 看板 + 定时任务。"""
    if not q:
        return _ok(sources={})
    results = {}
    # 搜索会话
    try:
        convs = sessions.search_messages(q)
        results["conversations"] = convs[:10]
    except Exception:
        results["conversations"] = []
    # 搜索 Wiki
    try:
        we = wiki_engine
        wiki_items = we.search(q) if we else []
        results["wiki"] = wiki_items[:10]
    except Exception:
        results["wiki"] = []
    # 搜索记忆
    try:
        import memory as _mem
        mem_items = []
        for f in (_mem.list() or []):
            if q.lower() in (f.get("text") or "").lower() or q.lower() in (f.get("name") or "").lower():
                mem_items.append({"name": f.get("name"), "snippet": (f.get("text") or "")[:200]})
        results["memory"] = mem_items[:10]
    except Exception:
        results["memory"] = []
    # 搜索看板
    try:
        import kanban as _kb
        kb_items = _kb.search(q) if hasattr(_kb, "search") else []
        results["kanban"] = kb_items[:10]
    except Exception:
        results["kanban"] = []
    # 搜索定时任务
    try:
        import cron as _cron
        cron_items = []
        for j in (_cron.list() or []):
            if q.lower() in (j.get("name") or "").lower() or q.lower() in (j.get("prompt") or "").lower():
                cron_items.append({"name": j.get("name"), "schedule": j.get("schedule"), "snippet": (j.get("prompt") or "")[:200]})
        results["cron"] = cron_items[:10]
    except Exception:
        results["cron"] = []
    return _ok(sources=results)


# ---------------------------------------------------------------------------
# 文件内联预览（A4：安全读取 + 沙箱化渲染，依赖 A1 净化）
# ---------------------------------------------------------------------------
@app.get("/api/file/preview")
def api_file_preview(path: str = ""):
    import file_preview as _fp
    return _fp.preview_file(path)


@app.post("/api/conversations")
async def api_conv_new(req):
    try:
        body = await req.json()
    except Exception:
        body = {}
    return _ok(item=sessions.create(body.get("title") or ""))


@app.get("/api/conversations/{cid}")
def api_conv_get(cid: str):
    s = sessions.get(cid)
    if not s:
        return JSONResponse(_err("会话不存在"), status_code=404)
    items = []
    for m in s.get("messages") or []:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue                                   # system/tool 不进气泡流
        txt = _msg_text(m.get("content"))
        if not txt.strip():
            continue
        items.append({"role": role, "text": txt,
                      "html": render_markdown(txt) if role == "assistant" else "",
                      "attachments": m.get("attachments") or []})
    return _ok(id=cid, title=s.get("title"), messages=items,
               pinned=bool(s.get("pinned")), archived=bool(s.get("archived")),
               tags=list(s.get("tags") or []), group=s.get("group") or "",
               context_folder=s.get("context_folder"))


@app.post("/api/conversations/{cid}/rename")
async def api_conv_rename(cid: str, req):
    body = await req.json()
    return sessions.rename(cid, body.get("title") or "")


@app.post("/api/conversations/{cid}/pin")
async def api_conv_pin(cid: str, req):
    body = await req.json()
    return sessions.set_pinned(cid, bool(body.get("pinned")))


@app.post("/api/conversations/{cid}/copy")
async def api_conv_copy(cid: str):
    return sessions.copy(cid)


@app.post("/api/conversations/{cid}/archive")
async def api_conv_archive(cid: str, req):
    body = await req.json()
    return sessions.archive(cid, bool(body.get("archived")))


@app.post("/api/conversations/{cid}/tags")
async def api_conv_tags(cid: str, req):
    body = await req.json()
    return sessions.set_tags(cid, body.get("tags") or [])


@app.post("/api/conversations/{cid}/group")
async def api_conv_group(cid: str, req):
    body = await req.json()
    return sessions.set_group(cid, body.get("group") or "")


@app.get("/api/conversations/{cid}/export")
def api_conv_export(cid: str, fmt: str = "json"):
    return sessions.export_session(cid, fmt)


@app.post("/api/conversations/import")
async def api_conv_import(req):
    body = await req.json()
    return sessions.import_session(body.get("payload") or body)


@app.delete("/api/conversations/{cid}")
def api_conv_del(cid: str):
    return sessions.delete(cid)


@app.post("/api/conversations/batch-delete")
async def api_conv_batch_delete(req):
    """批量删除会话：接收 {ids:[...]}，一次事务内删除多个会话及其消息。"""
    body = await req.json()
    ids = body.get("ids") or []
    if not isinstance(ids, list) or not ids:
        return {"ok": False, "error": "ids 须为非空数组"}
    return sessions.delete_many(ids)


# ---------------------------------------------------------------------------
# 用量分析（对标 hermes-studio「Usage Analytics」）
