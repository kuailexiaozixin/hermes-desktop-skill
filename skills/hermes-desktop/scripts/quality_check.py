#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quality_check.py — hermes-desktop 全量质量门禁编排（SKILL.md §5 工作流 / §6 铁律「反复核实」；细节见 references/07-quality-gates.md#gates）

把分散的门禁合成一条命令，CI / 提交前 / 构建前跑一次即可：
  [1] 语法编译       —— 递归 py_compile 所有 .py（agent_runtime / _testkit / test_bridge / 各脚本）
  [2] 技能结构门禁   —— check_skill_gate.py（SKILL.md 引用文件齐备 + hermes-llms-full.txt 在位）
  [3] 离线桥接测试   —— test_bridge.py（注入 FakeAIAgent，无需 hermes-agent / API Key）
  [4] 源码签名漂移   —— check_api_signature.py（若当前 Python 装了 hermes-agent 才比对；否则跳过）

退出码：0 = 无失败（跳过不算失败）；1 = 任一硬性门禁失败。

用法：
    python scripts/quality_check.py
    python scripts/quality_check.py --quiet
"""
from __future__ import annotations

import os
import py_compile
import subprocess
import json
import sys

SKILL_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
EXAMPLE_DIR = os.path.join(SKILL_ROOT, "examples", "01-hermes-desktop")
PY = sys.executable


def _run_step(label: str, cmd: list[str], cwd: str | None = None) -> tuple[bool, str, int]:
    """运行一个子步骤，返回 (passed, output, returncode)。exit 0 = pass；非 0 交给调用方解读。"""
    try:
        proc = subprocess.run(
            [PY, *cmd],
            cwd=cwd or SKILL_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except Exception as e:  # 工具自身炸了
        return False, f"工具异常: {e}", 1
    out = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, out, proc.returncode


def step_pycompile() -> tuple[bool, str]:
    bad = []
    for dirpath, _dirs, files in os.walk(SKILL_ROOT):
        # 跳过产物/缓存目录
        if any(seg in dirpath for seg in ("__pycache__", ".venv", "build", "dist")):
            continue
        for fn in files:
            if fn.endswith(".py"):
                fp = os.path.join(dirpath, fn)
                try:
                    py_compile.compile(fp, doraise=True)
                except py_compile.PyCompileError as e:
                    bad.append(f"{fp}: {e}")
    if bad:
        return False, "编译失败:\n" + "\n".join(bad)
    return True, "全部 .py 语法编译通过"


def step_gate() -> tuple[bool, str]:
    return _run_step("gate", ["scripts/check_skill_gate.py"])


def step_bridge() -> tuple[bool, str]:
    return _run_step("bridge", ["test_bridge.py"], cwd=EXAMPLE_DIR)


def step_signature() -> tuple[bool, str, str]:
    """返回 (status, output, kind)。kind ∈ {pass, fail, skip}。"""
    # 直接调用 check_api_signature.py（内含自动扫描 venv，无需预检），
    # 由它自身 report 去判断是否可以定位 run_agent.py。
    ok, out, rc = _run_step("signature", ["scripts/check_api_signature.py", "--json"])
    if rc == 2:
        # 工具/环境问题（如找不到 run_agent.py、解析失败）降级为跳过，不阻塞发布
        return True, out, "skip"
    return ok, out, ("pass" if ok else "fail")


def step_web_regression() -> tuple[bool, str, str]:
    """[5] 网页回归测试夹具（smoke_test_web --json）。kind ∈ {pass, fail, skip}。

    rc==2（工具/环境问题，如缺 starlette、找不到 main.py）降级为 skip，不阻塞发布。
    从输出中提取 smoke_test_web 的 JSON（其 stdout 为纯 JSON，stderr 混有 main 初始化日志），
    以 failed==0 判定通过。
    """
    ok, out, rc = _run_step("web_regression",
                            ["scripts/smoke_test_web.py", "--json", "--root", EXAMPLE_DIR])
    if rc == 2:
        return True, out, "skip"
    failed = 1
    marker = '"tool": "smoke_test_web"'
    idx = out.find(marker)
    if idx != -1:
        brace = out.rfind("{", 0, idx)
        if brace != -1:
            try:
                data, _ = json.JSONDecoder().raw_decode(out[brace:])
                failed = data.get("failed", 1)
            except Exception:
                failed = 1
    return failed == 0, out, ("pass" if failed == 0 else "fail")

def step_doc_links() -> tuple[bool, str, str]:
    """[6] 文档相对链接完整性检查（check_doc_links.py）。kind ∈ {pass, fail, skip}。

    默认检查人工编写的技能文档（SKILL.md / references / templates / docs），
    排除自动生成的 api-reference 与 examples 第三方案例。rc==2 降级 skip。
    """
    ok, out, rc = _run_step("doc_links", ["scripts/check_doc_links.py"])
    if rc == 2:
        return True, out, "skip"
    return ok, out, ("pass" if ok else "fail")

def main() -> int:
    quiet = "--quiet" in sys.argv[1:]
    results: list[tuple[str, bool, str, str]] = []  # (label, passed, output, kind)

    # [1] py_compile
    p, o = step_pycompile()
    results.append(("语法编译 (py_compile)", p, o, "pass" if p else "fail"))

    # [2] gate
    p, o, _rc = step_gate()
    results.append(("技能结构门禁 (check_skill_gate)", p, o, "pass" if p else "fail"))

    # [3] bridge
    p, o, _rc = step_bridge()
    results.append(("离线桥接测试 (test_bridge)", p, o, "pass" if p else "fail"))

    # [4] signature
    p, o, kind = step_signature()
    results.append(("源码签名漂移 (check_api_signature)", p, o, kind))
    # [5] web_regression
    p, o, kind = step_web_regression()
    results.append(("网页回归测试 (smoke_test_web)", p, o, kind))
    # [6] doc_links
    p, o, kind = step_doc_links()
    results.append(("文档链接完整性 (check_doc_links)", p, o, kind))

    # 输出
    print("=" * 64)
    print(" hermes-desktop 全量质量门禁")
    print("=" * 64)
    n_pass = n_fail = n_skip = 0
    for label, passed, out, kind in results:
        if kind == "skip":
            mark, n_skip = "⚠️ 跳过", n_skip + 1
        elif passed:
            mark, n_pass = "✅", n_pass + 1
        else:
            mark, n_fail = "❌", n_fail + 1
        print(f"  [{mark}] {label}")
        if (not quiet) and out:
            for line in out.splitlines()[-12:]:
                print(f"        {line}")
    print("-" * 64)
    print(f"  结果：{n_pass} 通过 / {n_fail} 失败 / {n_skip} 跳过")
    if n_fail:
        print("❌ 存在失败的硬性门禁，禁止提交/构建。先修掉上面的 ❌。")
        return 1
    print("✅ 全部硬性门禁通过（跳过项不计入失败）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
