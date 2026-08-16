#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hermes-desktop 网页回归测试夹具（无头、离线、可重复、可扩展）。

把「页面能启动、但 GET / 渲染时崩溃」这类 bug（如 `main.py` 漏导入 `Input` 导致
`index()` `NameError`，而 `/healthz` 冒烟看不见）从一次性人工检查，升级为**可重复的
回归断言**。结构级：不需要 API Key、不触发真实 LLM 往返。

与 quality_check.py 集成：`python scripts/quality_check.py` 会把它作为门禁步骤之一，
以 `--json` 消费结构化结果。

特性：
  - 结构化测试用例（标准库轻量框架，无第三方依赖）：每个用例 = 名称 + 描述 + 断言
  - 可重复 / 幂等：临时 HERMES_HOME + 离线市场 + 确定性顺序，不依赖外部状态与网络
  - 可选择性：`--list` 列用例；`--case NAME[,NAME...]` 只跑指定用例
  - 结构化输出：`--json` 供 CI / quality_check 消费
  - 可扩展：用 `@case("name", "desc")` 注册新用例即可增加回归覆盖

退出码：0 = 全部通过；1 = 有断言失败；2 = 工具/环境问题（缺依赖、找不到 root/main）。

用法：
    uv run python scripts/smoke_test_web.py                 # 跑全部用例
    uv run python scripts/smoke_test_web.py --list          # 列出用例
    uv run python scripts/smoke_test_web.py --case healthz  # 只跑 healthz
    uv run python scripts/smoke_test_web.py --json          # 机器可读输出
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_ROOT = SKILL_ROOT / "examples" / "01-hermes-desktop"

# ─────────────────────────────────────────────────────────────────────────
# 轻量用例框架（无第三方依赖）
# ─────────────────────────────────────────────────────────────────────────
CASES: dict[str, tuple[str, callable]] = {}  # name -> (desc, fn)


def case(name: str, desc: str):
    """注册一个测试用例。fn 签名：fn(client, rep) -> None，内部用 rep.check 断言。"""
    def deco(fn):
        CASES[name] = (desc, fn)
        return fn
    return deco


class Report:
    """一个用例内的断言收集器。"""

    def __init__(self, case_name: str):
        self.case_name = case_name
        self.assertions: list[dict] = []

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        self.assertions.append({"ok": bool(ok), "label": label, "detail": detail})
        return bool(ok)

    @property
    def passed(self) -> bool:
        return all(a["ok"] for a in self.assertions)


# ─────────────────────────────────────────────────────────────────────────
# 环境准备：临时 HERMES_HOME + 离线市场（必须在任何 hermes 导入前设置）
# ─────────────────────────────────────────────────────────────────────────
def _prepare_env(root: Path) -> Path:
    # HERMES_HOME 指向可写临时路径，避免污染真实 .hermes_data（见 main.py 顶部注释）
    tmp = Path(tempfile.mkdtemp(prefix="hermes_smoke_"))
    os.environ["HERMES_HOME"] = str(tmp)
    # 市场走离线：避免触发「在线拉取 Hermes 中心索引」子进程（数十 MB，受限环境会硬杀子进程）。
    # 离线模式仍验证路由形状契约与精选段渲染，符合「冒烟 = 结构级、无需联网」定位。
    os.environ["HERMES_MARKET_OFFLINE"] = "1"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return tmp


def _load_app(root: Path):
    """导入 main 并返回 ASGI app。失败抛异常，由调用方转为 rc=2。"""
    try:
        from starlette.testclient import TestClient
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"需要 starlette（fasthtml 依赖，uv 环境内应有）：{e}") from e
    try:
        import main  # noqa: F401  (导入即执行 fast_app，注册全部路由)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"导入 main.py 失败：{type(e).__name__}: {e}") from e
    app = getattr(main, "app", None)
    if app is None:
        raise RuntimeError("main.py 未暴露 `app` 对象（fast_app 返回值）")
    return TestClient(app)


# ─────────────────────────────────────────────────────────────────────────
# 用例定义（与 docs/delivery-checklist.md B 档 DOM id 对齐）
# ─────────────────────────────────────────────────────────────────────────
DOM_CHECKS = [
    ("convSearch", "会话搜索框"),
    ("usageChip", "用量芯片"),
    ("analyticsBody", "用量分析面板"),
    ("Hermes Desktop", "首页标题"),
    ("btnAnalytics", "用量按钮"),
]


@case("healthz", "/healthz 返回 200 且为 JSON 自检")
def case_healthz(client, rep):
    try:
        r = client.get("/healthz")
        rep.check(r.status_code == 200, "/healthz 状态码==200", f"实际={r.status_code}")
    except Exception as e:  # noqa: BLE001
        rep.check(False, "/healthz 无异常", f"{type(e).__name__}: {e}")


@case("index_dom", "首页 GET / 200 且含关键 DOM id")
def case_index_dom(client, rep):
    html = None
    try:
        r = client.get("/")
        rep.check(r.status_code == 200, "GET / 状态码==200", f"实际={r.status_code}")
        if r.status_code == 200:
            html = r.text
    except Exception as e:  # noqa: BLE001
        rep.check(False, "GET / 无异常", f"{type(e).__name__}: {e}")
        return
    if html is None:
        rep.check(False, "首页 HTML 可取", "未能取得 HTML")
        return
    for token, label in DOM_CHECKS:
        rep.check(token in html, f"页面含 {label}（{token}）")


def _get_json(client, path: str):
    r = client.get(path)
    ctype = r.headers.get("content-type", "")
    if ctype.startswith("application/json"):
        try:
            return r.status_code, r.json()
        except Exception:  # noqa: BLE001
            return r.status_code, None
    return r.status_code, None


@case("api_mcp_shape", "/api/mcp 返回 items 为 list（前端 for...of 安全）")
def case_mcp_shape(client, rep):
    code, data = _get_json(client, "/api/mcp")
    rep.check(code == 200, "/api/mcp 状态码==200", f"实际={code}")
    rep.check(isinstance(data, dict) and isinstance(data.get("items"), list),
              "/api/mcp.items 为 list", f"items 类型={type(data.get('items')).__name__ if isinstance(data, dict) else 'n/a'}")


@case("skill_store_shape", "/api/skill-store/skills 返回 items 为 list（SkillHub 在线）")
def case_skill_store_shape(client, rep):
    code, data = _get_json(client, "/api/skill-store/skills")
    rep.check(code == 200, "/api/skill-store/skills 状态码==200", f"实际={code}")
    rep.check(isinstance(data, dict) and isinstance(data.get("items"), list),
              "/api/skill-store/skills.items 为 list")


@case("mcp_store_shape", "/api/mcp-store/servers 返回 items 为 list（LobeHub 在线）")
def case_mcp_store_shape(client, rep):
    code, data = _get_json(client, "/api/mcp-store/servers")
    rep.check(code == 200, "/api/mcp-store/servers 状态码==200", f"实际={code}")
    rep.check(isinstance(data, dict) and isinstance(data.get("items"), list),
              "/api/mcp-store/servers.items 为 list")


@case("proveit_mcp_items", "Prove-It：/api/mcp.items 不得退化为 dict")
def case_proveit_mcp_items(client, rep):
    # 故意把 /api/mcp 形状回退成 dict 也得被「前端契约」断言抓住。
    # 这里直接验证 main 的 _guard 摊平逻辑——若日后改坏，items 会变 dict 触发 FAIL。
    code, data = _get_json(client, "/api/mcp")
    is_dict = isinstance(data, dict) and isinstance(data.get("items"), dict)
    rep.check(not is_dict, "/api/mcp.items 不是 dict（前端 for...of 安全）",
              f"items 类型={type(data.get('items')).__name__ if isinstance(data, dict) else 'n/a'}")


# ─────────────────────────────────────────────────────────────────────────
# 运行 / 输出
# ─────────────────────────────────────────────────────────────────────────
def _run_cases(client, only: set[str]) -> list[dict]:
    results = []
    for name in CASES:  # 确定性顺序（dict 保持注册顺序）
        if only and name not in only:
            continue
        desc, fn = CASES[name]
        rep = Report(name)
        try:
            fn(client, rep)
        except Exception as e:  # noqa: BLE001
            rep.check(False, "用例执行异常", f"{type(e).__name__}: {e}")
        results.append({
            "case": name,
            "desc": desc,
            "passed": rep.passed,
            "assertions": rep.assertions,
        })
    return results


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="网页回归测试夹具（结构级，无需 API Key）")
    p.add_argument("--root", default=str(DEFAULT_ROOT), help="示例目录（含 main.py）")
    p.add_argument("--list", action="store_true", help="列出全部用例并退出")
    p.add_argument("--case", default=None, help="只跑指定用例（逗号分隔）")
    p.add_argument("--json", action="store_true", help="机器可读 JSON 输出")
    args = p.parse_args(argv)

    if args.list:
        for name, (desc, _fn) in CASES.items():
            print(f"{name:24s} {desc}")
        return 0

    root = Path(args.root).resolve()
    if not (root / "main.py").is_file():
        if args.json:
            print(json.dumps({"error": f"找不到 {root / 'main.py'}", "results": [], "passed": 0, "failed": 1, "total": 0}))
        else:
            print(f"[ERR] 找不到 {root / 'main.py'}")
        return 2

    only = {s.strip() for s in args.case.split(",")} if args.case else set()
    if only and not only.issubset(CASES):
        unknown = only - set(CASES)
        if args.json:
            print(json.dumps({"error": f"未知用例: {sorted(unknown)}", "results": [], "passed": 0, "failed": 1, "total": 0}))
        else:
            print(f"[ERR] 未知用例: {sorted(unknown)}（可用 --list 查看）")
        return 2

    _prepare_env(root)
    try:
        client = _load_app(root)
    except Exception as e:  # noqa: BLE001
        if args.json:
            print(json.dumps({"error": str(e), "results": [], "passed": 0, "failed": 1, "total": 0}))
        else:
            print(f"[ERR] {e}")
        return 2

    results = _run_cases(client, only)
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])

    if args.json:
        print(json.dumps({
            "tool": "smoke_test_web",
            "root": str(root),
            "results": results,
            "passed": passed,
            "failed": failed,
            "total": len(results),
        }, indent=2, ensure_ascii=False))
        return 0 if failed == 0 else 1

    print("=" * 60)
    print(" 网页回归测试夹具 (smoke_test_web)")
    print("=" * 60)
    for r in results:
        tag = "PASS" if r["passed"] else "FAIL"
        print(f"  [{tag}] {r['case']} — {r['desc']}")
        for a in r["assertions"]:
            mark = "OK" if a["ok"] else "✗"
            extra = f"  ({a['detail']})" if a.get("detail") else ""
            print(f"      {mark} {a['label']}{extra}")
    print("-" * 60)
    print(f"RESULT: {passed} passed, {failed} failed, {len(results)} total")
    if failed:
        return 1
    print("  （真实 LLM 往返仍见 §5 步骤⑦ 端到端对话冒烟）")
    return 0


if __name__ == "__main__":
    _code = main()
    # main.py import 会启动非 daemon 后台线程（cron 调度等），阻塞进程正常退出。
    # 测试夹具定位：跑完断言即退出，用 os._exit 强制结束，避免在 CI / quality_check 中挂起。
    os._exit(_code)
