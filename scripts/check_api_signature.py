#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_api_signature.py — Hermes Python Library 源码签名基线比对工具。

用 ast **静态解析**（不 import run_agent，避免触发 Hermes 的任何副作用），
提取以下三个签名的参数集合与默认值，与 scripts/api-baseline.json 比对：

    AIAgent.__init__
    AIAgent.run_conversation
    AIAgent.chat

输出三类差异：
    REMOVED        基线有、当前没有  → 破坏性变更，代码会炸，必须改技能与 examples
    ADDED          新增参数          → 可能有新能力，考虑纳入技能
    DEFAULT_CHANGED 默认值变了        → 静默行为变化（最危险，如 max_iterations 90→500）

用法：
    python scripts/check_api_signature.py                       # 自动定位已装 Library 并比对基线
    python scripts/check_api_signature.py --dump               # 导出当前签名 JSON 到 stdout
    python scripts/check_api_signature.py --baseline X.json    # 指定基线文件
    python scripts/check_api_signature.py --path /abs/run_agent.py   # 指定源码路径
    python scripts/check_api_signature.py --json               # 机器可读输出
    python scripts/check_api_signature.py --from-pypi          # 从 PyPI 下载最新版 wheel 比对签名（上游漂移检测）
    python scripts/check_api_signature.py --dump-pypi          # 从 PyPI 下载最新版 wheel 并导出签名

退出码：0 = 无破坏性变更；1 = 发现 REMOVED / DEFAULT_CHANGED；2 = 工具/环境问题。
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BASELINE = os.path.normpath(
    os.path.join(SCRIPT_DIR, "api-baseline.json")
)

# 基线版本集中自 scripts/api-baseline.json（单一事实来源），避免多处硬编码漂移
try:
    with open(DEFAULT_BASELINE, "r", encoding="utf-8") as _bf:
        BASELINE_VERSION = json.load(_bf).get("baseline_version", "0.19.0")
except Exception:
    BASELINE_VERSION = "0.19.0"


def locate_run_agent(explicit: str | None = None) -> str | None:
    """定位已安装的 run_agent。优先 explicit，其次 importlib 解析，最后扫 sys.path。

    返回单个 .py 文件路径，或包目录（run_agent 是包时），调用方用 extract_signatures 兼容两者。
    """
    if explicit:
        if os.path.isfile(explicit):
            return explicit
        if os.path.isdir(explicit):
            return explicit
        print(f"[ERR] --path 指定的文件/目录不存在: {explicit}", file=sys.stderr)
        return None
    try:
        spec = importlib.util.find_spec("run_agent")
        if spec:
            locs = getattr(spec, "submodule_search_locations", None)
            if locs:  # 包：返回目录，让 extract_signatures 扫整个包，避免漏掉子模块里的 AIAgent
                return locs[0]
            origin = getattr(spec, "origin", None)
            if origin:
                return origin
    except Exception:
        pass
    # 兜底：扫 sys.path 找 run_agent.py / run_agent/__init__.py
    for entry in sys.path:
        cand = os.path.join(entry, "run_agent.py")
        if os.path.isfile(cand):
            return cand
        cand2 = os.path.join(entry, "run_agent", "__init__.py")
        if os.path.isfile(cand2):
            return os.path.join(entry, "run_agent")  # 返回目录

    # 自动扫描常见 venv 路径（用户零配置，自动发现）
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.normpath(os.path.join(_script_dir, ".."))
    _venv_candidates = []

    # ① 项目根目录下的常见 venv 目录名
    for _vn in (".venv", "venv", ".venv_hermes", "venv_hermes"):
        _venv_candidates.append(os.path.join(_project_root, _vn))

    # ② Windows: %LOCALAPPDATA%/hermes-desktop/venvs/*/
    _local_appdata = os.environ.get("LOCALAPPDATA", "")
    if _local_appdata:
        _venvs_dir = os.path.join(_local_appdata, "hermes-desktop", "venvs")
        if os.path.isdir(_venvs_dir):
            try:
                for _entry in sorted(os.listdir(_venvs_dir)):
                    _p = os.path.join(_venvs_dir, _entry)
                    if os.path.isdir(_p):
                        _venv_candidates.append(_p)
            except Exception:
                pass

    # ③ examples/ 下各子目录的 venv
    _examples_dir = os.path.join(_project_root, "examples")
    if os.path.isdir(_examples_dir):
        try:
            for _entry in sorted(os.listdir(_examples_dir)):
                _sub = os.path.join(_examples_dir, _entry)
                if os.path.isdir(_sub):
                    for _vn in (".venv", "venv"):
                        _venv_candidates.append(os.path.join(_sub, _vn))
        except Exception:
            pass

    # 扫描所有候选 venv 目录
    for _vd in _venv_candidates:
        if not os.path.isdir(_vd):
            continue
        # Windows: {venv}/Lib/site-packages/
        _sp = os.path.join(_vd, "Lib", "site-packages")
        if os.path.isdir(_sp):
            _cand = os.path.join(_sp, "run_agent.py")
            if os.path.isfile(_cand):
                return _cand
            _pkg = os.path.join(_sp, "run_agent")
            if os.path.isdir(_pkg):
                return _pkg
        # Linux/macOS: {venv}/lib/python*/site-packages/
        _lib = os.path.join(_vd, "lib")
        if os.path.isdir(_lib):
            try:
                for _py_dir in os.listdir(_lib):
                    if _py_dir.startswith("python"):
                        _sp = os.path.join(_lib, _py_dir, "site-packages")
                        if os.path.isdir(_sp):
                            _cand = os.path.join(_sp, "run_agent.py")
                            if os.path.isfile(_cand):
                                return _cand
                            _pkg = os.path.join(_sp, "run_agent")
                            if os.path.isdir(_pkg):
                                return _pkg
            except Exception:
                pass

    return None


def default_repr(node) -> str | None:
    """把 ast 默认值的节点转成可读字符串用于比对。None 表示该参数无默认值。"""
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return "<expr>"


def extract_func_params(func_node: ast.FunctionDef) -> dict:
    """提取一个函数的具名参数 -> 默认值字符串。忽略 *args/**kwargs（非具名）。"""
    out: dict = {}
    args = func_node.args
    pos = args.args
    defaults = list(args.defaults)
    n, m = len(pos), len(defaults)
    for i, a in enumerate(pos):
        dflt = defaults[i - (n - m)] if i >= (n - m) else None
        out[a.arg] = default_repr(dflt)
    for j, a in enumerate(args.kwonlyargs):
        out[a.arg] = default_repr(args.kw_defaults[j])
    return out


def _extract_from_file(path: str) -> dict:
    """解析单个 .py 文件，返回其中的 AIAgent 签名。"""
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src, filename=path)
    sigs: dict = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "AIAgent":
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name in (
                    "__init__",
                    "run_conversation",
                    "chat",
                ):
                    sigs[f"AIAgent.{sub.name}"] = {
                        "params": extract_func_params(sub)
                    }
    return sigs


def extract_signatures(path: str) -> dict:
    """静态解析文件或包目录，返回 { 'AIAgent.__init__': {'params': {...}}, ... }。

    当 path 是目录（run_agent 为包）时，扫描目录下所有 .py 并合并签名，
    避免 AIAgent 定义在子模块时漏抓导致假 REMOVED。
    """
    if os.path.isdir(path):
        merged: dict = {}
        for root, _dirs, files in os.walk(path):
            if any(seg in root for seg in ("__pycache__",)):
                continue
            for fn in files:
                if fn.endswith(".py"):
                    for k, v in _extract_from_file(os.path.join(root, fn)).items():
                        merged.setdefault(k, v)  # 同函数名取首次出现
        return merged
    return _extract_from_file(path)


def compare(baseline_sigs: dict, current_sigs: dict) -> dict:
    report = {
        "REMOVED": [],
        "ADDED": [],
        "DEFAULT_CHANGED": [],
        "OK": True,
    }
    for key, bval in baseline_sigs.items():
        if key not in current_sigs:
            report["REMOVED"].append(key)
            report["OK"] = False
            continue
        bp = bval["params"]
        cp = current_sigs[key]["params"]
        for name, dflt in bp.items():
            if name not in cp:
                report["REMOVED"].append(f"{key}.{name}")
                report["OK"] = False
            elif cp[name] != dflt:
                report["DEFAULT_CHANGED"].append(
                    f"{key}.{name}: {dflt} -> {cp[name]}"
                )
                report["OK"] = False
        for name in cp:
            if name not in bp:
                report["ADDED"].append(f"{key}.{name}")
    for key in current_sigs:
        if key not in baseline_sigs:
            report["ADDED"].append(key)
    return report


def fetch_upstream_run_agent() -> tuple[str | None, dict | None, str | None]:
    """轻量级：从 PyPI JSON API 获取最新版版本号，不下载 wheel，秒级完成。

    返回 (version, None, error) 三元组：
        version:    版本号，如 "0.19.0"（失败时为 None）
        error:      None 表示成功，否则为错误描述字符串

    需要详细签名比对时使用 --from-pypi（会下载 wheel 做 ast 解析）。
    """
    _PYPI_JSON = "https://pypi.org/pypi/hermes-agent/json"
    _UA = "hermes-desktop-skill/1.0"
    try:
        req = urllib.request.Request(_PYPI_JSON, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        version = data.get("info", {}).get("version", "?")
        return version, None, None
    except urllib.error.URLError as e:
        return None, None, f"PyPI API 不可达: {e.reason}"
    except Exception as e:
        return None, None, f"PyPI API 请求失败: {type(e).__name__}: {e}"

def check_upstream_signature() -> dict:
    """轻量级上游签名检查：仅比对 PyPI 版本号，不下载 wheel，秒级完成。

    返回 dict 格式与 track_upstream.py 的 check_signature() 兼容：
        track: "signature"
        status: "OK" / "DRIFT" / "SKIPPED"
        source: 版本来源描述
    """
    version, _, err = fetch_upstream_run_agent()
    if err:
        return {"track": "signature", "status": "SKIPPED", "error": err}

    if version == BASELINE_VERSION:
        return {
            "track": "signature",
            "status": "OK",
            "source": f"PyPI hermes-agent=={version}",
        }

    return {
        "track": "signature",
        "status": "DRIFT",
        "source": f"PyPI hermes-agent=={version} (基线 {BASELINE_VERSION})",
        "note": "上游版本已变化，运行 --dump-pypi 查看详细签名变更",
    }

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Hermes Library 源码签名基线比对")
    p.add_argument("--dump", action="store_true",
                    help="导出当前本地签名 JSON 到 stdout")
    p.add_argument("--dump-pypi", action="store_true",
                    help="从 PyPI 下载最新版 wheel 并导出签名 JSON 到 stdout")
    p.add_argument("--from-pypi", action="store_true",
                    help="从 PyPI 下载最新版 wheel 比对签名（替代本地检测，真正的上游漂移检测）")
    p.add_argument("--baseline", default=DEFAULT_BASELINE, help="基线 JSON 路径")
    p.add_argument("--path", default=None, help="显式指定 run_agent.py 路径")
    p.add_argument("--json", action="store_true", help="机器可读输出")
    args = p.parse_args(argv)

    # --from-pypi: 轻量级上游版本检查（秒级，不下载 wheel）
    if args.from_pypi:
        result = check_upstream_signature()
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            st = result.get("status", "ERROR")
            if st == "OK":
                print(f"✅ 上游版本与基线一致: {result.get('source')}")
            elif st == "DRIFT":
                print(f"🔴 {result.get('source')}")
                print(f"   提示: {result.get('note', '')}")
            else:
                print(f"⚠️ 跳过: {result.get('error', '')}")
        return 0 if result.get("status") in ("OK", "SKIPPED") else 1

    # --dump-pypi: 从 PyPI 下载最新版 wheel 并导出签名（重量级，需网络）
    if args.dump_pypi:
        _PYPI_JSON = "https://pypi.org/pypi/hermes-agent/json"
        _UA = "hermes-desktop-skill/1.0"
        tmpdir = tempfile.mkdtemp(prefix="hermes_pypi_sig_")
        try:
            req = urllib.request.Request(_PYPI_JSON, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                pypi_data = json.loads(r.read())
            version = pypi_data.get("info", {}).get("version", "?")
            wheel_url = None
            for url_info in pypi_data.get("urls", []):
                if url_info.get("packagetype") == "bdist_wheel":
                    wheel_url = url_info["url"]
                    break
            if not wheel_url:
                print("[ERR] 无 wheel 发行版", file=sys.stderr)
                return 2
            req = urllib.request.Request(wheel_url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                wheel_data = r.read()
            whl_path = os.path.join(tmpdir, "pkg.whl")
            with open(whl_path, "wb") as f:
                f.write(wheel_data)
            run_agent_bytes: bytes | None = None
            with zipfile.ZipFile(whl_path, "r") as zf:
                for name in zf.namelist():
                    if name.endswith("run_agent.py") and not name.startswith("_")                             and "/test" not in name and "test_" not in name:
                        candidate = zf.read(name)
                        if run_agent_bytes is None or len(name.split("/")) < 2:
                            run_agent_bytes = candidate
            if run_agent_bytes is None:
                print("[ERR] 未找到 run_agent.py", file=sys.stderr)
                return 2
            tmp_py = os.path.join(tmpdir, "run_agent.py")
            with open(tmp_py, "wb") as f:
                f.write(run_agent_bytes)
            signatures = extract_signatures(tmp_py)
            dump = {
                "baseline_version": version,
                "captured_from": f"PyPI hermes-agent=={version}",
                "signatures": signatures,
            }
            print(json.dumps(dump, indent=2, ensure_ascii=False))
            return 0
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", file=sys.stderr)
            return 2
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    path = locate_run_agent(args.path)
    if not path:
        print(
            "[ERR] 找不到已安装的 run_agent.py。请确认 hermes-agent 已装进当前"
            " Python（或用 --path 指定），且运行此脚本的解释器就是跑 GUI 的那个。",
            file=sys.stderr,
        )
        return 2

    try:
        current = extract_signatures(path)
    except SyntaxError as e:
        print(f"[ERR] 解析 {path} 失败: {e}", file=sys.stderr)
        return 2

    if args.dump:
        dump = {
            "baseline_version": BASELINE_VERSION,
            "captured_from": path,
            "signatures": current,
        }
        print(json.dumps(dump, indent=2, ensure_ascii=False))
        return 0

    if not os.path.isfile(args.baseline):
        print(
            f"[WARN] 基线文件不存在: {args.baseline}\n"
            f"        先用 `--dump` 导出一个作为基线：\n"
            f"        python scripts/check_api_signature.py --dump > {args.baseline}\n"
            f"        下面打印的是当前从 {path} 提取到的签名，供你审阅：\n",
            file=sys.stderr,
        )
        print(json.dumps(current, indent=2, ensure_ascii=False))
        return 2

    with open(args.baseline, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    baseline_sigs = baseline.get("signatures", baseline)

    report = compare(baseline_sigs, current)

    if args.json:
        out = dict(report)
        out["baseline_file"] = args.baseline
        out["source"] = path
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"源码: {path}")
        print(f"基线: {args.baseline} (version {baseline.get('baseline_version', '?')})")
        print("-" * 60)
        if report["REMOVED"]:
            print("🔴 REMOVED（破坏性，必须修技能/examples）:")
            for x in report["REMOVED"]:
                print(f"     - {x}")
        if report["DEFAULT_CHANGED"]:
            print("🟠 DEFAULT_CHANGED（静默行为变化，最危险）:")
            for x in report["DEFAULT_CHANGED"]:
                print(f"     - {x}")
        if report["ADDED"]:
            print("🟢 ADDED（新增能力，可纳入技能）:")
            for x in report["ADDED"]:
                print(f"     + {x}")
        if report["OK"]:
            print("✅ 签名与基线一致，无破坏性变更。")
        else:
            print(
                "\n⚠️ 发现破坏性变更：禁止在未更新技能的情况下宣称「已适配」。\n"
                "   按 SKILL.md §0 工作流更新 references/01-library-api.md 与 examples。"
            )

    return 0 if report["OK"] else 1


if __name__ == "__main__":
    sys.exit(main())
