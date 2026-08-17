#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_tristructure.py — 三系统架构验证门禁（可选模式）。

三系统架构是「单工程内嵌」的可选升级（见 references/18-tristructure-architecture.md）。
本脚本仅在检测到三系统骨架（业务系统/ + 连接系统/ + 替换Agent系统.md）时执行门禁；
未启用三系统 → 报告 SKIP，不阻断。

硬门禁（任一失败则非零退出）：
  [0] structure_ok        —— 三系统骨架齐全（业务系统/、连接系统/、替换Agent系统.md 存在）
  [1] biz_no_agent_import —— 业务系统无 import 任何 Agent 系统模块
                             （server / routes / agent_runtime / tools / hermes_config / app_tools / hermes_*）
  [2] conn_unique_assembly—— 「from server import」只允许出现在连接系统（唯一装配点）
  [3] biz_independent_entry—— 业务系统有独立入口（app.py + 启动.bat / 启动.bat）
  [4] agent_purity        —— Agent系统（三系统根）无业务痕迹（无业务模块名 / 业务技能目录）

用法：
  python scripts/verify_tristructure.py                    # 默认检查 examples/01-hermes-desktop
  python scripts/verify_tristructure.py --root <三系统根>   # 检查指定三系统根目录

退出码：0 = 通过（或未启用三系统 SKIP）；1 = 三系统门禁有失败。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

# Agent 系统模块的 import 特征（业务系统一旦 import 即视为耦合破坏）
_AGENT_MODULES = (
    "server", "routes", "agent_runtime", "hermes_config", "hermes_features",
    "app_tools", "channels", "sessions", "memory_providers", "context_provider",
    "unified_skills_client", "wiki_engine", "hermes_skills_client", "skillhub_client",
    "mcpstore_client", "host_tools", "file_tools", "file_preview", "cron_scheduler",
)
# 形如 from X import Y / import X(.Y) 的 import 语句
_IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)

# 业务系统内允许自身模块/标准库/第三方，但不得触及上述 Agent 模块
def _imported_names(text: str) -> list[str]:
    names = []
    for m in _IMPORT_RE.finditer(text):
        top = (m.group(1) or m.group(2)).split(".")[0]
        names.append(top)
    return names


def _is_agent_import(top: str) -> bool:
    return top in _AGENT_MODULES or top.startswith("hermes_") or top == "agent"


class Gate:
    def __init__(self, root: Path):
        self.root = root
        self.checks: list[tuple[str, str, bool, str]] = []  # (id, desc, ok, detail)

    def add(self, cid: str, desc: str, ok: bool, detail: str = ""):
        self.checks.append((cid, desc, ok, detail))

    def run(self):
        biz = self.root / "业务系统"
        conn = self.root / "连接系统"
        replace_doc = self.root / "替换Agent系统.md"

        # [0] 骨架
        skeleton = biz.is_dir() and conn.is_dir() and replace_doc.is_file()
        self.add("structure_ok", "三系统骨架齐全（业务系统/ + 连接系统/ + 替换Agent系统.md）",
                 skeleton,
                 "、".join(
                     ("业务系统/" if biz.is_dir() else "缺 业务系统/",
                      "连接系统/" if conn.is_dir() else "缺 连接系统/",
                      "替换Agent系统.md" if replace_doc.is_file() else "缺 替换Agent系统.md")))

        # [1] 业务系统无 Agent import
        biz_agent_imports = []
        if biz.is_dir():
            for f in sorted(biz.rglob("*.py")):
                if "__pycache__" in f.parts:
                    continue
                try:
                    txt = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                for top in _imported_names(txt):
                    if _is_agent_import(top):
                        biz_agent_imports.append(f"{f.relative_to(self.root)}: {top}")
        self.add("biz_no_agent_import", "业务系统无 import Agent 模块",
                 not biz_agent_imports,
                 "；".join(biz_agent_imports[:10]) if biz_agent_imports else "OK")

        # [2] 连接唯一装配点：from server import 只允许在连接系统
        server_import_sites = []
        for sub in ("业务系统", "连接系统"):
            d = self.root / sub
            if not d.is_dir():
                continue
            for f in sorted(d.rglob("*.py")):
                if "__pycache__" in f.parts:
                    continue
                try:
                    txt = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                if re.search(r"^\s*from\s+server\s+import", txt, re.M):
                    server_import_sites.append(f"{f.relative_to(self.root)}")
        # 允许连接系统有 from server import；禁止业务系统
        ok2 = all("业务系统" not in s for s in server_import_sites)
        self.add("conn_unique_assembly",
                 "「from server import」仅存在于连接系统（唯一装配点）",
                 ok2,
                 "；".join(server_import_sites) if server_import_sites else "未发现 server import")

        # [3] 业务系统独立入口
        entry_ok = False
        entry_detail = []
        if biz.is_dir():
            has_app = (biz / "app.py").is_file()
            has_bat = (biz / "启动.bat").is_file()
            entry_ok = has_app and has_bat
            entry_detail = [("app.py" if has_app else "缺 app.py"),
                            ("启动.bat" if has_bat else "缺 启动.bat")]
        self.add("biz_independent_entry", "业务系统有独立入口（app.py + 启动.bat）",
                 entry_ok, "、".join(entry_detail) if entry_detail else "OK")

        # [4] Agent 系统（= 三系统根）无业务痕迹
        biz_markers = ("rdapp", "业务", "费用系统", "项目系统")
        found_markers = []
        if self.root.is_dir():
            for name in self.root.iterdir():
                nm = name.name
                if nm in ("业务系统", "连接系统", "替换Agent系统.md"):
                    continue
                if any(m in nm for m in biz_markers):
                    found_markers.append(nm)
        self.add("agent_purity", "Agent系统（三系统根）无业务痕迹",
                 not found_markers,
                 "；".join(found_markers) if found_markers else "OK")


def main() -> int:
    ap = argparse.ArgumentParser(description="三系统架构验证门禁")
    ap.add_argument("--root", default=str(SKILL_ROOT / "examples" / "01-hermes-desktop"),
                    help="三系统根目录（默认 examples/01-hermes-desktop）")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    if not root.is_dir():
        print(f"[verify_tristructure] 根目录不存在: {root}")
        return 1

    biz = root / "业务系统"
    conn = root / "连接系统"
    replace_doc = root / "替换Agent系统.md"
    if not (biz.is_dir() and conn.is_dir() and replace_doc.is_file()):
        print(f"[verify_tristructure] SKIP：{root} 未启用三系统架构（无 业务系统/ + 连接系统/ + 替换Agent系统.md）")
        return 0

    g = Gate(root)
    g.run()

    print(f"[verify_tristructure] 三系统门禁 — 根目录: {root}")
    all_ok = True
    for cid, desc, ok, detail in g.checks:
        flag = "PASS" if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"  [{flag}] {cid}: {desc}")
        if detail and detail != "OK":
            print(f"        └─ {detail}")

    print(f"\n[verify_tristructure] 结果: {'全部通过' if all_ok else '存在失败（阻断交付）'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
