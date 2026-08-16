# 09 · 集成自测与端到端验证（跑通一个集成）

> 验证相关的红线、门禁与工作流见 `07-quality-gates.md`，对应脚本见 `scripts/*`。
> 本文把「怎么确认一个**进程内** Hermes 集成**真的跑通了**」串成一段可执行的 walkthrough，
> 并特别考量 **Hermes 是一个 Agent 智能体**带来的测试特殊性——它不是无状态 REST 端点，
> 「测试通过」不等于「HTTP 200」，而是「Agent 真正用事件流把任务跑到了 `done`」。
>
> **适用性**：本文是 07 §2 门禁脚本与 §4 工作流的**补充专章**；07 讲「护栏与门禁」，
> 本文讲「具体的跑通步骤与 Agent 专项断言」。

---

## 1. Hermes 作为 Agent 智能体的测试特殊性 <a id="agent-nature"></a>

进程内 `AIAgent` 不是一个函数调用，而是一个**有状态、长程、事件驱动**的智能体。
自测 / 端到端验证必须据此设计，否则会出现「假绿」（进程起来、API 可 import，但 Agent 实际不干活）：

| 特殊性 | 对测试的含义 |
| --- | --- |
| **状态化、长程** | 一次 `run_conversation` 可能循环数十次工具调用（`max_iterations` 默认 90）。测试不能只 assert「返回了字符串」，要 assert「任务被真正完成」。 |
| **事件流（SSE 词汇）** | Agent 产出 `delta`/`reasoning`/`action`/`action_result`/`tool_progress`/`done`/`error`（`01` §4.1）。测试要**捕获并断言事件流形状**，而不只是 `chat()` 的返回值。 |
| **工具闭环** | 完成任务常需调工具：每个 `action` 必须配对一个 `action_result`（除非 `error`）。测试要把「工具被调用且完成」当成核心断言。 |
| **进程内直跑、无网关** | 选用进程内直跑路线时不起 Hermes 网关、不 spawn `hermes` 子进程、不连 `127.0.0.1:8642`（`07` R1/R2）。测试要 statically 断言「没起网关、没拉起 hermes 子进程」（改选跨进程路线则按对应路线手册另测，见 references/02-integration-core.md §2 路径 D）。 |
| **异步 / 事件驱动** | 流式靠后台 `worker` 线程 + `queue.Queue`（`02` §2、§6）。测试不能在 UI 主线程同步跑，要像生产代码一样用 worker + queue 收集事件。 |
| **回调两套入口** | `event_callback` 是**构造器**参数（统一事件总线）；`stream_callback` 是 `run_conversation` 的**方法参数**（增量文本）。两套都要接，否则观察不全。 |
| **模块懒加载** | 部分模块（如示例 `wiki_engine.py`）在编译/查询时才懒加载 `AIAgent`。测试要覆盖「导入测试 + 运行时 `runtime_ready()`」，确认懒加载路径也 OK。 |
| **费用仅为估算** | `get_credits_*` 返回**估算值**，非真实账单（`01` §5）。测试**不能** assert「真实扣费金额」。 |
| **委派事件未证实** | `event_callback` 是否透传子代理委派事件**未经实测**（R6）。测试若依赖委派卡片，必须先实测透传，否则以「静默不显示」兜底，不得假设有 `delegation` 事件。 |

---

## 2. 自测金字塔（四层，与 `scripts/` 对应）

```
L0 结构门禁      check_skill_gate.py        → 关键文件齐备、hermes-llms-full.txt 体积合理
L1 质量门禁      quality_check.py            → 改 .py：py_compile + 导入测试；改 .js：node --check
   (改完即跑)    check_js_modules.py
─────────────────────────────────────────────────────────────────────────────────
L2 集成自测  ★本文★  → 进程内实例化 AIAgent，跑真实任务，断言事件流 + 终态（Agent 专项）
L3 端到端/发版  release_gate.py             → quality → check_endpoints → smoke_test_web
   (打包后)     启动 EXE 验证业务健康端点（防 HTTP 200 假绿）
```

- **L0/L1 是静态护栏**：只证明「代码能编译、文件不缺」。它们**无法证明 Agent 能跑通一个任务**——
  这正是本文 L2 要补的缺口。
- **L2 是本文核心**：在 L0/L1 之后、L3 之前，用真实 provider 跑一次端到端对话。
- **L3 是发版总闸**：L2 通过后再打包，跑 `release_gate.py` 并启动 EXE 验证业务端点。

> 流程衔接：L0 → L1 → **L2（本文 walkthrough）** → L3。任何一层失败都先修该层，不跳过。

---

## 3. 跑通一个集成 · walkthrough（step by step） <a id="walkthrough"></a>

下面是一段**可直接落为脚本**的端到端自测。前置假设：已装 `hermes-agent==0.19.0`、
provider API key 已配置、本机**未起** Hermes 网关 / 未拉 `hermes` 子进程（进程内直跑路线前置；若选网关路线则按需）。

### Step 0 · 前置核查

```bash
# 1) 装包（连字符包名；[web] 仅 FastHTML/pywebview 路线需要）
pip install "hermes-agent[web]==0.19.0"

# 2) 确认无网关在跑（进程内直跑路线一般不应监听 8642；若选网关路线则跳过此步）
#    Windows:  netstat -ano | findstr 8642   → 应为空
#    macOS/Linux: lsof -i:8642               → 应为空

# 3) 配置凭证（不写死在代码里；走环境变量或 provider 默认凭证源）
export HERMES_API_KEY="..."   # 或 provider 自有环境变量
```

### Step 1 · `runtime_ready()` 自检（复用 `07` §3 模式）

先确认 Library 可导入、版本正确、回调签名齐全——比「直接 `import` 跑一下」更早暴露漂移。

```python
import inspect, importlib.metadata as md
from run_agent import AIAgent

def runtime_ready() -> dict:
    info = {"importable": False, "version": None,
            "callbacks_ok": False, "stream_ok": False}
    info["version"] = md.version("hermes-agent")          # 应为 0.19.0
    info["importable"] = True
    init_p = inspect.signature(AIAgent.__init__).parameters
    run_p = inspect.signature(AIAgent.run_conversation).parameters
    info["callbacks_ok"] = all(k in init_p for k in
        ("tool_start_callback", "tool_complete_callback",
         "reasoning_callback", "event_callback"))
    info["stream_ok"] = "stream_callback" in run_p        # 方法参数，非构造器
    return info

print(runtime_ready())
# 期望: {'importable': True, 'version': '0.19.0',
#        'callbacks_ok': True, 'stream_ok': True}
```

### Step 2 · 最小 `AIAgent` 构造 + 接事件总线

构造遵循**减法原则**（`enabled_toolsets=None` 全量 + `disabled_toolsets=["terminal"]`，
见 `01` §3.2 / `03` §1），并把两个回调入口都接上。

```python
import queue, threading

events = []                       # 收集到的内核事件
deltas = []                       # 增量文本

def on_event(name: str, payload: dict):
    events.append((name, payload))

def on_delta(text: str):
    deltas.append(text)

agent = AIAgent(
    provider="deepseek", model="deepseek-chat",   # 换成你的 provider/model
    disabled_toolsets=["terminal"],               # 进程内常态：禁 spawn-per-call 终端
    quiet_mode=True,
    event_callback=on_event,                      # 构造器参数：统一事件总线
)
```

### Step 3 · 跑一次对话并收集事件流

生产代码用 worker 线程 + queue（`02` §2、§6）。自测保持一致，避免在调用线程里阻塞。

```python
q = queue.Queue(); SENTINEL = object()

def worker():
    try:
        result = agent.run_conversation(
            "用一句话解释什么是进程内 Agent。",
            stream_callback=on_delta,             # 方法参数：增量文本
        )
        q.put(("result", result))
    except Exception as e:
        q.put(("error", e))
    finally:
        q.put(SENTINEL)

threading.Thread(target=worker, daemon=True).start()
while True:
    item = q.get()
    if item is SENTINEL:
        break
    # 这里可把 item 转成断言；生产代码则转 SSE / 更新 GUI
```

### Step 4 · 断言（Agent 专项）

```python
names = [n for (n, _) in events]
assert ("done" in names) or ("error" in names), "必须收到 done 或 error 终态"
assert "done" in names, "正常路径必须收到 done（错误路径才不发 done）"
assert len(deltas) > 0, "应产生增量文本（delta）"
assert names.count("action") == names.count("action_result"), \
    "每个 action 必须有配对的 action_result（除非 error）"
```

### Step 5 · 端到端场景任务（给一个「需要工具」的任务）

只测「聊天」不够——要给 Agent 一个**必须调工具才能完成**的任务，断言工具闭环。
例如用 `file` 工具集读目录并总结（需 `enabled_toolsets=None` 默认含 `file`）：

```python
events2 = []
agent2 = AIAgent(provider="deepseek", model="deepseek-chat",
                 disabled_toolsets=["terminal"], quiet_mode=True,
                 event_callback=lambda n, p: events2.append((n, p)))
agent2.run_conversation("列出当前目录下的文件，并挑一个 README 用一句话总结它的作用。")
n2 = [n for (n, _) in events2]
assert "done" in n2
# 该任务需要 file 工具：应至少出现一次 action(action_result 配对)
assert n2.count("action") >= 1 and n2.count("action") == n2.count("action_result"), \
    "场景任务应触发工具调用并形成 action→action_result 闭环"
agent2.close()
```

### Step 5b · 宿主系统原有功能用例（必须覆盖）<a id="domain-cases"></a>

L2 不能只测「通用对话 / 文件工具」——**必须包含直接命中宿主系统原有功能的提示词**。
集成本身的意义就是让 Agent 能操作业务系统既有的数据/能力；若这些用例缺失，
等于没验证「集成」这件事，只验证了「Agent 能聊天」。

> 泛化说明：本技能教学文档不绑定具体业务（见铁律）。下面用占位 `my_domain`
> （可替换为 `customer` / `order` / `product` 等你的领域实体）示意；具体实体名
> 与工具由宿主系统自行暴露——常见做法是通过 `register_pure_python_tools` 注册
> 纯 Python 业务工具，使 Agent 能查询/操作宿主的既有数据。

```python
# 每个用例：prompt（命中宿主原有功能）+ 期望被触发的领域行为（行为契约，不比对回答文本）
DOMAIN_CASES = [
    ("查询当前进行中的 <业务实体> 及其状态",
     "期望触发领域查询工具并形成 action→action_result 闭环"),
    ("对 <业务实体> ID=123 执行一次状态变更",
     "期望触发领域写操作工具且 done"),
]

for prompt, expect in DOMAIN_CASES:
    ev = []
    ag = AIAgent(provider=PROVIDER, model=MODEL,
                 disabled_toolsets=["terminal"], quiet_mode=True,
                 event_callback=lambda n, p: ev.append((n, p)))
    ag.run_conversation(prompt)
    ag.close()
    ne = [n for (n, _) in ev]
    assert "done" in ne, f"宿主功能用例未 done: {prompt} -> {ne}"
    assert ne.count("action") >= 1 and ne.count("action") == ne.count("action_result"), \
        f"宿主功能用例未触发工具闭环: {prompt} -> {ne}  (期望: {expect})"
```

要点：
- 断言的是**行为**（触发了领域工具 + 跑到 `done`），不是回答的具体措辞；
- 若宿主系统原有功能是通过「注册纯 Python 工具」暴露的，**用例必须覆盖到这些工具被实际调用**——
  否则只是「Agent 自己编了一段话」，并未真正连通业务系统。

### Step 6 · 接入门禁工作流

L2 通过后，回到 07 §4 主线继续：

```bash
python scripts/quality_check.py            # L1：py_compile + 导入
# （打包）python scripts/release_gate.py   # L3：quality → check_endpoints → smoke_test_web
```

把 Step 1–5 收成一个 `self_test_integration.py`，可在 `release_gate` 之前手动跑，
作为「集成真的跑通」的硬性证据（完整骨架见 §7）。

---

## 4. Agent 特殊性专项断言清单 <a id="assertions"></a>

| # | 断言 | 为什么（对应 §1 特殊性） | 失败含义 |
| --- | --- | --- | --- |
| A1 | `runtime_ready()["importable"]` 且 `version=="0.19.0"` | 状态/长程；版本漂移会让后面全崩 | Library 没装对或版本不符 |
| A2 | `callbacks_ok` 且 `stream_ok` | 两套回调入口都要接 | 事件观察不全 |
| A3 | 事件流终态必为 `done` 或 `error`；`error` 路径不再发 `done` | 事件流 | 终态语义错 |
| A4 | `len(deltas) > 0`（正常路径） | 事件流 | 没产生正文 |
| A5 | `action` 数 == `action_result` 数 | 工具闭环 | 工具调了没回结果（卡死/异常） |
| A6 | 场景任务触发 ≥1 次 `action` 且配对 | 工具闭环 | Agent 没真正用工具完成任务 |
| A7 | **未起网关**：`netstat/lsof` 查 8642 为空；**未 spawn** `hermes` 子进程 | 进程内直跑路线无网关 | 进程内直跑路线下偷偷走了网关路线（R1/R2 违例） |
| A8 | 不 assert `get_credits_*` 为真实账单 | 费用仅为估算 | 误判扣费 |
| A9 | 不依赖 `delegation` 事件（R6 未证实） | 委派未证实 | 依赖了未实测能力 |
| A10 | 每个「宿主原有功能」用例触发对应领域工具并形成 `action`→`action_result` 闭环、终态 `done` | 集成意义（Step 5b） | 集成没真正连通业务系统，只验证了「Agent 能聊天」 |

---

## 5. 与门禁脚本衔接（把 walkthrough 接进提交 / CI） <a id="gate-wiring"></a>

- **L2 是 L1 与 L3 之间的桥**：`quality_check.py` 只保证「能编译」，
  `release_gate.py` 只保证「打包后能起、业务端点通」。中间「Agent 真能跑通任务」靠本文 L2。
- **建议落点**：把 §7 的 `self_test_integration.py` 放在 `examples/01-hermes-desktop/`
  （或你的应用 `tests/` 下），在 `release_gate.py` 之前手动/CI 跑一次。
- **不是强制门禁**：L2 需要真实 provider 网络与 key，不适合作为无网络的纯结构门禁
  （`check_skill_gate.py` 不依赖网络）。因此 L2 是「人工/CI 集成证据」，L0/L1/L3 是「硬门禁」。
- **漂移联动**：若升级 `hermes-agent` 后 L2 失败，先跑 `check_api_signature.py` 比对
  `api-baseline.json`（`07` §2），确认是签名漂移还是集成写错，再决定改文档还是改代码。

---

## 6. 测试反模式（⛔ 这几条会制造假绿） <a id="anti-patterns"></a>

| ⛔ | 反模式 | 正确做法 |
| --- | --- | --- |
| T1 | 用 HTTP 200 / EXE 能启动 当「集成成功」 | 必须断言事件流终态 + Agent 实际产出（A3–A6） |
| T2 | 只调 `chat()` 不接回调就断言「流式可用」 | 接 `event_callback` + `stream_callback`，断言 `delta`/`done`（A2/A4） |
| T3 | assert `get_credits_*` 为真实账单 | 费用仅估算，不 assert 真实扣费（A8） |
| T4 | 进程内直跑路线下起 Hermes 网关做「集成测试」 | 进程内直跑路线一般不起网关；测试前确认 8642 空、无 hermes 子进程（A7） |
| T5 | 在 UI 主线程同步跑 `run_conversation` | 用 worker 线程 + `queue.Queue`（`02` §6），否则冻屏 |
| T6 | 假设有 `delegation` 事件并据此断言 | 委派未证实（R6），先实测 `event_callback` 透传，否则静默（A9） |
| T7 | 只测「聊天」不测「工具闭环」 | 给需要工具的场景任务，断言 action→action_result（A5/A6） |
| T8 | 只测通用对话/文件工具，不测宿主原有功能 | 必须包含命中业务系统既有能力的领域提示词（Step 5b / A10） |

---

## 7. 最小自测脚本完整骨架（可直接落为测试文件） <a id="skeleton"></a>

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
self_test_integration.py — hermes-desktop 进程内集成自测（跑通一个集成）

前置：hermes-agent==0.19.0 已装、provider API key 已配置、本机未起 Hermes 网关（进程内直跑路线前置）。
用法：python self_test_integration.py
退出码：0 = 通过，1 = 失败
"""
from __future__ import annotations

import inspect
import queue
import sys
import threading
from run_agent import AIAgent

PROVIDER = "deepseek"
MODEL = "deepseek-chat"
SIMPLE_PROMPT = "用一句话解释什么是进程内 Agent。"
TASK_PROMPT = "列出当前目录下的文件，并挑一个 README 用一句话总结它的作用。"
# 宿主系统原有功能用例（必须覆盖）：用占位 <业务实体> 指代你的领域实体
# （customer/order/product…）；具体实体名与工具由宿主系统自行暴露。
DOMAIN_PROMPTS = [
    "查询当前进行中的 <业务实体> 及其状态",
    "对 <业务实体> ID=123 执行一次状态变更",
]


def runtime_ready() -> dict:
    import importlib.metadata as md
    info = {"importable": False, "version": None,
            "callbacks_ok": False, "stream_ok": False}
    info["version"] = md.version("hermes-agent")
    info["importable"] = True
    init_p = inspect.signature(AIAgent.__init__).parameters
    run_p = inspect.signature(AIAgent.run_conversation).parameters
    info["callbacks_ok"] = all(k in init_p for k in
        ("tool_start_callback", "tool_complete_callback",
         "reasoning_callback", "event_callback"))
    info["stream_ok"] = "stream_callback" in run_p
    return info


def run_and_collect(agent: AIAgent, prompt: str):
    """后台线程跑对话，返回 (events, deltas, error)。复刻生产 worker+queue 模式。"""
    events: list = []
    deltas: list = []
    holder = {}

    def worker():
        try:
            res = agent.run_conversation(
                prompt,
                stream_callback=lambda t: deltas.append(t),
            )
            holder["result"] = res
        except Exception as e:  # noqa: BLE001
            holder["error"] = e
        finally:
            events.extend(holder.get("_ev", []))

    # 用 event_callback 收集
    agent.event_callback = lambda n, p: events.append((n, p))
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout=300)
    return events, deltas, holder.get("error")


def main() -> int:
    # A1/A2
    ready = runtime_ready()
    assert ready["importable"] and ready["version"] == "0.19.0", f"runtime_ready 失败: {ready}"
    assert ready["callbacks_ok"] and ready["stream_ok"], f"回调签名缺失: {ready}"
    print(f"[OK] runtime_ready: {ready}")

    # Step 2-4：简单对话
    agent = AIAgent(provider=PROVIDER, model=MODEL,
                    disabled_toolsets=["terminal"], quiet_mode=True)
    events, deltas, err = run_and_collect(agent, SIMPLE_PROMPT)
    agent.close()
    assert err is None, f"对话抛错: {err}"
    names = [n for (n, _) in events]
    # A3/A4
    assert "done" in names, f"未收到 done，事件: {names}"
    assert len(deltas) > 0, "未产生 delta 增量文本"
    # A5
    assert names.count("action") == names.count("action_result"), \
        f"action/action_result 不配对: {names}"
    print(f"[OK] 简单对话跑通：{len(deltas)} 段 delta，事件={names}")

    # Step 5：场景任务（必须调工具）
    agent2 = AIAgent(provider=PROVIDER, model=MODEL,
                     disabled_toolsets=["terminal"], quiet_mode=True)
    ev2, _, err2 = run_and_collect(agent2, TASK_PROMPT)
    agent2.close()
    assert err2 is None, f"场景任务抛错: {err2}"
    n2 = [n for (n, _) in ev2]
    # A6/A5
    assert "done" in n2, f"场景任务未 done: {n2}"
    assert n2.count("action") >= 1, f"场景任务未触发工具调用: {n2}"
    assert n2.count("action") == n2.count("action_result"), \
        f"场景任务 action/action_result 不配对: {n2}"
    print(f"[OK] 场景任务跑通（工具闭环）：事件={n2}")

    # Step 5b：宿主系统原有功能用例（必须覆盖，否则等于没测「集成」）
    for dp in DOMAIN_PROMPTS:
        ag = AIAgent(provider=PROVIDER, model=MODEL,
                     disabled_toolsets=["terminal"], quiet_mode=True)
        evd, _, errd = run_and_collect(ag, dp)
        ag.close()
        assert errd is None, f"宿主功能用例抛错: {dp} -> {errd}"
        nd = [n for (n, _) in evd]
        assert "done" in nd, f"宿主功能用例未 done: {dp} -> {nd}"
        assert nd.count("action") >= 1 and nd.count("action") == nd.count("action_result"), \
            f"宿主功能用例未触发工具闭环: {dp} -> {nd}"
        print(f"[OK] 宿主原有功能用例跑通：{dp} -> 事件={nd}")

    # A7（静态）：本自测自身（进程内直跑路线）不起网关/子进程，由运行环境保证 8642 为空
    print("[OK] 集成自测全部通过（注意：A7 网关/子进程检查由运行环境保证）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as e:
        print(f"[FAIL] 集成自测未通过：{e}")
        sys.exit(1)
```

> 旗舰示例 `examples/01-hermes-desktop/agent_runtime.py` 的 `runtime_ready()` /
> `build_agent()` 是本文模式的生产级实现，可作为对照样本。

---

## 8. Agent 输出评估（LLM Judge 三段式，依托 `ctx.llm.complete_structured`）<a id="agent-evals"></a>

> 与 pydantic_evals 的「数据集 → 任务 → 评估」三段式同源；这里**只依托 hermes 原生能力**落地，不引入
> 额外依赖。核心：用 `PluginLlm.complete_structured()` 跑一个结构化 LLM Judge，对 Agent 输出批量打分。
> 关键在**强类型**——判分返回必须是可解析、可校验的 JSON（`res.parsed` 即校验后的 dict）。

**三段式**：

1. **数据集**：一组 `(输入, 期望)` 用例（内存 list / JSON 文件 / `$HERMES_HOME` 会话均可）。
2. **任务**：跑被评估的 Agent（`AIAgent.run_conversation`），收集每个用例的 `final_response`。
3. **评估**：LLM Judge 对每个输出结构化判分。

```python
# 评估端（插件内）——Judge 用宿主模型 + 强类型 schema，结果可落库/可断言
from agent.plugin_llm import PluginLlmTextInput

def judge(ctx, question, agent_output, expectation):
    res = ctx.llm.complete_structured(
        instructions=(
            "你是严格评估员。判断 Agent 回答是否满足期望，返回 JSON："
            "{\"pass\": bool, \"score\": number(0-1), \"reason\": string}"
        ),
        input=[
            PluginLlmTextInput(text=f"问题:{question}\n期望:{expectation}\n回答:{agent_output}"),
        ],
        json_schema={
            "type": "object",
            "properties": {
                "pass": {"type": "boolean"},
                "score": {"type": "number"},
                "reason": {"type": "string"},
            },
            "required": ["pass", "score", "reason"],
        },
    )
    return res.parsed  # {'pass': True/False, 'score': ..., 'reason': ...}
```

**门禁衔接**：把「通过率阈值」接进 §5 的门禁工作流（如 `pass_rate >= 0.9` 才算绿）；
输出质量回归纳入 §2 自测金字塔的顶层。相比纯文本断言（§4），Judge 能捕获**语义偏差**而非仅字符串匹配。

**注意**：Judge 是**有网络/有模型**的测试，属「集成后验证」，与 §9 的离线确定性测试互补——CI 里两者都跑：
离线测「链路不 404 / 事件形状正确」，在线 Judge 测「输出语义达标」。

## 9. 离线确定性测试（无网络，依托 `test_bridge` + mock 回放）<a id="offline-test"></a>

> pydantic-ai 有测试替身 model；hermes 无内置 test model，但可**用固定回放（fixture）让 Agent 走确定性路径**，
> 使 CI 在**无 provider key / 无网络**下仍能验证集成链路与事件形状。旗舰示例 `examples/01-hermes-desktop/test_bridge.py`
> 即此思路的离线桥接自测（`quality_check.py` 第 3 步已接入，12 passed）。

**做法**：

- **不真正调 LLM**：用预置 `(输入 → 事件流/输出)` 回放字典替身，验证「UI 桥接层 → 事件总线 → 渲染」链路与
  事件形状（`delta`/`reasoning`/`action`/`action_result`/`done`），而不是验证模型输出质量（那交给 §8）。
- **mock provider 回放**：把一次真实会话的响应序列存为 fixture，注入一个假 `provider`/回调，让 `AIAgent`
  的事件收集逻辑在无网下跑通，断言事件数与顺序。

**适合离线断言的**：会话/记忆运行时方法（`01` §5）、SSE 桥接（`02` §3）、回调事件形状（`01` §4）、
路由不 404（`check_endpoints`）。
**不适合离线断言的**：任何依赖真实模型输出的语义（交给 §8 Judge）。

**与 §8 分工**：离线=确定性、快、无网，锁「链路与契约」；在线 Judge=真实模型，锁「输出质量」。两者合起来
才覆盖 §2 金字塔的「跑通 + 达标」两层。
