# 会话持久化 — 示例实战：SQLite + FTS5（from examples/01-hermes-desktop，57/57 测试通过）

> 本文件从 `references/01-library-api.md` 抽出：旗舰示例如何把会话库从整文件 JSON 重写为生产级 SQLite + FTS5。
> 属示例耦合内容，不进入技能核心骨干（通用持久化方法见 `references/01-library-api.md` §1–§2 / §3–§5）。

---

上面的极简版能跑，但**撑不住真实规模**：整文件 JSON 在 200 会话 × 400 消息 ≈ 16 万条时，
单次 `append` 整文件重写阻塞 **0.75–2.5s（均值 ~1.1s）**，search 无索引需全表扫描 ~270–330ms。
旗舰示例把会话库重写为**真正的 SQLite + FTS5**，实测同规模：

| 指标 | 旧（整文件 JSON） | 新（SQLite + FTS5） | 提升 |
| --- | --- | --- | --- |
| `append` 峰值 | 0.75–2.5s（随总量退化） | **24.4ms（O(1)，不随总量退化）** | ~45× |
| `search` 峰值 | ~270–330ms（全表扫） | **0.6ms（FTS5 索引命中）** | ~500× |

关键设计（节选自 `examples/01-hermes-desktop/sessions.py`，行号随版本变动）：

- **三表结构**：`conversations(id PK, title, pinned, archived, tags, "group", created_at, updated_at)`
  + `messages(cid, seq, role, content, attachments)` + `msg_fts` **FTS5 虚拟表**（`USING fts5(content)`）覆盖消息正文。
- **崩溃安全**：`PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=5000` —— 读不阻塞写，进程崩了不损库。
- **O(1) append**：`append()` 只 `INSERT` 一行（与已存消息总量**无关**）；`MAX_MESSAGES` 守卫淘汰时
  **只删被淘汰消息对应的 FTS 行**（按 rowid），不整体重算索引。
- **向后兼容迁移**：首启若发现旧 `sessions.json` 且库为空，自动迁移入库；旧文件改名备份为
  `.migrated-<ts>.json`，**不重复迁移、不丢数据**；迁移异常 `rollback`，保留 json 下次可重试。
- **FTS5 降级**：运行环境若不支持 FTS5（极少见），`search_messages` 自动降级为 `LIKE` 全表扫描，语义一致。
- **接口稳定**：`append` / `get` / `search_messages` / `count_conversations` 公开签名逐字节兼容，旧调用零改动；
  `tests/test_sessions_sqlite.py` **57/57** 覆盖 CRUD / append O(1) 实证 / FTS 搜索 / JSON 迁移 / MAX 淘汰 / 分析 / 复制导出导入。

> 直接复用：把 `examples/01-hermes-desktop/sessions.py` 整个拷进你的工程即可（标准库 `sqlite3`，零额外依赖）。
> 它已遵循 `HERMES_HOME/desktop/sessions.db` 落点约定（见 §3 / `05-install-and-env.md`）。
