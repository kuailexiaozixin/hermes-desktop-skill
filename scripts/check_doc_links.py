#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_doc_links.py — 文档相对链接完整性检查。

扫描 SKILL.md、references/、templates/、docs/、examples/ 下的 .md 文件，
校验其中 markdown 相对链接（`[text](target)`）指向的目标是否存在。
忽略 http(s)/mailto/#锚点 及纯锚点链接。发现断链返回 1。

用法：
    uv run python scripts/check_doc_links.py            # 全量扫描
    uv run python scripts/check_doc_links.py --root DIR # 指定技能根目录
退出码：0 = 无断链；1 = 有断链。
"""
from __future__ import annotations

import argparse
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
SCAN_ITEMS = ["SKILL.md", "references", "templates", "docs"]  # 技能自有文档
SCAN_ITEMS_EXAMPLES = ["examples"]  # 第三方案例（默认跳过）

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _collect_md_files(root: str, include_examples: bool = False,
                      include_api_ref: bool = False) -> list[str]:
    items = list(SCAN_ITEMS)
    if include_examples:
        items += SCAN_ITEMS_EXAMPLES
    api_ref_marker = os.path.join("references", "api-reference")
    files = []
    for item in items:
        p = os.path.join(root, item)
        if os.path.isfile(p):
            files.append(p)
        elif os.path.isdir(p):
            for r, _d, fs in os.walk(p):
                # 默认排除自动生成的 api-reference（docstring 内嵌占位链接不受控）
                if not include_api_ref and api_ref_marker in os.path.normpath(r):
                    continue
                for f in fs:
                    if f.endswith(".md"):
                        files.append(os.path.join(r, f))
    return files


def check(root: str, include_examples: bool = False,
          include_api_ref: bool = False) -> tuple[int, list[tuple[str, str]]]:
    broken: list[tuple[str, str]] = []
    checked = 0
    for fp in _collect_md_files(root, include_examples, include_api_ref):
        with open(fp, encoding="utf-8", errors="replace") as f:
            src = f.read()
        for m in LINK_RE.finditer(src):
            target = m.group(1).strip()
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            t = target.split("#")[0].strip()
            if not t:
                continue
            dest = os.path.normpath(os.path.join(os.path.dirname(fp), t))
            checked += 1
            if not os.path.exists(dest):
                broken.append((os.path.relpath(fp, root), target))
    return checked, broken


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="文档相对链接完整性检查")
    p.add_argument("--root", default=DEFAULT_ROOT, help="技能根目录")
    p.add_argument("--include-examples", action="store_true", help="同时检查 examples/ 第三方案例（其 README 引用上游文档，默认跳过）")
    p.add_argument("--include-api-ref", action="store_true", help="同时检查自动生成的 references/api-reference（docstring 占位链接，默认跳过）")
    args = p.parse_args(argv)
    checked, broken = check(args.root, args.include_examples, args.include_api_ref)
    print(f"文档链接检查 (root={args.root})")
    for bf, tgt in broken:
        print(f"  [断链] {bf}  ->  {tgt}")
    print(f"检查 {checked} 个相对链接，断链 {len(broken)} 个")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
