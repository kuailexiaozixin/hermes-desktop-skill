"""file_tools.py — 纯 Python 文件工具（覆盖 Hermes 内置 `file` 工具集，零 subprocess）

为什么需要它
============
Hermes 内置的 ``file`` 工具集与 ``terminal`` 工具集在多数平台上依赖外部 shell
（Windows 上需要 Git Bash / PortableGit）。桌面端要做到「解压即用、无外部依赖」，
就必须：

1. ``disabled_toolsets=["terminal"]`` 彻底禁用 spawn-per-call 的终端工具；
2. 用 ``registry.register(..., toolset="file", override=True)`` 以**纯 Python**
   handler 覆盖内置 ``read_file`` / ``write_file`` / ``patch`` / ``search_files``；
3. 新增 ``list_dir``（替代不存在的 ``ls`` / ``dir``）与 ``run_python``
   （进程内执行 Python，替代 terminal + code_execution 子进程）。

这样 Agent 依然拥有完整的「读 / 写 / 改 / 搜 / 列 / 跑」能力，但整条链路都在
当前进程内完成——冻结成单文件 EXE 后仍然可用。

路径解析铁律
============
``_expand()`` 是所有工具的统一入口：

- **绝对路径原样遵从**。早期实现曾把绝对路径「只取文件名拼到项目根」，导致用户
  给的真实路径被改写成项目内不存在的路径而报「path not found」，无法读取项目外
  的文件。此处直接 ``resolve()``。
- **相对路径统一相对「项目根」解析**（frozen = EXE 同目录），不依赖进程 cwd，
  保证 ``output/xxx.html`` 始终落到产物目录，而不随工作目录漂移。

注意：本模块**不能**命名为 ``tools.py`` 或放进名为 ``tools/`` 的包，
``tools`` 是 hermes-agent 的顶层包名，会被遮蔽。
"""
from __future__ import annotations

import contextlib
import fnmatch
import io
import json
import os
import re
import threading
import traceback
from pathlib import Path
from typing import Any, Iterator

try:
    from hermes_config import project_root as _project_root
except Exception:  # pragma: no cover - 离线/测试兜底
    def _project_root() -> Path:  # type: ignore[misc]
        import sys
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).resolve().parent

# 单个工具返回给模型的最大字符数（超出后截断并给出分页指针）
MAX_TOOL_OUTPUT = 100_000


# ---------------------------------------------------------------------------
# 编辑追踪：根除「AI 声称改成功，界面却没变」的假成功
# ---------------------------------------------------------------------------
# 进程内 Agent 每轮对话通过 write_file / patch 改动文件。记录这些路径，供
# ``stream_agent_chat`` 在 ``done`` 事件回传给前端：静态文件自动重载、服务端
# 文件提示重启。没有这层闭环，Agent 只能看到工具返回的 ``{"ok": true}``，于是对
# 「改了 pages.py 但服务端不重载」「改了 chat.js 但没人刷新」无从知晓，便报告成功。
# 以线程 id 为键：Agent 在 worker 线程内进程内调用这些 handler，主生成器线程
# 通过 worker 线程 id 读回，互不串台；多会话并发也各自独立。
_EDITS: dict[int, list] = {}
_EDITS_LOCK = threading.Lock()


def reset_edited_files() -> None:
    """在 worker 线程开头调用，清空本线程的编辑记录。"""
    tid = threading.current_thread().ident
    with _EDITS_LOCK:
        _EDITS[tid] = []


def record_edit(path) -> None:
    """记录一次成功写盘，供本轮结束后回传前端。"""
    tid = threading.current_thread().ident
    with _EDITS_LOCK:
        lst = _EDITS.setdefault(tid, [])
        p = str(path)
        if p not in lst:
            lst.append(p)


def get_edited_files() -> list:
    """worker 线程内读取本轮被改动的文件路径列表。"""
    tid = threading.current_thread().ident
    with _EDITS_LOCK:
        return list(_EDITS.get(tid, []))


def clear_edited_files() -> None:
    tid = threading.current_thread().ident
    with _EDITS_LOCK:
        _EDITS.pop(tid, None)


# ---------------------------------------------------------------------------
# tool_result / tool_error：优先用 Hermes 原生实现，未安装时本地兜底
# ---------------------------------------------------------------------------
# 原生实现在 `tools.registry`（hermes-agent 顶层包）。做本地兜底的意义：本模块
# 可在**未安装 hermes-agent** 的环境被直接调用与单测（离线门禁 / CI），返回的
# JSON 形状与原生一致（ok=True/False + 字段）。
_TR: Any = None
_TE: Any = None


def _local_tool_result(**kw) -> str:
    payload = dict(kw)
    payload.setdefault("ok", True)
    return json.dumps(payload, ensure_ascii=False, default=str)


def _local_tool_error(message: str, **kw) -> str:
    payload = {"ok": False, "error": message}
    payload.update(kw)
    return json.dumps(payload, ensure_ascii=False, default=str)


def _rt():
    global _TR, _TE
    if _TR is None or _TE is None:
        try:
            from tools.registry import tool_error as _te, tool_result as _tr
            _TR, _TE = _tr, _te
        except Exception:  # pragma: no cover - 离线兜底
            _TR, _TE = _local_tool_result, _local_tool_error
    return _TR, _TE


def tool_result(**kw) -> str:
    return _rt()[0](**kw)


def tool_error(message: str, **kw) -> str:
    return _tool_error_wrapped(message, **kw)


def _tool_error_wrapped(message: str, **kw) -> str:
    """包裹底层 tool_error（真实库或离线兜底），确保返回含 ``ok:False``，契约一致。

    真实 hermes-agent 的 ``tools.registry.tool_error`` 返回 ``{"error": ...}``（无 ``ok`` 键），
    而离线兜底 ``_local_tool_error`` 返回 ``{"ok": False, "error": ...}``；两者不一致会让
    前端 / 桥接测试在「装了 hermes-agent」与「离线」两种环境下行为分叉。这里统一补 ``ok:False``。
    """
    raw = _rt()[1](message, **kw)
    try:
        d = json.loads(raw)
    except Exception:
        return raw
    if not d.get("ok"):
        d["ok"] = False
    return json.dumps(d, ensure_ascii=False, default=str)

# 每次 run_python 之间共享的全局命名空间，使 Agent 可跨调用复用变量 / import
_PYNS: dict[str, Any] = {"__name__": "__agent_run_python__"}


def _expand(path: str) -> Path:
    """把工具入参的路径解析为真实绝对路径。见模块 docstring「路径解析铁律」。"""
    p = Path(os.path.expanduser(str(path or "")))
    if p.is_absolute():
        return p.resolve()
    return (_project_root() / p).resolve()


def _is_binary_sample(data: bytes) -> bool:
    """判断文件头部样本是否为二进制。

    能按 UTF-8 / GBK 解码的文本（含中文）不应被判为二进制，否则中文文档会被
    当成二进制拒读。兜底再看不可打印字节占比。
    """
    if b"\x00" in data:
        return True
    if not data:
        return False
    for enc in ("utf-8", "gbk"):
        try:
            data.decode(enc)
            return False
        except UnicodeDecodeError:
            continue
    text_chars = bytes(range(0x20, 0x7F)) + b"\n\r\t\f\b"
    nontext = sum(1 for b in data if b not in text_chars)
    return nontext / len(data) > 0.30


# ============================================================================
# read_file
# ============================================================================
def handle_read_file(args: dict, **kwargs) -> str:

    raw = args.get("path")
    if not raw:
        return tool_error("path is required")
    p = _expand(raw)
    if not p.exists():
        return tool_error(f"file not found: {p}")
    if p.is_dir():
        return tool_error(f"path is a directory, not a file: {p}")
    try:
        head = p.read_bytes()[:4096]
    except Exception as e:  # noqa: BLE001
        return tool_error(f"cannot read file: {e}")
    if _is_binary_sample(head):
        return tool_result(ok=True, binary=True, path=str(p),
                           size=p.stat().st_size,
                           note="binary file; content not shown")
    try:
        offset = max(1, int(args.get("offset", 1) or 1))
    except Exception:
        offset = 1
    try:
        limit = int(args.get("limit", 500) or 500)
    except Exception:
        limit = 500
    limit = max(1, min(limit, 2000))

    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = p.read_text(encoding="gbk")
        except Exception:
            text = p.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    total = len(lines)
    start = offset - 1
    chunk = lines[start:start + limit]
    numbered = "\n".join(f"{start + i + 1}|{ln}" for i, ln in enumerate(chunk))
    out: dict[str, Any] = {"ok": True, "path": str(p), "total_lines": total,
                           "offset": offset, "returned": len(chunk),
                           "content": numbered}
    nxt = start + limit
    if nxt < total:
        out["next_offset"] = nxt + 1
    payload = json.dumps(out, ensure_ascii=False)
    if len(payload) > MAX_TOOL_OUTPUT:
        keep = MAX_TOOL_OUTPUT - 2000
        out["content"] = numbered[:keep] + "\n…[truncated]"
        out["truncated"] = True
        out.setdefault("next_offset", start + limit + 1)
        payload = json.dumps(out, ensure_ascii=False)
    return payload


# ============================================================================
# write_file
# ============================================================================
def handle_write_file(args: dict, **kwargs) -> str:

    raw = args.get("path")
    if not raw:
        return tool_error("path is required")
    content = args.get("content")
    if content is None:
        return tool_error("content is required")
    p = _expand(raw)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        existed = p.exists()
        p.write_text(str(content), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        return tool_error(f"write failed: {e}")
    record_edit(p)
    return tool_result(ok=True, path=str(p),
                       action="overwritten" if existed else "created",
                       bytes=len(str(content).encode("utf-8")))


# ============================================================================
# patch（replace 模式 + 极简 V4A patch 模式）
# ============================================================================
def _apply_v4a(patch_text: str) -> dict:
    """极简 V4A applier：支持 ``*** Update/Add/Delete File`` 三类 hunk。

    Update File 用 +/- 行 + 上下文行做锚定替换；容错优先，失败返回 error。
    """
    lines = patch_text.splitlines()
    i = 0
    changed: list[str] = []
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^\*\*\* (Update|Add|Delete) File: (.+)$", line.strip())
        if not m:
            i += 1
            continue
        action, fpath = m.group(1), m.group(2).strip()
        target = _expand(fpath)
        i += 1
        if action == "Delete":
            if target.exists():
                target.unlink()
            record_edit(target)
            changed.append(f"deleted {target}")
            continue
        body: list[str] = []
        while i < len(lines) and not lines[i].startswith("*** "):
            body.append(lines[i])
            i += 1
        if action == "Add":
            new_content = "\n".join(
                l[1:] if l.startswith("+") else l for l in body
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(new_content, encoding="utf-8")
            record_edit(target)
            changed.append(f"added {target}")
            continue
        if not target.exists():
            return {"ok": False, "error": f"cannot update missing file: {target}"}
        old_block: list[str] = []
        new_block: list[str] = []
        for l in body:
            if l.startswith("@@"):
                continue
            if l.startswith("-"):
                old_block.append(l[1:])
            elif l.startswith("+"):
                new_block.append(l[1:])
            elif l.startswith(" "):
                old_block.append(l[1:])
                new_block.append(l[1:])
            else:
                old_block.append(l)
                new_block.append(l)
        src = target.read_text(encoding="utf-8")
        old_str = "\n".join(old_block)
        new_str = "\n".join(new_block)
        if old_str and old_str in src:
            target.write_text(src.replace(old_str, new_str, 1), encoding="utf-8")
            record_edit(target)
            changed.append(f"updated {target}")
        else:
            return {"ok": False, "error": f"context not found in {target}"}
    return {"ok": True, "changed": changed}


def handle_patch(args: dict, **kwargs) -> str:

    mode = (args.get("mode") or "replace").strip()
    if mode == "patch":
        patch_text = args.get("patch") or ""
        if not patch_text.strip():
            return tool_error("patch content is required when mode='patch'")
        res = _apply_v4a(patch_text)
        if not res.get("ok"):
            return tool_error(res.get("error", "patch failed"))
        return tool_result(ok=True, changed=res.get("changed", []))

    raw = args.get("path")
    if not raw:
        return tool_error("path is required when mode='replace'")
    old_string = args.get("old_string")
    new_string = args.get("new_string")
    if old_string is None:
        return tool_error("old_string is required when mode='replace'")
    if new_string is None:
        new_string = ""
    p = _expand(raw)
    if not p.exists():
        return tool_error(f"file not found: {p}")
    try:
        src = p.read_text(encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        return tool_error(f"cannot read file: {e}")
    count = src.count(old_string)
    if count == 0:
        return tool_error("old_string not found in file")
    replace_all = bool(args.get("replace_all", False))
    if count > 1 and not replace_all:
        return tool_error(
            f"old_string is not unique ({count} matches); set replace_all=true "
            "or provide a larger unique context"
        )
    new_src = (src.replace(old_string, new_string) if replace_all
               else src.replace(old_string, new_string, 1))
    try:
        p.write_text(new_src, encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        return tool_error(f"write failed: {e}")
    record_edit(p)
    return tool_result(ok=True, path=str(p),
                       replaced=(count if replace_all else 1))


# ============================================================================
# search_files
# ============================================================================
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
              "dist", "build", ".hermes_data", "hermes_data"}


def _iter_files(root: Path, file_glob: str | None) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            if file_glob and not fnmatch.fnmatch(fn, file_glob):
                continue
            yield Path(dirpath) / fn


def handle_search_files(args: dict, **kwargs) -> str:

    pattern = args.get("pattern")
    if not pattern:
        return tool_error("pattern is required")
    target = (args.get("target") or "content").strip()
    base = _expand(args.get("path") or ".")
    if not base.exists():
        return tool_error(f"path not found: {base}")
    try:
        limit = int(args.get("limit", 50) or 50)
    except Exception:
        limit = 50
    try:
        offset = int(args.get("offset", 0) or 0)
    except Exception:
        offset = 0
    file_glob = args.get("file_glob")
    try:
        context = max(0, int(args.get("context", 0) or 0))
    except Exception:
        context = 0
    output_mode = (args.get("output_mode") or "content").strip()

    roots = ([base] if base.is_file()
             else list(_iter_files(base, file_glob if target == "content" else None)))

    if target == "files":
        results: list[str] = []
        walk_root = base if base.is_dir() else base.parent
        for f in _iter_files(walk_root, None):
            if fnmatch.fnmatch(f.name, pattern):
                results.append(str(f))
        sliced = results[offset:offset + limit]
        return tool_result(ok=True, target="files", total=len(results),
                           returned=len(sliced), matches=sliced)

    try:
        rx = re.compile(pattern)
    except re.error as e:
        return tool_error(f"invalid regex: {e}")
    hits: list[dict] = []
    files_seen: set[str] = set()
    for f in roots:
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            continue
        flines = text.splitlines()
        for idx, ln in enumerate(flines):
            if rx.search(ln):
                files_seen.add(str(f))
                if output_mode == "files_only":
                    break
                entry: dict[str, Any] = {"file": str(f), "line": idx + 1,
                                         "text": ln[:500]}
                if context:
                    lo = max(0, idx - context)
                    hi = min(len(flines), idx + context + 1)
                    entry["context"] = [
                        {"line": lo + j + 1, "text": flines[lo + j][:500]}
                        for j in range(hi - lo)
                    ]
                hits.append(entry)
    if output_mode == "files_only":
        files_list = sorted(files_seen)
        sliced = files_list[offset:offset + limit]
        return tool_result(ok=True, target="content", output_mode="files_only",
                           total=len(files_list), returned=len(sliced),
                           matches=sliced)
    total = len(hits)
    sliced = hits[offset:offset + limit]
    return tool_result(ok=True, target="content", total=total,
                       returned=len(sliced), matches=sliced)


# ============================================================================
# list_dir — 纯 Python 目录浏览（替代不存在的 ls / dir）
# ============================================================================
LIST_DIR_SCHEMA = {
    "name": "list_dir",
    "description": (
        "List the entries of a LOCAL directory. This REPLACES the `ls`/`dir` shell "
        "commands, which DO NOT EXIST in this environment (no terminal / no shell). "
        "Returns a JSON object with `entries`: a list of {name, type: 'dir'|'file', "
        "path, size}. Use this FIRST whenever the user points you at a local folder "
        "before reading any file inside it. Supports recursive=True with max_depth "
        "(default 3, 1-8) and an optional file_glob filter on file names."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or home-relative directory path to list.",
            },
            "recursive": {
                "type": "boolean", "default": False,
                "description": "Recurse into sub-directories (honors max_depth).",
            },
            "max_depth": {
                "type": "integer", "default": 3,
                "description": "Max recursion depth when recursive=True (1-8).",
            },
            "file_glob": {
                "type": "string", "default": None,
                "description": "Optional glob to filter file names (e.g. '*.py').",
            },
        },
        "required": ["path"],
    },

}


def handle_list_dir(args: dict, **kwargs) -> str:
    raw = args.get("path")
    if not raw:
        return tool_error("path is required")
    p = _expand(raw)
    if not p.exists():
        return tool_error(f"path not found: {p}")
    if p.is_file():
        return tool_error(f"path is a file, not a directory: {p}")
    try:
        recursive = bool(args.get("recursive", False))
    except Exception:
        recursive = False
    file_glob = args.get("file_glob")
    try:
        max_depth = int(args.get("max_depth", 3) or 3)
    except Exception:
        max_depth = 3
    max_depth = max(1, min(max_depth, 8))

    skip_dirs = _SKIP_DIRS | {".workbuddy"}
    entries: list[dict] = []

    def walk(d: Path | str, depth: int) -> None:
        try:
            with os.scandir(d) as it:
                items = sorted(it, key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return
        for e in items:
            rel = str(e.path)
            if e.is_dir():
                if e.name in skip_dirs:
                    entries.append({"name": e.name + "/", "type": "dir",
                                    "path": rel, "size": None, "skipped": True})
                    continue
                entries.append({"name": e.name + "/", "type": "dir",
                                "path": rel, "size": None})
                if recursive and depth < max_depth:
                    walk(e.path, depth + 1)
            else:
                if file_glob and not fnmatch.fnmatch(e.name, file_glob):
                    continue
                try:
                    sz = e.stat().st_size
                except Exception:
                    sz = None
                entries.append({"name": e.name, "type": "file",
                                "path": rel, "size": sz})

    walk(p, 1)
    truncated = False
    if len(entries) > 1000:
        entries = entries[:1000]
        truncated = True
    payload = json.dumps({"ok": True, "path": str(p), "count": len(entries),
                          "truncated": truncated, "entries": entries},
                         ensure_ascii=False)
    if len(payload) > MAX_TOOL_OUTPUT:
        payload = json.dumps({"ok": True, "path": str(p), "truncated": True,
                              "note": "too many entries; use recursive with "
                                      "file_glob to narrow",
                              "count": len(entries)}, ensure_ascii=False)
    return payload


# ============================================================================
# run_python — 进程内执行 Python（替代 terminal + code_execution 子进程）
# ============================================================================
RUN_PYTHON_SCHEMA = {
    "name": "run_python",
    "description": (
        "Execute Python code IN-PROCESS (no subprocess, no shell) and return its "
        "stdout/stderr. Use this for file/dir management (pathlib, shutil, os), data "
        "processing, HTTP calls, or any scripting. Variables and imports persist "
        "across calls in the same session. This REPLACES terminal/bash — there is "
        "no shell."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {"type": "string",
                     "description": "Python source code to execute."},
        },
        "required": ["code"],
    },

}


def handle_run_python(args: dict, **kwargs) -> str:

    code = args.get("code") or ""
    if not code.strip():
        return tool_error("code is required")
    buf = io.StringIO()
    try:
        compiled = compile(code, "<run_python>", "exec")
    except SyntaxError as e:
        return tool_error(f"SyntaxError: {e}")
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(compiled, _PYNS)  # noqa: S102 — 进程内脚本执行，正是本工具的用途
        out = buf.getvalue()
        if len(out) > MAX_TOOL_OUTPUT:
            out = out[:MAX_TOOL_OUTPUT] + "\n…[truncated]"
        return tool_result(ok=True, stdout=out)
    except Exception:  # noqa: BLE001
        out = buf.getvalue()
        return tool_error(
            "exception during execution",
            stdout=out[:MAX_TOOL_OUTPUT],
            traceback=traceback.format_exc()[-4000:],
        )


# ============================================================================
# 官方 file schema 的离线兜底
# ============================================================================
# 覆盖注册优先复用 `tools.file_tools` 的官方 schema，保证参数契约与上游**逐字段**
# 一致（模型看到的工具描述不变，只换 handler）。但离线门禁 / CI 里可能没有装
# hermes-agent，此时用下面这份对齐上游参数契约的最小 schema 兜底，使 register_into
# 仍可跑通、注册面可被单测覆盖。
# 契约来源：hermes-agent `tools/file_tools.py` 的 READ_FILE_SCHEMA / WRITE_FILE_SCHEMA
# / PATCH_SCHEMA / SEARCH_FILES_SCHEMA（字段名、类型、required、默认值一致）。
_FALLBACK_FILE_SCHEMAS: dict[str, dict] = {
    "read_file": {
        "name": "read_file",
        "description": "Read a text file with line numbers and pagination. "
                       "Output format: 'LINE_NUM|CONTENT'. Use offset/limit for large files.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read (absolute, relative, or ~/path)"},
                "offset": {"type": "integer", "description": "Line number to start reading from (1-indexed)", "default": 1, "minimum": 1},
                "limit": {"type": "integer", "description": "Maximum number of lines to read", "default": 500, "maximum": 2000},
            },
            "required": ["path"],
        },
    },
    "write_file": {
        "name": "write_file",
        "description": "Write content to a file, completely replacing existing content. "
                       "Creates parent directories automatically. Use 'patch' for targeted edits.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {"type": "string", "description": "Complete content to write to the file"},
                "cross_profile": {"type": "boolean", "description": "Opt out of the cross-profile soft guard.", "default": False},
            },
            "required": ["path", "content"],
        },
    },
    "patch": {
        "name": "patch",
        "description": "Targeted find-and-replace edits in files. "
                       "REPLACE MODE (mode='replace', default): mode + path + old_string + new_string. "
                       "PATCH MODE (mode='patch'): V4A multi-file patch content.",
        "parameters": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["replace", "patch"],
                         "description": "Edit mode.", "default": "replace"},
                "path": {"type": "string", "description": "REQUIRED when mode='replace'. File path to edit."},
                "old_string": {"type": "string", "description": "REQUIRED when mode='replace'. Exact text to find."},
                "new_string": {"type": "string", "description": "REQUIRED when mode='replace'. Replacement text."},
                "replace_all": {"type": "boolean", "description": "Replace all occurrences.", "default": False},
                "patch": {"type": "string", "description": "REQUIRED when mode='patch'. V4A format patch content."},
                "cross_profile": {"type": "boolean", "description": "Opt out of the cross-profile soft guard.", "default": False},
            },
            "required": ["mode"],
        },
    },
    "search_files": {
        "name": "search_files",
        "description": "Search file contents (target='content') or find files by name (target='files').",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern for content search, or glob pattern for file search"},
                "target": {"type": "string", "enum": ["content", "files"], "description": "Search target", "default": "content"},
                "path": {"type": "string", "description": "Directory or file to search in", "default": "."},
                "file_glob": {"type": "string", "description": "Filter files by pattern in grep mode"},
                "limit": {"type": "integer", "description": "Maximum number of results", "default": 50},
                "offset": {"type": "integer", "description": "Skip first N results", "default": 0},
                "output_mode": {"type": "string", "enum": ["content", "files_only", "count"],
                                "description": "Output format for grep mode", "default": "content"},
                "context": {"type": "integer", "description": "Context lines around each match", "default": 0},
            },
            "required": ["pattern"],
        },
    },
}


def _official_file_schemas() -> tuple[dict, dict, dict, dict]:
    """取官方 file schema；hermes-agent 不可用时回落到 ``_FALLBACK_FILE_SCHEMAS``。"""
    try:
        from tools.file_tools import (  # noqa: PLC0415 — 可选依赖，必须懒导入
            READ_FILE_SCHEMA, WRITE_FILE_SCHEMA, PATCH_SCHEMA, SEARCH_FILES_SCHEMA,
        )
        return READ_FILE_SCHEMA, WRITE_FILE_SCHEMA, PATCH_SCHEMA, SEARCH_FILES_SCHEMA
    except Exception:  # pragma: no cover - 离线兜底
        f = _FALLBACK_FILE_SCHEMAS
        return f["read_file"], f["write_file"], f["patch"], f["search_files"]


# ============================================================================
# 注册入口
# ============================================================================
def register_into(registry) -> list[str]:
    """把本模块的纯 Python 工具覆盖注册进 Hermes registry，返回工具名列表。

    ``read_file`` / ``write_file`` / ``patch`` / ``search_files`` 复用 Hermes 内置
    的官方 schema（保证参数契约与上游一致），仅替换 handler；``list_dir`` /
    ``run_python`` 使用本模块自带 schema。全部 ``override=True``、幂等。
    """
    (READ_FILE_SCHEMA, WRITE_FILE_SCHEMA,
     PATCH_SCHEMA, SEARCH_FILES_SCHEMA) = _official_file_schemas()

    specs = [
        ("read_file", READ_FILE_SCHEMA, handle_read_file, "\U0001f4d6"),
        ("write_file", WRITE_FILE_SCHEMA, handle_write_file, "\u270d\ufe0f"),
        ("patch", PATCH_SCHEMA, handle_patch, "\U0001f527"),
        ("search_files", SEARCH_FILES_SCHEMA, handle_search_files, "\U0001f50e"),
        ("list_dir", LIST_DIR_SCHEMA, handle_list_dir, "\U0001f4c1"),
        ("run_python", RUN_PYTHON_SCHEMA, handle_run_python, "\U0001f40d"),
    ]
    for name, schema, handler, emoji in specs:
        registry.register(
            name=name, toolset="file", schema=schema, handler=handler,
            is_async=False, description=f"pure-python {name} (no shell)",
            emoji=emoji, max_result_size_chars=MAX_TOOL_OUTPUT, override=True,
        )
    return [s[0] for s in specs]
