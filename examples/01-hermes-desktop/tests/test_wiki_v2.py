"""test_wiki_v2.py — Part 1 LLM Wiki v2 功能缺口落地验证（B8/C2/B3/E2/G2/G3）。

隔离：所有测试用 tempfile.mkdtemp() 作 HERMES_HOME，绝不触碰真实数据。
运行：python tests/test_wiki_v2.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

# 让脚本在 examples/01-hermes-desktop 下可直接运行
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import wiki_engine as we  # noqa: E402


def _fresh_home() -> Path:
    h = Path(tempfile.mkdtemp(prefix="wiki_v2_"))
    we.ensure_structure(h)
    return h


def _cleanup(h: Path):
    shutil.rmtree(h, ignore_errors=True)


def test_b8_rename_cascade():
    """B8：改名一页，全库引用联动更新 + 反链重算 + 旧 slug 失效。"""
    h = _fresh_home()
    try:
        # 建三页：transformer 引用 llm 与 attention；llm 反向引用 transformer
        we.save_page(h, slug="concepts/transformer", title="Transformer",
                     type_="concept", text="核心见 [[entities/llm]] 与 "
                     "[[concepts/attention]]。")
        we.save_page(h, slug="entities/llm", title="LLM", type_="entity",
                     text="基于 [[concepts/transformer]] 架构。")
        we.save_page(h, slug="concepts/attention", title="Attention",
                     type_="concept", text="注意力机制。")

        # 旧 slug 可达
        assert we.get_page(h, "concepts/transformer") is not None
        # llm 正文含旧链接
        llm_before = we.get_page(h, "entities/llm")["body"]
        assert "[[concepts/transformer]]" in llm_before

        # 执行改名
        res = we.rename_page(h, "concepts/transformer", "concepts/attention-mechanism")
        assert res["ok"], res
        assert res["new"] == "concepts/attention-mechanism"
        assert res["updated"], "应有 ≥1 页引用被联动更新"

        # 旧 slug 不可达，新 slug 可达
        assert we.get_page(h, "concepts/transformer") is None, "旧 slug 应已失效"
        assert we.get_page(h, "concepts/attention-mechanism") is not None

        # llm 正文引用已联动到新 slug
        llm_after = we.get_page(h, "entities/llm")["body"]
        assert "[[concepts/transformer]]" not in llm_after, "旧链接应已被替换"
        assert "[[concepts/attention-mechanism]]" in llm_after, "引用未联动到新 slug"

        # 反链重算：新 slug 的 inbound 应含 entities/llm
        new_pg = we.get_page(h, "concepts/attention-mechanism")
        assert "entities/llm" in new_pg["inbound"], f"反链未重算: {new_pg['inbound']}"
    finally:
        _cleanup(h)


def test_b8_rename_cascade_short_form():
    """B8 回归：正文按「短名」（去掉类型子目录的叶子名）书写的 [[wikilinks]]，
    以及别名 [[x|显示]]、全长 [[concepts/x#锚]]，都必须在改名时联动更新。

    这是真实数据损坏 bug 的回归护栏：旧实现只替换全称 slug，导致短链残留为
    指向已删除页面的断链（文档所谓的「改名联动硬缺口」实为级联对短链失效）。
    """
    h = _fresh_home()
    try:
        we.save_page(h, slug="entities/llm", title="LLM", type_="entity", text="实体页。")
        we.save_page(h, slug="concepts/attention", title="Attention",
                     type_="concept", text="注意力。")
        # 正文用 无别名短链 + 别名 + 全长 三种写法混合
        we.save_page(h, slug="concepts/transformer", title="Transformer",
                     type_="concept",
                     text="见 [[llm]] 与短链 [[attention]] 与别名 [[attention|注意力]] "
                           "以及全长 [[concepts/attention#sec]]。")
        res = we.rename_page(h, "concepts/attention", "concepts/attention-v2")
        assert res["ok"], res
        assert res["updated"], "短链引用页应被联动更新"

        tf = we.get_page(h, "concepts/transformer")["body"]
        # 无别名短链更新
        assert "[[attention-v2]]" in tf, "无别名短链未更新: " + tf
        # 无关短链不被误改
        assert "[[llm]]" in tf, "无关短链不应被改动: " + tf
        # 别名更新
        assert "[[attention-v2|注意力]]" in tf, "别名未更新: " + tf
        # 全长更新（且子目录部分不被误改）
        assert "[[concepts/attention-v2#sec]]" in tf, "全长链接未更新: " + tf
        # 反链重算
        assert "concepts/transformer" in we.get_page(h, "concepts/attention-v2")["inbound"]
    finally:
        _cleanup(h)


def test_b8_rename_preserves_subdir():
    """B8：用户只填短名（无类型子目录）时，新文件仍落在原类型子目录，避免链接错落目录。"""
    h = _fresh_home()
    try:
        we.save_page(h, slug="concepts/foo", title="Foo", type_="concept", text="x")
        res = we.rename_page(h, "concepts/foo", "bar")
        assert res["ok"], res
        assert res["new"] == "concepts/bar", "应沿用 concepts 子目录: " + res["new"]
        assert we.get_page(h, "concepts/bar") is not None
        assert we.get_page(h, "concepts/foo") is None
    finally:
        _cleanup(h)


def test_b8_rename_conflict_protection():
    """B8：改名到已存在的 slug 应被拒绝（防覆盖）。"""
    h = _fresh_home()
    try:
        we.save_page(h, slug="concepts/a", title="A", type_="concept", text="x")
        we.save_page(h, slug="concepts/b", title="B", type_="concept", text="y")
        res = we.rename_page(h, "concepts/a", "concepts/b")
        assert not res["ok"], "冲突改名应失败"
        assert "已存在" in res["error"], res
        # 两页都还在
        assert we.get_page(h, "concepts/a") is not None
        assert we.get_page(h, "concepts/b") is not None
    finally:
        _cleanup(h)


def test_b3_write_time_broken_detection():
    """B3：保存页面时立即报告指向不存在页的 [[wikilinks]]。"""
    h = _fresh_home()
    try:
        res = we.save_page(h, slug="concepts/foo", title="Foo", type_="concept",
                           text="指向 [[concepts/bar-nonexistent]] 与 [[concepts/exists]]。")
        assert res["ok"]
        # bar-nonexistent 不存在 → 应报断链
        assert "concepts/bar-nonexistent" in res["broken"], res
        # exists 也不存在 → 同样断链（尚未创建）
        assert "concepts/exists" in res["broken"], res
        # 创建 exists 后，断链应只剩 bar-nonexistent
        we.save_page(h, slug="concepts/exists", title="Exists", type_="concept", text="ok")
        res2 = we.save_page(h, slug="concepts/foo2", title="Foo2", type_="concept",
                            text="指向 [[concepts/bar-nonexistent]] 与 [[concepts/exists]]。")
        assert "concepts/bar-nonexistent" in res2["broken"]
        assert "concepts/exists" not in res2["broken"], "已存在链接不应再报断链"
    finally:
        _cleanup(h)


def test_c2_fulltext_search():
    """C2：跨页面与 raw 源全文检索，返回带摘要结果。"""
    h = _fresh_home()
    try:
        we.save_page(h, slug="concepts/transformer", title="Transformer 模型",
                     type_="concept", tags=["深度学习"],
                     text="Transformer 用自注意力处理序列。")
        we.save_page(h, slug="entities/llm", title="大语言模型", type_="entity",
                     text="LLM 是生成式预训练模型。")
        # raw 源
        we.add_raw(h, "paper.txt", "Transformer 架构首次在论文中提出。", source_url="")

        res = we.search(h, "Transformer")
        kinds = {r["kind"] for r in res}
        assert "page" in kinds, "应命中页面"
        assert "raw" in kinds, "应命中 raw 源"
        assert any(r["kind"] == "page" and r["slug"] == "concepts/transformer" for r in res)
        # 摘要非空
        assert all(r.get("snippet") for r in res), "每个结果应有摘要"
        # 无命中
        assert we.search(h, "zzznotfound") == []
    finally:
        _cleanup(h)


def test_e2_fix_broken_links():
    """E2：一键为断链目标生成占位页，使链接可解析。"""
    h = _fresh_home()
    try:
        we.save_page(h, slug="concepts/orphan-ref", title="Orphan Ref",
                     type_="concept", text="指向 [[concepts/ghost]] 与 [[concepts/ghost2]]。")
        # 改前：ghost 不存在
        assert we.get_page(h, "concepts/ghost") is None
        before = we.get_page(h, "concepts/orphan-ref")
        assert "concepts/ghost" not in before["outbound"], "改前应为断链(不在 outbound)"

        res = we.fix_broken_links(h)
        assert res["ok"]
        assert "concepts/ghost" in res["created"], res
        assert "concepts/ghost2" in res["created"], res

        # 改后：占位页已生成，链接可解析
        assert we.get_page(h, "concepts/ghost") is not None
        after = we.get_page(h, "concepts/orphan-ref")
        assert "concepts/ghost" in after["outbound"], "修复后链接应可解析并入 outbound"
    finally:
        _cleanup(h)


def test_g2_g3_export_import():
    """G2/G3：导出无损 JSON 包，导入到新 HOME 还原。"""
    h1 = _fresh_home()
    try:
        we.save_page(h1, slug="concepts/transformer", title="Transformer",
                     type_="concept", tags=["dl"], text="自注意力。")
        we.save_page(h1, slug="entities/llm", title="LLM", type_="entity",
                     text="生成式模型。")
        we.add_raw(h1, "src.txt", "原始材料内容。", source_url="")

        exp = we.export_wiki(h1)
        assert exp["ok"]
        assert len(exp["pages"]) == 2
        assert len(exp["raw"]) == 1
        assert exp["schema"]

        # 导入到全新 HOME
        h2 = _fresh_home()
        try:
            imp = we.import_wiki(h2, exp)
            assert imp["ok"], imp
            # 页面还原
            assert we.get_page(h2, "concepts/transformer") is not None
            assert we.get_page(h2, "entities/llm") is not None
            pg = we.get_page(h2, "concepts/transformer")
            assert pg["body"].strip().endswith("自注意力。"), pg["body"]
            assert pg["tags"] == ["dl"], pg["tags"]
            # raw 还原（add_raw 统一落盘为 <name>.md）
            assert we.list_raw(h2)[0]["name"] == "src.txt.md"
            assert len(we.list_pages(h2)) == 2
        finally:
            _cleanup(h2)
    finally:
        _cleanup(h1)


def main():
    tests = [
        test_b8_rename_cascade,
        test_b8_rename_cascade_short_form,
        test_b8_rename_preserves_subdir,
        test_b8_rename_conflict_protection,
        test_b3_write_time_broken_detection,
        test_c2_fulltext_search,
        test_e2_fix_broken_links,
        test_g2_g3_export_import,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"[FAIL] {t.__name__}: {e!r}")
    print(f"\n=== {passed} passed, {failed} failed ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
