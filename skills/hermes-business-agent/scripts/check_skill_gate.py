#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_skill_gate.py — hermes-business-agent 技能自身结构门禁。

对应 SKILL.md 工作流第 ⑧ 步（交付）的「技能自身」维度：交付前确认主线引用的每份素材
仍原位存在，且磁盘上新增的素材已登记进主线（避免"写了文档但主线读不到"的孤儿文件）。

两个方向各一条检查：
  1) 正向：EXPECTED 清单（本文件下方，对应 SKILL.md 主线各引用点）逐项 exists。
     critical 项缺失 → 退出码 1。
  2) 反向：references/ 与 scripts/ 目录下实际存在、却未登记在 EXPECTED 的文件 → 记为孤儿，
     退出码 1（新增文档/脚本必须同时登记进主线清单）。
另加一条体积合理性检查：hermes-llms-full.txt 存在且不小于 DOCS_MIN_SIZE。

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

# SKILL.md 主线（入场检查 + 八步 + 回路）引用的关键文件（相对技能根）。critical 缺失即判失败。
# 按主线步骤归组，改哪一步的素材就动哪一段，避免清单与实际引用漂移。
EXPECTED = [
    # 主线本体与全量事实源
    ("SKILL.md", True),
    ("hermes-llms-full.txt", True),                    # 入场检查：官方文档全文，语义权威源
    ("CHANGELOG.md", True),                            # 第 ⑧ 步：版本记录（release_gate 校验版本一致）
    # 入场检查：上游没漂 + 语义权威源 + 环境可跑性
    ("references/00-index.md", True),
    ("references/01-library-api.md", True),
    ("references/docs-baseline.json", True),
    ("references/api-reference/01-run-agent.md", False),   # 自动生成，可 --regenerate-apiref
    ("scripts/api-baseline.json", True),
    ("scripts/track_upstream.py", True),
    ("scripts/check_api_signature.py", True),
    ("scripts/probe_library.py", True),
    ("scripts/gen_api_reference.py", True),
    # 第 ①② 步：定业务契约与定形态（路线/形态/分层）
    ("references/02-integration-core.md", True),
    ("references/15-api-server.md", True),
    ("references/16-gateway-package.md", True),
    ("references/18-tristructure-architecture.md", True),
    ("references/19-business-domain-model.md", True),
    # 第 ③ 步：最小可对话内核（环境与内核可行性已并入入场检查）
    ("references/05-install-and-env.md", True),
    ("references/03-capabilities-and-toolsets.md", True),
    ("references/10-hermes-cli.md", True),
    ("references/11-library-support.md", True),
    ("references/12-tools-modules.md", True),
    ("references/13-agent-modules.md", True),
    ("references/14-library-infra.md", True),
    # 第 ④ 步：接界面
    ("references/04-rendering-frameworks.md", True),
    ("templates/README.md", False),
    ("templates/fasthtml_minimal/main.py", False),
    ("templates/tkinter_minimal/main.py", False),
    # 第 ⑤ 步：赋业务（输出契约 / 能力语义）
    ("references/08-capability-integration.md", True),
    ("references/20-output-contract-and-golden-set.md", True),
    # 第 ⑥ 步：立闸门（含上线后运营与降级）
    ("references/21-operations-and-degradation.md", True),
    ("references/17-debug-discipline.md", True),
    # 第 ⑦ 步：取证
    ("references/07-quality-gates.md", True),
    ("references/09-integration-e2e.md", True),
    ("scripts/quality_check.py", True),
    ("scripts/check_golden_coverage.py", True),     # 第 ⑤⑦ 步：用例↔契约对账（跑在业务项目上）
    ("scripts/check_endpoints.py", True),
    ("scripts/check_js_modules.py", True),
    ("scripts/smoke_test_web.py", True),
    ("scripts/ui_window_verify.py", True),
    ("scripts/ui_automate.py", True),
    # 第 ⑧ 步：交付（门禁、打包、验收基线）
    ("references/06-packaging.md", True),
    ("docs/delivery-checklist.md", False),
    ("docs/glossary.md", False),
    ("docs/troubleshooting.md", False),
    ("scripts/check_doc_links.py", True),
    ("scripts/release_gate.py", True),
    ("scripts/check_skill_gate.py", True),
    ("scripts/check_api_server.py", True),             # 路线④⑤ 条件门禁
    ("scripts/verify_tristructure.py", True),          # 三系统形态条件门禁
    # 参考实现（Agent系统 为外部 submodule，未初始化时不阻断）
    ("examples/README.md", False),
    ("examples/01-hermes-desktop/README.md", True),    # 三目录关系 + submodule 初始化
    ("examples/01-hermes-desktop/替换Agent系统.md", True),  # 底座三步替换法（verify_tristructure 硬门禁）
    ("examples/01-hermes-desktop/业务系统/app.py", False),
    ("examples/01-hermes-desktop/连接系统/bridge.py", False),
    ("examples/01-hermes-desktop/Agent系统/test_bridge.py", False),
]

# 反向登记范围：这些目录下的自有文件必须出现在 EXPECTED 中（否则视为孤儿）。
# Agent系统/ 是外部底座、__pycache__/api-reference 为产物，均排除。
REGISTRY_DIRS = [("references", ".md"), ("scripts", ".py"), ("docs", ".md")]

# hermes-llms-full.txt 体积安全范围（当前基线 5,005,104 bytes，唯一真相见 references/docs-baseline.json；低于 1MB 视为下载损坏）
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

    # 反向：磁盘上有、清单里没有 → 孤儿文件（主线读不到它，等于没写）
    registered = {rel for rel, _ in EXPECTED}
    orphans = []
    for sub, ext in REGISTRY_DIRS:
        d = os.path.join(SKILL_ROOT, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.startswith(".") or name.startswith("__"):
                continue
            rel = f"{sub}/{name}"
            if os.path.isfile(os.path.join(SKILL_ROOT, rel.replace("/", os.sep))) \
                    and name.endswith(ext) and rel not in registered:
                orphans.append(rel)

    # hermes-llms-full.txt 体积合理性
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
             "orphans": orphans, "critical_fail": critical_fail,
             "ok": (not critical_fail) and docs_ok and not orphans},
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
        if orphans:
            print(f"❌ 未登记的孤儿素材（主线读不到 = 等于没写，请补进 EXPECTED 或删除）:")
            for o in orphans:
                print(f"   ⚠️  {o}")
        print("=" * 60)
        if critical_fail or not docs_ok or orphans:
            print("❌ 门禁失败：存在缺失的关键文件、文档异常或未登记素材。补齐后再提交。")
        else:
            missing_opt = [r["path"] for r in rows if not r["exists"]]
            if missing_opt:
                print(f"✅ 关键文件齐全。可选/参考文件未生成（不影响核心门禁）：{missing_opt}")
            else:
                print("✅ 全部文件齐备。")

    return 1 if (critical_fail or not docs_ok or orphans) else 0


if __name__ == "__main__":
    sys.exit(main())
