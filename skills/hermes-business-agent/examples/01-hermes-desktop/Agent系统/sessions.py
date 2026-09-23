"""sessions.py — 多会话持久化（服务端唯一真相，落盘 HERMES_HOME/desktop/sessions.db）

为什么放服务端而不是 localStorage
================================
桌面应用的多轮上下文必须能**跨窗口重启**存活，并且要和交给模型的
``conversation_history`` 是**同一份数据**。早期版本把历史存在浏览器 localStorage：

* pywebview 窗口重建 / 清缓存即全部丢失；
* 前端存的是渲染后的 HTML，喂回模型会带一堆标签噪声；
* 前后端两份历史容易漂移，"界面上有、模型不知道"。

因此这里把会话作为服务端状态：前端只持有 ``conv_id``，消息与标题都从服务端取。
``messages`` 直接沿用 Hermes ``run_conversation`` 返回的 OpenAI 形状消息数组，
下一轮原样回喂，零转换。

存储选型（v1.4.13 起：SQLite 替代整文件 JSON）
============================================
旧实现把**全部会话**序列化进单个 ``sessions.json``，每次 ``append`` 都要整文件重写
（在 200 会话 × 400 消息 ≈ 16 万条 / 87MB 的设计上限下，单次 append 阻塞
0.75–2.5s，且 ``search_messages`` 无索引需全表扫描 270–330ms）。

新实现改用 SQLite（标准库 ``sqlite3``，进程内、零额外依赖）：
* **增量落盘**：``append`` 只 ``INSERT`` 一行消息 + 更新会话时间戳，复杂度 O(1)，
  与总量无关——彻底消除「对话越多越卡」的本质退化。
* **全文检索索引**：消息正文建 FTS5 虚拟表，``search_messages`` 走索引查询；
  运行环境若不支持 FTS5（极少见），自动降级为 LIKE 全表扫描，行为一致。
* **原子性与并发**：单进程桌面应用用 ``threading.RLock`` 串行化读写；SQLite 用
  WAL + busy_timeout 提供崩溃安全与读不阻塞写。
* **向后兼容**：首启若发现旧 ``sessions.json`` 且库为空，自动迁移入库（旧文件改名
  备份为 ``.migrated-<ts>.json``，防重复迁移、不丢数据）。

公开 API 与原 JSON 版**逐字节兼容**（函数名、参数、返回字典结构均不变），
``main.py`` / 前端 / 既有测试无需改动。
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

try:
    from hermes_config import get_hermes_home
except Exception:  # pragma: no cover - 离线兜底
    def get_hermes_home() -> Path:  # type: ignore[misc]
        import sys
        base = (Path(sys.executable).parent if getattr(sys, "frozen", False)
                else Path(__file__).resolve().parent)
        return base / ".hermes_data"

# 最多保留的会话数（超出后淘汰最旧且未置顶的）
MAX_SESSIONS = 200
# 单会话最多保留的消息条数（防止无限增长撑爆上下文与磁盘）
MAX_MESSAGES = 400

_LOCK = threading.RLock()
_CONN: sqlite3.Connection | None = None
_HAS_FTS: bool | None = None  # None=未探测；True/False

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT '新对话',
    pinned      INTEGER NOT NULL DEFAULT 0,
    archived    INTEGER NOT NULL DEFAULT 0,
    tags        TEXT NOT NULL DEFAULT '[]',
    "group"     TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    model       TEXT,
    usage_input  INTEGER NOT NULL DEFAULT 0,
    usage_output INTEGER NOT NULL DEFAULT 0,
    context_folder TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_conv_updated ON conversations(updated_at DESC, pinned);
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    cid        TEXT NOT NULL,
    seq        INTEGER NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    attachments TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_msg_cid_seq ON messages(cid, seq);
"""

_FTS_DDL = """
CREATE VIRTUAL TABLE IF NOT EXISTS msg_fts USING fts5(
    cid UNINDEXED,
    role UNINDEXED,
    content,
    tokenize='unicode61'
);
"""


# ---------------------------------------------------------------------------
# 连接与初始化
# ---------------------------------------------------------------------------
def _store_dir() -> Path:
    d = Path(get_hermes_home()) / "desktop"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _db_path() -> Path:
    return _store_dir() / "sessions.db"


def _get_conn() -> sqlite3.Connection:
    global _CONN, _HAS_FTS
    if _CONN is not None:
        return _CONN
    conn = sqlite3.connect(str(_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        pass
    conn.executescript(_SCHEMA)
    if _HAS_FTS is None:
        try:
            conn.executescript(_FTS_DDL)
            _HAS_FTS = True
        except sqlite3.OperationalError:
            _HAS_FTS = False
    elif _HAS_FTS:
        conn.executescript(_FTS_DDL)
    conn.commit()
    _migrate_json(conn)
    _migrate_messages_attachments(conn)
    _migrate_conversations_context_folder(conn)
    _CONN = conn
    return conn


def reset_cache() -> None:
    """丢弃连接与缓存，下次访问重新打开（测试用：切 HERMES_DESKTOP_HOME 后调用）。"""
    global _CONN
    with _LOCK:
        if _CONN is not None:
            try:
                _CONN.close()
            except Exception:
                pass
            _CONN = None


# ---------------------------------------------------------------------------
# JSON -> SQLite 迁移（向后兼容；仅首启、且库为空时执行）
# ---------------------------------------------------------------------------
def _migrate_json(conn: sqlite3.Connection) -> None:
    jp = _store_dir() / "sessions.json"
    if not jp.exists():
        return
    if conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] > 0:
        return  # 库已有数据，不重复迁移
    try:
        raw = json.loads(jp.read_text(encoding="utf-8"))
        sessions_map = raw.get("sessions") if isinstance(raw, dict) else None
        if not isinstance(sessions_map, dict):
            return
        order = raw.get("order") if isinstance(raw, dict) else None
        items = [(cid, sessions_map[cid]) for cid in (order or list(sessions_map.keys()))
                 if cid in sessions_map]
        for cid, s in items:
            _insert_conv(conn, cid, s)
        conn.commit()
        # 备份旧文件，避免下次重复迁移；.corrupt 处理保持兼容
        jp.rename(jp.with_suffix(".migrated-%d.json" % int(time.time())))
    except Exception:
        conn.rollback()  # 迁移失败不静默丢数据：保留 json，库空，下次可重试


def _migrate_messages_attachments(conn: sqlite3.Connection) -> None:
    """向后兼容：为已存在的 messages 表补 attachments 列（历史库无此列）。

    新库由 _SCHEMA 直接建列，本函数幂等跳过；旧库在此 ALTER 补齐，
    避免「重开旧会话附件芯片丢失」。失败（并发 DDL 等）静默跳过，不影响主流程。
    """
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
    except sqlite3.OperationalError:
        return
    if "attachments" not in cols:
        try:
            conn.execute("ALTER TABLE messages ADD COLUMN attachments TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass


def _migrate_conversations_context_folder(conn: sqlite3.Connection) -> None:
    """向后兼容：为已存在的 conversations 表补 context_folder 列（历史库无此列）。

    新库由 _SCHEMA 直接建列（NOT NULL DEFAULT ''），本函数幂等跳过；旧库在此
    ALTER 补齐，避免「重开旧会话固定文件夹上下文丢失」。失败（并发 DDL 等）静默跳过。
    """
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()}
    except sqlite3.OperationalError:
        return
    if "context_folder" not in cols:
        try:
            conn.execute("ALTER TABLE conversations ADD COLUMN context_folder TEXT NOT NULL DEFAULT ''")
            conn.commit()
        except sqlite3.OperationalError:
            pass


def _insert_conv(conn: sqlite3.Connection, cid: str, s: dict) -> None:
    msgs = s.get("messages") or []
    conn.execute(
        'INSERT OR REPLACE INTO conversations '
        '(id,title,pinned,archived,tags,"group",created_at,updated_at,model,usage_input,usage_output) '
        'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
        (cid, s.get("title") or "新对话", int(bool(s.get("pinned"))),
         int(bool(s.get("archived"))), json.dumps(list(s.get("tags") or []), ensure_ascii=False),
         s.get("group") or "", float(s.get("created_at") or time.time()),
         float(s.get("updated_at") or time.time()), s.get("model"),
         int((s.get("usage") or {}).get("input") or 0),
         int((s.get("usage") or {}).get("output") or 0)),
    )
    for i, m in enumerate(msgs):
        if isinstance(m, dict):
            _insert_msg(conn, cid, i, m.get("role"), m.get("content"), m.get("attachments"))


def _insert_msg(conn: sqlite3.Connection, cid: str, seq: int,
                role: Any, content: Any, attachments: Any = None) -> None:
    cur = conn.execute(
        "INSERT INTO messages (cid,seq,role,content,created_at,attachments) VALUES (?,?,?,?,?,?)",
        (cid, seq, role, json.dumps(content, ensure_ascii=False), time.time(),
         json.dumps(attachments, ensure_ascii=False) if attachments else None))
    if _HAS_FTS:
        conn.execute("INSERT INTO msg_fts (rowid,cid,role,content) VALUES (?,?,?,?)",
                     (cur.lastrowid, cid, role, _content_text(content)))


# ---------------------------------------------------------------------------
# 公共辅助
# ---------------------------------------------------------------------------
def _now() -> float:
    return time.time()


def _title_from(text: str) -> str:
    t = " ".join((text or "").split())[:28].strip()
    return t or "新对话"


def _content_text(content: Any) -> str:
    """把消息 content（str 或多模态 list）压成可检索文本。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content
                       if isinstance(p, dict) and p.get("type") == "text")
    return "" if content is None else str(content)


def _parse_cf(raw: Any) -> dict | None:
    """把 context_folder 列的 JSON 文本解析成 dict；空/非法返回 None。"""
    if not raw:
        return None
    try:
        d = json.loads(raw)
    except Exception:
        return None
    if isinstance(d, dict) and d.get("root"):
        return d
    return None


def _make_snippet(content: str, q: str, idx: int, role: str) -> str:
    """围绕首个命中位置截取约 80 字片段，role 前缀便于辨认。"""
    start = max(0, idx - 30)
    end = min(len(content), idx + len(q) + 50)
    frag = content[start:end].replace("\n", " ").strip()
    if start > 0:
        frag = "…" + frag
    if end < len(content):
        frag = frag + "…"
    prefix = "用户：" if role == "user" else "Hermes："
    return prefix + frag


def _row_to_summary(row: sqlite3.Row, count: int = 0) -> dict:
    return {
        "id": row["id"],
        "title": row["title"] or "新对话",
        "pinned": bool(row["pinned"]),
        "archived": bool(row["archived"]),
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "group": row["group"] or "",
        "count": count,
        "updated_at": row["updated_at"] or 0,
        "created_at": row["created_at"] or 0,
    }


def _evict(conn: sqlite3.Connection) -> None:
    """超出 MAX_SESSIONS 时，淘汰最旧且未置顶的会话。"""
    total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    if total <= MAX_SESSIONS:
        return
    need = total - MAX_SESSIONS
    rows = conn.execute(
        "SELECT id, pinned FROM conversations ORDER BY updated_at DESC").fetchall()
    to_del: list[str] = []
    for r in reversed(rows):  # 最旧在前
        if len(to_del) >= need:
            break
        if not r["pinned"]:
            to_del.append(r["id"])
    if not to_del:
        return
    conn.executemany("DELETE FROM conversations WHERE id=?", [(i,) for i in to_del])
    conn.executemany("DELETE FROM messages WHERE cid=?", [(i,) for i in to_del])
    if _HAS_FTS:
        for i in to_del:
            conn.execute("DELETE FROM msg_fts WHERE cid=?", (i,))
    conn.commit()


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------
def create(title: str = "", *, archived: bool = False, tags: list | None = None,
            group: str = "") -> dict:
    """新建会话，返回会话摘要。"""
    with _LOCK:
        conn = _get_conn()
        cid = "c" + uuid.uuid4().hex[:12]
        now = _now()
        conn.execute(
            'INSERT INTO conversations (id,title,pinned,archived,tags,"group",created_at,updated_at) '
            'VALUES (?,?,0,?,?,?,?,?)',
            (cid, title or "新对话", int(bool(archived)),
             json.dumps(list(tags or []), ensure_ascii=False), group or "", now, now))
        conn.commit()
        _evict(conn)
        return summary(cid)


def list_sessions(include_archived: bool = True, q: str = "") -> list[dict]:
    """按置顶优先 + 最近使用倒序返回会话摘要列表。

    include_archived=False 时过滤掉已归档会话；q 为标题/标签子串搜索。
    """
    with _LOCK:
        conn = _get_conn()
        rows = conn.execute(
            'SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.cid=c.id) AS cnt '
            'FROM conversations c').fetchall()
        out = [_row_to_summary(r, count=r["cnt"]) for r in rows]
        if not include_archived:
            out = [s for s in out if not s.get("archived")]
        q = (q or "").strip().lower()
        if q:
            out = [s for s in out
                   if q in (s.get("title") or "").lower()
                   or any(q in (t or "").lower() for t in (s.get("tags") or []))]
        out.sort(key=lambda s: (not s["pinned"], -(s.get("updated_at") or 0)))
        return out


def summary(cid: str) -> dict:
    with _LOCK:
        conn = _get_conn()
        row = conn.execute(
            'SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.cid=c.id) AS cnt '
            'FROM conversations c WHERE c.id=?', (cid,)).fetchone()
        if not row:
            return {"id": cid, "title": "新对话", "pinned": False, "archived": False,
                    "tags": [], "group": "", "count": 0, "updated_at": 0, "created_at": 0}
        return _row_to_summary(row, count=row["cnt"])


def search_messages(q: str, limit: int = 50) -> list[dict]:
    """跨会话对消息正文做全文匹配（对标 hermes-studio 的 Ctrl+K 检索）。

    返回命中会话的摘要，并附带命中的「片段(snippet)」与「命中条数(matches)」，
    按命中条数降序、更新时间降序排列。仅检索 user/assistant 文本消息。
    """
    q = (q or "").strip().lower()
    if not q:
        return []
    with _LOCK:
        conn = _get_conn()
        by_cid: dict[str, dict] = {}
        if _HAS_FTS:
            try:
                rows = conn.execute(
                    "SELECT cid, role, content FROM msg_fts WHERE msg_fts MATCH ?", (q,)
                ).fetchall()
                for cid, role, content in rows:
                    if role not in ("user", "assistant"):
                        continue
                    e = by_cid.setdefault(cid, {"matches": 0, "snippet": None})
                    e["matches"] += 1
                    if e["snippet"] is None:
                        e["snippet"] = _make_snippet(content, q, content.lower().find(q), role)
            except sqlite3.OperationalError:
                by_cid = _search_like(conn, q)
        else:
            by_cid = _search_like(conn, q)

        out = []
        for cid, e in by_cid.items():
            r = summary(cid)
            r["snippet"] = e["snippet"]
            r["matches"] = e["matches"]
            out.append(r)
        out.sort(key=lambda r: (-r["matches"], -(r.get("updated_at") or 0)))
        return out[:limit]


def _search_like(conn: sqlite3.Connection, q: str) -> dict[str, dict]:
    """FTS5 不可用时的降级全表扫描（语义与索引版一致）。"""
    rows = conn.execute("SELECT cid, role, content FROM messages").fetchall()
    by_cid: dict[str, dict] = {}
    for cid, role, content in rows:
        if role not in ("user", "assistant"):
            continue
        text = _content_text(json.loads(content) if content else None)
        if not text:
            continue
        idx = text.lower().find(q)
        if idx == -1:
            continue
        e = by_cid.setdefault(cid, {"matches": 0, "snippet": None})
        e["matches"] += 1
        if e["snippet"] is None:
            e["snippet"] = _make_snippet(text, q, idx, role)
    return by_cid


def get(cid: str) -> dict | None:
    """返回完整会话（含 messages）。不存在返回 None。"""
    with _LOCK:
        conn = _get_conn()
        row = conn.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
        if not row:
            return None
        msgs = conn.execute(
            "SELECT role, content, attachments FROM messages WHERE cid=? ORDER BY seq ASC", (cid,)
        ).fetchall()
        messages = [{
            "role": m["role"],
            "content": json.loads(m["content"]),
            "attachments": (json.loads(m["attachments"]) if m["attachments"] else None),
        } for m in msgs]
        return {
            "id": row["id"],
            "title": row["title"] or "新对话",
            "messages": messages,
            "created_at": row["created_at"],
            "pinned": bool(row["pinned"]),
            "archived": bool(row["archived"]),
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "group": row["group"] or "",
            "usage": {"input": row["usage_input"], "output": row["usage_output"]},
            "model": row["model"],
            "context_folder": _parse_cf(row["context_folder"]),
        }


def get_context_folder(cid: str) -> dict | None:
    """返回某会话绑定的固定文件夹上下文（dict：root/rel/display），未绑定返回 None。"""
    with _LOCK:
        conn = _get_conn()
        row = conn.execute(
            "SELECT context_folder FROM conversations WHERE id=?", (cid,)).fetchone()
        if not row:
            return None
        return _parse_cf(row["context_folder"])


def set_context_folder(cid: str, value: dict | None) -> dict:
    """绑定/解绑某会话的固定文件夹上下文。value=None 表示解绑。"""
    with _LOCK:
        conn = _get_conn()
        s = conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone()
        if not s:
            return {"ok": False, "error": "会话不存在"}
        raw = json.dumps(value, ensure_ascii=False) if value else ""
        conn.execute("UPDATE conversations SET context_folder=? WHERE id=?", (raw, cid))
        conn.commit()
        return {"ok": True, "context_folder": value}


def get_messages(cid: str) -> list[dict]:
    s = get(cid)
    return list(s.get("messages") or []) if s else []


def ensure(cid: str | None) -> str:
    """保证 cid 存在；为空或不存在时新建一个并返回其 id。"""
    with _LOCK:
        conn = _get_conn()
        if cid and conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone():
            return cid
        return create()["id"]


def set_messages(cid: str, messages: list[dict], *, title_hint: str = "") -> dict:
    """整体覆盖某会话的消息数组（Hermes run_conversation 的返回原样存）。"""
    with _LOCK:
        conn = _get_conn()
        now = _now()
        msgs = [m for m in (messages or []) if isinstance(m, dict)]
        if len(msgs) > MAX_MESSAGES:
            # 保留最早的 system（若有）+ 最近的 N 条，避免截断掉系统设定
            head = [m for m in msgs[:1] if m.get("role") == "system"]
            msgs = head + msgs[-(MAX_MESSAGES - len(head)):]
        if not conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone():
            conn.execute(
                'INSERT INTO conversations (id,title,pinned,archived,tags,"group",created_at,updated_at) '
                'VALUES (?,?,0,0,?,?,?,?)', (cid, "新对话", '[]', '', now, now))
        conn.execute("DELETE FROM messages WHERE cid=?", (cid,))
        if _HAS_FTS:
            conn.execute("DELETE FROM msg_fts WHERE cid=?", (cid,))
        for i, m in enumerate(msgs):
            _insert_msg(conn, cid, i, m.get("role"), m.get("content"), m.get("attachments"))
        conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, cid))
        if title_hint:
            cur = conn.execute("SELECT title FROM conversations WHERE id=?", (cid,)).fetchone()
            t = cur["title"] if cur else ""
            if not t or t in ("", "新对话", None):
                conn.execute("UPDATE conversations SET title=? WHERE id=?",
                             (_title_from(title_hint), cid))
        conn.commit()
        _evict(conn)
        return summary(cid)


def append(cid: str, role: str, content: Any, *, title_hint: str = "",
           attachments: Any = None) -> dict:
    """追加单条消息（用于用户消息即时落盘，避免流式中断丢失提问）。

    仅 INSERT 一行（复杂度 O(1)），与已存消息总量无关——彻底消除旧版
    「整文件 JSON 重写」随对话增长而退化的本质问题。
    """
    with _LOCK:
        conn = _get_conn()
        now = _now()
        if not conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone():
            conn.execute(
                'INSERT INTO conversations (id,title,pinned,archived,tags,"group",created_at,updated_at) '
                'VALUES (?,?,0,0,?,?,?,?)', (cid, "新对话", '[]', '', now, now))
        max_seq = conn.execute(
            "SELECT COALESCE(MAX(seq),-1) FROM messages WHERE cid=?", (cid,)).fetchone()[0]
        _insert_msg(conn, cid, max_seq + 1, role, content, attachments)
        conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, cid))
        if title_hint:
            cur = conn.execute("SELECT title FROM conversations WHERE id=?", (cid,)).fetchone()
            t = cur["title"] if cur else ""
            if not t or t in ("", "新对话", None):
                conn.execute("UPDATE conversations SET title=? WHERE id=?",
                             (_title_from(title_hint), cid))
        # MAX_MESSAGES 守卫：保留 system + 最近 N 条
        total = conn.execute("SELECT COUNT(*) FROM messages WHERE cid=?", (cid,)).fetchone()[0]
        if total > MAX_MESSAGES:
            sys_seqs = {r["seq"] for r in conn.execute(
                "SELECT seq FROM messages WHERE cid=? AND role='system' ORDER BY seq", (cid,))}
            n_keep = MAX_MESSAGES - len(sys_seqs)
            keep_extra = {r["seq"] for r in conn.execute(
                "SELECT seq FROM messages WHERE cid=? AND role!='system' ORDER BY seq DESC LIMIT ?",
                (cid, n_keep))}
            keep = sys_seqs | keep_extra
            deleted = total - len(keep)
            if deleted > 0:
                placeholders = ",".join("?" * len(keep)) or "NULL"
                # 仅删除被淘汰消息对应的 FTS 行（按 rowid），O(1) 维护、不整体重算
                if _HAS_FTS:
                    del_rows = conn.execute(
                        "SELECT id FROM messages WHERE cid=? AND seq NOT IN (%s)" % placeholders,
                        (cid, *keep)).fetchall()
                    if del_rows:
                        dph = ",".join("?" * len(del_rows))
                        conn.execute("DELETE FROM msg_fts WHERE rowid IN (%s)" % dph,
                                     [r["id"] for r in del_rows])
                conn.execute(
                    "DELETE FROM messages WHERE cid=? AND seq NOT IN (%s)" % placeholders,
                    (cid, *keep))
        conn.commit()
        return summary(cid)


def rename(cid: str, title: str) -> dict:
    with _LOCK:
        conn = _get_conn()
        s = conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone()
        if not s:
            return {"ok": False, "error": "会话不存在"}
        conn.execute("UPDATE conversations SET title=?, updated_at=? WHERE id=?",
                     (_title_from(title) if title else "新对话", _now(), cid))
        conn.commit()
        return {"ok": True, **summary(cid)}


def set_pinned(cid: str, pinned: bool) -> dict:
    with _LOCK:
        conn = _get_conn()
        s = conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone()
        if not s:
            return {"ok": False, "error": "会话不存在"}
        conn.execute("UPDATE conversations SET pinned=?, updated_at=? WHERE id=?",
                     (int(bool(pinned)), _now(), cid))
        conn.commit()
        return {"ok": True, **summary(cid)}


def delete(cid: str) -> dict:
    with _LOCK:
        conn = _get_conn()
        existed = conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone() is not None
        conn.execute("DELETE FROM messages WHERE cid=?", (cid,))
        conn.execute("DELETE FROM conversations WHERE id=?", (cid,))
        if _HAS_FTS:
            conn.execute("DELETE FROM msg_fts WHERE cid=?", (cid,))
        conn.commit()
        return {"ok": existed, "id": cid}


def delete_many(ids: list) -> dict:
    """批量删除：在一次事务中删除多个会话及其消息，返回实际删除数。"""
    ids = [str(i) for i in (ids or [])]
    deleted = 0
    with _LOCK:
        conn = _get_conn()
        for cid in ids:
            existed = conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone() is not None
            if not existed:
                continue
            conn.execute("DELETE FROM messages WHERE cid=?", (cid,))
            conn.execute("DELETE FROM conversations WHERE id=?", (cid,))
            if _HAS_FTS:
                conn.execute("DELETE FROM msg_fts WHERE cid=?", (cid,))
            deleted += 1
        conn.commit()
    return {"ok": True, "deleted": deleted, "total": len(ids)}


def copy(cid: str) -> dict:
    """复制整个会话（含消息），返回新会话摘要。"""
    with _LOCK:
        conn = _get_conn()
        src = conn.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
        if not src:
            return {"ok": False, "error": "源会话不存在"}
        now = _now()
        new_cid = "c" + uuid.uuid4().hex[:12]
        conn.execute(
            'INSERT INTO conversations (id,title,pinned,archived,tags,"group",created_at,updated_at,model,usage_input,usage_output) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            (new_cid, (src["title"] or "新对话") + "（副本）", src["pinned"], src["archived"],
             src["tags"], src["group"] or "", now, now, src["model"],
             src["usage_input"], src["usage_output"]))
        for m in conn.execute("SELECT seq, role, content, attachments FROM messages WHERE cid=? ORDER BY seq", (cid,)):
            _insert_msg(conn, new_cid, m["seq"], m["role"], json.loads(m["content"]),
                        json.loads(m["attachments"]) if m["attachments"] else None)
        conn.commit()
        _evict(conn)
        return {"ok": True, **summary(new_cid)}


def archive(cid: str, archived: bool) -> dict:
    with _LOCK:
        conn = _get_conn()
        s = conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone()
        if not s:
            return {"ok": False, "error": "会话不存在"}
        conn.execute("UPDATE conversations SET archived=?, updated_at=? WHERE id=?",
                     (int(bool(archived)), _now(), cid))
        conn.commit()
        return {"ok": True, **summary(cid)}


def set_tags(cid: str, tags: list) -> dict:
    with _LOCK:
        conn = _get_conn()
        s = conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone()
        if not s:
            return {"ok": False, "error": "会话不存在"}
        conn.execute("UPDATE conversations SET tags=?, updated_at=? WHERE id=?",
                     (json.dumps([str(t).lstrip("#").strip() for t in (tags or []) if str(t).strip()],
                                 ensure_ascii=False), _now(), cid))
        conn.commit()
        return {"ok": True, **summary(cid)}


def set_group(cid: str, group: str) -> dict:
    with _LOCK:
        conn = _get_conn()
        s = conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone()
        if not s:
            return {"ok": False, "error": "会话不存在"}
        conn.execute('UPDATE conversations SET "group"=?, updated_at=? WHERE id=?',
                     ((group or "").strip(), _now(), cid))
        conn.commit()
        return {"ok": True, **summary(cid)}


def export_session(cid: str, fmt: str = "json") -> dict:
    """导出会话为 JSON 或 Markdown 文本。"""
    with _LOCK:
        s = get(cid)
        if not s:
            return {"ok": False, "error": "会话不存在"}
        if fmt == "md":
            msgs = s.get("messages") or []
            model = s.get("model") or "未知"
            tags = s.get("tags") or []
            tag_str = ", ".join(tags) if tags else ""
            created = s.get("created_at") or ""
            if created and isinstance(created, str):
                created = created[:10] if len(created) >= 10 else created
            lines = [
                f"# {s.get('title') or '新对话'}",
                "",
                f"> 导出时间：{time.strftime('%Y-%m-%d %H:%M')}",
                f"> 模型：{model}",
                f"> 消息数：{len(msgs)}",
            ]
            if created:
                lines.append(f"> 创建时间：{created}")
            if tag_str:
                lines.append(f"> 标签：{tag_str}")
            lines.append("")
            for m in msgs:
                role = m.get("role")
                if role == "user":
                    lines.append("## 用户")
                elif role == "assistant":
                    lines.append("## Hermes")
                elif role == "tool":
                    lines.append("## 工具")
                else:
                    lines.append(f"## {role}")
                content = m.get("content")
                if isinstance(content, list):
                    parts = []
                    for p in content:
                        if not isinstance(p, dict):
                            parts.append(str(p))
                            continue
                        t = p.get("type", "")
                        if t == "text":
                            parts.append(p.get("text", ""))
                        elif t == "tool_use":
                            name = p.get("name", "")
                            inp = p.get("input", {})
                            parts.append(f"\n> **工具调用：{name}**\n```json\n{json.dumps(inp, ensure_ascii=False, indent=2)}\n```")
                        elif t == "tool_result":
                            tool_id = p.get("tool_use_id", "")
                            result = p.get("content", "")
                            if isinstance(result, list):
                                result = "\n".join(x.get("text", "") for x in result if isinstance(x, dict) and x.get("type") == "text")
                            parts.append(f"\n> **工具结果（{tool_id}）**\n```\n{result}\n```")
                        elif t == "reasoning":
                            parts.append(f"> 💭 *{p.get('text', '')}*")
                        else:
                            parts.append(p.get("text", "") or json.dumps(p, ensure_ascii=False))
                    content = "\n".join(parts)
                lines.append(str(content or ""))
                lines.append("")
            return {"ok": True, "format": "md", "text": "\n".join(lines),
                    "title": s.get("title") or "新对话"}
        return {"ok": True, "format": "json", "text": json.dumps(s, ensure_ascii=False, indent=2),
                "title": s.get("title") or "新对话"}


def import_session(payload: dict) -> dict:
    """从导出 JSON 导入一个会话（生成新 id，避免覆盖）。"""
    with _LOCK:
        conn = _get_conn()
        if not isinstance(payload, dict) or "messages" not in payload:
            return {"ok": False, "error": "无效的会话数据"}
        new_cid = "c" + uuid.uuid4().hex[:12]
        now = _now()
        conn.execute(
            'INSERT INTO conversations (id,title,pinned,archived,tags,"group",created_at,updated_at) '
            'VALUES (?,?,0,?,?,?,?,?)',
            (new_cid, (payload.get("title") or "导入会话")[:60], int(bool(payload.get("archived"))),
             json.dumps(list(payload.get("tags") or []), ensure_ascii=False),
             payload.get("group") or "", now, now))
        for i, m in enumerate([m for m in payload.get("messages", []) if isinstance(m, dict)]):
            _insert_msg(conn, new_cid, i, m.get("role"), m.get("content"))
        conn.commit()
        _evict(conn)
        return {"ok": True, **summary(new_cid)}


def clear_all() -> dict:
    with _LOCK:
        conn = _get_conn()
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM conversations")
        if _HAS_FTS:
            conn.execute("DELETE FROM msg_fts")
        conn.commit()
        return {"ok": True}


def count_conversations() -> int:
    """返回会话总数（供健康检查 / 体检使用，替代旧 sessions.json 文件计数）。"""
    with _LOCK:
        conn = _get_conn()
        return conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]


# ---------------------------------------------------------------------------
# 用量统计（对标 hermes-studio「Usage Analytics」；进程内路线无 provider 账单，纯估算）
# ---------------------------------------------------------------------------
_COST_IN_USD = 0.0001    # 每 1K 输入 token 的 USD 估算费率
_COST_OUT_USD = 0.0002   # 每 1K 输出 token 的 USD 估算费率
_USD_CNY = 7.2


def _est_cost_cny(in_tokens: int, out_tokens: int) -> float:
    usd = (in_tokens / 1000) * _COST_IN_USD + (out_tokens / 1000) * _COST_OUT_USD
    return usd * _USD_CNY


def set_usage(cid: str, input_tokens: int = 0, output_tokens: int = 0,
              model: str | None = None) -> dict:
    """写入某会话的累计 token 用量（前端估算值）。覆盖式存储，不累加。"""
    with _LOCK:
        conn = _get_conn()
        s = conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone()
        if not s:
            return {"ok": False, "error": "会话不存在"}
        conn.execute("UPDATE conversations SET usage_input=?, usage_output=? WHERE id=?",
                     (int(input_tokens or 0), int(output_tokens or 0), cid))
        if model:
            conn.execute("UPDATE conversations SET model=? WHERE id=?", (str(model), cid))
        conn.execute("UPDATE conversations SET updated_at=? WHERE id=?", (_now(), cid))
        conn.commit()
        return {"ok": True, **summary(cid)}


def analytics(days: int = 30) -> dict:
    """聚合用量：总量 / 近 N 日趋势 / 按模型分布（均为估算）。"""
    with _LOCK:
        conn = _get_conn()
        now = _now()
        tot_in = tot_out = 0
        by_day: dict[str, list[int]] = {}
        by_model: dict[str, int] = {}
        active_days: set[str] = set()
        sessions_count = 0
        for r in conn.execute("SELECT updated_at, usage_input, usage_output, model FROM conversations"):
            u_in = int(r["usage_input"] or 0)
            u_out = int(r["usage_output"] or 0)
            if u_in == 0 and u_out == 0:
                continue
            sessions_count += 1
            tot_in += u_in
            tot_out += u_out
            day = time.strftime("%Y-%m-%d", time.localtime(r["updated_at"] or now))
            bucket = by_day.setdefault(day, [0, 0])
            bucket[0] += u_in
            bucket[1] += u_out
            active_days.add(day)
            model = r["model"] or "unknown"
            by_model[model] = by_model.get(model, 0) + u_in + u_out
        series = []
        for i in range(max(0, days - 1), -1, -1):
            d = time.strftime("%Y-%m-%d", time.localtime(now - i * 86400))
            b = by_day.get(d, [0, 0])
            series.append({"date": d, "input": b[0], "output": b[1],
                           "total": b[0] + b[1]})
        total = tot_in + tot_out
        return {
            "ok": True,
            "totals": {"input": tot_in, "output": tot_out, "total": total,
                       "cost_cny": round(_est_cost_cny(tot_in, tot_out), 4)},
            "by_day": series,
            "by_model": [{"model": m, "total": t}
                         for m, t in sorted(by_model.items(), key=lambda x: -x[1])],
            "sessions": sessions_count,
            "active_days": len(active_days),
            "cost_note": "估算（进程内路线无 provider 账单，按 1K tokens 费率折算）",
        }
