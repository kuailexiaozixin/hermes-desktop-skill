#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_js_modules.py — 前端 ES 模块门禁校验（技能级、可单独外发、自包含）

为什么需要它（前提 / 适用边界）
----------------------------------------------------------------
本技能的"正常形态"是纯 Python（Tkinter 桌面壳）或 FastHTML + HTMX/Pico 的
服务端渲染，这两类**不写本地 ES 模块 JS**，于是没有前端模块需要校验，脚本自动
SKIP 不阻塞。只有当某个示例采用「**禁用 HTMX/Pico、改用原生 ES 模块前端**」
（即 `main.py` 以 `<script type="module">` 加载 `static/*.js`，把业务逻辑拆到
`static/src/*.js` 多模块、零构建、零运行时依赖）时，才有本地 JS 需要校验。

这类前端有一个隐蔽陷阱：浏览器按 ES 模块语法加载 `type="module"` 脚本，括号 /
`import`/`export` 的规矩是强制的；但只要有一个文件括号没配对（如函数头多写
一个 `{`），浏览器解析到末尾的 `export` 就会报 `Unexpected token 'export'`，
**整站前端直接瘫痪**。而 `node --check xxx.js` 默认按老式脚本解析、叠加新版 Node
对 `.js` 的自动模块探测更宽松，对这种模块级错误**反而放行**（假绿）。

因此本脚本强制"按浏览器真实方式"校验：
  1) 真·ES 模块语法：把每个 `.js` 复制成 `.mjs` 后 `node --check`（与浏览器加载
     方式一致），专抓 `node --check *.js` 漏报的模块级括号/语法错误。
  2) 跨模块链接：提取每个文件的 `export` 名，核对所有 `import { x }` 的 `x`
     是否真实存在于目标模块 `export` 中（含 `as` 别名 / 默认导入 / 命名空间导入）。

适用前提编码为：仅当 `examples/*/static/**/*.js` 存在时才校验；否则（纯 Python /
Tkinter / HTMX·Pico 示例）自动 SKIP。

退出码（与 release_gate 协同）
----------------------------------------------------------------
  0 = 全部通过（或本技能无 JS 前端，正常放行）
  1 = 存在语法/链接失败（硬失败，阻断发布）
  2 = SKIP（node 未安装 或 不存在任何 `static/**/*.js` 前端；不阻塞）

纯 Python 实现，唯一外部依赖是 `node`（缺失即 SKIP，不视为失败，与
release_gate「工具不可用则跳过」原则一致）。无机器专属绝对路径。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

# 扫描排除项（避免误判备份 / 依赖 / 构建产物）
_SKIP_DIRS = {"node_modules", "dist", "build", ".venv", "__pycache__", ".git"}


# ───────────────────────── 导出 / 导入静态解析 ─────────────────────────

RE_EXPORT_DECL = re.compile(
    r"export\s+(?:async\s+)?(?:const|let|var|function|class)\s+([A-Za-z0-9_$]+)"
)
RE_EXPORT_DEFAULT = re.compile(
    r"export\s+default\s+(?:async\s+)?(?:function|class)\s+([A-Za-z0-9_$]+)"
)
RE_EXPORT_LIST = re.compile(r"export\s*\{([^}]*)\}")


def extract_exports(code: str) -> set[str]:
    """提取模块具名导出集合（含 `as` 别名；匿名 `export { x as default }` 不计入）。"""
    names: set[str] = set()
    for m in RE_EXPORT_DECL.finditer(code):
        names.add(m.group(1))
    for m in RE_EXPORT_DEFAULT.finditer(code):
        names.add(m.group(1))
    for m in RE_EXPORT_LIST.finditer(code):
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            as_idx = part.find(" as ")
            exported = part[as_idx + 4:].strip() if as_idx >= 0 else part
            if exported and exported != "default":
                names.add(exported)
    return names


RE_IMPORT = re.compile(
    r"import\s+(?:([A-Za-z0-9_$]+)\s*,?\s*)?"      # 默认导入
    r"(?:\*\s+as\s+([A-Za-z0-9_$]+)\s*)?"           # 命名空间导入 *
    r"(?:\{([^}]*)\})?\s*"                          # 具名导入 { a, b as c }
    r"from\s*[\"']([^\"']+)[\"']"                    # 目标模块
)


def extract_imports(code: str) -> list[dict]:
    out: list[dict] = []
    for m in RE_IMPORT.finditer(code):
        default, namespace, named, target = m.groups()
        names: list[str] = []
        if named:
            for part in named.split(","):
                part = part.strip()
                if not part:
                    continue
                as_idx = part.find(" as ")
                orig = part[:as_idx].strip() if as_idx >= 0 else part
                if orig:
                    names.append(orig)
        out.append({
            "default": bool(default),
            "namespace": bool(namespace),
            "names": names,
            "target": target,
        })
    return out


def resolve_target(file_abs: Path, target: str) -> Path | None:
    """解析相对导入目标为绝对路径；外部裸模块（如 react）返回 None 跳过。"""
    if not target.startswith("."):
        return None
    base_dir = file_abs.parent
    resolved = (base_dir / target).resolve()
    candidates = [resolved, Path(str(resolved) + ".js")]
    for c in candidates:
        if c.exists() and c.suffix == ".js":
            return c
    return None


# ───────────────────────── 文件发现 ─────────────────────────

def find_js_files() -> list[Path]:
    """递归扫描所有 `examples/*/static/**/*.js`，排除备份/依赖/构建产物。"""
    found: list[Path] = []
    examples_dir = SKILL_ROOT / "examples"
    if not examples_dir.is_dir():
        return found
    for static_root in examples_dir.rglob("static"):
        if not static_root.is_dir():
            continue
        if any(part in _SKIP_DIRS for part in static_root.parts):
            continue
        for js in static_root.rglob("*.js"):
            if js.suffix != ".js" or js.name.endswith(".bak"):
                continue
            if any(part in _SKIP_DIRS for part in js.parts):
                continue
            found.append(js)
    # 稳定排序，输出可复现
    found.sort(key=lambda p: str(p.relative_to(SKILL_ROOT)))
    return found


# ───────────────────────── 校验 ─────────────────────────

def module_syntax_check(node: str, abs_path: Path) -> str | None:
    """复制为 .mjs 后 `node --check`（强制 ES 模块语法）。返回错误串或 None。"""
    tmp = None
    try:
        fd, tmp_str = tempfile.mkstemp(suffix=".mjs", prefix="hermes_jschk_")
        os.close(fd)
        tmp = Path(tmp_str)
        shutil.copy(abs_path, tmp)
        proc = subprocess.run(
            [node, "--check", str(tmp)],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0:
            return None
        msg = (proc.stderr or proc.stdout or "node --check failed").strip()
        # 仅取尾部 3 行，避免噪声
        return " | ".join([ln for ln in msg.splitlines() if ln][-3:]) or "node --check failed"
    except subprocess.TimeoutExpired:
        return "node --check 超时"
    except Exception as e:  # noqa: BLE001
        return f"工具异常: {e}"
    finally:
        if tmp is not None:
            try:
                tmp.unlink()
            except OSError:
                pass


def main() -> int:
    # 1) node 可用性 —— 缺失则 SKIP（不阻塞）
    node = shutil.which("node")
    if not node:
        print("[check_js_modules] SKIP: 未检测到 node（前端模块校验需 node；"
              "纯 Python/Tkinter/HTMX·Pico 示例无需此门禁）")
        return 2

    # 2) 文件发现 —— 无 JS 前端则 SKIP（自动适配"正常只有 Python"的前提）
    js_files = find_js_files()
    if not js_files:
        print("[check_js_modules] SKIP: 未发现 examples/*/static/**/*.js "
              "（本技能正常形态为纯 Python / HTMX·Pico，无原生 ES 模块前端，跳过）")
        return 2

    print(f"[check_js_modules] node={node}")
    print(f"[check_js_modules] 发现 {len(js_files)} 个前端 JS 模块"
          f"（将按浏览器 <script type=module> 方式强制 ES 模块语法校验）")

    # 3) 构建全局导出表（供跨模块链接核对）
    exports_map: dict[Path, set[str]] = {}
    for f in js_files:
        try:
            exports_map[f.resolve()] = extract_exports(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            exports_map[f.resolve()] = set()
            print(f"  {f.relative_to(SKILL_ROOT)}: 读取失败 {e}")

    # 4) 跨模块链接核对
    link_issues = 0
    for f in js_files:
        try:
            code = f.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue
        for imp in extract_imports(code):
            t_abs = resolve_target(f, imp["target"])
            if t_abs is None:
                continue  # 外部模块或不存在，跳过
            exp = exports_map.get(t_abs.resolve())
            if exp is None:
                continue
            if imp["namespace"]:
                continue  # import * as ns 不校验具体名
            for n in imp["names"]:
                if n not in exp:
                    link_issues += 1
                    print(f"  LINK-FAIL: {f.relative_to(SKILL_ROOT)} "
                          f"imports {{ {n} }} from {imp['target']} "
                          f"但目标未导出该名")

    # 5) 模块语法校验（强制 .mjs）
    syntax_fail = 0
    for f in js_files:
        err = module_syntax_check(node, f)
        rel = f.relative_to(SKILL_ROOT)
        if err:
            syntax_fail += 1
            print(f"  {rel}: SYNTAX-FAIL {err}")
        else:
            print(f"  {rel}: SYNTAX-OK")

    print("")
    if syntax_fail == 0 and link_issues == 0:
        print("ALL IMPORTS RESOLVED OK · MODULE SYNTAX OK (ES 模块强制校验)")
        return 0
    print(f"FAILED: syntax={syntax_fail} link={link_issues}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
