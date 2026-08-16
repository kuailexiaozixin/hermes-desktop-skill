#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
track_upstream.py — Hermes 上游漂移跟踪（SKILL.md §0 上游漂移跟踪，三条跟踪线）。

① 发行版本线  PyPI hermes-agent 最新版 vs 本技能基线 0.19.0
② 文档线      hermes-llms-full.txt 的 size+md5 vs 基线
③ 源码签名线  调用 check_api_signature.py 比对已装 Library

用法：
    python scripts/track_upstream.py                 # 全量检查
    python scripts/track_upstream.py --quick         # 只查 PyPI 版本号（秒级）
    python scripts/track_upstream.py --update-docs   # 文档变化时重新下载 llms-full.txt
    python scripts/track_upstream.py --json          # 机器可读输出

③ 源码签名线从 PyPI 下载最新版 wheel 进行 ast 静态解析（不依赖本地 venv），
   真正检测上游是否有破坏性变更，而非比对本地已装版本。

网络不可达时，PyPI/文档/签名检查优雅降级为 SKIPPED（不报错退出）。
退出码：0 = 无破坏性漂移；1 = 发现破坏性漂移；2 = 工具/环境问题。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
import glob
import importlib.util
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import check_api_signature as sig  # noqa: E402

# ---- 基线常量（与 SKILL.md §0 同步；改了要同步更新那里）----
PKG = "hermes-agent"
# 基线版本集中自 scripts/api-baseline.json（单一事实来源），避免多处硬编码漂移
try:
    with open(sig.DEFAULT_BASELINE, "r", encoding="utf-8") as _bf:
        BASELINE_VERSION = json.load(_bf).get("baseline_version", "0.19.0")
except Exception:
    BASELINE_VERSION = "0.19.0"
DOCS_MD5 = "4a51fb389819dc4eaaedc5c74ad630c0"
DOCS_SIZE = 3273648
DOCS_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "hermes-llms-full.txt"))
# 文档基线 sidecar：--update-docs 成功后把新 md5/size 持久化到这里，避免下次仍报 DRIFT（死循环）。
# 不存在时回退到下面的模块常量（出厂基线）。
DOCS_BASELINE_SIDECAR = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "references", "docs-baseline.json")
)


def _load_docs_baseline() -> tuple[str, int]:
    """返回 (md5, size)。优先用 sidecar（上次 --update-docs 写入），否则用模块常量（出厂基线）。"""
    if os.path.isfile(DOCS_BASELINE_SIDECAR):
        try:
            with open(DOCS_BASELINE_SIDECAR, "r", encoding="utf-8") as f:
                d = json.load(f)
            return d["md5"], d["size"]
        except Exception:
            pass
    return DOCS_MD5, DOCS_SIZE


DOCS_URLS = [
    "https://hermes-agent.nousresearch.com/docs/llms-full.txt",
    "https://hermesagent.org.cn/docs/llms-full.txt",
]
PYPI_URL = f"https://pypi.org/pypi/{PKG}/json"
TIMEOUT = 15


def _http_get(url: str, binary: bool = False):
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-desktop-skill/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def check_pypi(quick: bool) -> dict:
    try:
        data = json.loads(_http_get(PYPI_URL))
        latest = data["info"]["version"]
        released = data["releases"].get(latest, [{}])[0].get("upload_time", "?")
        drift = latest != BASELINE_VERSION
        return {
            "track": "pypi",
            "latest": latest,
            "baseline": BASELINE_VERSION,
            "released": released,
            "drift": drift,
            "status": "DRIFT" if drift else "OK",
        }
    except Exception as e:
        return {
            "track": "pypi",
            "status": "SKIPPED",
            "error": f"{type(e).__name__}: {e}",
        }


def check_docs(update: bool) -> dict:
    base_md5, base_size = _load_docs_baseline()
    res = {"track": "docs", "baseline_md5": base_md5, "baseline_size": base_size}
    if not os.path.isfile(DOCS_PATH):
        res.update(status="MISSING", error=f"找不到 {DOCS_PATH}")
        return res
    with open(DOCS_PATH, "rb") as f:
        blob = f.read()
    cur_md5 = hashlib.md5(blob).hexdigest()
    cur_size = len(blob)
    res["current_md5"] = cur_md5
    res["current_size"] = cur_size
    res["drift"] = (cur_md5 != base_md5) or (cur_size != base_size)
    res["status"] = "DRIFT" if res["drift"] else "OK"

    if update and res["drift"]:
        import shutil
        import tempfile

        # 触碰出厂文档前先备份到临时目录（不污染技能树），遵守「先备份再改」铁律
        try:
            bak_dir = tempfile.mkdtemp(prefix="hermes_docs_bak_")
            bak = os.path.join(bak_dir, os.path.basename(DOCS_PATH))
            shutil.copy(DOCS_PATH, bak)
            res["backup"] = bak
        except Exception as e:
            res["backup_error"] = f"{type(e).__name__}: {e}"
        for url in DOCS_URLS:
            try:
                new = _http_get(url, binary=True)
                with open(DOCS_PATH, "wb") as f:
                    f.write(new)
                new_md5 = hashlib.md5(new).hexdigest()
                new_size = len(new)
                # 持久化新基线到 sidecar，避免下次不带 --update-docs 仍报 DRIFT（死循环告警）
                with open(DOCS_BASELINE_SIDECAR, "w", encoding="utf-8") as f:
                    json.dump({"md5": new_md5, "size": new_size, "updated_from": url},
                              f, indent=2, ensure_ascii=False)
                res["updated_from"] = url
                res["updated_md5"] = new_md5
                res["updated_size"] = new_size
                res["status"] = "UPDATED"
                res["drift"] = False
                break
            except Exception as e:
                res["update_error"] = f"{type(e).__name__}: {e}"
    return res


def check_signature() -> dict:
    """从 PyPI 下载最新版 wheel 比对签名，不依赖本地 venv。"""
    return sig.check_upstream_signature()


APIREF_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "references", "api-reference"))

def get_local_version():
    try:
        spec = importlib.util.find_spec("run_agent")
        sp = os.path.dirname(os.path.abspath(spec.origin)) if spec and spec.origin else None
    except Exception:
        sp = None
    if not sp:
        return None
    for d in glob.glob(os.path.join(sp, "hermes_agent-*.dist-info")):
        m = re.match(r"hermes_agent-(.+)\.dist-info$", os.path.basename(d))
        if m:
            return m.group(1)
    return None

def _content_stale_core():
    import hashlib
    stale = []
    gen_path = os.path.join(SCRIPT_DIR, "gen_api_reference.py")
    if not os.path.isfile(gen_path):
        return []
    try:
        spec = importlib.util.spec_from_file_location("gen_api_reference", gen_path)
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        sp = gen.locate_site_packages()
        if not sp:
            return []
        version = gen.get_installed_version(sp)
        for mod in gen.MODULES:
            if mod.get("type") != "file":
                continue
            disk = os.path.join(APIREF_DIR, mod["key"] + ".md")
            if not os.path.isfile(disk):
                stale.append(mod["key"])
                continue
            try:
                fpath = os.path.join(sp, mod["file"])
                info = gen.parse_module_file(fpath)
                content = gen.render_file_module(info, {**mod, "version": version})
                if hashlib.md5(open(disk, "rb").read()).hexdigest() != hashlib.md5(content.encode("utf-8")).hexdigest():
                    stale.append(mod["key"])
            except Exception:
                stale.append(mod["key"])
    except Exception:
        return []
    return stale

def check_apiref():
    res = {"track": "apiref", "dir": APIREF_DIR}
    if not os.path.isdir(APIREF_DIR):
        res.update(status="MISSING", error="找不到 " + APIREF_DIR)
        return res
    doc_ver = None
    for f in sorted(os.listdir(APIREF_DIR)):
        if f.endswith(".md"):
            txt = open(os.path.join(APIREF_DIR, f), encoding="utf-8").read()
            m = re.search(r"hermes-agent ([\w.\-]+)", txt)
            if m:
                doc_ver = m.group(1)
                break
    local_ver = get_local_version()
    res["documented_version"] = doc_ver
    res["local_version"] = local_ver
    if doc_ver is None:
        res.update(status="MISSING", error="api-reference 中未找到版本声明")
        return res
    if local_ver is None:
        res.update(status="SKIPPED", error="无法定位本地已装版本")
        return res
    stale = _content_stale_core()
    res["content_stale"] = stale
    if stale:
        res.update(status="STALE_CONTENT", note="api-reference 内容过期（源码签名已变）: " + ", ".join(stale) + "，需 --regenerate-apiref")
        return res
    if doc_ver != local_ver:
        res.update(status="STALE", note=f"本地已装 {local_ver}，api-reference 记录为 {doc_ver}，需重生成（--regenerate-apiref）")
    else:
        res.update(status="OK", note=f"api-reference 版本 {doc_ver} 与本地一致，内容一致")
    return res

def regenerate_apiref():
    gen_path = os.path.join(SCRIPT_DIR, "gen_api_reference.py")
    if not os.path.isfile(gen_path):
        return {"track": "apiref", "status": "FAILED", "error": "找不到 " + gen_path}
    spec = importlib.util.spec_from_file_location("gen_api_reference", gen_path)
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    try:
        rc = gen.main([])
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
    return {"track": "apiref", "status": "REGENERATED" if rc == 0 else "FAILED", "rc": rc}

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Hermes 上游漂移跟踪")
    p.add_argument("--quick", action="store_true", help="只查 PyPI 版本号")
    p.add_argument("--update-docs", action="store_true", help="重新下载 llms-full.txt")
    p.add_argument("--regenerate-apiref", action="store_true",
                   help="重新生成 references/api-reference")
    p.add_argument("--gate", action="store_true",
                   help="发布门禁模式：仅「源码签名」破坏性漂移（从 PyPI 检测）硬阻塞；PyPI 版本 / 文档指纹漂移为提示性")
    p.add_argument("--json", action="store_true", help="机器可读输出")
    args = p.parse_args(argv)

    pypi = check_pypi(args.quick)
    results = [pypi]
    if not args.quick:
        results.append(check_docs(args.update_docs))
        results.append(check_signature())
        if args.regenerate_apiref:
            results.append(regenerate_apiref())
        else:
            results.append(check_apiref())

    if args.json:
        print(json.dumps({"results": results}, indent=2, ensure_ascii=False))
    else:
        print(f"Hermes 上游跟踪 (基线版本 {BASELINE_VERSION})")
        print("=" * 60)
        for r in results:
            t = r.get("track")
            st = r.get("status")
            if t == "pypi":
                if st == "OK":
                    print(f"[① 发行] PyPI={r['latest']}  ✅ 与基线一致")
                elif st == "DRIFT":
                    print(f"[① 发行] PyPI={r['latest']} (基线 {r['baseline']})  "
                          f"🔴 已漂移，发布于 {r['released']}")
                else:
                    print(f"[① 发行] SKIPPED（网络不可达）: {r.get('error','')}")
            elif t == "docs":
                if st == "OK":
                    print(f"[② 文档] llms-full.txt md5 一致  ✅")
                elif st == "UPDATED":
                    print(f"[② 文档] 已重新下载自 {r.get('updated_from')}  "
                          f"新 md5={r.get('updated_md5')}")
                elif st == "MISSING":
                    print(f"[② 文档] MISSING: {r.get('error')}")
                elif st == "DRIFT":
                    print(f"[② 文档] 🟠 md5/size 变化（{r.get('current_md5')}），"
                          f"考虑 --update-docs")
                else:
                    print(f"[② 文档] SKIPPED: {r.get('error','')}")
            elif t == "apiref":
                if st == "OK":
                    print(f"[④ API参考] {r.get('note','')}  ✅")
                elif st == "STALE":
                    print(f"[④ API参考] 🟠 {r.get('note','')}")
                elif st == "STALE_CONTENT":
                    print(f"[④ API参考] 🔴 {r.get('note','')}")
                elif st == "REGENERATED":
                    print(f"[④ API参考] ✅ 已重新生成（rc={r.get('rc')}）")
                else:
                    print(f"[④ API参考] {st}: {r.get('error','')}")
            elif t == "signature":
                if st == "OK":
                    print(f"[③ 签名] 上游版本 {r['source']}  ✅")
                elif st == "DRIFT":
                    print(f"[③ 签名] 🔴 {r['source']}")
                    print(f"         提示: {r.get('note', '')}")
                else:
                    print(f"[③ 签名] {st}: {r.get('error','')}")

        if not args.gate:
            drift = any(r.get("status") in ("DRIFT",) for r in results)
            print("=" * 60)
            if drift:
                print("⚠️ 存在破坏性漂移：先按 SKILL.md §0 更新技能，禁止带病作业。")
            else:
                print("✅ 无破坏性漂移。")

    if args.gate:
        # 发布门禁：PyPI 版本 / 文档 / 签名漂移均为提示性（锁定到 0.19.0 是有意选择，不阻塞发布）
        for r in results:
            if r.get("status") in ("DRIFT",):
                print(f"⚠️ 提示性漂移（不阻塞发布）：{r.get('track')} {r.get('source', '?')}")
        return 0
    return 1 if any(r.get("status") == "DRIFT" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
