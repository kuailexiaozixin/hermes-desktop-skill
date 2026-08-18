"""test_workspace.py — 验证「工作区文件浏览器」后端：授权根约束 + 浏览/读写/删除/附件。

安全核心：所有路径必须落在「授权根」之内，越界（目录穿越）一律 403 / 抛 ValueError。
隔离：HERMES_DESKTOP_HOME 指向临时目录，测试用根也用临时目录，绝不触碰真实数据。
运行：python tests/test_workspace.py  或  pytest tests/test_workspace.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["HERMES_DESKTOP_HOME"] = tempfile.mkdtemp(prefix="ws_home_")
os.environ["HERMES_HOME"] = os.environ["HERMES_DESKTOP_HOME"]


def _client_and_root():
    """返回 TestClient 与一个已授权（加入白名单）的临时根目录绝对路径。"""
    import main  # 延迟到 env 设置之后 import
    from starlette.testclient import TestClient
    c = TestClient(main.app)
    tmp = tempfile.mkdtemp(prefix="ws_root_")
    r = c.post("/api/workspace/roots", json={"path": tmp, "label": "test-root"})
    assert r.status_code == 200, r.text
    return c, tmp


def _auth_tmp():
    """创建一个临时目录并把它加入授权根，返回 (client, tmp)。供 helper 测试用。"""
    c, tmp = _client_and_root()
    return c, tmp


# ── 安全解析helper ──────────────────────────────────────────────────────
def test_helper_resolve_ok():
    import main
    _, tmp = _auth_tmp()
    abs_p, rel = main._ws_resolve(tmp, "a/b/c.txt")
    assert rel == "a/b/c.txt", rel
    assert str(abs_p) == os.path.join(tmp, "a", "b", "c.txt")
    assert str(abs_p.resolve()).startswith(str(Path(tmp).resolve()) + os.sep)
    print("  test_helper_resolve_ok OK")


def test_helper_resolve_traversal():
    import main
    _, tmp = _auth_tmp()
    for rel in ("../../etc/secret", "/abs/etc/secret", "a/../../b", "..\\..\\win"):
        try:
            abs_p, _ = main._ws_resolve(tmp, rel)
        except ValueError:
            continue
        # 若未抛错，也必须落在根内
        assert str(abs_p.resolve()).startswith(str(Path(tmp).resolve()) + os.sep), rel
        assert ".." not in str(abs_p), rel
    print("  test_helper_resolve_traversal OK")


def test_helper_resolve_unauthorized_root():
    import main
    foreign = tempfile.mkdtemp(prefix="ws_foreign_")  # 未授权
    try:
        main._ws_resolve(foreign, "x.txt")
        raise AssertionError("应拒绝未授权根")
    except ValueError as e:
        assert "授权" in str(e), e
    print("  test_helper_resolve_unauthorized_root OK")


# ── 端点：浏览 / 读取 ──────────────────────────────────────────────────
def test_endpoint_list_and_read():
    c, tmp = _client_and_root()
    (Path(tmp) / "sub").mkdir()
    f = Path(tmp) / "hello.txt"
    f.write_text("workspace content", encoding="utf-8")
    r = c.get("/api/workspace/list", params={"root": tmp, "path": ""})
    assert r.status_code == 200, r.text
    j = r.json()
    names = [e["name"] for e in j["entries"]]
    assert "hello.txt" in names and "sub/" in names, names
    r2 = c.get("/api/workspace/read", params={"root": tmp, "path": "hello.txt"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["content"] == "workspace content"
    print("  test_endpoint_list_and_read OK")


def test_endpoint_traversal_403():
    c, tmp = _client_and_root()
    # 越界（目录穿越）由「未授权根」这一关拦截：传入不在白名单的绝对根 → 403
    foreign = tempfile.mkdtemp(prefix="ws_foreign_")
    r = c.get("/api/workspace/list", params={"root": foreign, "path": "x"})
    assert r.status_code == 403, r.text
    assert "授权" in r.json().get("error", ""), r.text
    # path 带 .. 企图跳出授权根：经 _ws_resolve 的 commonpath 越界检查，
    # 严格返回 403（防御纵深，绝不 neutralize 成 200/404 让逃逸请求「看似成功」）。
    r2 = c.get("/api/workspace/list", params={"root": tmp, "path": "../../../../etc"})
    assert r2.status_code == 403, r2.text
    assert "越界" in r2.json().get("error", ""), r2.text
    print("  test_endpoint_traversal_403 OK")


# ── 端点：写 / 建 / 改名 / 删 ───────────────────────────────────────────
def test_endpoint_write_mkdir_rename_delete():
    c, tmp = _client_and_root()
    # 写文件（含自动建父目录）
    r = c.post("/api/workspace/write", json={"root": tmp, "path": "a/b/note.md", "content": "# hi"})
    assert r.status_code == 200, r.text
    assert (Path(tmp) / "a/b/note.md").read_text(encoding="utf-8") == "# hi"
    # 建目录
    r = c.post("/api/workspace/mkdir", json={"root": tmp, "path": "a/c"})
    assert r.status_code == 200, r.text
    assert (Path(tmp) / "a/c").is_dir()
    # 改名
    r = c.post("/api/workspace/rename", json={"root": tmp, "src": "a/b/note.md", "dst": "a/b/note2.md"})
    assert r.status_code == 200, r.text
    assert (Path(tmp) / "a/b/note2.md").exists() and not (Path(tmp) / "a/b/note.md").exists()
    # 删除
    r = c.post("/api/workspace/delete", json={"root": tmp, "path": "a"})
    assert r.status_code == 200, r.text
    assert not (Path(tmp) / "a").exists()
    print("  test_endpoint_write_mkdir_rename_delete OK")


def test_endpoint_write_rejects_directory():
    c, tmp = _client_and_root()
    (Path(tmp) / "d").mkdir()
    r = c.post("/api/workspace/write", json={"root": tmp, "path": "d", "content": "x"})
    assert r.status_code in (400, 500) or r.json().get("ok") is False, r.text
    print("  test_endpoint_write_rejects_directory OK")


# ── 端点：附件化（复制进 uploads，复用 /api/chat 注入） ────────────────
def test_endpoint_attach():
    c, tmp = _client_and_root()
    f = Path(tmp) / "data.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    r = c.post("/api/workspace/attach", json={"root": tmp, "path": "data.csv"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j.get("ok") is True and j.get("attachment"), j
    att = j["attachment"]
    saved = Path(att["path"])
    assert saved.exists() and saved.read_text(encoding="utf-8") == "a,b\n1,2\n"
    # 落盘点必须在 HERMES_DESKTOP_HOME/uploads 之内
    up = Path(os.environ["HERMES_DESKTOP_HOME"]) / "uploads"
    assert str(saved.resolve()).startswith(str(up.resolve()) + os.sep), saved
    print("  test_endpoint_attach OK")


def test_endpoint_attach_traversal_403():
    c, tmp = _client_and_root()
    foreign = tempfile.mkdtemp(prefix="ws_foreign_")
    r = c.post("/api/workspace/attach", json={"root": foreign, "path": "x"})
    assert r.status_code == 403, r.text
    assert "授权" in r.json().get("error", ""), r.text
    print("  test_endpoint_attach_traversal_403 OK")


# ── 端点：授权根增删 ───────────────────────────────────────────────────
def test_endpoint_roots_add_remove():
    import main
    from starlette.testclient import TestClient
    c = TestClient(main.app)
    extra = tempfile.mkdtemp(prefix="ws_extra_")
    r = c.post("/api/workspace/roots", json={"path": extra, "label": "extra"})
    assert r.status_code == 200, r.text
    assert any(x["path"] == str(Path(extra).resolve()) for x in r.json()["roots"])
    # 移除（用 query 参数，避免老版本 TestClient 对 DELETE body 的限制）
    r = c.delete("/api/workspace/roots?path=" + str(Path(extra).resolve()))
    assert r.status_code == 200, r.text
    assert not any(x["path"] == str(Path(extra).resolve()) for x in r.json()["roots"])
    print("  test_endpoint_roots_add_remove OK")


if __name__ == "__main__":
    test_helper_resolve_ok()
    test_helper_resolve_traversal()
    test_helper_resolve_unauthorized_root()
    test_endpoint_list_and_read()
    test_endpoint_traversal_403()
    test_endpoint_write_mkdir_rename_delete()
    test_endpoint_write_rejects_directory()
    test_endpoint_attach()
    test_endpoint_attach_traversal_403()
    test_endpoint_roots_add_remove()
    print("ALL WORKSPACE TESTS PASSED")
