#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_skill_gate.py — hermes-desktop 技能自身结构门禁（SKILL.md §0 上游漂移跟踪 / §6 铁律「反复核实」）。

校验 SKILL.md 引用的关键文件是否齐备、hermes-llms-full.txt 是否原位且体积合理。
任何「关键文件」缺失则整体失败（退出码 1）。

用法：
    python scripts/check_skill_gate.py
    python scripts/check_skill_gate.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

SKILL_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# SKILL.md §4 引用的关键文件（相对技能根）。标记为 critical 的缺失即判失败。
EXPECTED = [
    ("SKILL.md", True),
    ("hermes-llms-full.txt", True),
    ("references/00-index.md", True),
    ("references/01-library-api.md", True),
    ("references/02-integration-core.md", True),
    ("references/03-capabilities-and-toolsets.md", True),
    ("references/04-rendering-frameworks.md", True),
    ("references/05-install-and-env.md", True),
    ("references/06-packaging.md", True),
    ("references/07-quality-gates.md", True),
    ("references/08-capability-integration.md", True),
    ("references/09-integration-e2e.md", False),
    ("references/10-hermes-cli.md", True),
    ("scripts/api-baseline.json", True),
    ("scripts/track_upstream.py", True),
    ("scripts/check_api_signature.py", True),
    ("scripts/probe_library.py", True),
    ("scripts/check_skill_gate.py", True),
    ("scripts/quality_check.py", True),
    ("scripts/release_gate.py", True),
    ("scripts/check_endpoints.py", True),
    ("scripts/smoke_test_web.py", True),
    ("scripts/check_js_modules.py", True),
    ("scripts/ui_window_verify.py", True),
    ("scripts/ui_automate.py", True),
    ("docs/delivery-checklist.md", False),
    ("docs/troubleshooting.md", False),
    ("docs/glossary.md", False),
    ("CHANGELOG.md", False),
    ("examples/01-hermes-desktop/README.md", False),
    ("examples/01-hermes-desktop/test_bridge.py", False),
    ("templates/README.md", False),
]

# hermes-llms-full.txt 体积安全范围（基线 3,273,648 bytes；低于 1MB 视为损坏）
DOCS_MIN_SIZE = 1_000_000


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="技能结构门禁")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    rows = []
    critical_fail = False
    for rel, critical in EXPECTED:
        fp = os.path.join(SKILL_ROOT, rel)
        exists = os.path.isfile(fp)
        if not exists and critical:
            critical_fail = True
        rows.append({"path": rel, "exists": exists, "critical": critical})

    # 文档体积校验
    docs_path = os.path.join(SKILL_ROOT, "hermes-llms-full.txt")
    docs_ok = True
    docs_note = ""
    if os.path.isfile(docs_path):
        sz = os.path.getsize(docs_path)
        if sz < DOCS_MIN_SIZE:
            docs_ok = False
            docs_note = f"体积异常 ({sz} bytes < {DOCS_MIN_SIZE})，可能损坏"
    else:
        docs_ok = False
        docs_note = "缺失"

    if args.json:
        print(json.dumps(
            {"rows": rows, "docs_ok": docs_ok, "docs_note": docs_note,
             "critical_fail": critical_fail},
            indent=2, ensure_ascii=False,
        ))
    else:
        print(f"技能结构门禁 ({SKILL_ROOT})")
        print("=" * 60)
        for r in rows:
            mark = "✅" if r["exists"] else ("❌" if r["critical"] else "⚠️ ")
            tag = " [关键]" if r["critical"] else ""
            print(f"{mark} {r['path']}{tag}")
        print("-" * 60)
        print(f"hermes-llms-full.txt: {'✅' if docs_ok else '❌ ' + docs_note}")
        print("=" * 60)
        if critical_fail or not docs_ok:
            print("❌ 门禁失败：存在缺失的关键文件或文档异常。补齐后再提交。")
        else:
            missing_opt = [r["path"] for r in rows if not r["exists"]]
            if missing_opt:
                print(f"✅ 关键文件齐全。可选/参考文件未生成（不影响核心门禁）：{missing_opt}")
            else:
                print("✅ 全部文件齐备。")

    return 1 if (critical_fail or not docs_ok) else 0


if __name__ == "__main__":
    sys.exit(main())
