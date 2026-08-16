"""test_context_folder.py — 验证「会话固定文件夹上下文（G6）」后端。

覆盖：sessions 存取 / 旧库迁移加列 / 受限递归读取（安全+限额）/ 绑定·查询·解绑 API /
未授权根拒绝（防穿越）。隔离：HERMES_DESKTOP_HOME 指向临时目录，绝不触碰真实数据。
运行：python tests/test_context_folder.py  或  pytest tests/test_context_folder.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["HERMES_DESKTOP_HOME"] = tempfile.mkdtemp(prefix="ctx_home_")
os.environ["HERMES_HOME"] = os.environ["HERMES_DESKTOP_HOME"]


def _client_and_root():
    """返回 TestClient 与一个已授权（加入白名单）的临时根目录绝对路径。"""
    import main  # 延迟到 env 设置之后 import
    import sessions
    sessions.reset_cache()  # 确保使用当前临时 HOME 的库
    from starlette.testclient import TestClient
    c = TestClient(main.app)
    tmp = tempfile.mkdtemp(prefix="ctx_root_")
    r = c.post("/api/workspace/roots", json={"path": tmp, "label": "test-root"})
    assert r.status_code == 200, r.text
    return c, tmp


# ── sessions 存取 ───────────────────────────────────────────────────────
def test_sessions_set_get_context_folder():
    import sessions
    sessions.reset_cache()
    cid = sessions.create()["id"]
    assert sessions.get_context_folder(cid) is None
    val = {"root": "/tmp/x", "rel": "a/b", "display": "/tmp/x/a/b"}
    r = sessions.set_context_folder(cid, val)
    assert r["ok"] is True
    assert sessions.get_context_folder(cid) == val
    # get() 也应带回 context_folder
    assert sessions.get(cid)["context_folder"] == val
    # 解绑
    sessions.set_context_folder(cid, None)
    assert sessions.get_context_folder(cid) is None
    print("  test_sessions_set_get_context_folder OK")


def test_migration_column_exists():
    import main
    import sessions
    sessions.reset_cache()
    conn = sessions._get_conn()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()}
    assert "context_folder" in cols, cols
    print("  test_migration_column_exists OK")


# ── 受限递归读取：安全 + 限额 ──────────────────────────────────────────
def test_read_context_folder_basic():
    import main
    c, tmp = _client_and_root()
    # 文本文件（应被读）
    (Path(tmp) / "readme.md").write_text("# hello\nworld", encoding="utf-8")
    sub = Path(tmp) / "src"
    sub.mkdir()
    (sub / "a.py").write_text("print(1)", encoding="utf-8")
    # 跳过的目录（node_modules）里的文本不应被计入
    nm = Path(tmp) / "node_modules"
    nm.mkdir()
    (nm / "lib.js").write_text("should be skipped", encoding="utf-8")
    # 二进制（非文本扩展名）不应被读
    (Path(tmp) / "img.bin").write_text("bin", encoding="utf-8")

    info = main._read_context_folder(tmp, "")
    assert info["error"] is None, info
    assert info["files"] == 2, info  # readme.md + src/a.py
    assert "hello" in info["text"] and "print(1)" in info["text"]
    assert "should be skipped" not in info["text"]  # 跳过 node_modules
    assert "bin" not in info["text"]  # 非文本扩展名不计
    print("  test_read_context_folder_basic OK")


def test_read_context_folder_empty_and_rel():
    import main
    c, tmp = _client_and_root()
    # 空文件夹 → 无注入
    info = main._read_context_folder(tmp, "")
    assert info["files"] == 0 and info["text"] == ""
    # 子目录相对路径（目录不存在 → 无注入）
    info2 = main._read_context_folder(tmp, "no_such_dir")
    assert info2["error"] == "目录不存在"
    print("  test_read_context_folder_empty_and_rel OK")


def test_read_context_folder_truncation():
    import main
    c, tmp = _client_and_root()
    big = Path(tmp) / "big.txt"
    big.write_text("X" * 50000, encoding="utf-8")  # 超过单文件 20KB 上限
    info = main._read_context_folder(tmp, "")
    assert info["files"] == 1
    assert "文件截断" in info["text"]
    print("  test_read_context_folder_truncation OK")


# ── 端点：绑定 · 查询 · 解绑 ───────────────────────────────────────────
def test_api_bind_get_clear():
    import main
    c, tmp = _client_and_root()
    (Path(tmp) / "doc.txt").write_text("ctx content", encoding="utf-8")
    # 先建会话
    conv = c.post("/api/conversations", json={"title": ""})
    assert conv.status_code == 200, conv.text
    cid = conv.json()["item"]["id"]
    # 绑定
    r = c.post("/api/context-folder", json={"conv_id": cid, "root": tmp, "rel": ""})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True and j["context_folder"], j
    assert j["context_folder"]["display"] == str(Path(tmp).resolve())
    assert j["stats"]["files"] >= 1, j
    # 查询
    g = c.get("/api/context-folder", params={"conv_id": cid})
    assert g.status_code == 200, g.text
    assert g.json()["context_folder"]["root"] == str(Path(tmp).resolve())
    # 解绑
    d = c.delete("/api/context-folder?conv_id=" + cid)
    assert d.status_code == 200, d.text
    assert d.json()["context_folder"] is None
    # api_conv_get 也应不再返回绑定
    g2 = c.get("/api/conversations/" + cid)
    assert g2.status_code == 200, g2.text
    assert g2.json().get("context_folder") is None
    print("  test_api_bind_get_clear OK")


def test_api_bind_creates_conv_when_empty():
    import main
    c, tmp = _client_and_root()
    (Path(tmp) / "x.txt").write_text("hi", encoding="utf-8")
    r = c.post("/api/context-folder", json={"conv_id": "", "root": tmp, "rel": ""})
    assert r.status_code == 200, r.text
    assert r.json()["context_folder"], r.json()
    print("  test_api_bind_creates_conv_when_empty OK")


def test_api_bind_403_unauthorized_root():
    import main
    c, tmp = _client_and_root()
    conv = c.post("/api/conversations", json={"title": ""})
    cid = conv.json()["item"]["id"]
    foreign = tempfile.mkdtemp(prefix="ctx_foreign_")  # 未授权根
    r = c.post("/api/context-folder", json={"conv_id": cid, "root": foreign, "rel": ""})
    assert r.status_code == 403, r.text
    assert "授权" in r.json().get("error", ""), r.text
    print("  test_api_bind_403_unauthorized_root OK")


if __name__ == "__main__":
    test_sessions_set_get_context_folder()
    test_migration_column_exists()
    test_read_context_folder_basic()
    test_read_context_folder_empty_and_rel()
    test_read_context_folder_truncation()
    test_api_bind_get_clear()
    test_api_bind_creates_conv_when_empty()
    test_api_bind_403_unauthorized_root()
    print("ALL CONTEXT-FOLDER TESTS PASSED")
