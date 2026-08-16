# 08 · 能力集成（Capability Integrations，工具集之外）

> 本文档覆盖 **57 个工具集（见 `03-capabilities-and-toolsets.md`）之外的 Hermes 能力层**：
> 目标 / 状态快照 / 多模型编排 / 项目 / 技能捆绑 / 安全审计 / 蓝图 / 批处理 / 历程 / 备份 /
> 档案 / 策展 / 供应商路由 / 看板 / 即时消息桥。
>
> **准确性声明**：本文件每个模块的「内核模块」「是什么」「关键 API」三栏，均经 `hermes-agent==0.19.0`
> 安装包内省（docstring + 公开 API 签名）逐条核实，结论以 0.19.0 源码为准。
> 凡标 ⛔ 者一般不在进程内直跑路线启用；凡标 🔁 者其底层数据落在 `HERMES_HOME`（打包态恒为 `<exe>/hermes_data`，见 `05`）。

---

## 0. 能力总览（速查表）

| 能力 | 内核模块（site-packages 内，已核实） |
| --- | --- |
| Goals（目标） | `hermes_cli.goals` |
| State Snapshots（状态快照） | `tools.checkpoint_manager` |
| MOA（多模型编排） | `agent.moa_loop` + `hermes_cli.moa_config` |
| Projects（项目） | `hermes_cli.projects_db` + 工具集 `project` |
| Bundles（技能捆绑） | `agent.skill_bundles` + `hermes_cli.bundles` |
| Security Audit（安全审计） | `hermes_cli.security_audit` + `security_audit_startup` |
| Blueprints（蓝图自动化） | `tools.blueprints` + `hermes_cli.blueprint_cmd` |
| Batch（批处理） | `batch_runner` |
| Journey（历程） | `hermes_cli.journey` |
| Backup（备份） | `hermes_cli.backup` |
| Profiles（档案） | `hermes_cli.profiles` |
| Curator（策展） | `agent.curator` + `hermes_cli.curator` |
| Provider Routing（供应商路由） | `hermes_cli.providers` + `provider_catalog` |
| Kanban（看板） | 工具集 `kanban` |
| IM 桥（即时消息） | 24 个 `hermes-*` 工具集 |

> **LLM Wiki（应用层模式，非 Library 能力）**：`hermes-agent==0.19.0` 不提供 `wiki` 模块、
> `wiki` 工具集或 `llm-wiki` 技能文件（全包内省确认：无任何 `llm-wiki` / `wiki` 内核源码）。
> LLM Wiki 类需求应在**应用层自建**——内置参考实现 `examples/01-hermes-desktop/wiki_engine.py`
> 提供纯标准库引擎（三层目录 + `[[wikilinks]]` 互联 + 自动反链 + Ingest/Query/Lint/Graph），
> 仅在编译/查询时懒加载 `AIAgent` 做 LLM 往返，数据落在 `HERMES_HOME/wiki`。可照此模式复用，
> 无需调用任何 Library wiki API；若需知识检索，也可走 `memory` / `session_search` 工具集。

---

## 1. Goals（常驻目标）<a id="goals"></a>

- **内核模块**：`hermes_cli.goals`（docstring 已核实）。
- **是什么**（源 docstring 直译）：*"Persistent session goals — the Ralph loop for Hermes. A goal is a
  free-form user objective that stays active across turns. After each turn completes, a small judge call
  asks an auxiliary model 'is this goal met?'"* —— 目标是跨回合保持活跃的自由形式用户意图；每回合结束后，
  用一个**辅助模型**做一次轻量判定："本回合是否满足该目标"。
- **关键 API（已核实签名）**：
  - `GoalManager(session_id: str, *, default_max_turns: int = 20)`
  - `GoalState(goal, status='active', turns_used=0, max_turns=20, contract=GoalContract(), …)`
  - `GoalContract(outcome='', verification='', constraints='', boundaries='', stop_when='')`
  - `draft_contract(objective: str, *, timeout: float = 30.0) -> Optional[GoalContract]`
  - `clear_goal(session_id: str) -> None`
- **进程内集成范式**：桌面应用可在应用层复用 `GoalManager` 维护跨回合目标，并把目标状态（active / paused /
  met）显示在侧栏；判定调用的是**辅助模型**（额外成本，非主对话模型），UI 须明示"目标看护中"。
- **反模式红线**：❌ 不要把 Goals 当成主模型的系统提示硬塞进每轮 prompt；它应通过"回合末判定"闭环
  （`evaluate_after_turn` 语义），而非注入主对话上下文。

### 1.1 进程内集成实战（基于 `examples/01-hermes-desktop/hermes_features.py` 真实写法）

> 下面片段是该旗舰示例**实际在跑**的写法（已门禁验证），不是伪代码。核心要点：
> ① 惰性导入内核模块、不可用时优雅降级；② 用 `get_text_auxiliary_client("goal_judge")` 探测裁判模型；
> ③ `GoalState` 非 dataclass，序列化须手写 `_serialize_goal_state()`（内核 `to_json` 对其会失败）。

```python
import hermes_cli.goals as _g
from agent.auxiliary_client import get_text_auxiliary_client

# 1) 构造管理器（以会话 id 为 key 维护跨回合目标）
gm = _g.GoalManager(str(conv_id))

# 2) 设定目标：parse_contract 把自由文本拆成「标题 + 契约(GoalContract)」五字段
headline, contract = _g.parse_contract(user_text)
if contract_text:                       # 可选：用户额外给的契约细则
    _, c2 = _g.parse_contract(contract_text)
    merged = {f: (c2.to_dict().get(f) or contract.to_dict().get(f) or "")
              for f in ("outcome", "verification", "constraints", "boundaries", "stop_when")}
    contract = _g.GoalContract(**merged)
state = gm.set(headline or user_text, max_turns=max_turns,
               contract=(contract if (contract and not contract.is_empty()) else None))

# 3) 读取状态（侧栏展示 active/paused/met/cleared + turns_used/max_turns）
st = gm.state

# 4) 回合末判定（在主对话 run_conversation 返回后调用；返回 last_verdict/last_reason）
verdict = gm.evaluate_after_turn(last_response=reply_text)
#     ⚠️ 该判定会消耗一次辅助模型调用——须先用 get_text_auxiliary_client("goal_judge")
#        探测可用性，不可用时 Goals 仅作记录、不自动续跑、不烧轮次。

# 5) 暂停/继续/清除（用户侧栏按钮对应）
gm.pause(reason="user-paused"); gm.resume(); gm.clear()
```

**GUI 桥接范式**：把 `goals_get(conv_id)` 返回的状态字典（`status`/`turns_used`/`max_turns`/
`contract`/`last_verdict`）渲染成侧栏「目标看护」卡片；每次对话结束后异步调 `evaluate_after_turn`
并更新卡片，UI 文案须明示"目标看护中（额外消耗裁判模型）"，避免用户误以为免费。


---

## 2. State Snapshots（状态快照 / Checkpoints）<a id="snapshot"></a>

- **内核模块**：`tools.checkpoint_manager`（docstring 已核实）。
- **是什么**（源 docstring 直译）：*"Checkpoint Manager — Transparent filesystem snapshots via a single
  shared shadow git store. Creates automatic snapshots of working directories before file-mutating
  operations (`write_file`, `patch` …)"* —— 在**文件变更类操作**之前，自动对工作目录做快照，便于回滚。
- **关键 API（已核实签名）**：
  - `CheckpointManager(enabled: bool = False, max_snapshots: int = 20, max_total_size_mb: int = 500, max_file_size_mb: int = 10)`
  - `prune_checkpoints(retention_days: int = 7, delete_orphans: bool = True, checkpoint_base=None, max_total_size_mb: int = 0) -> Dict[str, int]`
  - `maybe_auto_prune_checkpoints(retention_days=7, min_interval_hours=24, delete_orphans=True, …)`
  - `store_status(checkpoint_base=None) -> Dict`；`clear_all(checkpoint_base=None) -> Dict[str, int]`
- **进程内集成范式**：构造 `AIAgent` 时开 `checkpoints_enabled=True` 及相关 `checkpoint_max_snapshots` /
  `checkpoint_max_total_size_mb` / `checkpoint_max_file_size_mb`（参数名已在 `01` §3.5 经 `AIAgent.__init__`
  核实）。桌面 UI 把"快照列表 + 回滚"做成面板；快照存储落在 `HERMES_HOME` 内（🔁 冻结态即 `<exe>/hermes_data`）。
- **反模式红线**：❌ 不要自己手写 sqlite / 文件拷贝来实现"快照"——复用内核 `CheckpointManager`，
  否则会丢失 shadow-git 去重与自动裁剪语义。

### 2.1 概念澄清：内核 Checkpoint（文件快照）vs 会话消息快照（应用层）

⚠️ **易混点**：Hermes 有两套"快照"，**不要混为一一**：

| 维度 | 内核 Checkpoint（`tools.checkpoint_manager`） | 会话消息快照（应用层，如 examples/01） |
| --- | --- | --- |
| 快照对象 | **工作目录文件**（在 `write_file`/`patch` 等变更前自动备份） | **某会话的消息历史**（JSON 落盘） |
| 触发 | `checkpoints_enabled=True` 自动，**无显式 API 调用** | 应用层显式调 `checkpoints_create(cid, label)` |
| 回滚 | 经内核 shadow-git store 还原文件 | 应用层 `checkpoints_restore(cid, cp_id)` 重写消息 |
| 存储 | `HERMES_HOME` 内核 shadow store | `HERMES_HOME/checkpoints/<cid>/*.json` |
| 用途 | 防 Agent 误改文件可回退 | 防对话跑偏可"回到某轮" |

进程内桌面路线**两者都可用**：想防文件误改 → 开 `checkpoints_enabled`；想防对话跑偏 → 自己写
消息快照（examples/01 的 `checkpoints_*` 即此模式，落盘在 `HERMES_HOME/checkpoints/`）。
本文 §2 顶栏的 `CheckpointManager` 指**前者（文件快照）**；消息快照属应用层模式，不在内核 API 内。

### 2.2 内核 Checkpoint 实战（基于 `01` §3.5 实测参数）

```python
from run_agent import AIAgent

# 开启后，Agent 每次改文件前自动经 shadow-git 做快照，UI 无需手动调 API
agent = AIAgent(
    provider=..., model=..., disabled_toolsets=["terminal"],
    checkpoints_enabled=True,            # 0.19.0 实测默认 False
    checkpoint_max_snapshots=20,         # 实测默认 20
    checkpoint_max_total_size_mb=500,    # 实测默认 500
    checkpoint_max_file_size_mb=10,      # 实测默认 10
)
```

若需在 UI 展示/管理内核快照，直接 import 内核管理器（与 08 顶部签名一致）：

```python
from tools.checkpoint_manager import (
    CheckpointManager, prune_checkpoints, maybe_auto_prune_checkpoints,
    store_status, clear_all,
)
mgr = CheckpointManager(enabled=True, max_snapshots=20)
status = store_status()                  # 当前快照占用
pruned = prune_checkpoints(retention_days=7, delete_orphans=True)   # 手动裁剪
```

> 注意：examples/01 的 `checkpoints_*` 是**消息快照**（落 `HERMES_HOME/checkpoints/<cid>/`），
> 与内核 `CheckpointManager`（文件快照）是两套独立机制，互不替代。选哪种取决于你要"回退文件"还是"回退对话"。


---

## 3. MOA（多智能体混合 / Mixture-of-Agents）<a id="moa"></a>

- **内核模块**：`agent.moa_loop` + `hermes_cli.moa_config` + `hermes_cli.moa_cmd`（docstring 已核实）。
- **是什么**（源 `agent.moa_loop` docstring 直译）：*"Mixture-of-Agents runtime helpers for `/moa` turns.
  The slash command is deliberately not a model tool. It marks one user turn as MoA-enabled; the normal
  Hermes agent loop still owns tool calling…"* —— `/moa` 是一个**斜杠命令而非模型工具**：它把某一用户回合
  标记为"启用 MoA"，正常 Hermes agent 循环仍主导工具调用与文本生成，仅在该回合叠加多参考模型聚合。
- **关键 API（已核实签名）**：
  - `agent.moa_loop.MoAClient(preset_name: str, reference_callback: Any = None)`
  - `agent.moa_loop.MoAChatCompletions(preset_name: str, reference_callback: Any = None)`
  - `agent.moa_loop.aggregate_moa_context(*, user_prompt, api_messages, reference_models, aggregator, temperature=None, aggregator_temperature=None, max_tokens=None) -> str`
  - `hermes_cli.moa_config.build_moa_turn_prompt(user_prompt, config=None, preset=None) -> str`
  - `hermes_cli.moa_config.encode_moa_turn / decode_moa_turn / normalize_moa_config / list_moa_presets / resolve_moa_preset / set_active_moa_preset`
- **进程内集成范式**：桌面 UI 提供 MoA 预设编辑器（`resolve_moa_preset` / `set_active_moa_preset`），聊天界面用
  `tool_progress_callback`（见 `02` §2）驱动"参考模型"折叠块渲染；用户消息前加 `/moa` 即触发。
- **反模式红线**：❌ 不要试图把 MoA 做成 `AIAgent` 的一个"模型工具"——它本质是回合标记 + 聚合上下文，
  由 `aggregate_moa_context` 在 `agent.moa_loop` 内完成，不是工具调用。

### 3.1 进程内集成实战（基于 `examples/01-hermes-desktop/hermes_features.py` 真实写法）

> MOA 的真实机制（0.19.0 实证）：MOA 是 Hermes 的**虚拟 provider**。当 `AIAgent` 的
> `provider=="moa"` 且 `model==<preset 名>` 时，`agent_init.py` 自动构造 `MoAClient` 接管每次
> LLM 调用，并把每个参考模型的回答以 `moa.reference` / `moa.aggregating` 事件经
> `tool_progress_callback` 透出。**配置零手写 schema**——全部交给内核 `moa_config` 与 `config`。

```python
import hermes_cli.config as _cfg
import hermes_cli.moa_config as _moa

# 1) 读取 + 归一化（不手写 schema，避免与内核漂移）
raw = _cfg.load_config()
norm = _moa.normalize_moa_config(raw.get("moa"))

# 2) 保存预设（前端整体提交 presets + default_preset/active_preset）
merged = dict(raw.get("moa") or {})
merged["presets"] = inc_presets
merged["default_preset"] = inc_default
raw["moa"] = _moa.normalize_moa_config(merged)
_cfg.save_config(raw)

# 3) 激活某预设作为当前模型（关键两步）
_moa.resolve_moa_preset(raw["moa"], name)          # 不存在抛 KeyError
raw["moa"] = _moa.set_active_moa_preset(raw["moa"], name)
_cfg.save_config(raw)
#    同时把 llm.json 顶层置 provider="moa" / model=name，
#    使 AIAgent.__init__ 自动走 MoAClient（agent_init.py:816）
```

**GUI 桥接范式**：预设编辑器绑定 `moa_get()/moa_save()/moa_set_active()/moa_delete()`；
聊天界面用 `tool_progress_callback` 捕获 `moa.reference`（参考模型建议）与 `moa.aggregating`（聚合中）
事件，渲染为"多模型参考"折叠块。激活状态从 `llm.json` 顶层 `provider=="moa"` 反查（`active_in_agent`）。


---

## 4. Projects（项目）<a id="projects"></a>

- **内核模块**：`hermes_cli.projects_db`（docstring 已核实）+ 工具集 `project`（3 工具，见 `03` §3.4）。
- **是什么**（源 docstring 直译）：*"Per-profile first-class Project store. A **Project** is a human-named,
  multi-folder workspace."* —— 项目是每-profile 的一等公民存储，是一个人类命名、含多文件夹的工作区。
- **关键 API（已核实签名）**：
  - `Project(id, slug, name, created_at, description=None, icon=None, color=None, board_slug=None, primary_path=None, archived=False, folders: List[ProjectFolder] = [])`
  - `ProjectFolder(path: str, label=None, is_primary: bool = False, added_at: int = 0)`
  - `create_project(conn, *, name, slug=None, folders=None, primary_path=None, description=None, icon=None, color=None, board_slug=None) -> str`
  - `connect(db_path: Optional[Path] = None) -> sqlite3.Connection`
  - `archive_project(conn, project_id) -> bool`；`delete_project(conn, project_id) -> bool`
  - `add_folder(conn, project_id, path, *, label=None, is_primary=False) -> str`
- **进程内集成范式**：项目存于 `HERMES_HOME` 下的 per-profile SQLite；桌面 UI 提供项目切换器
  （`project_list` / `project_create` / `project_switch` 工具集见 `03`）。多文件夹工作区以 `ProjectFolder` 建模。
- **反模式红线**：❌ 不要用会话 `cwd` + git probe 去"推断"工作区（旧桌面实现踩过的坑）——项目是显式一等存储，
  用 `projects_db` 的 API 读写，不要自建推断逻辑。

### 4.1 进程内集成实战（基于 `examples/01-hermes-desktop/hermes_features.py` 真实写法）

> 项目是 **per-profile 一等存储**（SQLite），所有操作走 `connect_closing()` 上下文管理器
> （自动提交/关闭），**不要自己 hold 连接或手写 git probe 推断工作区**。

```python
import hermes_cli.projects_db as _pdb

# 1) 列出项目（含当前激活 id）
with _pdb.connect_closing() as conn:
    active_id = _pdb.get_active_id(conn)
    projs = _pdb.list_projects(conn, include_archived=False)

# 2) 创建项目（多文件夹工作区）
with _pdb.connect_closing() as conn:
    pid = _pdb.create_project(
        conn, name="我的研发项目", slug=None,
        folders=["/abs/path/A", "/abs/path/B"],   # 多文件夹工作区
        primary_path="/abs/path/A",
        description="...", icon="📁", color="#3b82f6",
        board_slug=None,
    )
    _pdb.set_active(conn, pid)                     # 设为当前激活

# 3) 切换/归档/删除
with _pdb.connect_closing() as conn:
    _pdb.set_active(conn, target_pid)             # 切换
    _pdb.archive_project(conn, pid)               # 归档
    _pdb.delete_project(conn, pid)                # 删除
```

**GUI 桥接范式**：项目切换器绑定 `projects_list()/projects_create()/projects_update()/projects_delete()`；
每个项目的 `folders`（`ProjectFolder.path/label/is_primary`）渲染成侧栏工作区树。激活状态用
`get_active_id(conn)` 反查，切换时同步刷新 Agent 的 `session_id`（见 `09` 会话持久化）。


---

## 5. Bundles（技能捆绑）<a id="bundles"></a>

- **内核模块**：`agent.skill_bundles` + `hermes_cli.bundles`（docstring 已核实）。
- **是什么**（源 `agent.skill_bundles` docstring 直译）：*"Skill bundles — aliases that load multiple skills
  under one slash command. A skill bundle is a small YAML file that names a set of skills to load together.
  Invoking `/<bundle-name>` from the CLI or…"* —— 捆绑包是命名一组技能的小 YAML，斜杠命令 `/<bundle-name>`
  一次性加载这组技能。
- **关键 API（已核实签名）**：
  - `agent.skill_bundles.save_bundle(name: str, skills: List[str], description: str = '', instruction: str = '', overwrite: bool = False) -> Path`
  - `agent.skill_bundles.get_bundle(name: str) -> Optional[Dict[str, Any]]`
  - `agent.skill_bundles.list_bundles() -> List[Dict[str, Any]]`；`reload_bundles() -> Dict[str, Any]`
  - `agent.skill_bundles.build_bundle_invocation_message(cmd_key, user_instruction='', task_id=None, platform=None) -> Optional[Tuple[str, List[str], List[str]]]`
  - `agent.skill_bundles.resolve_bundle_command_key(command: str) -> Optional[str]`
  - `hermes_cli.bundles.scan_bundles() -> Dict[str, Dict[str, Any]]`；`delete_bundle(name: str) -> Path`
- **进程内集成范式**：桌面 UI 提供捆绑包管理器（列出 / 新建 / 删除），新建走 `save_bundle`；调用时由
  `build_bundle_invocation_message` 拼出"系统提示 + 待加载技能列表 + 指令"。
- **反模式红线**：❌ 不要把捆绑包当成"新对象类型"去建独立存储——它只是 YAML + 斜杠命令别名，复用
  `agent.skill_bundles` 即可。

### 5.1 进程内集成实战（基于 `examples/01-hermes-desktop/hermes_features.py` 真实写法）

> 捆绑包是**命名一组技能的小 YAML**，落盘在 `HERMES_HOME/skill-bundles/<slug>.yaml`，
> 斜杠命令 `/<bundle-name>` 一次性加载这组技能。直接用内核 `agent.skill_bundles`，**不要自建存储**。

```python
import agent.skill_bundles as m

# 1) 列出已安装捆绑包
items = m.list_bundles()                 # -> List[Dict]，含 name/slug/skills/description

# 2) 新建/覆盖（写 skill-bundles/<slug>.yaml）
path = m.save_bundle(
    name="my-bundle",
    skills=["skill_a", "skill_b", "skill_c"],
    description="一键加载 ABC 技能组",
    instruction="进入此模式后优先使用上述技能",
    overwrite=False,                      # 已存在抛 FileExistsError
)

# 3) 读取单个 + 删除
info = m.get_bundle("my-bundle")         # -> Optional[Dict]
m.delete_bundle("my-bundle")             # -> Path（删除 yaml）

# 4) 调用：拼出「系统提示 + 待加载技能 + 指令」（投喂给 AIAgent 的 system_message）
msg = m.build_bundle_invocation_message("my-bundle", user_instruction="帮我做 X")
#    -> Optional[(system_prompt, skills_to_load, instruction)]
```

**GUI 桥接范式**：捆绑包管理器绑定 `bundles_list()/bundles_install()/bundles_uninstall()/bundles_get()`；
用户选某捆绑包后，调 `build_bundle_invocation_message` 把结果作为下一次 `run_conversation` 的
`system_message` 前缀，实现"一键切换技能组"。`save_bundle(overwrite=False)` 已存在的包抛
`FileExistsError`——UI 须提示"已存在，是否覆盖"。


---

## 6. Security Audit（安全审计）<a id="security-audit"></a>

- **内核模块**：`hermes_cli.security_audit` + `hermes_cli.security_audit_startup`（docstring 已核实）。
- **是什么**（源 docstring 直译）：*"On-demand supply-chain audit for Hermes Agent installs. Scans three
  surfaces a Hermes user actually controls and we can map to upstream advisories without auth or extra
  binaries: 1. The Hermes venv…"* —— 按需的供应链审计，扫描用户实际可控的三类面（venv 依赖 / 插件 / MCP），
  映射到上游 OSV 公告，无需鉴权或额外二进制。
- **关键 API（已核实签名）**：
  - `run_audit(*, skip_venv: bool = False, skip_plugins: bool = False, skip_mcp: bool = False, hermes_home: Optional[Path] = None) -> list[Finding]`
  - `Finding(component: Component, vuln: Vulnerability)`；`Component(name, version, ecosystem, source)`
  - `Vulnerability(osv_id: str, severity: str = 'UNKNOWN', summary: str = '', fixed_versions: list[str] = [])`
  - `hermes_cli.security_audit_startup.log_startup_security_warnings(*, hermes_home=None, config=None, force=False) -> list[str]`（warn-on-load，**从不阻塞**）
- **进程内集成范式**：桌面 UI 提供"供应链扫描"面板，按需调 `run_audit(hermes_home=…)` 并展示
  `Finding`（含 `severity`）；启动期接 `log_startup_security_warnings` 做曝光提示，但**绝不让其阻塞启动**。
- **反模式红线**：❌ 不要把审计做成阻塞启动的硬门禁——`security_audit_startup` 的设计语义就是
  "warn-on-load, never blocks"，照搬到桌面也要保持非阻塞。

---

## 7. Blueprints（蓝图自动化）<a id="blueprint"></a>

- **内核模块**：`tools.blueprints` + `hermes_cli.blueprint_cmd`（docstring 已核实）。
- **是什么**（源 `tools.blueprints` docstring 直译）：*"Blueprints: shareable plain-language automations
  layered on skills + cron. A 'blueprint' is NOT a new object type. It is an ordinary skill (a SKILL.md the
  agent loads) that additionally declares an automation spec."* —— 蓝图是可分享的自然语言自动化，叠加在
  skill + cron 之上；它**不是新对象类型**，而是一个普通 skill（会被 agent 加载的 SKILL.md）额外声明了一段
  自动化规格。
- **关键 API（已核实签名）**：
  - `BlueprintSpec(skill_name: str, schedule: str, deliver: str = 'origin', prompt: Optional[str] = None, no_agent: bool = False, model: Optional[str] = None, provider: Optional[str] = None, enabled_toolsets: Optional[List[str]] = None, raw: Dict = {})`
  - `tools.blueprints.parse_blueprint(skill_md_text: str) -> Optional[BlueprintSpec]`
  - `tools.blueprints.blueprint_spec_for_installed(skill_name: str) -> Optional[BlueprintSpec]`
  - `tools.blueprints.blueprint_to_job_spec(spec, *, name=None) -> Dict[str, Any]`
  - `tools.blueprints.create_blueprint_job(spec, *, origin=None, name=None) -> Dict[str, Any]`
  - `hermes_cli.blueprint_cmd.handle_blueprint_command(args: str, *, origin=None, surface: str = 'cli') -> BlueprintCommandResult`
- **进程内集成范式**：桌面"自动化"表单 = schedule 选择器 + deliver 目标；`deliver` 默认 `'origin'`，
  桌面端即"本地交付"（对应旧示例的 `deliver` 默认 local 适配）。蓝图经 `blueprint_to_job_spec` 转成 cron job。
- **反模式红线**：❌ 不要把蓝图当成独立调度对象去自研——它底层就是 skill + cron，复用 `tools.blueprints`
  与现有 cron 机制（见 `03` §4 的 `hermes-cron`）。

---

## 8. Batch（批处理）<a id="batch"></a>

- **内核模块**：`batch_runner`（docstring 已核实）。
- **是什么**（源 docstring 直译）：*"Batch Agent Runner. This module provides parallel batch processing
  capabilities for running the agent across multiple prompts from a dataset. It includes: Dataset loading
  and batching — Parallel bat…"* —— 针对数据集中的多条 prompt 并行跑 agent。
- **关键 API（已核实签名）**：
  - `BatchRunner(dataset_file: str, batch_size: int, run_name: str, distribution: str = 'default', max_iterations: int = 10, base_url=None, api_key=None, model: str = 'claude-opus-4-20250514', num_workers: int = 4, verbose: bool = False, ephemeral_system_prompt=None, providers_allowed=None, providers_ignored=None, providers_order=None, provider_sort=None, max_tokens=None, reasoning_config=None, prefill_messages=None, max_samples=None)`
  - `batch_runner` 同时重导出 `AIAgent`（其 `BatchRunner` 内部用独立 `AIAgent` 配置驱动每个 worker）。
- **进程内集成范式**：桌面 UI 提供"批量跑"面板（上传数据集 / 配置并发 `num_workers` / 选择 `model`），
  后端起 `BatchRunner`；结果落轨迹文件（`save_trajectories` 在 `AIAgent` 层），前端汇总。
- **反模式红线**：❌ 不要在桌面主线程里串行跑数据集——`BatchRunner` 用 `multiprocessing.Pool`
  （`num_workers` 控制）并行；进程内直跑时须把批量任务放到后台 worker，避免冻结 UI。

---

## 9. Journey（历程）<a id="journey"></a>

- **内核模块**：`hermes_cli.journey`（docstring 已核实）。
- **是什么**（源 docstring 直译）：*"hermes journey — what Hermes has learned, on a timeline. A terminal-native
  rendition of the desktop Star Map / Memory Graph: a horizontal timeline bar chart of learned skills and
  memories over ti…"* —— 把"学到了什么"按时间线呈现，是桌面 Star Map / Memory Graph 的终端版：横向时间轴上
  展示已学技能与记忆。
- **关键 API（已核实签名）**：
  - `cmd_journey(args: argparse.Namespace) -> int`
  - `register_cli(parent: argparse.ArgumentParser) -> None`
- **进程内集成范式**：桌面 UI 提供"历程 / Star Map"时间线视图，数据来自记忆与技能学习记录；可复用
  `journey` 的聚合逻辑（或等价地从 `memory` / `curator` 状态派生）渲染时间轴。
- **反模式红线**：❌ 不要把 Journey 当成独立数据库去自建——它是记忆/技能学习记录的时间线投影，
  复用现有记忆与策展状态即可。

---

## 10. Backup（备份）<a id="backup"></a>

- **内核模块**：`hermes_cli.backup`（docstring 已核实）🔁 落 `HERMES_HOME`。
- **是什么**（源 docstring 直译）：*"Backup and import commands for hermes CLI. `hermes backup` creates a zip
  archive of the entire ~/.hermes/ directory (excluding the hermes-agent repo and transient files). `hermes
  import` restores fr…"* —— 备份整个 `HERMES_HOME`（排除 hermes-agent 仓库与瞬态文件），导入可还原。
- **关键 API（已核实签名）**：
  - `create_quick_snapshot(label: Optional[str] = None, hermes_home: Optional[Path] = None, keep: Optional[int] = None) -> Optional[str]`
  - `create_pre_update_backup(hermes_home=None, keep: int = 5) -> Optional[Path]`
  - `create_pre_migration_backup(hermes_home=None, keep: int = 5) -> Optional[Path]`
  - `list_quick_snapshots(limit: int = 20, hermes_home=None) -> List[Dict[str, Any]]`
  - `prune_quick_snapshots(keep: int = 20, hermes_home=None) -> int`
  - `restore_cron_jobs_if_emptied(snapshot_id: str, hermes_home=None) -> Optional[Dict[str, Any]]`
- **进程内集成范式**：桌面 UI 提供"备份 / 还原"面板；🔁 打包态 `HERMES_HOME` 恒为 `<exe>/hermes_data`，
  备份须捕获该目录，还原前按 `07` §运行数据保护规则先备份→变更→还原→md5 校验。
- **反模式红线**：❌ 还原时直接覆盖运行中的出厂数据——遵循"先备份、再变更、再还原、md5 校验"铁律（见 `07`）。

---

## 11. Profiles（档案）<a id="profiles"></a>

- **内核模块**：`hermes_cli.profiles`（docstring 已核实）🔁 每 profile 独立 `HERMES_HOME`。
- **是什么**（源 docstring 直译）：*"Profile management for multiple isolated Hermes instances. Each profile
  is a fully independent HERMES_HOME directory with its own config.yaml, .env, memory, sessions, skills,
  gateway, cron, and logs."* —— 每个 profile 是完全独立的 `HERMES_HOME` 目录（各自 config/.env/记忆/会话/
  技能/gateway/cron/日志）。
- **关键 API（已核实签名）**：
  - `create_profile(name: str, clone_from: Optional[str] = None, clone_all: bool = False, clone_config: bool = False, no_alias: bool = False, no_skills: bool = False, description: Optional[str] = None) -> Path`
  - `delete_profile(name: str, yes: bool = False) -> Path`
  - `export_profile(name: str, output_path: str) -> Path`
  - `build_alias_map() -> dict[str, str]`；`check_alias_collision(name: str) -> Optional[str]`
  - `create_wrapper_script(name: str, target: Optional[str] = None) -> Optional[Path]`
- **进程内集成范式**：桌面 UI 提供多 profile 切换器；🔁 注意打包态 `HERMES_HOME` 已冻结为 `<exe>/hermes_data`，
  多 profile 隔离需通过 `HERMES_HOME` 子目录或独立 profile 目录实现，不能重定向冻结根。
- **反模式红线**：❌ 不要试图重定向冻结态 `HERMES_HOME` 根——它恒为 `<exe>/hermes_data`，profile 隔离
  只能在该根内做，与外部 `profiles` CLI 的"独立 HERMES_HOME 目录"语义在打包态下要重新映射。

---

## 12. Curator（策展）<a id="curator"></a>

- **内核模块**：`agent.curator` + `hermes_cli.curator`（docstring 已核实）。
- **是什么**（源 `agent.curator` docstring 直译）：*"Curator — background skill maintenance orchestrator.
  The curator is an auxiliary-model task that periodically reviews agent-created skills and maintains the
  collection. It runs inactivity-triggered…"* —— 后台技能维护编排器，是一个周期性审查 agent 自建技能、
  维护技能集合的辅助模型任务，按"不活跃即触发"等策略运行。
- **关键 API（已核实签名）**：
  - `agent.curator.apply_automatic_transitions(now: Optional[datetime] = None) -> Dict[str, int]`
  - `agent.curator.get_archive_after_days() -> int`；`get_consolidate() -> bool`；`get_interval_hours() -> int`
  - `agent.curator.atomic_json_write(path, data, *, indent=2, …) -> None`
  - `hermes_cli.curator.cli_main(argv=None) -> int`（薄壳：`agent/curator.py` + `tools/skill_usage.py`）
- **进程内集成范式**：桌面 UI 提供策展状态面板（运行 / 暂停 / 钉住技能），调用 `cli_main` 或等价地
  直接驱动 `agent.curator` 的转移逻辑；状态用 `atomic_json_write` 原子落盘。
- **反模式红线**：❌ 不要在主线程/UI 线程同步跑策展——它是后台辅助模型任务，须放后台，避免阻塞对话。

---

## 13. Provider Routing（供应商路由）<a id="routing"></a>

- **内核模块**：`hermes_cli.providers` + `hermes_cli.provider_catalog`（docstring 已核实）。
- **是什么**（源 `hermes_cli.providers` docstring 直译）：*"Single source of truth for provider identity in
  Hermes Agent. Two data sources, merged at runtime: 1. **models.dev catalog** — 109+ providers with base
  URLs, env vars, display names, and full mod…"* —— 供应商身份的**唯一真相源**，运行时合并两类数据源
  （models.dev 目录 109+ 供应商 + 自定义覆盖）。
- **关键 API（已核实签名）**：
  - `ProviderDef(id, name, transport, api_key_env_vars, base_url='', base_url_env_var='', is_aggregator=False, auth_type='api_key', doc='', source='')`
  - `get_provider(name: str) -> Optional[ProviderDef]`；`is_aggregator(provider: str) -> bool`
  - `determine_api_mode(provider: str, base_url: str = '') -> str`；`get_label(provider_id: str) -> str`
  - `hermes_cli.provider_catalog.ProviderDescriptor(slug, label, description, auth_type, tab, api_key_env_vars, base_url_env_var, signup_url, order)`
  - `hermes_cli.provider_catalog.provider_catalog() -> list[ProviderDescriptor]`；`provider_catalog_by_slug() -> dict`
- **进程内集成范式**：桌面 **Settings → Providers（账号 + API Key）** 标签页**必须**以
  `provider_catalog()` 为数据源渲染（CLI/TUI 的 `hermes model` 也同源），不要硬编码供应商列表；
  身份解析走 `get_provider` / `determine_api_mode`。
- **反模式红线**：❌ 不要在桌面硬编码供应商清单或 base_url——`hermes_cli.providers` 是合并了 models.dev
  目录与自定义覆盖的唯一真相源，硬编码会随上游漂移立刻失效。
- **动态查询示例（实测 0.19.0，uv 环境）**——桌面 Settings 页应这样用 `provider_catalog()` 渲染，而非硬编码：
  ```python
  from hermes_cli.provider_catalog import provider_catalog, provider_catalog_by_slug

  cats = provider_catalog()          # list[ProviderDescriptor]，本机实测 41 个
  by_slug = provider_catalog_by_slug()

  d = by_slug["anthropic"]           # ⚠️ 必须运行时查——openai/ollama 等并无固定 slug，硬编码会失效
  d.auth_type                        # 'api_key'
  d.api_key_env_vars                 # ('ANTHROPIC_API_KEY','ANTHROPIC_TOKEN','CLAUDE_CODE_OAUTH_TOKEN')
  d.base_url_env_var                 # 'ANTHROPIC_BASE_URL'
  ```
  实测输出（0.19.0）：`provider_catalog()` 返回 **41** 项；`nous` 为 `oauth_device_code`（env `NOUS_API_KEY`）、
  `openrouter` 为 `api_key`（env `OPENROUTER_API_KEY`）。连 `openai` 都没有固定 slug——再次印证必须用
  `provider_catalog()` 运行时渲染，不可硬编码（与上面反模式红线一致）。

---

## 14. Kanban（看板）<a id="kanban"></a>

- **内核模块**：工具集 `kanban`（9 工具，已核实于 `03` §3.6）+ `hermes_cli.kanban`（CLI 壳）。
- **工具清单（已核实）**：`kanban_show` / `kanban_list` / `kanban_complete` / `kanban_block` / `kanban_heartbeat`
  / `kanban_comment` / `kanban_create` / `kanban_link` / `kanban_unblock`。
- **能力语义**：看板是任务卡片的可见状态机（`create → (block/unblock) → complete`，`link` 建依赖，
  `heartbeat` 心跳续命，`comment` 备注）。桌面 UI 可直接调这 9 个工具，或调 `hermes_cli.kanban` 壳。
- **反模式红线**：❌ 不要自建 `tasks` 表去复制看板状态——`kanban` 工具集已封装底层存储与状态机，
  复用即可（详见 `03` §3.6，避免旧实现踩过的 `tasks` 表坑）。

---

## 15. IM 桥（即时消息）<a id="im"></a>

- **内核模块**：24 个 `hermes-*` 工具集中的即时消息子集（已核实于 `03` §4.2）。
- **覆盖范围**：`hermes-discord`（51 工具）/ `hermes-feishu`（54）/ `hermes-yuanbao`（54）/ `hermes-webhook`（4）
  等将 Agent 接入 Discord / 飞书 / 元宝 / Webhook 渠道。
- **进程内集成范式**：进程内直跑路线**一般不启用**这些 `hermes-*` 集成（它们面向网关/长连渠道）。
  若需"把桌面 Agent 接到 IM"，可走网关部署（见 `03` §4.1），而非把 `hermes-discord` 等塞进进程内
  `enabled_toolsets`——否则会引入长连 WebSocket / 令牌轮转等进程内不支持的负担。
- **反模式**：不要在进程内 `enabled_toolsets` 里加 `hermes-discord` / `hermes-feishu` 等 IM 集成；
  它们依赖网关态的常驻连接，进程内直跑路线不启用（同 `03` §4.2 的禁用清单）。
