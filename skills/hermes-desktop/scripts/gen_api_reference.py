#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_api_reference.py — 从本机已装 hermes-agent 源码自动生成 API 参考文档。

用 ast **静态解析**（不 import 任何 hermes 模块，避免触发副作用），提取核心模块的
类 / 方法 / 函数签名（参数名 + 类型注解 + 默认值）、返回类型、异常（docstring 与
raise 语句双来源），按模块拆分/聚合为 markdown，输出到 references/api-reference/。

两种模块形态：
  * `file` 单文件模块 —— 独立成档（run_agent / toolsets / gateway.session / mcp_serve）
  * `dir`  包聚合      —— 遍历包内全部 .py（递归），每个模块一个小节聚合成一份文档
                        （agent / gateway / tools / plugins / hermes_cli）

用法：
    uv run python scripts/gen_api_reference.py                        # 生成全部
    uv run python scripts/gen_api_reference.py --module agent          # 仅某模块/包
    uv run python scripts/gen_api_reference.py --out DIR               # 指定输出目录
    uv run python scripts/gen_api_reference.py --site-packages DIR     # 显式 site-packages
    uv run python scripts/gen_api_reference.py --skip {agent,...}      # 跳过（跳过重型包，供快速重生成）

退出码：0 = 成功；1 = 有模块解析失败。
"""
from __future__ import annotations

import argparse
import ast
import glob
import importlib.util
import os
import re
import sys

# ---------------------------------------------------------------------------
# 模块清单：key(输出文件名) / title / 说明 / 形态（file|dir）+ 定位
# ---------------------------------------------------------------------------
MODULES = [
    {"key": "01-run-agent", "title": "run_agent — AIAgent 主类与入口",
     "desc": "Hermes Agent 核心运行类 AIAgent 与模块入口 main()。", "type": "file", "file": "run_agent.py"},
    {"key": "02-toolsets", "title": "toolsets — 工具集注册与解析",
     "desc": "工具集（toolset）的注册、解析、校验与创建。", "type": "file", "file": "toolsets.py"},
    {"key": "03-gateway-session", "title": "gateway.session — 会话数据模型",
     "desc": "Hermes Gateway 的会话存储与上下文模型。", "type": "file", "file": "gateway/session.py"},
    {"key": "04-mcp-serve", "title": "mcp_serve — MCP 服务",
     "desc": "将 Hermes 暴露为 MCP 服务器的实现。", "type": "file", "file": "mcp_serve.py"},
    {"key": "05-agent", "title": "agent — Agent 内核包（156 模块）",
     "desc": "Agent 内核：对话循环、适配器、工具执行、记忆、模型注册等。", "type": "dir", "dir": "agent"},
    {"key": "06-gateway", "title": "gateway — 网关包（77 模块）",
     "desc": "网关：会话、运行、平台注册、流分发、投递、配置等。", "type": "dir", "dir": "gateway"},
    {"key": "07-tools", "title": "tools — 工具包（114 模块）",
     "desc": "内置工具：代码执行、浏览器、委托、文件、MCP 等。", "type": "dir", "dir": "tools"},
    {"key": "08-plugins", "title": "plugins — 插件包（187 模块）",
     "desc": "内置插件：技能、工作流、看板、学习、多 Agent 等。", "type": "dir", "dir": "plugins"},
    {"key": "09-hermes-cli", "title": "hermes_cli — 命令行包（206 模块）",
     "desc": "命令行/网关/配置/Web 服务等顶层入口。", "type": "dir", "dir": "hermes_cli"},
]

# ---------------------------------------------------------------------------
# ast 辅助
# ---------------------------------------------------------------------------
def type_str(node) -> str:
    if node is None:
        return ""
    try:
        s = ast.unparse(node)
    except Exception:
        s = "<expr>"
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        s = node.value
    return s


def default_str(node) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return "<expr>"


def func_kind(func, decorators) -> str:
    if isinstance(func, ast.AsyncFunctionDef):
        return "async def"
    for d in decorators:
        dn = d if isinstance(d, str) else ast.unparse(d)
        if "classmethod" in dn:
            return "classmethod"
        if "staticmethod" in dn:
            return "staticmethod"
        if "property" in dn or ".setter" in dn or ".deleter" in dn:
            return "property"
    return "def"


def extract_raises_doc(doc: str) -> list:
    if not doc:
        return []
    found = []
    m = re.search(r"Raises[:\s]+(.*)", doc, re.IGNORECASE | re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            line = line.strip()
            mm = re.match(r"^([A-Za-z_][\w.]*)\s*:", line)
            if mm:
                found.append(mm.group(1))
    for mm in re.finditer(r":\s*raises\s+([A-Za-z_][\w.]*)", doc, re.IGNORECASE):
        found.append(mm.group(1))
    seen, out = set(), []
    for x in found:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def extract_raises_body(func) -> list:
    found = []
    for node in ast.walk(func):
        if isinstance(node, ast.Raise) and node.exc is not None:
            e = node.exc
            if isinstance(e, ast.Call):
                e = e.func
            name = ""
            if isinstance(e, ast.Name):
                name = e.id
            elif isinstance(e, ast.Attribute):
                name = ast.unparse(e)
            if name and name not in ("Exception", "BaseException"):
                found.append(name)
    seen, out = set(), []
    for x in found:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ---------------------------------------------------------------------------
# 解析
# ---------------------------------------------------------------------------
def parse_module_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src, filename=path)
    doc = ast.get_docstring(tree) or ""
    classes, top_funcs = [], []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append(parse_class(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            top_funcs.append(parse_func(node, "def"))
    return {"doc": doc, "classes": classes, "funcs": top_funcs}


def parse_class(node: ast.ClassDef) -> dict:
    bases = [ast.unparse(b) for b in node.bases]
    methods = []
    for sub in node.body:
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            deco = [ast.unparse(d) for d in sub.decorator_list]
            methods.append(parse_func(sub, func_kind(sub, deco), is_method=True))
    return {"name": node.name, "bases": bases, "doc": ast.get_docstring(node) or "", "methods": methods}


def parse_func(func, kind: str, is_method: bool = False) -> dict:
    args = func.args
    params = []
    n, m = len(args.args), len(args.defaults)
    for i, a in enumerate(args.args):
        has_default = i >= (n - m)
        params.append({"name": a.arg, "ann": type_str(a.annotation),
                       "default": default_str(args.defaults[i - (n - m)]) if has_default else ""})
    if args.vararg:
        params.append({"name": "*" + args.vararg.arg, "ann": type_str(args.vararg.annotation), "default": ""})
    for i, a in enumerate(args.kwonlyargs):
        params.append({"name": a.arg, "ann": type_str(a.annotation),
                       "default": default_str(args.kw_defaults[i]) if args.kw_defaults[i] else ""})
    if args.kwarg:
        params.append({"name": "**" + args.kwarg.arg, "ann": type_str(args.kwarg.annotation), "default": ""})
    doc = ast.get_docstring(func) or ""
    doc_raises = extract_raises_doc(doc)
    raises = doc_raises + [r for r in extract_raises_body(func) if r not in doc_raises]
    return {"name": func.name, "kind": kind, "params": params, "ret": type_str(func.returns),
            "doc": doc, "raises": raises}


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------
def _sig(f) -> str:
    parts = []
    for p in f["params"]:
        if f["name"] == "__init__" and p["name"] == "self":
            continue
        nm = p["name"]
        star = ""
        if nm.startswith("**"):
            nm = nm[2:]; star = "**"
        elif nm.startswith("*"):
            nm = nm[1:]; star = "*"
        part = star + nm
        if p["ann"]:
            part += f": {p['ann']}"
        if p["default"]:
            part += f" = {p['default']}"
        parts.append(part)
    return ", ".join(parts)


def render_func_md(f) -> str:
    ret = f" -> {f['ret']}" if f["ret"] else ""
    out = [f"#### {f['kind']} `{f['name']}({_sig(f)}){ret}`"]
    doc = f["doc"].strip()
    if doc:
        out.append("")
        out.append(doc)
    if f["raises"]:
        out.append("")
        out.append("**异常**: " + ", ".join(f"`{r}`" for r in f["raises"]))
    out.append("")
    return "\n".join(out)


def render_module_section(info: dict, prefix: str = "") -> str:
    """渲染单个模块的 API 内容（类 + 顶层函数）。prefix 用于包聚合时的模块标题前缀。"""
    lines = []
    if info["doc"]:
        lines.append("### 模块文档")
        lines.append("")
        lines.append(info["doc"].strip())
        lines.append("")
    for c in info["classes"]:
        if c["name"].startswith("_"):
            continue
        bases = "、".join(f"`{b}`" for b in c["bases"]) if c["bases"] else "`object`"
        n_pub = sum(1 for m in c["methods"] if not m["name"].startswith("_"))
        lines.append(f"### class {c['name']}")
        lines.append("")
        lines.append(f"> 继承: {bases} ｜ 方法数: {len(c['methods'])}（公开 {n_pub}）")
        lines.append("")
        if c["doc"]:
            lines.append(c["doc"].strip())
            lines.append("")
        for m in c["methods"]:
            if m["name"].startswith("_") and m["name"] != "__init__":
                continue
            lines.append(render_func_md(m))
        lines.append("")
    pub_funcs = [f for f in info["funcs"] if not f["name"].startswith("_")]
    if pub_funcs:
        lines.append("### 顶层函数")
        lines.append("")
        for f in pub_funcs:
            lines.append(render_func_md(f))
        lines.append("")
    return "\n".join(lines)


def render_file_module(info: dict, meta: dict) -> str:
    lines = []
    lines.append(f"# {meta['title']}")
    lines.append("")
    lines.append(f"> **模块**: `{meta['file']}`")
    lines.append(f"> **来源**: 本机已装 `hermes-agent {meta['version']}` 源码（ast 静态解析，未 import）")
    lines.append(f"> **说明**: {meta['desc']}")
    lines.append("")
    if info["doc"]:
        lines.append("## 模块文档")
        lines.append("")
        lines.append(info["doc"].strip())
        lines.append("")
    lines.append(render_module_section(info))
    return "\n".join(lines)


def render_dir_module(mod_infos: list, meta: dict) -> str:
    lines = []
    lines.append(f"# {meta['title']}")
    lines.append("")
    lines.append(f"> **模块**: `{meta['dir']}/`（包，共 {len(mod_infos)} 个模块）")
    lines.append(f"> **来源**: 本机已装 `hermes-agent {meta['version']}` 源码（ast 静态解析，未 import）")
    lines.append(f"> **说明**: {meta['desc']}")
    lines.append("")
    for mod_name, info in mod_infos:
        lines.append(f"## {mod_name}")
        lines.append("")
        lines.append(render_module_section(info))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 目录扫描
# ---------------------------------------------------------------------------
def iter_py_files(dir_path: str):
    for path in sorted(glob.glob(os.path.join(dir_path, "**", "*.py"), recursive=True)):
        if "__pycache__" in path:
            continue
        yield path


def scan_dir(root: str) -> list:
    """返回 [(模块显示名, info)]，按模块路径排序。"""
    out = []
    for path in iter_py_files(root):
        rel = os.path.relpath(path, os.path.dirname(root))
        mod_name = rel.replace(os.sep, ".")[:-3]  # agent/agent_init.py -> agent.agent_init
        try:
            info = parse_module_file(path)
        except SyntaxError:
            continue
        out.append((mod_name, info))
    return out


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def locate_site_packages(explicit: str | None = None) -> str | None:
    if explicit and os.path.isdir(explicit):
        return explicit
    try:
        spec = importlib.util.find_spec("run_agent")
        if spec and spec.origin:
            p = os.path.dirname(os.path.abspath(spec.origin))
            if os.path.isdir(p):
                return p
    except Exception:
        pass
    return None


def get_installed_version(sp: str) -> str:
    for d in glob.glob(os.path.join(sp, "hermes_agent-*.dist-info")):
        m = re.match(r"hermes_agent-(.+)\.dist-info$", os.path.basename(d))
        if m:
            return m.group(1)
        v = os.path.basename(d).split("-")[1]
        return v[: -len(".dist")] if v.endswith(".dist") else v
    return "?"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Hermes Library API 参考文档生成器")
    p.add_argument("--module", default=None, help="仅生成指定 key（如 agent）")
    p.add_argument("--out", default=None, help="输出目录")
    p.add_argument("--site-packages", default=None, help="显式 site-packages")
    p.add_argument("--skip", default=None, help="跳过 key（逗号分隔，供快速重生成重型包）")
    args = p.parse_args(argv)

    sp = locate_site_packages(args.site_packages)
    if not sp:
        print("[ERR] 无法定位 site-packages", file=sys.stderr)
        return 2
    version = get_installed_version(sp)
    print(f"[info] site-packages: {sp}  版本: {version}")

    out_dir = args.out or os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "references", "api-reference"))
    os.makedirs(out_dir, exist_ok=True)

    skip = {s.strip() for s in args.skip.split(",")} if args.skip else set()
    rc = 0
    for mod in MODULES:
        if args.module and mod["key"] != args.module:
            continue
        if mod["key"] in skip:
            print(f"[SKIP] {mod['key']}")
            continue
        try:
            if mod["type"] == "file":
                fpath = os.path.join(sp, mod["file"])
                if not os.path.isfile(fpath):
                    print(f"[WARN] 未找到 {mod['file']}", file=sys.stderr)
                    continue
                info = parse_module_file(fpath)
                md = render_file_module(info, {**mod, "version": version})
                n_classes = len([c for c in info["classes"] if not c["name"].startswith("_")])
                n_methods = sum(len(c["methods"]) for c in info["classes"])
                extra = f"类 {n_classes} / 方法 {n_methods}"
            else:
                root = os.path.join(sp, mod["dir"])
                if not os.path.isdir(root):
                    print(f"[WARN] 未找到包 {mod['dir']}", file=sys.stderr)
                    continue
                infos = scan_dir(root)
                md = render_dir_module(infos, {**mod, "version": version})
                extra = f"{len(infos)} 模块"
            out_file = os.path.join(out_dir, mod["key"] + ".md")
            with open(out_file, "w", encoding="utf-8", newline="\n") as f:
                f.write(md)
            print(f"[OK] {mod['key']:20s} {out_file}  ({extra}, {len(md.splitlines())} 行)")
        except SyntaxError as e:
            print(f"[ERR] 解析失败: {e}", file=sys.stderr)
            rc = 1
        except Exception as e:  # noqa: BLE001
            print(f"[ERR] {mod['key']}: {type(e).__name__}: {e}", file=sys.stderr)
            rc = 1
    print(f"\n输出目录: {out_dir}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
