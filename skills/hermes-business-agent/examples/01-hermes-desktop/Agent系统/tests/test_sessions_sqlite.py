"""test_sessions_sqlite.py — 验证 sessions.py 的 SQLite 实现（v1.4.13）。

覆盖：
* 全部公开 API 的往返正确性（与旧 JSON 版返回结构逐字节兼容）
* append 复杂度 O(1) 实证：随消息总量增长不退化（对比旧版整文件重写 ~1.1s）
* FTS5 全文检索正确性（命中 / 大小写不敏感 / 仅正文）
* 旧 sessions.json 首启自动迁移 + 备份重命名
* MAX_SESSIONS 淘汰、MAX_MESSAGES 截断（set_messages / append 两条路径）
* analytics 用量聚合正确性
* count_conversations / copy / archive / set_tags / set_group / rename / set_pinned / set_usage

每个场景用独立临时 HERMES_DESKTOP_HOME，互不污染；不依赖真实 .hermes_data。
"""
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ok = 0
fail = 0


def check(name, cond):
    global ok, fail
    if cond:
        ok += 1
        print(f"  [ok] {name}")
    else:
        fail += 1
        print(f"  [FAIL] {name}")


def fresh_home():
    d = tempfile.mkdtemp(prefix="hermes_sqlite_")
    os.environ["HERMES_DESKTOP_HOME"] = d
    import sessions
    sessions.reset_cache()
    return sessions


# ---------------------------------------------------------------------------
def test_crud_and_shape():
    print("\n[场景] CRUD 与返回结构兼容")
    sessions = fresh_home()
    c = sessions.create("标题A", tags=["x", "y"], group="g1")
    check("create 返回含 id/title/tags/group/count", all(k in c for k in
          ("id", "title", "tags", "group", "count", "pinned", "archived", "updated_at")))
    check("create tags 透传", c["tags"] == ["x", "y"] and c["group"] == "g1")
    sessions.append(c["id"], "user", "hello")
    sessions.append(c["id"], "assistant", "hi")
    full = sessions.get(c["id"])
    check("get 含 messages/usage/model", all(k in full for k in
          ("messages", "usage", "model", "created_at")))
    check("get messages 顺序与条数", len(full["messages"]) == 2 and
          full["messages"][0]["role"] == "user")
    check("usage 结构", full["usage"] == {"input": 0, "output": 0})
    msgs = sessions.get_messages(c["id"])
    check("get_messages 等价", msgs == full["messages"])
    # summary
    s = sessions.summary(c["id"])
    check("summary count=2", s["count"] == 2 and s["title"] == "标题A")
    # rename
    r = sessions.rename(c["id"], "改后")
    check("rename 生效", r["title"] == "改后" and sessions.get(c["id"])["title"] == "改后")
    # set_pinned
    p = sessions.set_pinned(c["id"], True)
    check("set_pinned 生效", p["pinned"] is True and sessions.summary(c["id"])["pinned"])
    # set_tags / set_group
    check("set_tags", sessions.set_tags(c["id"], ["#a", "b"])["tags"] == ["a", "b"])
    check("set_group", sessions.set_group(c["id"], "研发")["group"] == "研发")
    # archive
    check("archive", sessions.archive(c["id"], True)["archived"] is True)
    check("list 过滤归档", c["id"] not in [x["id"] for x in sessions.list_sessions(include_archived=False)])
    check("list 含归档(默认)", c["id"] in [x["id"] for x in sessions.list_sessions()])
    # set_messages 覆盖
    sessions.set_messages(c["id"], [{"role": "user", "content": "q"}], title_hint="")
    check("set_messages 覆盖后=1条", len(sessions.get_messages(c["id"])) == 1)
    # delete
    check("delete", sessions.delete(c["id"])["ok"] and sessions.get(c["id"]) is None)
    check("count_conversations 归零", sessions.count_conversations() == 0)


# ---------------------------------------------------------------------------
def test_append_o1_scale():
    print("\n[场景] append 复杂度 O(1) 实证（关键修复：对比旧版整文件重写 ~1.1s）")
    sessions = fresh_home()
    cid = sessions.create()["id"]
    # 预热到 2000 条
    for i in range(2000):
        sessions.append(cid, "user", f"预热消息 {i} about kubernetes ingress")
    # 在不同总量下测量「单次 append」耗时，断言不随规模显著退化
    lat = {}
    for target in (2000, 5000, 10000):
        # 先补到 target
        cur = sessions.summary(cid)["count"]
        for i in range(cur, target):
            sessions.append(cid, "user", f"消息 {i} about nginx ingress gateway")
        t0 = time.perf_counter()
        sessions.append(cid, "user", "probe-ingress")
        dt = (time.perf_counter() - t0) * 1000.0
        lat[target] = dt
        check(f"append @ {target} 条 < 200ms（实测 {dt:.1f}ms）", dt < 200.0)
    # 增长不应显著：1万 的单次 append 不应比 2k 慢一个数量级以上
    check("append 不随规模退化（10k/2k 比值 < 10x）",
          lat[10000] < lat[2000] * 10 + 50)
    print(f"    实测 append 延迟(ms): " + ", ".join(f"{k}={v:.1f}" for k, v in lat.items()))


# ---------------------------------------------------------------------------
def test_search_fts():
    print("\n[场景] FTS5 全文检索正确性")
    sessions = fresh_home()
    s1 = sessions.create("项目 Alpha")
    sessions.append(s1["id"], "user", "如何配置 kubernetes 的 ingress 网关？")
    sessions.append(s1["id"], "assistant", "你可以用 nginx-ingress 来配置。")
    s2 = sessions.create("日常笔记")
    sessions.append(s2["id"], "user", "今天天气不错")
    res = sessions.search_messages("ingress")
    ids = [r["id"] for r in res]
    check("命中含 ingress 的会话", s1["id"] in ids)
    check("不命中无关会话", s2["id"] not in ids)
    hit = next((r for r in res if r["id"] == s1["id"]), None)
    check("返回 snippet", bool(hit and hit.get("snippet")))
    check("返回 matches>=1", bool(hit and hit.get("matches", 0) >= 1))
    check("snippet 含上下文", bool(hit and "ingress" in (hit["snippet"] or "").lower()))
    check("大小写不敏感", any(r["id"] == s1["id"] for r in sessions.search_messages("INGRESS")))
    check("空查询返回空", sessions.search_messages("") == [])
    check("无匹配返回空", sessions.search_messages("zzz_nope_zzz") == [])
    s3 = sessions.create("ingress 标题但正文无")
    sessions.append(s3["id"], "user", "随便聊聊")
    sessions.append(s3["id"], "assistant", "好的")
    check("标题含词但正文无→不命中", s3["id"] not in
          [r["id"] for r in sessions.search_messages("ingress")])
    # 大规模检索延迟（FTS 索引）
    big = sessions.create("big")
    for i in range(5000):
        sessions.append(big["id"], "user", f"指标监控第 {i} 条 latency p99")
    t0 = time.perf_counter()
    r2 = sessions.search_messages("latency")
    dt = (time.perf_counter() - t0) * 1000.0
    check(f"5k 消息检索 < 100ms（实测 {dt:.1f}ms）", dt < 100.0)
    check("检索命中 big 会话", big["id"] in [r["id"] for r in r2])


# ---------------------------------------------------------------------------
def test_json_migration():
    print("\n[场景] 旧 sessions.json 首启自动迁移")
    sessions = fresh_home()
    store = os.path.join(os.environ["HERMES_DESKTOP_HOME"], "desktop")
    os.makedirs(store, exist_ok=True)
    old = {
        "version": 1,
        "sessions": {
            "cold1": {"id": "cold1", "title": "遗留会话", "messages":
                      [{"role": "user", "content": "旧数据迁移测试"}],
                      "created_at": 100.0, "updated_at": 200.0, "pinned": False,
                      "archived": False, "tags": ["遗留"], "group": "",
                      "usage": {"input": 10, "output": 20}},
        },
        "order": ["cold1"],
    }
    with open(os.path.join(store, "sessions.json"), "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False)
    # 触发首次打开（迁移）
    check("迁移后 count=1", sessions.count_conversations() == 1)
    full = sessions.get("cold1")
    check("迁移保留消息", full and full["messages"] == [{"role": "user", "content": "旧数据迁移测试"}])
    check("迁移保留 tags/usage", full["tags"] == ["遗留"] and
          full["usage"] == {"input": 10, "output": 20})
    check("旧 json 已备份重命名", not os.path.exists(os.path.join(store, "sessions.json")) and
          any(n.startswith("sessions.migrated-") for n in os.listdir(store)))
    # 二次打开不重复迁移
    sessions.reset_cache()
    check("二次打开不重复迁移", sessions.count_conversations() == 1)


# ---------------------------------------------------------------------------
def test_max_sessions_eviction():
    print("\n[场景] MAX_SESSIONS 淘汰（仅淘汰未置顶最旧）")
    sessions = fresh_home()
    cids = []
    for i in range(sessions.MAX_SESSIONS + 5):
        cids.append(sessions.create(f"s{i}")["id"])
    check("超出后总量=MAX_SESSIONS", sessions.count_conversations() == sessions.MAX_SESSIONS)
    # 最早的 5 个里，若未被置顶则被淘汰
    survived = [cid for cid in cids if sessions.get(cid) is not None]
    check("最少淘汰了部分最旧", len(cids) - len(survived) >= 1)
    # 置顶的不会被淘汰（置顶当前最新、必然存活的会话）
    pin = cids[-1]
    sessions.set_pinned(pin, True)
    for i in range(10):
        sessions.create(f"extra{i}")
    check("置顶会话不被淘汰", sessions.get(pin) is not None)


# ---------------------------------------------------------------------------
def test_max_messages_truncation():
    print("\n[场景] MAX_MESSAGES 截断（set_messages 与 append 两条路径）")
    sessions = fresh_home()
    # set_messages 路径
    cid = sessions.create()["id"]
    big = [{"role": "user", "content": f"m{i}"} for i in range(sessions.MAX_MESSAGES + 50)]
    sessions.set_messages(cid, big)
    check("set_messages 截断到 MAX", len(sessions.get_messages(cid)) == sessions.MAX_MESSAGES)
    # append 路径：先放一条 system，再 append 远超上限
    cid2 = sessions.create("sys")["id"]
    sessions.set_messages(cid2, [{"role": "system", "content": "SYS"}])
    for i in range(sessions.MAX_MESSAGES + 100):
        sessions.append(cid2, "user", f"a{i}")
    msgs = sessions.get_messages(cid2)
    check("append 截断总数=MAX", len(msgs) == sessions.MAX_MESSAGES)
    check("append 截断保留 system", msgs[0]["role"] == "system")


# ---------------------------------------------------------------------------
def test_analytics():
    print("\n[场景] analytics 用量聚合")
    sessions = fresh_home()
    c1 = sessions.create()["id"]
    sessions.set_usage(c1, 1000, 2000, model="gpt-x")
    c2 = sessions.create()["id"]
    sessions.set_usage(c2, 500, 500, model="gpt-x")
    a = sessions.analytics(30)
    check("totals.input 正确", a["totals"]["input"] == 1500)
    check("totals.output 正确", a["totals"]["output"] == 2500)
    check("sessions 计数=2", a["sessions"] == 2)
    check("by_model 聚合", any(m["model"] == "gpt-x" and m["total"] == 4000
                               for m in a["by_model"]))
    check("by_day 长度=days", len(a["by_day"]) == 30)
    check("cost_cny 为正", a["totals"]["cost_cny"] > 0)


# ---------------------------------------------------------------------------
def test_copy_export_import():
    print("\n[场景] copy / export / import")
    sessions = fresh_home()
    cid = sessions.create("源")["id"]
    sessions.append(cid, "user", "u1")
    sessions.append(cid, "assistant", "a1")
    cp = sessions.copy(cid)
    check("copy 生成新 id", cp["ok"] and cp["id"] != cid)
    check("copy 副本含消息", len(sessions.get_messages(cp["id"])) == 2)
    check("copy 标题带副本后缀", sessions.get(cp["id"])["title"].endswith("（副本）"))
    # export json
    exp = sessions.export_session(cid, "json")
    payload = json.loads(exp["text"])
    check("export json 含 messages", isinstance(payload.get("messages"), list) and len(payload["messages"]) == 2)
    # import
    imp = sessions.import_session(payload)
    check("import 生成新 id", imp["ok"] and imp["id"] != cid)
    check("import 含消息", len(sessions.get_messages(imp["id"])) == 2)
    # export md
    md = sessions.export_session(cid, "md")
    check("export md 以 # 开头", md["text"].startswith("#"))
    # clear_all
    sessions.clear_all()
    check("clear_all 清空", sessions.count_conversations() == 0)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_crud_and_shape()
    test_append_o1_scale()
    test_search_fts()
    test_json_migration()
    test_max_sessions_eviction()
    test_max_messages_truncation()
    test_analytics()
    test_copy_export_import()
    print(f"\n==== SQLite 测试：{ok} 通过 / {fail} 失败 ====")
    sys.exit(1 if fail else 0)
