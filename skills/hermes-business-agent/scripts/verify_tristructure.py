#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_tristructure.py — 三系统架构验证门禁（可选模式）。

三系统架构是「单工程内嵌」的可选升级（见 references/18-tristructure-architecture.md）。
本脚本仅在检测到三系统骨架时执行门禁；未启用三系统 → 报告 SKIP，不阻断。
判据（_tristructure_enabled）：业务系统/ + 连接系统/ + （Agent系统/ 或 替换Agent系统.md）。

硬门禁（任一 FAIL 则非零退出）：
  [0] structure_ok        —— 三系统骨架齐全：业务系统/ + 连接系统/ + （Agent系统/ 或 替换Agent系统.md）
  [1] biz_no_agent_import —— 业务系统的 .py 顶层 import 不落在 _AGENT_MODULES 名单内，
                             且不以 hermes_ 开头、不等于 agent（名单以本文件常量为准）
  [2] conn_unique_assembly—— 只扫 业务系统/ 与 连接系统/ 两处，断言「from server import」在业务系统零命中
                             （Agent系统/ 与根目录不在扫描范围内；它查"业务侧不自行装配"，不查全仓装配点散落）
  [3] biz_independent_entry—— 业务系统有独立入口：app.py 与 启动.bat 都在位
  [4] agent_purity        —— 三系统根的顶层条目名无业务痕迹（不递归其内容）
  [6] replace_doc         —— 替换Agent系统.md 在位（缺它 = 底座不可安全替换）

软门禁（"软"只在取不到证据时成立）：
  [5] agent_zero_diff     —— 底座零差异：用 git status --porcelain --untracked-files=no 判 Agent系统/
                             工作区是否被本地改动，并打印 HEAD 短 sha 供人工比对上游。
                             四类取不到证据的情形判 SKIP 不阻断（--strict 下才计失败）：
                             无 Agent系统/ 目录 / 该目录非 git 仓库或 submodule 未初始化 /
                             git 命令不可用 / git status 执行失败。
                             一旦 git 可用且检出改动，它是 FAIL 并阻断——不是"记录一下"。
                             注：本检查不联网，故只验「没被本地改动」，不验「与上游最新版一致」；
                             后者由人工按 18 §6 三步替换法执行，漂移监测用 track_upstream.py。

用法：
  python scripts/verify_tristructure.py                    # 默认检查 examples/01-hermes-desktop
  python scripts/verify_tristructure.py --root <三系统根>   # 检查指定三系统根目录
  python scripts/verify_tristructure.py --strict           # 软门禁 SKIP 也算失败

退出码：0 = 通过（或未启用三系统 SKIP）；1 = 三系统门禁有失败。
"""
from __future__ import annotations

import argparse
import re
import subprocess
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


def _tristructure_enabled(root: Path) -> bool:
    """三系统骨架判据：业务系统/ + 连接系统/ + （Agent系统/ 或 替换Agent系统.md）。

    注意：`替换Agent系统.md` 是 18 §5 第 4 步要求的说明文件，历史上曾作为**唯一**判据，
    导致缺该文件时门禁整体静默 SKIP（连四条硬门禁都不跑）。现以 `Agent系统/` 目录为主判据。
    """
    return ((root / "业务系统").is_dir() and (root / "连接系统").is_dir()
            and ((root / "Agent系统").is_dir() or (root / "替换Agent系统.md").is_file()))

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
        self.checks: list[tuple[str, str, str, str]] = []  # (id, desc, status, detail)

    def add(self, cid: str, desc: str, ok: bool, detail: str = ""):
        self.checks.append((cid, desc, "PASS" if ok else "FAIL", detail))

    def skip(self, cid: str, desc: str, detail: str = ""):
        self.checks.append((cid, desc, "SKIP", detail))

    def run(self):
        biz = self.root / "业务系统"
        conn = self.root / "连接系统"
        agent = self.root / "Agent系统"
        replace_doc = self.root / "替换Agent系统.md"

        # [0] 骨架
        skeleton = _tristructure_enabled(self.root)
        self.add("structure_ok", "三系统骨架齐全（业务系统/ + 连接系统/ + Agent系统/ 或 替换Agent系统.md）",
                 skeleton,
                 "、".join(
                     ("业务系统/" if biz.is_dir() else "缺 业务系统/",
                      "连接系统/" if conn.is_dir() else "缺 连接系统/",
                      "Agent系统/" if agent.is_dir() else ("替换Agent系统.md" if replace_doc.is_file()
                                                           else "缺 Agent系统/ 与 替换Agent系统.md"))))

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

        # [5] 底座零差异（软门禁；不可判定时 SKIP，不阻断）
        if not agent.is_dir():
            self.skip("agent_zero_diff", "底座零差异（Agent系统/ 未被本地改动）",
                      "SKIP：无 Agent系统/ 目录（单工程内嵌形态无此概念）")
        elif not (agent / ".git").exists():
            self.skip("agent_zero_diff", "底座零差异（Agent系统/ 未被本地改动）",
                      "SKIP：Agent系统/ 非 git 仓库或 submodule 未初始化——先 `git submodule update --init`；"
                      "仍不可得则记为「未验证」并沉淀到 docs/troubleshooting.md（离线不得当作通过）")
        else:
            try:
                dirty = subprocess.run(
                    ["git", "-C", str(agent), "status", "--porcelain", "--untracked-files=no"],
                    capture_output=True, text=True, timeout=30,
                )
                head = subprocess.run(["git", "-C", str(agent), "rev-parse", "--short", "HEAD"],
                                      capture_output=True, text=True, timeout=30)
            except Exception as e:  # 无 git 可执行 / 超时
                self.skip("agent_zero_diff", "底座零差异（Agent系统/ 未被本地改动）",
                          f"SKIP：git 不可用（{type(e).__name__}: {e}）——离线降级为未验证")
            else:
                if dirty.returncode != 0:
                    self.skip("agent_zero_diff", "底座零差异（Agent系统/ 未被本地改动）",
                              f"SKIP：git status 失败（{(dirty.stderr or '').strip()[:120]}）")
                else:
                    changed = [ln.strip() for ln in dirty.stdout.splitlines() if ln.strip()]
                    sha = (head.stdout or "").strip()
                    self.add("agent_zero_diff", "底座零差异（Agent系统/ 未被本地改动）",
                             not changed,
                             f"HEAD={sha or '?'}；改动文件 {len(changed)} 个：" + "、".join(changed[:8])
                             if changed else f"HEAD={sha or '?'}，工作区干净")

        # [6] 底座替换说明文件（18 §5 第 4 步要求；软门禁）
        self.add("replace_doc", "替换Agent系统.md 在位（底座三步替换法说明）", replace_doc.is_file(),
                 "在位" if replace_doc.is_file() else "缺：按 18 §5 第 4 步补写，缺它底座不可安全替换")


def main() -> int:
    ap = argparse.ArgumentParser(description="三系统架构验证门禁")
    ap.add_argument("--root", default=str(SKILL_ROOT / "examples" / "01-hermes-desktop"),
                    help="三系统根目录（默认 examples/01-hermes-desktop）")
    ap.add_argument("--strict", action="store_true",
                    help="软门禁（agent_zero_diff）SKIP 也算失败")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    if not root.is_dir():
        print(f"[verify_tristructure] 根目录不存在: {root}")
        return 1

    if not _tristructure_enabled(root):
        print(f"[verify_tristructure] SKIP：{root} 未启用三系统架构"
              f"（判据：业务系统/ + 连接系统/ + Agent系统/ 或 替换Agent系统.md）")
        return 0

    g = Gate(root)
    g.run()

    print(f"[verify_tristructure] 三系统门禁 — 根目录: {root}")
    all_ok = True
    skips = []
    for cid, desc, status, detail in g.checks:
        print(f"  [{status}] {cid}: {desc}")
        if detail and detail != "OK":
            print(f"        └─ {detail}")
        if status == "FAIL":
            all_ok = False
        elif status == "SKIP":
            skips.append(cid)

    if skips and args.strict:
        all_ok = False
        print(f"\n[verify_tristructure] --strict：软门禁未验证项 {skips} 视为失败")
    print(f"\n[verify_tristructure] 结果: {'全部通过' if all_ok else '存在失败（阻断交付）'}"
          + (f"（未验证项: {'、'.join(skips)}）" if skips else ""))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
