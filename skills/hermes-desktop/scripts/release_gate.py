#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
release_gate.py — hermes-desktop 统一发布门禁。

打包前 / 交付前跑一次，串联本技能全部硬性门禁，全绿才放行：

硬门禁（REQUIRED，任一失败则非零退出）：
  [0] track_upstream    —— §0 上游漂移跟踪（--gate 模式：仅「源码签名」破坏性漂移硬阻塞；PyPI 版本 / 文档指纹漂移为提示性，不阻塞；网络不可达时 SKIPPED 不阻塞）
  [1] quality_check     —— py_compile + 技能结构门禁 + 离线桥接测试 + 源码签名漂移
  [2] check_endpoints   —— 前端→后端 路由链路校验（捕获运行时 404 隐患）
  [3] smoke_test_web    —— 网页无头冒烟（结构级：GET / 含关键 DOM id，捕获首页渲染崩溃）
  [4] check_js_modules  —— 前端 ES 模块强制校验（**条件性硬门禁**）：仅当某示例采用
                          「禁用 HTMX/Pico、改用原生 ES 模块前端」（`examples/*/static/**/*.js`
                          存在）时才校验；node 缺失 / 无 JS 前端 → 以退出码 2 SKIP 不阻塞；
                          JS 损坏（模块级括号错误 / 跨文件 import↔export 断链）→ FAIL 阻断。
                          专治「`node --check *.js` 假绿、漏报模块级语法错误拖垮整站」的盲区。
  [5] version_consistency —— SKILL.md frontmatter `version` 与 CHANGELOG 最新 `## [x.y.z]` 一致（杜绝 version 滞后）；
                          不一致时可用 `--bump-version` 从 CHANGELOG 自动同步进 SKILL.md。

CI 建议项（ADVISORY，失败只告警、不阻塞门禁）：
  [6] verify_imports    —— scripts/ 下全部门禁脚本可导入（无循环依赖/缺失引用）
  [7] check_refs        —— references/ 文档中 ```python 代码块语法正确

用法：
  python scripts/release_gate.py                  # 硬门禁 + CI 建议项全跑
  python scripts/release_gate.py --advisory-only # 只跑 CI 建议项
  python scripts/release_gate.py --skip-smoke     # 跳过网页无头冒烟
  python scripts/release_gate.py --skip-endpoints
  python scripts/release_gate.py --skip-quality
  python scripts/release_gate.py --skip-js        # 跳过前端 ES 模块校验
  python scripts/release_gate.py --skip-imports --skip-refs

退出码：0 = 硬门禁通过（CI 建议项失败仅告警）；1 = 硬门禁有 REQUIRED 失败。
"""
from __future__ import annotations

import argparse
import compileall
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# 导入检查跳过的目录（避免误判 venv / 构建产物 / 缓存）
_SKIP_DIRS = {"__pycache__", ".git", "venv", ".venv", "node_modules",
              ".workbuddy", "build", "dist", "_internal"}


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run([PY, *cmd], cwd=SKILL_ROOT,
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=180)
    except Exception as e:  # 工具自身炸了
        return 1, f"工具异常: {e}"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _step(label: str, cmd: list[str], skip_codes: tuple[int, ...] = ()) -> tuple[bool, bool, str]:
    print("\n" + "=" * 64)
    print(f" [{label}]")
    print("=" * 64)
    code, out = _run(cmd)
    for line in out.splitlines()[-25:]:
        print(f"   {line}")
    if code in skip_codes:
        print(f"   [{label}] ⊘ SKIPPED（退出码 {code} 视为跳过，不阻塞）")
        return True, True, out
    return code == 0, False, out


def _check_imports() -> tuple[str, str]:
    """ADVISORY：scripts/ 下全部门禁脚本可导入（不实际执行）。"""
    scripts_dir = SKILL_ROOT / "scripts"
    if not scripts_dir.exists():
        return "WARNING", "scripts/ 不存在"
    failures = []
    count = 0
    for py in sorted(scripts_dir.rglob("*.py")):
        rel = py.relative_to(SKILL_ROOT)
        if any(s in rel.parts for s in _SKIP_DIRS):
            continue
        count += 1
        try:
            r = subprocess.run(
                [PY, "-c",
                 f"import sys; sys.path.insert(0, {str(scripts_dir)!r}); "
                 f"import importlib.util as u; "
                 f"spec = u.spec_from_file_location('__chk__', {str(py)!r}); "
                 f"m = u.module_from_spec(spec); spec.loader.exec_module(m); "
                 f"print('OK')"],
                capture_output=True, text=True, timeout=30,
            )
            if "OK" not in r.stdout:
                failures.append(f"{rel}: 导入失败")
        except Exception as e:  # noqa: BLE001
            failures.append(f"{rel}: 异常 {e}")
    if failures:
        return "WARNING", f"{len(failures)} 个脚本导入失败（CI 建议项）: " + "; ".join(failures[:5])
    return "PASS", f"已检查 {count} 个脚本（CI 建议项）"


def _check_refs() -> tuple[str, str]:
    """ADVISORY：references/ 文档中 ```python 代码块语法正确。"""
    refs_dir = SKILL_ROOT / "references"
    if not refs_dir.exists():
        return "WARNING", "references/ 不存在"
    errors = []
    for md in sorted(refs_dir.rglob("*.md")):
        content = md.read_text(encoding="utf-8")
        in_block, block_lines, block_start = False, [], 0
        for i, line in enumerate(content.splitlines(), 1):
            if line.startswith("```python"):
                in_block, block_lines, block_start = True, [], i
            elif line.startswith("```") and in_block:
                in_block = False
                code = "\n".join(block_lines)
                if len(code.strip()) > 20 and "..." not in code[:50]:
                    try:
                        compile(code, str(md.relative_to(SKILL_ROOT)), "exec")
                    except SyntaxError as e:  # noqa: BLE001
                        errors.append(f"{md.relative_to(SKILL_ROOT)}:{block_start}: {e}")
                block_lines = []
            elif in_block:
                block_lines.append(line)
    if errors:
        return "WARNING", f"{len(errors)} 个代码块语法问题: " + "; ".join(errors[:5])
    return "PASS", "references/ 代码块语法检查通过"


def _read_skill_version() -> str | None:
    """从 SKILL.md frontmatter 读取 version（形如 "1.7.13"）。"""
    skill_md = SKILL_ROOT / "SKILL.md"
    if not skill_md.exists():
        return None
    m = re.search(r'^version:\s*"([^"]+)"', skill_md.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def _read_changelog_latest() -> str | None:
    """从 CHANGELOG.md 读取最新版本号（第一个 ## [x.y.z]）。"""
    ch = SKILL_ROOT / "CHANGELOG.md"
    if not ch.exists():
        return None
    m = re.search(r"^##\s*\[([\w.]+)\]", ch.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def _bump_skill_version(changelog_ver: str) -> bool:
    """把 CHANGELOG 最新版本写入 SKILL.md frontmatter。返回是否发生了改动。"""
    skill_md = SKILL_ROOT / "SKILL.md"
    s = skill_md.read_text(encoding="utf-8")
    s2 = re.sub(r'^version:\s*"[^"]*"', f'version: "{changelog_ver}"', s, count=1, flags=re.M)
    if s2 == s:
        return False
    skill_md.write_text(s2, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="hermes-desktop 统一发布门禁")
    ap.add_argument("--skip-track", action="store_true", help="跳过 track_upstream（上游漂移跟踪）")
    ap.add_argument("--skip-quality", action="store_true", help="跳过 quality_check")
    ap.add_argument("--skip-endpoints", action="store_true", help="跳过 check_endpoints")
    ap.add_argument("--skip-smoke", action="store_true", help="跳过网页无头冒烟")
    ap.add_argument("--skip-js", action="store_true", help="跳过前端 ES 模块校验（check_js_modules）")
    ap.add_argument("--skip-imports", action="store_true", help="跳过导入检查")
    ap.add_argument("--skip-refs", action="store_true", help="跳过文档代码块检查")
    ap.add_argument("--skip-version", action="store_true", help="跳过 SKILL.md 与 CHANGELOG 版本一致性检查")
    ap.add_argument("--bump-version", action="store_true",
                    help="把 CHANGELOG 最新版本号写入 SKILL.md frontmatter（自动同步 version）")
    ap.add_argument("--advisory-only", action="store_true",
                    help="只跑 CI 建议项（verify_imports / check_refs），跳过硬门禁")
    args = ap.parse_args()

    # --bump-version：把 CHANGELOG 最新版本自动同步进 SKILL.md frontmatter（杜绝 version 滞后）
    if args.bump_version:
        ch_ver = _read_changelog_latest()
        if not ch_ver:
            print("❌ 无法从 CHANGELOG.md 读取最新版本号，无法执行 --bump-version。")
            return 1
        if _bump_skill_version(ch_ver):
            print(f"✅ 已把 SKILL.md frontmatter version 同步为 CHANGELOG 最新版 {ch_ver}")
        else:
            print(f"ℹ️ SKILL.md version 已是 {ch_ver}，无需改动（与 CHANGELOG 一致）")

    print("#" * 64)
    print("# hermes-desktop 统一发布门禁 (release_gate)")
    print("#" * 64)

    required_failures = 0
    warnings = 0

    if args.advisory_only:
        steps = []
        print("MODE: --advisory-only（仅 CI 建议项）")
    else:
        print("MODE: 硬门禁（track_upstream + quality_check + check_endpoints + "
              "smoke_test_web + check_js_modules（条件性：无 node/无 JS 前端则 SKIP））")
        steps = [
            ("0/5 track_upstream", ["scripts/track_upstream.py", "--gate"], args.skip_track, ()),
            ("1/5 quality_check", ["scripts/quality_check.py"], args.skip_quality, ()),
            ("2/5 check_endpoints", ["scripts/check_endpoints.py"], args.skip_endpoints, ()),
            ("3/5 smoke_test_web", ["scripts/smoke_test_web.py"], args.skip_smoke, ()),
            ("4/5 check_js_modules", ["scripts/check_js_modules.py"], args.skip_js, (2,)),
        ]

    for label, cmd, skip, skip_codes in steps:
        if skip:
            print(f"\n[{label}] ⨯ SKIPPED")
            continue
        ok, skipped, _ = _step(label, cmd, skip_codes=skip_codes)
        if skipped:
            continue
        if not ok:
            required_failures += 1

    # ── 版本一致性（硬门禁：SKILL.md version ↔ CHANGELOG 最新，杜绝滞后）──
    if not args.skip_version and not args.advisory_only:
        skill_ver = _read_skill_version()
        ch_ver = _read_changelog_latest()
        print("\n" + "-" * 64)
        print(" 版本一致性（SKILL.md version ↔ CHANGELOG 最新）")
        print("-" * 64)
        if not skill_ver or not ch_ver:
            print(" ⚠️ 无法读取 SKILL.md version 或 CHANGELOG 最新版本（文件缺失）")
        elif skill_ver == ch_ver:
            print(f" ✅ SKILL.md version={skill_ver} 与 CHANGELOG 最新一致")
        else:
            print(f" ❌ 不一致：SKILL.md={skill_ver} vs CHANGELOG={ch_ver}")
            print("    用 `python scripts/release_gate.py --bump-version` 自动同步，或手动对齐。")
            required_failures += 1

    # ── CI 建议项（ADVISORY，不阻塞）──
    print("\n" + "-" * 64)
    print(" CI 建议项（ADVISORY，不阻塞门禁）")
    print("-" * 64)
    advisory = [
        ("verify_imports", _check_imports, args.skip_imports),
        ("check_refs", _check_refs, args.skip_refs),
    ]
    for name, fn, skip in advisory:
        if skip:
            print(f"\n[{name}] ⨯ SKIPPED")
            continue
        status, detail = fn()
        icon = {"PASS": "✅", "WARNING": "⚠️", "SKIPPED": "⊘"}.get(status, "?")
        print(f"\n[{name}] {icon} {status}")
        if status != "PASS":
            print(f"     {detail}")
            warnings += 1

    # ── 汇总 ──
    print("\n" + "=" * 64)
    if required_failures > 0:
        print(f"❌ {required_failures} 个硬门禁失败，禁止打包 / 交付。先修掉上面的 ❌。")
        return 1
    print("✅ 全部硬性门禁通过，可以进入打包 / 交付。")
    if warnings:
        print(f"   （{warnings} 项 CI 建议项告警，不阻塞，建议修复。）")
    print("   交付前仍须人工确认（见 docs/delivery-checklist.md）：")
    print("     · 一次真实 LLM 往返成功（非仅 HTTP 200）")
    print("     · 启动.bat 双击启动无报错")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
