"""test_wiki_llm.py — Part 2 LLM Wiki 的 LLM 核心路径离线验证（Ingest / Query / lint 只读 / save_page 矛盾标记）。

通过 mock `agent_runtime.build_agent`，无需真实 API Key 即可验证：
  - Ingest 走 `_ask_agent` → 编译出页面（`concepts/alpha`、`concepts/beta`）并互联反链；
  - Query 走 `_ask_agent` → 解析 `CITED:` 引用；
  - lint 为只读：运行 lint 不修改 `_backlinks.json`；
  - save_page 产出 `contested` / `contradictions` frontmatter（供 Lint 矛盾标记触发）。

隔离：所有测试用临时目录作 HERMES_HOME，绝不触碰真实数据。
运行：python tests/test_wiki_llm.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

# 让脚本在 examples/01-hermes-desktop 下可直接运行
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import wiki_engine as we  # noqa: E402
import agent_runtime  # noqa: E402  (patch build_agent)


class _FakeAgent:
    """根据提示内容返回确定性 canned 结果，模拟 Hermes LLM 往返。"""

    def run_conversation(self, user_message, system_message=None):
        # Ingest 提示含「源材料」→ 返回编译好的 JSON 页数组
        if "源材料" in (user_message or ""):
            pages = [
                {
                    "slug": "concepts/alpha",
                    "title": "Alpha",
                    "type": "concept",
                    "tags": ["demo"],
                    "confidence": "high",
                    "body": "# Alpha\nAlpha 与 [[concepts/beta]] 相关。",
                },
                {
                    "slug": "concepts/beta",
                    "title": "Beta",
                    "type": "concept",
                    "tags": ["demo"],
                    "confidence": "medium",
                    "body": "# Beta\nBeta 见 [[concepts/alpha]]。",
                },
            ]
            return {"final_response": json.dumps(pages, ensure_ascii=False)}
        # Query 提示 → 返回带 CITED 的答案
        return {
            "final_response": "基于知识库，Alpha 与 Beta 互联。\nCITED: concepts/alpha, concepts/beta"
        }


def _use_fake_agent():
    agent_runtime.build_agent = lambda *a, **k: _FakeAgent()


def _fresh_home() -> Path:
    h = Path(tempfile.mkdtemp(prefix="wiki_llm_"))
    we.ensure_structure(h)
    return h


def run():
    _use_fake_agent()
    cfg = {"api_key": "test-key"}  # 仅用于绕过「未配置 Key」校验，实际不发起网络请求
    checks: list[tuple[str, bool]] = []

    h = _fresh_home()
    try:
        # 1) add_raw 写入源 frontmatter
        we.add_raw(h, "src.md", "# 源\nAlpha 与 Beta。", source_url="https://example.com/src")
        raw_text = (h / "wiki" / "raw" / "src.md").read_text(encoding="utf-8")
        checks.append(("add_raw 写源 frontmatter",
                       raw_text.startswith("---") and "sha256:" in raw_text and "source_url:" in raw_text))

        # 2) ingest 走 LLM 路径，产出页面
        res = we.ingest(h, model_cfg=cfg)
        pages = we.list_pages(h)
        slugs = {p["slug"] for p in pages}
        checks.append(("ingest 经 LLM 产出页面",
                       res["ok"] and {"concepts/alpha", "concepts/beta"} <= slugs))

        # 3) ingest 后反链已建立（alpha <-> beta 互联）
        ga = we.get_page(h, "concepts/alpha")
        checks.append(("反链已解析", ga is not None and "concepts/beta" in ga["outbound"]))

        # 4) query 走 LLM 路径，解析 cited
        q = we.query(h, "Alpha 与 Beta 的关系", model_cfg=cfg)
        checks.append(("query 解析 CITED",
                       q["ok"] and set(q["cited"]) >= {"concepts/alpha", "concepts/beta"}))

        # 5) lint 只读：运行前后 _backlinks.json 内容不变
        bl_before = (h / "wiki" / "_backlinks.json").read_text(encoding="utf-8")
        we.lint(h)
        bl_after = (h / "wiki" / "_backlinks.json").read_text(encoding="utf-8")
        checks.append(("lint 为只读（不回写反链）", bl_before == bl_after))

        # 6) save_page 产出 contested / contradictions frontmatter
        we.save_page(h, title="Gamma", type_="concept", text="# Gamma",
                     contested=True, contradictions=["concepts/alpha"], model_cfg=cfg)
        gp = None
        for p in we.list_pages(h):
            if p["title"] == "Gamma":
                gp = we.get_page(h, p["slug"])
        checks.append(("save_page 产出 contested/contradictions",
                       gp is not None
                       and gp.get("contested") is True
                       and "concepts/alpha" in (gp.get("contradictions") or [])))

        # 7) lint 矛盾标记：带 contested 的页应被标出
        lint_res = we.lint(h)
        contradiction_hit = any(i["check"] == "contradiction" for i in lint_res["issues"])
        checks.append(("lint 触发矛盾标记", contradiction_hit))
    finally:
        shutil.rmtree(h, ignore_errors=True)

    ok = all(v for _, v in checks)
    for name, v in checks:
        print(f"  [{'PASS' if v else 'FAIL'}] {name}")
    print(f"\n=== {'ALL PASS' if ok else 'SOME FAILED'} ({sum(1 for _, v in checks if v)}/{len(checks)}) ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
