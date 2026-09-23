#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
release_gate.py — hermes-business-agent 统一发布门禁。

打包前 / 交付前跑一次，串联本技能全部硬性门禁，全绿才放行：

硬门禁（REQUIRED，任一失败则非零退出）：
  [0] track_upstream    —— §0 上游漂移跟踪（--gate 模式：四条漂移线 PyPI 版本 / 文档指纹 / 源码签名 / API 参考一律只打印提示、恒返回 0，锁定基线版本是有意选择；签名漂移的硬阻塞在 [1] 内的 check_api_signature。不带 --gate 运行时任一 DRIFT 才返回 1。网络不可达或超时（该步限 420s，其余步 180s）时 SKIPPED 不阻塞——超时＝没测出来，不等于测出问题）
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

条件性硬门禁（按需开启，未开启即不跑）：
  [8] verify_launch     —— `--verify-launch`：把 `references/06-packaging.md` §7 的「确保启动」四步
                          变成可执行验证（真起进程 → 等端口 LISTENING → 健康端点 200 → 首页含标志文本），
                          跑完自动终止进程并确认端口释放。补的是其余门禁的共同盲区：
                          它们都在**进程内/静态**层面检查，没有一个真的把应用起在端口上。
  [9] api_server        —— `--api-server`：路线④⑤（API Server / `/v1`）落地校验，对**在跑的服务**做
                          真实 HTTP 探测（/health 200 + /v1/models 认证存在 [+ 带 key 可列模型]）。
                          服务不可达 → 退出码 2 视为 SKIP（进程内形态本就不开 8642，不阻断）；
                          服务可达但断言不过 → 硬失败。

用法：
  python scripts/release_gate.py                  # 硬门禁 + CI 建议项全跑
  python scripts/release_gate.py --advisory-only # 只跑 CI 建议项
  python scripts/release_gate.py --skip-smoke     # 跳过网页无头冒烟
  python scripts/release_gate.py --skip-endpoints
  python scripts/release_gate.py --skip-quality
  python scripts/release_gate.py --skip-js        # 跳过前端 ES 模块校验
  python scripts/release_gate.py --skip-imports --skip-refs
  python scripts/release_gate.py --verify-launch                       # 追加 06 §7 四步启动验证
  python scripts/release_gate.py --verify-launch --launch-root examples/01-hermes-desktop/连接系统 \
                                 --launch-port 8800 --health-path /healthz --expect "Hermes Desktop"
  python scripts/release_gate.py --verify-launch --launch-python "%LOCALAPPDATA%\\hermes-business-agent\\venvs\\myapp\\Scripts\\python.exe"
  python scripts/release_gate.py --api-server --api-port 8642 --api-key your-secret-key

退出码：0 = 硬门禁通过（CI 建议项失败仅告警）；1 = 硬门禁有 REQUIRED 失败。
"""
from __future__ import annotations

import argparse
import compileall
import json
import os
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# 导入检查跳过的目录（避免误判 venv / 构建产物 / 缓存）
_SKIP_DIRS = {"__pycache__", ".git", "venv", ".venv", "node_modules",
              ".workbuddy", "build", "dist", "_internal"}


def _run(cmd: list[str], timeout: int = 180) -> tuple[int, str]:
    try:
        proc = subprocess.run([PY, *cmd], cwd=SKILL_ROOT,
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        # 超时＝没测出来，不等于测出问题。只有网络型步骤（[0]）把它当 SKIP，其余步骤仍 FAIL。
        return -1, f"工具超时（>{timeout}s），未判定"
    except Exception as e:  # 工具自身炸了
        return 1, f"工具异常: {e}"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _step(label: str, cmd: list[str], skip_codes: tuple[int, ...] = (),
          timeout: int = 180) -> tuple[bool, bool, str]:
    print("\n" + "=" * 64)
    print(f" [{label}]")
    print("=" * 64)
    code, out = _run(cmd, timeout=timeout)
    for line in out.splitlines()[-25:]:
        print(f"   {line}")
    if code in skip_codes:
        why = "超时未判定" if code == -1 else f"退出码 {code}"
        print(f"   [{label}] ⊘ SKIPPED（{why} 视为跳过，不阻塞）")
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
                encoding="utf-8", errors="replace",
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


# ─────────────────────────────────────────────────────────────────────────
# 条件性硬门禁 [8] verify_launch：06 §7「确保启动」四步的可执行化
# ─────────────────────────────────────────────────────────────────────────
def _tcp_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_status(url: str, timeout: float = 5.0) -> tuple[int, str]:
    """GET → (status, body)。连接失败返回 (-1, 错误文本)。"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"


def _kill_tree(pid: int) -> None:
    """终止被测应用进程树（Windows 走 taskkill /T，POSIX 先 terminate 再 kill）。"""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/PID", str(pid), "/T"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except OSError:
        pass


def _verify_launch(args) -> tuple[str, str]:
    """06 §7 四步启动验证的外层：跑探测 → 无论如何都收尾 → 把收尾结论并入报告。

    收尾必须发生在任何返回路径之后（进程/端口是这条门禁唯一留下的副作用），
    所以拆成 wrapper + probe，而不是在 probe 内部 print。
    """
    ctx: dict = {}
    try:
        status, detail = _launch_probe(args, ctx)
    except Exception as e:  # noqa: BLE001  工具自身异常也要报告，不掩盖
        status, detail = "FAIL", f"启动验证异常：{type(e).__name__}: {e}"
    return status, detail + "\n      " + ctx.get("teardown", "收尾：未启动进程（前置步骤即失败）")


def _launch_probe(args, ctx: dict) -> tuple[str, str]:
    """按 references/06-packaging.md §7 的四步判据真起一次应用。

    返回 (status, detail)，status ∈ {PASS, FAIL}。
    与其它门禁的分工：它们验「代码/路由/HTML 结构」，本步验「进程真能在端口上服务」。
    """
    root = Path(args.launch_root)
    if not root.is_absolute():
        root = (SKILL_ROOT / root).resolve()
    entry = root / args.launch_entry
    py = str(Path(args.launch_python).expanduser()) if args.launch_python else PY
    host, port = args.launch_host, int(args.launch_port)

    # 步骤 1 · 解释器与入口（venv/依赖在打包阶段已由 06 §1/§5 建立，这里验可解析性）
    if not entry.is_file():
        return "FAIL", f"步骤1 入口不存在：{entry}"
    try:
        ver = subprocess.run([py, "-c", "import sys;print(sys.version.split()[0])"],
                             capture_output=True, text=True, timeout=30,
                             encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return "FAIL", f"步骤1 解释器不可用（{py}）：{type(e).__name__}: {e}"
    if ver.returncode != 0:
        return "FAIL", (f"步骤1 解释器不可用（{py}）："
                        f"{(ver.stderr or '').strip()[-200:]}")
    lines = [f"步骤1 解释器 OK：{py} (Python {ver.stdout.strip()})"]
    if args.launch_imports:
        for mod in [m.strip() for m in args.launch_imports.split(",") if m.strip()]:
            r = subprocess.run([py, "-c", f"import {mod}"],
                               capture_output=True, text=True, timeout=60, cwd=str(root),
                               encoding="utf-8", errors="replace")
            if r.returncode != 0:
                return "FAIL", "\n".join(lines) + f"\n      步骤1 关键依赖不可导入：{mod} —— " \
                       f"{(r.stderr or '').strip().splitlines()[-1] if (r.stderr or '').strip() else 'ImportError'}"
        lines.append(f"      步骤1 关键依赖均可导入：{args.launch_imports}")

    # 步骤 2 · 后台启动（日志落临时文件，便于失败时取 traceback）
    env = dict(os.environ)
    env["PORT"] = str(port)
    env.setdefault("PYTHONUNBUFFERED", "1")
    logf = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False, encoding="utf-8",
                                        prefix="release_launch_")
    try:
        proc = subprocess.Popen([py, str(entry)], cwd=str(root), env=env,
                                stdout=logf, stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                                if os.name == "nt" else 0)
    except Exception as e:  # noqa: BLE001
        logf.close()
        return "FAIL", "\n".join(lines) + f"\n      步骤2 启动失败：{type(e).__name__}: {e}"

    try:
        # 步骤 3 · 等端口 LISTENING
        deadline = time.time() + args.launch_timeout
        while time.time() < deadline:
            if _tcp_open(host, port):
                break
            if proc.poll() is not None:
                logf.flush()
                tail = Path(logf.name).read_text(encoding="utf-8", errors="replace").strip().splitlines()[-15:]
                return "FAIL", "\n".join(lines) + (
                    f"\n      步骤2/3 进程启动后自行退出（rc={proc.returncode}），端口 {port} 从未 LISTENING"
                    f"\n      日志尾部：\n        " + "\n        ".join(tail))
            time.sleep(0.5)
        else:
            return "FAIL", "\n".join(lines) + f"\n      步骤3 端口 {host}:{port} 在 {args.launch_timeout}s 内未 LISTENING"
        lines.append(f"      步骤3 端口 LISTENING：{host}:{port}（pid={proc.pid}）")

        # 步骤 3bis · 健康端点 200
        st, body = _http_status(f"http://{host}:{port}{args.health_path}")
        if st != 200:
            return "FAIL", "\n".join(lines) + f"\n      步骤3 健康端点 {args.health_path} -> {st} {body[:200]}"
        lines.append(f"      步骤3 健康端点 {args.health_path} 200")

        # 步骤 4 · 首页 200 + 标志文本
        st2, html = _http_status(f"http://{host}:{port}/")
        if st2 != 200:
            return "FAIL", "\n".join(lines) + f"\n      步骤4 首页 GET / -> {st2} {html[:200]}"
        if args.expect and args.expect not in html:
            return "FAIL", "\n".join(lines) + f"\n      步骤4 首页 200 但不含标志文本「{args.expect}」" \
                   f"（页面渲染不完整或服务起错）"
        lines.append(f"      步骤4 首页 200" + (f"，含标志「{args.expect}」" if args.expect else "（未设 --expect）"))
        return "PASS", "\n".join(lines)
    finally:
        # 收尾 · 终止进程树 + 确认端口释放（06 §7 收尾要求）
        _kill_tree(proc.pid)
        try:
            proc.wait(timeout=15)
        except Exception:  # noqa: BLE001
            pass
        released = not _tcp_open(host, port, timeout=1.0)
        logf.close()
        try:
            os.unlink(logf.name)
        except OSError:
            pass
        ctx["teardown"] = (f"收尾：进程已终止（pid={proc.pid}），端口"
                           + ("已释放" if released else f"仍被占用（{host}:{port}）——请手动清理"))


def _api_server_cmd(args) -> list[str]:
    cmd = ["scripts/check_api_server.py", "--host", args.api_host,
           "--port", str(args.api_port), "--skip"]
    if args.api_key:
        cmd += ["--key", args.api_key]
    return cmd


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
    ap = argparse.ArgumentParser(description="hermes-business-agent 统一发布门禁")
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

    # 条件性硬门禁 [8] 启动验证（06 §7 四步）
    ap.add_argument("--verify-launch", action="store_true",
                    help="追加「确保启动」四步验证：真起进程 → 等端口 → 健康端点 200 → 首页含标志文本")
    ap.add_argument("--launch-root", default="examples/01-hermes-desktop/连接系统",
                    help="被测应用目录（默认三系统融合入口 连接系统/）")
    ap.add_argument("--launch-entry", default="main.py", help="应用入口文件名")
    ap.add_argument("--launch-python", default=None,
                    help="启动用哪个解释器（默认当前 python；验证生产 venv 时显式指向它）")
    ap.add_argument("--launch-imports", default="",
                    help="步骤1 额外断言：逗号分隔的关键依赖必须可导入（如 uvicorn,starlette）")
    ap.add_argument("--launch-host", default="127.0.0.1")
    ap.add_argument("--launch-port", type=int, default=8800,
                    help="探测端口（同时以 PORT 环境变量传给应用）")
    ap.add_argument("--health-path", default="/healthz", help="步骤3 健康端点路径")
    ap.add_argument("--expect", default="", help="步骤4 首页必须包含的标志文本（空=只校验 200）")
    ap.add_argument("--launch-timeout", type=int, default=90, help="等端口 LISTENING 的秒数上限")

    # 条件性硬门禁 [9] 路线④⑤ API Server 真实探测
    ap.add_argument("--api-server", action="store_true",
                    help="追加路线④⑤ 门禁：对**在跑的** API Server 做真实 HTTP 探测（不可达则 SKIP）")
    ap.add_argument("--api-host", default="127.0.0.1")
    ap.add_argument("--api-port", type=int, default=8642)
    ap.add_argument("--api-key", default=None, help="提供则额外校验 /v1/models 带 key 200 且可列模型")
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
    print("# hermes-business-agent 统一发布门禁 (release_gate)")
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
            # (label, cmd, --skip-*, skip_codes, 超时秒)：[0] 要连打 PyPI 与官网，网络慢时按 SKIP 处理
            ("[0] track_upstream [Check] (REQUIRED)", ["scripts/track_upstream.py", "--gate"], args.skip_track, (-1,), 420),
            ("[1] quality_check [Check] (REQUIRED)", ["scripts/quality_check.py"], args.skip_quality, (), 180),
            ("[2] check_endpoints [Check] (REQUIRED)", ["scripts/check_endpoints.py"], args.skip_endpoints, (), 180),
            ("[3] smoke_test_web [Test] (REQUIRED)", ["scripts/smoke_test_web.py"], args.skip_smoke, (), 180),
            ("[4] check_js_modules [Check] (REQUIRED, 条件性)", ["scripts/check_js_modules.py"], args.skip_js, (2,), 180),
        ]

    for label, cmd, skip, skip_codes, timeout in steps:
        if skip:
            print(f"\n[{label}] ⨯ SKIPPED")
            continue
        ok, skipped, _ = _step(label, cmd, skip_codes=skip_codes, timeout=timeout)
        if skipped:
            continue
        if not ok:
            required_failures += 1

    # ── 版本一致性（硬门禁：SKILL.md version ↔ CHANGELOG 最新，杜绝滞后）──
    if not args.skip_version and not args.advisory_only:
        skill_ver = _read_skill_version()
        ch_ver = _read_changelog_latest()
        print("\n" + "-" * 64)
        print(" [5] version_consistency (REQUIRED) [Layer: Check] 版本一致性（SKILL.md version ↔ CHANGELOG 最新）")
        print("-" * 64)
        if not skill_ver or not ch_ver:
            print(" ⚠️ 无法读取 SKILL.md version 或 CHANGELOG 最新版本（文件缺失）")
        elif skill_ver == ch_ver:
            print(f" ✅ SKILL.md version={skill_ver} 与 CHANGELOG 最新一致")
        else:
            print(f" ❌ 不一致：SKILL.md={skill_ver} vs CHANGELOG={ch_ver}")
            print("    用 `python scripts/release_gate.py --bump-version` 自动同步，或手动对齐。")
            required_failures += 1

    # ── 条件性硬门禁 [8] verify_launch（06 §7 四步启动验证）──
    if not args.advisory_only:
        if args.verify_launch:
            print("\n" + "-" * 64)
            print(" [8] verify_launch (REQUIRED when --verify-launch) [Layer: Test] "
                  "确保启动四步（06 §7）")
            print("-" * 64)
            status, detail = _verify_launch(args)
            icon = {"PASS": "✅", "FAIL": "❌", "SKIPPED": "⊘"}.get(status, "?")
            print(f" {icon} {status}")
            for line in detail.splitlines():
                print(f"   {line}")
            if status != "PASS":
                required_failures += 1
        else:
            print("\n[8] verify_launch ⊘ 未启用（加 --verify-launch 跑 06 §7 四步启动验证）")

        # ── 条件性硬门禁 [9] api_server（路线④⑤）──
        if args.api_server:
            ok, skipped, _ = _step("[9] api_server (REQUIRED when --api-server; 路线④⑤) [Test]",
                                   _api_server_cmd(args), skip_codes=(2,))
            if not ok and not skipped:
                required_failures += 1
        else:
            print("[9] api_server ⊘ 未启用（路线④⑤ 交付时加 --api-server [--api-key ...]）")

    # ── CI 建议项（ADVISORY，不阻塞）──
    print("\n" + "-" * 64)
    print(" CI 建议项（ADVISORY，不阻塞门禁）")
    print("-" * 64)
    advisory = [
        ("verify_imports [6]", _check_imports, args.skip_imports),
        ("check_refs [7]", _check_refs, args.skip_refs),
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
    if args.advisory_only:
        print("⊘ --advisory-only：只跑了 CI 建议项，**硬门禁未执行**，不得据此宣称可交付。")
        return 0
    print("✅ 全部硬性门禁通过，可以进入打包 / 交付。")
    if warnings:
        print(f"   （{warnings} 项 CI 建议项告警，不阻塞，建议修复。）")
    print("   交付前仍须人工确认（见 docs/delivery-checklist.md）：")
    print("     · 一次真实 LLM 往返成功（非仅 HTTP 200）——本门禁全为结构级/离线检查，不含真实往返")
    if args.verify_launch:
        print("     · 启动四步已由 [8] verify_launch 代跑（端口/健康端点/首页 + 进程收尾）；"
              "原生窗口是否真打开仍需 ui_window_verify.py 或人工")
    else:
        print("     · 启动.bat 双击启动无报错（加 --verify-launch 可把 06 §7 前三步自动化）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
