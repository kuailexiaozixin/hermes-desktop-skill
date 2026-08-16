# 反模式与红线 — 示例实战反模式（from examples/01-hermes-desktop，已实测并修正）

> 本文件从 `references/07-quality-gates.md#antipatterns` 抽出：本技能在打磨旗舰示例时**真实踩过、并已修正**的反模式。
> 属示例耦合内容，不进入技能核心骨干（通用反模式红线见 `references/07-quality-gates.md#antipatterns` 上半部分）。

---

以下反模式都是本技能在打磨旗舰示例时**真实踩过、并已修正**的，列为此处硬警示：

- **SSE 事件词表张冠李戴** → 前端 `switch` 写 `case "tool_start"` / `case "tool_complete"` /
  `case "end"`，但 Hermes 内核**只发** `delta` / `reasoning` / `action` / `action_result` / `done`。
  结果：工具卡永远不更新、流式永不收尾，且**不报错**（静默假死）。正确：前端只认五种 `type`，
  构造器回调 `tool_start_callback`/`tool_complete_callback` 映射到桥事件 `action`/`action_result`
  （对照见 `01` §3.5 / `03` 词汇框）。`test_bridge.py` 已用断言锁死这五种词。

- **工具注册 schema 双重包装** → `registry.register(...)` 的 `schema` 必须是**扁平形**
  `{"name","description","parameters"}`；`get_definitions()` 会自动包成
  `{"type":"function","function":{...}}`。若你再手动包一层 `{"type":"function",...}`，
  工具定义就废了，模型看不到工具。正确：注册时给扁平 schema，包装交给 `get_definitions`
  （详见 `07-tooling.md#tools` §3.3）。

- **进程内 MCP 陷阱** → 在 `hermes config` 里配了 MCP server，但进程内 `AIAgent` 路线下
  `discover_builtin_tools()` **不会自动拉起**你配置的 MCP server（那是 gateway 进程的事）。
  表现：工具"声称存在实则无" → 模型调它必失败/拒绝。正确：自建工具走 `registry.register`
  （见 `07-tooling.md#system`），别指望进程内自动启动配置的 MCP。

- **会话整文件 JSON 重写** → 把全部会话序列化进单个 `sessions.json`，每次 `append` 都整文件
  重写（`indent=1`）。满规模（16 万条）下单次 append 阻塞 0.75–2.5s，search 无索引全表扫 ~300ms。
  正确：改 SQLite + FTS5，append 仅 INSERT 一行（O(1)），实测 ~45× / ~500× 提升（见 `09` §2.1）。
  旧 `sessions.json` 首次启动自动迁移入库并改名备份，不丢数据。

- **目录穿越（附件 / 工作区 / 上传）** → 直接把用户给的 `../../../etc/passwd` 当路径读，
  或把上传文件落到授权根之外。正确：所有路径经白名单解析（`_ws_resolve` / `_resolve_upload_target`）
  剔除 `..`/空段、落盘严格校验在授权根内，越界一律 403。示例 `file_preview.resolve_safe()`
  同样拒绝 `..` 与软链越界（见 `08` §8.1）。

- **冻结态不设 `HERMES_HOME`** → EXE 写到 Program Files 只读区 → 启动即崩（见 `10` §3 / `11` §4）。
  这是打包发布的头号灾难，非反模式细枝。
