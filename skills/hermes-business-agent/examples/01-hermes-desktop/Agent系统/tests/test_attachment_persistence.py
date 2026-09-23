"""test_attachment_persistence.py — 验证附件元数据跨「落盘 → 重开 → Agent 覆盖 → 复制」持久化。

隔离：HERMES_DESKTOP_HOME 指向临时目录，绝不触碰真实数据。
运行：python tests/test_attachment_persistence.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["HERMES_DESKTOP_HOME"] = tempfile.mkdtemp(prefix="attach_persist_")
os.environ["HERMES_HOME"] = os.environ["HERMES_DESKTOP_HOME"]
import sessions  # noqa: E402

sessions.reset_cache()

ATT = [
    {"name": "a.txt", "path": "/tmp/a.txt", "size": 10},
    {"name": "b.csv", "path": "/tmp/b.csv", "size": 20},
]


def test_append_persists():
    sessions.append("c1", "user", "hi", attachments=ATT)
    msgs = sessions.get_messages("c1")
    assert len(msgs) == 1
    assert msgs[0]["attachments"] == ATT, msgs[0]["attachments"]
    print("  test_append_persists OK")


def test_get_returns_attachments():
    s = sessions.get("c1")
    assert s["messages"][0]["attachments"] == ATT
    print("  test_get_returns_attachments OK")


def test_set_messages_preserves():
    # 模拟 Agent 回传（不含 attachments），整体覆盖前需回填，否则刚落盘的附件被冲掉
    msgs = [
        {"role": "user", "content": "hi", "attachments": ATT},
        {"role": "assistant", "content": "hello back"},
    ]
    sessions.set_messages("c1", msgs)
    out = sessions.get_messages("c1")
    assert out[0]["role"] == "user" and out[0]["attachments"] == ATT
    assert out[1]["role"] == "assistant" and out[1]["attachments"] is None
    print("  test_set_messages_preserves OK")


def test_copy_preserves():
    r = sessions.copy("c1")
    assert r.get("ok")
    out = sessions.get_messages(r["id"])
    user_msgs = [m for m in out if m["role"] == "user"]
    assert user_msgs and user_msgs[0]["attachments"] == ATT
    print("  test_copy_preserves OK")


def test_backward_compat_null():
    sessions.append("c2", "user", "no attach")  # 无 attachments
    msgs = sessions.get_messages("c2")
    assert msgs[0]["attachments"] is None
    print("  test_backward_compat_null OK")


def test_schema_has_column():
    dbp = Path(os.environ["HERMES_DESKTOP_HOME"]) / "desktop" / "sessions.db"
    conn = sqlite3.connect(str(dbp))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
    conn.close()
    assert "attachments" in cols, cols
    print("  test_schema_has_column OK")


def test_migration_old_db():
    # 构造一个无 attachments 列的旧库，验证 _migrate_messages_attachments 补齐且不报错
    d = Path(tempfile.mkdtemp(prefix="attach_old_"))
    dbp = d / "desktop" / "sessions.db"
    dbp.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(dbp))
    c.executescript(
        "CREATE TABLE conversations (id TEXT PRIMARY KEY, title TEXT, pinned INTEGER, "
        "archived INTEGER, tags TEXT, \"group\" TEXT, created_at REAL, updated_at REAL, "
        "model TEXT, usage_input INTEGER, usage_output INTEGER);"
        "CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, cid TEXT, seq INTEGER, "
        "role TEXT, content TEXT, created_at REAL);"
    )
    c.commit()
    c.close()
    os.environ["HERMES_DESKTOP_HOME"] = str(d)
    sessions.reset_cache()
    sessions.append("x", "user", "old", attachments=ATT)  # 触发迁移 + 写入
    msgs = sessions.get_messages("x")
    assert msgs[0]["attachments"] == ATT
    print("  test_migration_old_db OK")


def main():
    tests = [
        test_append_persists,
        test_get_returns_attachments,
        test_set_messages_preserves,
        test_copy_preserves,
        test_backward_compat_null,
        test_schema_has_column,
        test_migration_old_db,
    ]
    for t in tests:
        t()
    print("\nALL ATTACHMENT PERSISTENCE TESTS PASSED")


if __name__ == "__main__":
    main()
