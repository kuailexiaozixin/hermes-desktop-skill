#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_endpoints.py — 前端→后端 路由链路校验。

为什么需要：Hermes 桌面示例是「FastHTML 后端 + 前端 JS 调 fetch」结构。前端写了
`fetch("/api/conversations/" + cid + "/rename")`，但后端若从未注册对应路由，
运行时才 404，HTTP 200 冒烟测试 / 纯 HTML 结构审计都看不见这类断裂。


  * 后端：递归扫描示例目录下全部 `.py` 文件（`main.py` 只是入口，实际路由注册在
    `routes/` 包，如 chat.py / misc.py / ...）的 `@app.get/post/...("PATH")` 装饰器。
  * 前端：扫描 `static/` 下全部 `.js` 文件：
      - 字面量字符串  `"/api/..."` / `"/artifact/..."`（去查询串）
      - 模板字符串    `` `/api/...${x}...` ``（`${...}` 视为动态段 `<p>`）
      - 拼接链        `"/api/x/" + var + "/y"`（中间表达式视为 `<p>` 合并）
  * 归一化：去查询串；`{param}` / `<param:type>` / `${...}` / `:path` → `<p>`；
    空段丢弃。
  * 匹配：引用路径与某注册路由「段数相等且逐段相等（注册段为 <p> 通配）」或「互为
    前缀」即视为已覆盖。

  ⚠️ 静态解析的固有限制（已知，非 bug，结果须人工复核）：
    * main.py 的**文档字符串 / 注释**里出现的 `@app.get("/x")` 也会被当作真实路由，
      可能「假 PASS」掩盖本应 404 的端点（如示例里写反面教材的路径）。
    * 后端用**变量拼接**注册的路由（如 `app.route(PREFIX + "/x")`）抓不到，
      可能「假 FAIL」。此类路由请改用字面量装饰器，或人工复核。

退出码：0 = 无未覆盖引用（或文件缺失被 --skip 跳过）；1 = 发现未覆盖引用（阻断发布）；
        2 = 工具/参数问题。
"""
from __future__ import annotations

import argparse
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_EXAMPLE = os.path.join(SKILL_ROOT, "examples", "01-hermes-desktop")
DEFAULT_MAIN = os.path.join(DEFAULT_EXAMPLE, "main.py")
DEFAULT_STATIC = os.path.join(
    SKILL_ROOT, "examples", "01-hermes-desktop", "static"
)


# --------------------------------------------------------------------------- #
# 归一化
# --------------------------------------------------------------------------- #
def normalize(path: str) -> list[str]:
    """路径 → 段列表（去除查询串、把动态段统一成 <p>、丢弃空段）。"""
    path = path.split("?")[0].split("#")[0]
    path = re.sub(r"\{[^}]+\}", "<p>", path)          # {cid}
    path = re.sub(r"<[^>]+>", "<p>", path)            # <path:path> / 已生成的 <p>
    path = re.sub(r"\$\{[^}]+\}", "<p>", path)        # ${x}
    path = path.replace(":path", "<p>")               # fastHTML :path 转换器
    segs = [s for s in path.split("/") if s]
    return segs


def is_wild(seg: str) -> bool:
    return seg == "<p>"


def is_prefix(pre: list[str], full: list[str]) -> bool:
    """pre 是否为 full 的前缀（动态段视作通配）。"""
    if len(pre) > len(full):
        return False
    for r, s in zip(pre, full):
        if not (is_wild(r) or is_wild(s) or r == s):
            return False
    return True


def matches(ref_segs: list[str], registered: list[list[str]]) -> bool:
    for reg in registered:
        if len(reg) == len(ref_segs):
            if all(is_wild(r) or r == s for r, s in zip(reg, ref_segs)):
                return True
        elif is_prefix(ref_segs, reg):
            # 仅「引用是某注册路由的前缀」才放行——用于拼接链里被拆出的裸片段
            # （如 "/api/conversations/" 是 "/api/conversations/{cid}" 的前缀）。
            # 反向（注册路由是引用的前缀）不放行：否则 "/api/conversations/X/renamed"
            # 会被 "/api/conversations/{cid}" 误判为已覆盖，漏掉真实 404。
            return True
    return False


# --------------------------------------------------------------------------- #
# 后端路由提取
# --------------------------------------------------------------------------- #
BACKEND_RE = re.compile(
    r"@[\w_]+\.(?:get|post|put|delete|patch|head|options|route|websocket)\s*\(\s*"
    r'["\']([^"\']+)["\']'
)


def collect_py_files(example_dir: str) -> list[str]:
    """递归收集示例目录下全部 .py 文件（后端路由可能分散在 routes/ 包等）。"""
    out: list[str] = []
    for root, _dirs, files in os.walk(example_dir):
        for fn in files:
            if fn.endswith(".py"):
                out.append(os.path.join(root, fn))
    return sorted(out)


def extract_backend(py_files: list[str]) -> list[list[str]]:
    """从若干 .py 文件提取后端路由。示例 main.py 只是入口，实际路由
    注册在 routes/ 包（chat.py/misc.py/...），故需全量扫描而非只看 main.py。"""
    out: list[list[str]] = []
    for pypath in py_files:
        with open(pypath, "r", encoding="utf-8") as f:
            src = f.read()
        for m in BACKEND_RE.finditer(src):
            p = m.group(1)
            # 跳过明显的纯注释/示例路径（文档里常写 "@app.get("/assets/app.css")" 作反面教材）
            # 这类多余项不会造成误报（后端多路由是允许的），但 /assets 之类非 API 前缀
            # 仅在被前端引用时才可能触发，这里保留即可。
            out.append(normalize(p))
    return out


# --------------------------------------------------------------------------- #
# 前端引用提取
# --------------------------------------------------------------------------- #
def _extract_literals(js: str) -> list[str]:
    """提取所有以 /api 或 /artifact 开头的字符串字面量（单/双/反引号）。"""
    found: list[str] = []
    for m in re.finditer(r'["\'`](/(?:api|artifact)[^"\'`]*?)["\'`]', js):
        found.append(m.group(1))
    return found


def _merge_concat(js: str) -> set[str]:
    """合并 `"/api/x/" + expr + "/y"` 拼接链，中间表达式 → <p>。反复合并以支持多级链。"""
    # 捕获：以 /api|/artifact 开头的字符串 + 表达式 + 字符串
    pat = re.compile(
        r'(["\'])(/(?:api|artifact)[^"\']*)\1'          # 首串（去引号后 group2）
        r"\s*\+\s*([^\"'\s][^\"']*?)"                    # 中间表达式（去引号）group3
        r'\s*\+\s*(["\'])([^"\']*)\4'                   # 尾串（去引号后 group5）
    )
    merged: set[str] = set()
    text = js
    changed = True
    guard = 0
    while changed and guard < 50:
        changed = False
        guard += 1
        for m in pat.finditer(text):
            a = m.group(2)
            b = m.group(5)
            combined = a + "<p>" + b
            text = text[: m.start()] + '"' + combined + '"' + text[m.end():]
            merged.add(combined)
            changed = True
            break
    return merged


def extract_frontend(js_path: str) -> list[list[str]]:
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()
    paths: set[str] = set()
    # 1) 字面量
    for lit in _extract_literals(js):
        paths.add(lit)
    # 2) 拼接链合并
    for merged in _merge_concat(js):
        paths.add(merged)
    # 3) 也兜底扫一遍 EventSource / WebSocket（hermes 当前未用，留作扩展）
    for m in re.finditer(r"(?:EventSource|WebSocket)\(\s*[\"'`]([^\"'`]+)[\"'`]", js):
        paths.add(m.group(1))
    return [normalize(p) for p in paths]


def collect_js_files(static_dir: str) -> list[str]:
    """递归收集 static 目录下全部 .js 文件（前端→后端契约的引用来源）。"""
    out: list[str] = []
    for root, _dirs, files in os.walk(static_dir):
        for fn in files:
            if fn.endswith(".js"):
                out.append(os.path.join(root, fn))
    return sorted(out)


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="前端→后端 路由链路校验")
    p.add_argument("example_dir", nargs="?", default=None,
                   help="示例目录（含 main.py 与 static/app.js）；默认 examples/01-hermes-desktop")
    p.add_argument("--main", default=None, help="main.py 路径（显式指定优先于 example_dir）")
    p.add_argument("--js", default=None, help="app.js 路径（显式指定优先于 example_dir）")
    p.add_argument("--skip-if-missing", action="store_true",
                   help="main.py 或 app.js 缺失时退出 0（不阻断）而非报错")
    p.add_argument("--warn", action="store_true",
                   help="发现未覆盖引用时只警告（exit 0）而非阻断（exit 1）")
    args = p.parse_args(argv)

    # 后端路由来源：--main 显式单文件 > example_dir 递归全量 .py（main.py + routes/ 包）> 内置默认
    if args.main:
        py_files = [args.main]
    else:
        example_dir = args.example_dir if args.example_dir else DEFAULT_EXAMPLE
        py_files = collect_py_files(example_dir)
        if not py_files:
            py_files = [os.path.join(example_dir, "main.py")]

    # 前端引用来源：--js 显式单文件 > example_dir 的 static/ 递归全量 > 内置默认 static/
    if args.js:
        js_files = [args.js]
    else:
        static_dir = (os.path.join(args.example_dir, "static")
                      if args.example_dir else DEFAULT_STATIC)
        js_files = collect_js_files(static_dir)

    if not js_files:
        msg = f"[ERR] 在 {static_dir} 下未找到任何 .js 文件"
        if args.skip_if_missing:
            print(f"[跳过] {msg}（--skip-if-missing）")
            return 0
        print(msg, file=sys.stderr)
        return 2

    registered = extract_backend(py_files)
    referenced: list[list[str]] = []
    for jf in js_files:
        referenced.extend(extract_frontend(jf))

    unmatched = [r for r in referenced if not matches(r, registered)]

    print("=" * 64)
    print(" 前端→后端 路由链路校验 (check_endpoints)")
    print("=" * 64)
    print(f" 后端注册路由数 : {len(registered)}")
    print(f" 前端引用路径数 : {len(referenced)}")
    print("-" * 64)
    if not unmatched:
        print(" ✅ 全部前端引用均有对应后端路由，无运行时 404 隐患。")
        print("=" * 64)
        return 0

    print(f" 🔴 发现 {len(unmatched)} 个「前端引用了、后端未注册」的端点：")
    for r in unmatched:
        print(f"     - /{'/'.join(r)}")
    print("-" * 64)
    if args.warn:
        print(" ⚠️ 仅警告（--warn），不阻断。")
        return 0
    print(" ⛔ 阻断发布：请为上述端点补后端路由，或修正前端 URL。")
    print("=" * 64)
    return 1


if __name__ == "__main__":
    sys.exit(main())
