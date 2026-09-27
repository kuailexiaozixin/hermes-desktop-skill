#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模块清单表机器校验：references/10、11、12、13、16 与已装 hermes-agent 包源码逐条对账。

检查项全部是静态 `ast` 解析，不 import 被查包（`hermes_cli` 的模块在 import 阶段会做
TTY / 网络 / 凭据相关动作；`tools` 下 34 个、`agent` 下 6 个模块在 import 期就自注册）。
检查项：

  1. 表内每行的模块在已装包里真实存在；已装包里的模块一个不漏（子包目录本身允许由
     分组标题代表，不单列行）。
  2. 「代表 API」列里的每个名字都定义在该模块自己的命名空间：顶层 def / async def /
     class / 赋值（含带类型标注的赋值）/ `__all__`，含写在顶层 if / try / with 块里的
     定义；子包取 `__init__.py` 的再导出；`10` 的 `组内文件.py::名()` 形式按那个文件核对。
  3. 分组标题里的「（N 个）」等于该组表内行数。
  4. 文档头部声明的数量口径等于磁盘实测（库升级后这里会失败，提醒同步文档）。
  5. `11` 各节「**规模**：N 类 / M 函数」等于该顶层模块源码里名字不以下划线开头的顶层
     类与函数个数（同样按 "## N. 模块名" 那样的节标题定位所属模块）。

退出码：0 通过；1 有不一致；2 环境原因跳过（未装 hermes-agent，无法核对）。
"""
from __future__ import annotations

import ast
import os
import re
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(SKILL_ROOT, "references")

# style: bare=行内是 hermes_cli 顶层裸模块名；dotted=行内是全限定名；
#        grouped=行内是裸名，所属子包由 `### 1.x` 标题给出
SPECS = [
    dict(doc="10-hermes-cli.md", pkg="hermes_cli", style="bare",
         py_excl_root=205, top_mods=146, subpkgs=3, rows=157,
         claims=["顶层 146 个模块文件 + 3 个子包，含嵌套共 205 个 `.py`",
                 "全部 149 个顶层条目（146 个模块文件"]),
    dict(doc="12-tools-modules.md", pkg="tools", style="dotted",
         py_excl_root=113, top_mods=None, subpkgs=None, rows=113,
         claims=["## 1. 全量模块清单（113 个"]),
    dict(doc="13-agent-modules.md", pkg="agent", style="dotted",
         py_excl_root=155, top_mods=None, subpkgs=None, rows=155,
         claims=["## 1. 全量模块清单（155 个"]),
    dict(doc="16-gateway-package.md", pkg="gateway", style="grouped",
         py_excl_root=76, top_mods=None, subpkgs=None, rows=73,
         claims=["共 77 个 `.py`", "全部 77 个 `.py`（72 个功能模块 + 5 个 `__init__.py`）",
                 "## 1. 全量模块清单（73 个模块行"]),
]


def find_site_packages() -> list[str]:
    """自动发现候选 site-packages（与 check_api_signature.py 的扫描面一致）。"""
    cands: list[str] = []
    for vn in (".venv", "venv", ".venv_hermes", "venv_hermes"):
        cands.append(os.path.join(SKILL_ROOT, vn, "Lib", "site-packages"))
        cands.append(os.path.join(SKILL_ROOT, vn, "lib"))
    la = os.environ.get("LOCALAPPDATA", "")
    if la:
        vd = os.path.join(la, "hermes-business-agent", "venvs")
        if os.path.isdir(vd):
            for e in sorted(os.listdir(vd)):
                cands.append(os.path.join(vd, e, "Lib", "site-packages"))
    ex = os.path.join(SKILL_ROOT, "examples")
    if os.path.isdir(ex):
        for sub in sorted(os.listdir(ex)):
            for vn in (".venv", "venv"):
                cands.append(os.path.join(ex, sub, vn, "Lib", "site-packages"))
    import site
    import sysconfig
    cands.extend(site.getsitepackages() + [site.getusersitepackages()])
    cands.append(sysconfig.get_paths()["purelib"])

    res: list[str] = []
    for c in cands:
        if not os.path.isdir(c):
            continue
        if os.path.basename(c) == "site-packages":
            if c not in res:
                res.append(c)
            continue
        for e in sorted(os.listdir(c)):  # venv: lib/python*/site-packages
            sp = os.path.join(c, e, "site-packages")
            if os.path.isdir(sp) and sp not in res:
                res.append(sp)
    return res


def locate(sp_dirs: list[str], pkg: str) -> str | None:
    for sp in sp_dirs:
        p = os.path.join(sp, pkg)
        if os.path.isdir(p) and os.path.isfile(os.path.join(p, "__init__.py")):
            return p
    return None


def pkg_metrics(root: str) -> tuple[int, int, int]:
    """(不含包根的 .py 数, 顶层模块文件数, 含 __init__.py 的直接子包数)。"""
    excl = top = sub = 0
    for dname, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        pys = [f for f in files if f.endswith(".py")]
        if dname == root:
            excl += len(pys) - 1                      # 扣掉包根 __init__.py
            top = len([f for f in pys if f != "__init__.py"])
            sub = len([d for d in dirs
                       if os.path.isfile(os.path.join(dname, d, "__init__.py"))])
        else:
            excl += len(pys)
    return excl, top, sub


def disk_modules(root: str) -> set[str]:
    """包内模块的点分名（子包以其包名计入，包根不计）。"""
    out: set[str] = set()
    for dname, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(dname, fn), root)[:-3].replace(os.sep, ".")
            if rel.endswith(".__init__"):
                rel = rel[: -len(".__init__")]
            if rel in ("__init__", ""):
                continue
            out.add(rel)
    return out


def pool(root: str, mod: str) -> set[str] | None:
    """该模块自身命名空间里的顶层名字（含私有名；子包含 `__init__.py` 再导出）。"""
    parts = mod.split(".")
    py = os.path.join(root, *parts) + ".py"
    init = os.path.join(root, *parts, "__init__.py")
    fp = py if os.path.isfile(py) else (init if os.path.isfile(init) else None)
    if fp is None:
        return None
    with open(fp, encoding="utf-8", errors="replace") as fh:
        tree = ast.parse(fh.read())
    names: set[str] = set()
    alls: set[str] = set()
    is_pkg = fp == init

    def block(body):
        nonlocal names, alls
        for n in body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(n.name)
            elif isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                tgts = n.targets if isinstance(n, ast.Assign) else [n.target]
                for t in tgts:
                    if not isinstance(t, ast.Name):
                        continue
                    val = getattr(n, "value", None)
                    if t.id == "__all__" and isinstance(val, (ast.List, ast.Tuple)):
                        alls |= {e.value for e in val.elts if isinstance(e, ast.Constant)}
                    else:
                        names.add(t.id)
            elif isinstance(n, ast.If):
                block(n.body)
                block(n.orelse)
            elif isinstance(n, ast.Try):
                block(n.body)
                block(n.orelse)
                block(n.finalbody)
                for h in n.handlers:
                    block(h.body)
            elif isinstance(n, ast.With):
                block(n.body)
            elif is_pkg and isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    names.add(a.asname or a.name.split(".")[0])

    block(tree.body)
    return (names | alls) - {"annotations"}


def public_defs(path: str) -> tuple[int, int]:
    """顶层（不以下划线开头）类与函数的个数——`11` 各节「规模」行的口径。"""
    with open(path, encoding="utf-8", errors="replace") as fh:
        tree = ast.parse(fh.read())
    cls = fn = 0
    for n in tree.body:
        if not isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if n.name.startswith("_"):
            continue
        if isinstance(n, ast.ClassDef):
            cls += 1
        else:
            fn += 1
    return cls, fn


# `11-library-support.md` 各节的「规模」行：按 `## N. \`模块名\`` 标题定位所属顶层模块文件
SUPPORT_DOC = "11-library-support.md"
SUPPORT_HEAD = re.compile(r"^## \d+\. `([a-z_][a-z0-9_]*)`")
SUPPORT_SCALE = re.compile(r"\*\*规模\*\*：(\d+) 类 / (\d+) 函数")


def check_support(sp_dirs: list[str]) -> tuple[list[str], int]:
    """对账 `11` 的「N 类 / M 函数」声明；返回（问题列表，核对条数）。"""
    with open(os.path.join(REF, SUPPORT_DOC), encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    problems: list[str] = []
    mod: str | None = None
    n = 0
    for i, ln in enumerate(lines, 1):
        h = SUPPORT_HEAD.match(ln)
        if h:
            mod = h.group(1)
            continue
        if ln.startswith("## "):
            mod = None
        s = SUPPORT_SCALE.search(ln)
        if not s or mod is None:
            continue
        n += 1
        py = next((os.path.join(sp, mod + ".py") for sp in sp_dirs
                   if os.path.isfile(os.path.join(sp, mod + ".py"))), None)
        if py is None:
            problems.append("L%d %s：已装包中找不到顶层模块文件 %s.py" % (i, mod, mod))
            continue
        got = public_defs(py)
        want = (int(s.group(1)), int(s.group(2)))
        if got != want:
            problems.append("L%d %s：文档写 %d 类 / %d 函数，源码实测 %d 类 / %d 函数"
                            % (i, mod, want[0], want[1], got[0], got[1]))
    return problems, n


def iter_rows(lines: list[str], style: str, pkg: str):
    prefix = ""
    for i, ln in enumerate(lines, 1):
        m = re.match(r"^### 1\.\d+\s+(.+?)（\d+ 个", ln) or re.match(r"^### 2\.\d+\b", ln)
        if m and style == "grouped" and m.lastindex:
            g = m.group(1).strip("`").rstrip(".*")
            prefix = g.split(pkg + ".")[-1] if g != "(top)" else ""
        if not ln.startswith("| `"):
            continue
        cells = [c.strip() for c in ln.replace(r"\|", "\u00a6").split("|")]
        name = cells[1].strip("`") if len(cells) > 1 else ""
        if not re.fullmatch(r"[\w][\w.]*", name):
            continue
        if style == "bare":
            mod = name
        elif style == "dotted":
            if not name.startswith(pkg + "."):
                continue
            mod = name[len(pkg) + 1:]
        else:
            mod = name[len(pkg) + 1:] if name.startswith(pkg + ".") else (
                (prefix + "." if prefix else "") + name)
        tail = [c for c in cells[2:] if c]
        yield i, mod, (tail[-1] if tail else "")


def api_names(cell: str) -> list[str]:
    out: list[str] = []
    for tok in re.split(r"[,;，、]| / ", cell):
        tok = tok.strip().strip("`")
        m = re.match(r"^(?:[\w./-]+\.py::)?([A-Za-z_]\w*)", tok)
        if m:
            out.append(m.group(1))
    return out


def check(spec: dict, root: str) -> list[str]:
    with open(os.path.join(REF, spec["doc"]), encoding="utf-8") as fh:
        text = fh.read()
    lines = text.split("\n")
    problems: list[str] = []

    excl, top, sub = pkg_metrics(root)
    for label, got, want in (("不含包根的 .py", excl, spec["py_excl_root"]),
                             ("顶层模块文件", top, spec["top_mods"]),
                             ("子包数", sub, spec["subpkgs"])):
        if want is not None and got != want:
            problems.append("磁盘 %s = %d，文档口径 %d（库版本变了就同步改文档与 SPECS）" % (label, got, want))
    for phrase in spec["claims"]:
        if phrase not in text:
            problems.append("文档头部口径句缺失：%r" % phrase)

    seen: dict[str, list[int]] = {}
    head = None
    for ln in lines:
        if ln.startswith("## "):       # 离开清单区，停止按组累计行数
            head = None
            continue
        m = re.match(r"^### (1\.\d+|2\.\d+)([^\n]*)", ln)
        if m:
            head = m.group(1)
            c = re.search(r"（(\d+) 个", m.group(2))
            if c:
                seen.setdefault(head, [int(c.group(1)), 0])
        elif ln.startswith("| `") and head in seen:
            seen[head][1] += 1
    for h, (want, got) in seen.items():
        if want != got:
            problems.append("组 %s 标题写 %d 个，表内 %d 行" % (h, want, got))

    cited: set[str] = set()
    n_rows = 0
    for i, mod, api in iter_rows(lines, spec["style"], spec["pkg"]):
        n_rows += 1
        cited.add(mod)
        p = pool(root, mod)
        if p is None:
            problems.append("L%d %s.%s：已装包中不存在" % (i, spec["pkg"], mod))
            continue
        for nm in api_names(api):
            if nm in p:
                continue
            m2 = re.search(r"([\w./-]+)\.py::" + re.escape(nm), api)
            if m2:
                path = m2.group(1).replace("/", ".")
                cand = path if path.startswith(mod) else mod + "." + path
                sub_pool = pool(root, cand)
                if sub_pool is not None and nm in sub_pool:
                    continue
            problems.append("L%d %s.%s：API 名 `%s` 不在该模块命名空间" % (i, spec["pkg"], mod, nm))
    if n_rows != spec["rows"]:
        problems.append("表内 %d 行，文档口径 %d 行" % (n_rows, spec["rows"]))
    for m in sorted(disk_modules(root) - cited):
        if os.path.isdir(os.path.join(root, *m.split("."))):
            continue  # 子包目录由分组标题代表
        if spec["style"] == "bare" and "." in m:
            continue  # 10 只到顶层条目：子包内部的模块由该子包那一行代表
        problems.append("已装包模块 %s.%s 未进表" % (spec["pkg"], m))
    return problems


def main() -> int:
    sp_dirs = find_site_packages()
    checked = 0
    failed = False
    for spec in SPECS:
        root = locate(sp_dirs, spec["pkg"])
        if root is None:
            print("SKIP：未找到已装包 %s，%s 未核对" % (spec["pkg"], spec["doc"]))
            continue
        checked += 1
        problems = check(spec, root)
        if problems:
            failed = True
            print("[FAIL] %s（%d 处）" % (spec["doc"], len(problems)))
            for p in problems[:40]:
                print("       " + p)
            if len(problems) > 40:
                print("       ...另有 %d 处" % (len(problems) - 40))
        else:
            print("[PASS] %s：%d 行与已装 %s 包对账一致" % (spec["doc"], spec["rows"], spec["pkg"]))
    if checked == 0:
        print("SKIP：hermes-agent 未安装，清单文档与「规模」声明均未核对")
        return 2

    problems, n = check_support(sp_dirs)
    if n == 0:
        print("SKIP：%s 没有可核对的「规模」行" % SUPPORT_DOC)
    elif problems:
        failed = True
        print("[FAIL] %s（%d 处）" % (SUPPORT_DOC, len(problems)))
        for p in problems[:40]:
            print("       " + p)
    else:
        print("[PASS] %s：%d 条「规模」声明与源码实测一致" % (SUPPORT_DOC, n))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
