# 04 · 多框架接入与整合（Hermes Python Library 接入）

> 本文件讲解如何把 Hermes Python Library（`from run_agent import AIAgent`）接入到不同应用框架。
> 调用 Python Library 有 5 条**平等可选**技术路线（进程内直跑 / Hermes 网关 / spawn CLI / API Server / `/v1`），**无先后顺序**。本文以**进程内直跑**为叙述示例（仅示例，不代表该路线优先），讲解各框架如何把 `AIAgent` 接进 GUI；跨进程路线的选型与落地见 references/02-integration-core.md §2 路径 D。
> 本文其余「不连网关 / 不碰 `8642`」的约束，均为**进程内直跑路线**下的接入约定；若选用跨进程路线，则按对应路线评估（见 references/02-integration-core.md §2 路径 D）。
> 各框架的本质差异只是「UI 线程 / 宿主进程 与 Python 主线程如何交互」。
> 本文件**只讲接入与整合**，不对标任何外部项目。
>
> 按宿主技术栈分三类：
>
> - **A 类 · Python 原生**：FastHTML / Tkinter / pywebview / textual / PyQt6·PySide6 / wxPython——Library 与 UI 同进程，最直接。
> - **B 类 · Python 后端 + JS/Web 前端桥接**：Electron / React·Vue(+Vite) / Koa BFF——Python 进程内跑 `AIAgent`，JS 前端经**本地桥接**（stdio / 命名管道 / 本地 socket / 嵌入 webview）通信。
> - **C 类 · 其他语言宿主**：.NET(C#) / Java / C / C++ / Rust——嵌入 Python 运行时（pythonnet / JPype / libpython / PyO3）或独立 Python 进程 + 本地桥接；Library 仍在进程内（嵌入）或受控进程内（桥接）。
>
> 红线见 §16。通用桥接范式见 `02` §2（worker + 队列）、SSE 词汇见 `01` §4。
>
> **篇幅与阅读提示**：A 类（Python 原生框架）是本文重点与最常用路径，应优先掌握；B/C 类为完整性与参考给出。
> C 类嵌入代码为**示意、未经 0.19.0 实测**（见 §10 提示），复制前务必自行验证。
> 本文各框架节末尾重复的「进程内直跑不连 `8642` / 改选其它路线另行评估」均为同一约束的框架化重申，可按需略读。

---

## 1. FastHTML（服务端 SSE 桥接）· A 类

- 形态：Python 服务端用 FastHTML/uvicorn 渲染页面，经 SSE 把内核事件推到浏览器。
- 桥接：后端持有 `AIAgent`（`02` §2 的 worker+queue 模式），把 `event_callback` /
  `stream_delta_callback` 转成 SSE 流（`delta`/`reasoning`/`action`/`action_result`/`done`/`error`）。
- 前端范式：工具卡片 + 推理折叠 + 代码复制 + Mermaid 可视化。
- 适用：rich Web UI、流式工具可视化、附件抽屉、Usage Analytics、多会话侧栏。
- 依赖：`hermes-agent[web]` 已含 FastHTML/uvicorn/jinja2。

---

## 2. Tkinter（原生桌面 GUI）· A 类

- 形态：纯 Python 原生窗口，无浏览器、无 Node。
- 桥接：在 Tk 主循环外起 worker 线程跑 `AIAgent`，用 `event_callback` 把事件经 `root.after()` 回主线程更新控件。
- 适用：轻量单机工具、系统托盘助手、无头/内网环境、最低依赖。
- 注意：UI 表达力弱于 Web；流式「工具卡片」需用 Treeview/Listbox 近似。

---

## 3. pywebview（原生 WebView 壳）· A 类

- 形态：用 pywebview 起一个**原生 WebView 窗口**（Edge Chromium / WebKit），内部仍跑 FastHTML 式
  SSE 桥接；本质是「Web UI 装在原生壳里」。
- 桥接：`webview.platforms.winforms` + `webview.platforms.edgechromium`（Windows）；打包需把
  `webview/lib` 随包分发（`06` §2）。
- 适用：既要 Web UI 表现力、又要独立桌面窗口/托盘/无地址栏。
- 多智能体示例：`examples/02-hermes-pywebview-multiagent` 演示 pywebview 壳内的多 Agent 布局。

---

## 4. textual（终端 TUI）· A 类

- 形态：纯 Python 终端 UI（TUI），无浏览器、无 Node；在 SSH / 服务器 / 低带宽环境也能跑。
- 桥接：在 textual `App` 里起 worker 线程（`app.run_worker`）跑 `AIAgent`，用 `event_callback`
  经 `app.call_from_thread` 把事件推回主线程更新 Widget；`delta` 增量写 Rich 文本区，
  `action`/`action_result` 用 `DataTable`/`Tree` 呈现工具卡，`done` 触发最终刷新。
- 适用：CLI 工具、SSH 远程运维助手、服务器侧智能体、无图形环境。
- 注意：无图形；图片/图表用链接或终端图形库近似。

---

## 5. PyQt6 / PySide6（Qt 原生桌面）· A 类

- 形态：Python + Qt 原生窗口，表现力介于 Tkinter 与 Web 之间，跨平台（Win/mac/Linux），原生菜单/托盘/系统托盘集成好。
- 桥接：`QThread` worker 跑 `AIAgent`，通过 `pyqtSignal` / `Signal` 把 SSE 事件发回主线程更新 `QWidget`；
  `delta`→`QTextEdit` 追加，`action`→`QListWidget` 工具卡。
- 适用：需要原生系统集成（菜单/托盘/文件关联）的专业桌面工具。
- 打包：`PyInstaller --onefile`，hidden-import `PyQt6` 或 `PySide6`；注意 Qt 插件路径随包分发。
- 许可：PySide6（LGPL）与 PyQt6（GPL / 商业许可）按分发许可选择。

---

## 6. wxPython（原生桌面，轻量跨平台）· A 类

- 形态：Python + wxWidgets 原生控件，比 Tkinter 表现力强、比 Qt 轻，传统桌面业务工具常用。
- 桥接：wx 多线程（`wx.CallAfter`）把 worker 线程的 `AIAgent` 事件回主线程更新控件。
- 适用：传统桌面业务系统、内部工具。

---

## 7. Electron（Node 桌面壳 + Python 后端）· B 类

- 形态：Electron 提供原生窗口 + Chromium 渲染（JS/HTML/CSS），但**内核不在 Node 里**——单独起一个
  Python 进程跑 `AIAgent`（进程内 Library）。
- 桥接（关键）：Electron 主进程通过 `child_process` 拉起 Python 后端，双向用 **stdio JSON-RPC**
  （或 `node-ipc` 命名管道 / 本地 `ws` socket）通信；Python 后端持有 `AIAgent`，把 SSE 事件经桥接推给
  Electron renderer。桥端口是你自己的本地端口，**不是** Hermes 网关 `8642`。
- 最小骨架（Python 后端，经 stdio 与 Electron 通信；核心 worker+queue 见 `02` §2，此处为该框架落地形态）：

  ```python
  # backend.py —— 进程内跑 AIAgent，经 stdio 与 Electron 通信（非 Hermes 网关）
  import sys, json, threading
  from queue import Queue
  from run_agent import AIAgent

  agent = AIAgent(...)            # 构造范式见 01 §3
  q: Queue = Queue()
  agent.event_callback = lambda ev: q.put(ev)   # SSE 事件入队

  def pump():
      while not q.empty():
          print(json.dumps(q.get()), flush=True)   # 每行一个事件 JSON -> Electron stdout

  for line in sys.stdin:                          # 读 Electron 发来的用户消息
      msg = json.loads(line)
      threading.Thread(
          target=lambda: (agent.run_conversation(msg["text"]), pump()),
          daemon=True,
      ).start()
  ```

  Electron 侧：`child_process.spawn('python', ['backend.py'])`，`stdout.on('data', ...)` 收事件、
  `child.stdin.write(json + '\n')` 发消息。
- 进程内直跑路线**不**装 Hermes 网关、不连 `127.0.0.1:8642`、不用 `electron-updater` 自更网关；若选跨进程路线则另行评估（见 references/02-integration-core.md §2 路径 D）。
- 适用：需要成熟桌面壳（窗口/托盘/快捷键/自动更新壳）+ Web 技术栈的团队。
- 打包坑：Python 后端需随 Electron 包分发并**显式定位解释器/venv**（`06` §2）；`child_process.spawn` 的 `python` 路径勿依赖系统 PATH（环境差异会导致找不到解释器），应打包自带 venv 或 embeddable 解释器。

---

## 8. React / Vue（+Vite）（Web 前端 + Python 后端）· B 类

- 形态：React/Vue 单页前端（Vite 构建），后端是 Python 进程内 `AIAgent`。
- 桥接：两种本地模式——
  1. **纯本地桥**：Python 后端经 stdio/命名管道与前端 dev-server 插件通信；或前端直接
     `new WebSocket('ws://127.0.0.1:<本地端口>')` 连 Python 后端（该端口是你自己的本地桥，**不是** Hermes 网关 8642）。
  2. **FastHTML 混合**：用 FastHTML（`01`/`03` 已有）做后端 + SSE，React/Vue 作为前端组件挂载——走 FastHTML 的
     SSE 桥，无需自建 WS。
- 最小骨架（Python 本地 WebSocket 桥，非 Hermes 网关；核心 worker+queue 见 `02` §2，此处为该框架落地形态）：

  ```python
  # ws_bridge.py —— 进程内 AIAgent + 本地 WebSocket 桥（仅本机，非 8642）
  import asyncio, json
  from run_agent import AIAgent

  agent = AIAgent(...)            # 构造范式见 01 §3
  loop = asyncio.get_event_loop()

  async def handler(ws):
      async for raw in ws:
          payload = json.loads(raw)
          agent.run_conversation(
              payload["text"],
              event_callback=lambda ev: asyncio.run_coroutine_threadsafe(
                  ws.send(json.dumps(ev)), loop),
          )
  # 监听 127.0.0.1:<本地端口>，仅本机；非 Hermes 网关 8642
  ```

- 进程内直跑路线不连 `127.0.0.1:8642` 的 Hermes `/v1`；若选跨进程路线则按需（见 references/02-integration-core.md §2 路径 D）。
- 适用：已有 React/Vue 技术栈的团队、内部 Web 控制台。

---

## 9. Koa / Node BFF（Node 后端桥接 Python 进程）· B 类

- 形态：Node(Koa) 作 BFF，桥接一个 Python Hermes 进程；前端经 BFF 通信。
- 桥接：Koa 用 `child_process` 拉起 Python 后端，经 **Socket.IO / 命名管道** 桥接
  （例如 `ipc:///tmp/hermes-agent-bridge.sock` 或本地 TCP）；Python 端跑 `AIAgent` 进程内，经桥接回传 SSE 事件。
- 进程内直跑路线**不**开启 `HERMES_WEB_UI_MANAGED_GATEWAY`、不托管 Hermes 网关子进程、不依赖 `127.0.0.1:8642`——
  那是网关路线的能力；若选跨进程路线则另行评估（见 references/02-integration-core.md §2 路径 D）。
- 适用：Node 团队、需要 BFF 聚合多服务。

---

> ⚠️ **C 类（§10–13）说明**：以下嵌入路线（pythonnet / JPype / libpython / PyO3）代码为**示意**，
> 未在 `hermes-agent==0.19.0` 环境实测。嵌入 CPython 涉及 `PYTHONHOME` / GIL / venv 包路径等大量坑，
> **复制前务必自行验证**；嵌入不可靠时，优先走「独立 Python 进程 + 本地桥接」（同 §7 JSON-RPC 协议）。

## 10. .NET / C#（嵌入 Python 或子进程桥接）· C 类

- 形态：C# 宿主（WPF / WinForms / MAUI / 控制台）要调用 Hermes 能力。
- 路线 (a) **pythonnet 嵌入 CPython**（Library 在 .NET 进程内，仍是进程内、无网关）：

  ```csharp
  // 宿主进程内嵌入 Python 运行时，直接调 Library（无 Hermes 网关）
  using Python.Runtime;
  PythonEngine.Initialize();
  using (Py.GIL())
  {
      dynamic run_agent = Py.Import("run_agent");
      dynamic agent = run_agent.AIAgent(/* 构造参数见 01 §3 */);
      agent.run_conversation(userMessage: "你好");
  }
  ```

- 路线 (b) **子进程桥接**：C# 用 `System.Diagnostics.Process` 拉起 Python 后端（`backend.py`，同 §7 骨架），经 stdio JSON-RPC 通信。
- 进程内形态不连 Hermes 网关；嵌入路线靠 pythonnet 现成 CPython，桥接路线靠本地 stdio。
- 适用：已有 .NET 桌面/企业应用的团队。

---

## 11. Java（JPype 嵌入或子进程桥接）· C 类

- 形态：Java/Swing/JavaFX/Spring 宿主要调用 Hermes 能力。
- 路线 (a) **JPype 嵌入**：在 JVM 内启动 CPython，直接调 `run_agent`：

  ```java
  // JVM 内嵌入 Python；调用前确保 JPype 已装且 PYTHONHOME 指向 hermes venv
  Jpype.startJVM(Jpype.getDefaultJVMPath(), "-Dpython.home=" + venvHome);
  Jpype.importSitePackages();
  PyObject run_agent = Jpype.importModule("run_agent");
  PyObject agent = run_agent.call("AIAgent", /* 构造参数见 01 §3 */);
  agent.call("run_conversation", "你好");
  ```

- 路线 (b) **子进程桥接**：Java 用 `ProcessBuilder` 拉起 Python 后端，读 `Process.getInputStream()` 收事件、写 `getOutputStream()` 发消息（同 §7 JSON-RPC）。
- 进程内形态不连 Hermes 网关；JPype 嵌入即进程内 Library。
- 适用：已有 Java 企业应用的团队。

---

## 12. C / C++（libpython 嵌入或子进程 + IPC）· C 类

- 形态：原生 C/C++ 应用（Qt C++ / GTK / 游戏引擎 / 嵌入式）要调用 Hermes 能力。
- 路线 (a) **libpython 嵌入**：在宿主进程内初始化 CPython，导入 `run_agent`：

  ```c
  // 宿主进程内嵌入 CPython；编译时链接 libpython，运行时 PYTHONHOME 指向 hermes venv
  Py_Initialize();
  PyObject *mod = PyImport_ImportModule("run_agent");
  PyObject *AIAgent = PyObject_GetAttrString(mod, "AIAgent");
  PyObject *agent = PyObject_CallObject(AIAgent, args);   // 构造参数见 01 §3
  PyObject_CallMethod(agent, "run_conversation", "(s)", "你好");
  ```

- 路线 (b) **子进程 + 本地 IPC**：C/C++ 用 `popen`/`CreateProcess` 拉起 Python 后端，经命名管道 / Unix socket 交换 JSON 事件（同 §7 协议）。
- 进程内形态不连 Hermes 网关；嵌入路线靠 libpython，桥接路线靠本地 IPC。
- 适用：原生桌面/嵌入式/高性能宿主。

---

## 13. Rust（PyO3 嵌入或 std::process 桥接）· C 类

- 形态：Rust（Tauri / 原生 GUI / CLI）要调用 Hermes 能力。
- 路线 (a) **PyO3 嵌入**：在 Rust 内持有 Python GIL，调 `run_agent`（编译依赖 libpython）：

  ```rust
  // Rust 内嵌入 Python；Cargo.toml 加 pyo3（features=["auto-initialize"]）
  Python::with_gil(|py| {
      let run_agent = py.import("run_agent").unwrap();
      let agent = run_agent.getattr("AIAgent").unwrap()
          .call1((/* 构造参数见 01 §3 */)).unwrap();   // 构造参数需经 Py 对象传
      agent.call_method1("run_conversation", ("你好",)).unwrap();
  });
  ```

- 路线 (b) **`std::process::Command` 桥接**：Rust 拉起 `python backend.py`，经 `stdin`/`stdout` 的 JSON-RPC 通信（同 §7 协议）。
- 进程内形态不连 Hermes 网关；嵌入路线靠 PyO3，桥接路线靠子进程 stdio。
- 适用：Rust 桌面（Tauri）/CLI 宿主。

---

## 14. 框架选型速查

| 场景 | 首选框架 | 类 | 集成模式 |
| --- | --- | --- | --- |
| 富 Web UI、流式工具卡、多会话 | FastHTML | A | 同进程 SSE |
| 独立桌面窗口/托盘、Web 体验 | pywebview + FastHTML | A | 同进程 SSE |
| 最低依赖、内网/无头、SSH | Tkinter / textual | A | worker + 主线程回传 |
| 原生菜单/托盘/系统集成 | PyQt(PySide) / wxPython | A | QThread/CallAfter + 信号 |
| 已有 Web 技术栈（React/Vue） | React/Vue + Python 后端 | B | 本地桥（stdio/ws/命名管道） |
| 成熟桌面壳 + Web 栈团队 | Electron + Python 后端 | B | 本地桥（stdio/命名管道） |
| Node 团队、BFF 聚合 | Koa + Python 后端 | B | 本地桥（IPC/ws） |
| .NET 桌面/企业应用 | pythonnet 嵌入 / 子进程桥 | C | 进程内嵌入 或 stdio |
| Java 企业应用 | JPype 嵌入 / 子进程桥 | C | 进程内嵌入 或 stdio |
| 原生 C/C++ 宿主 | libpython 嵌入 / 子进程 IPC | C | 进程内嵌入 或 本地 IPC |
| Rust（Tauri/CLI）宿主 | PyO3 嵌入 / 子进程桥 | C | 进程内嵌入 或 stdio |

---

**选型权衡维度**（§14 速查表只给映射，这里给权衡）：
- **Web 表达力**：FastHTML / pywebview / Electron / React·Vue 最强（富工具卡、推理折叠、Mermaid）；Tkinter/textual 最弱。
- **打包体积与分发**：A 类纯 Python（Tkinter/textual 最小）；pywebview/Qt 需带渲染层/插件；Electron 体积最大。
- **依赖复杂度**：Tkinter→pywebview→Qt→Electron 递增；C 类嵌入（pythonnet/JPype/libpython/PyO3）工程复杂度最高（GIL/PYTHONHOME/venv）。
- **跨平台**：Qt / wxPython / Electron / pywebview 最佳；Tkinter 内建但 UI 弱。
- **团队技术栈**：前端团队优先 B 类（React/Vue/Electron）；纯 Python 团队优先 A 类；已有 .NET/Java/原生宿主优先 C 类。
- **决策建议**：单机 Python 桌面 → 默认 FastHTML + pywebview（表现力+独立窗口）；已有前端栈 → B 类本地桥；其他语言宿主 → C 类优先子进程桥（嵌入仅当必须，且先验证 PYTHONHOME/GIL）。

## 15. 框架整合与组合

- **Web UI 进原生壳**：FastHTML 后端 + pywebview 壳 = 富 Web 体验 + 独立窗口/托盘。两者共用同一套
  `AIAgent` worker+queue（`02` §2），仅把 HTTP/SSE 端点改为 pywebview 的本地 `webview.create_window` 内部地址。
- **原生 GUI 与系统托盘**：Tkinter / PyQt 适合做系统托盘助手、无头环境的最小控件；若需要 richer 面板，
  可把原生 GUI 作为启动器/托盘层，Web 部分交给 FastHTML + pywebview。
- **多智能体布局**：pywebview 或 Electron 壳内用多个 `AIAgent` 实例（各自 worker+queue），前端用多面板呈现；
  见 `examples/02-hermes-pywebview-multiagent`。
- **B 类通用桥接范式**（进程内形态）：Electron / React / Vue / Koa 都遵循同一结构——**Python 进程内 `AIAgent` + 本地桥
  （stdio/命名管道/Unix socket/嵌入 webview）连 JS 前端**；桥端口是你自己的本地端口，默认不指向 Hermes 网关 8642（若放开为网关形态则按网关方案）。
- **C 类通用范式**：.NET/Java/C/C++/Rust 都遵循「**嵌入 Python 运行时（进程内 Library）** 或 **独立 Python 进程 + 本地桥接**」二选一；前者 Library 在宿主进程内，后者 Library 在受控 Python 进程内，二者默认都**不**走 Hermes 网关（若放开为网关形态则按网关方案）。
- **共享内核约束**：无论哪种渲染层/宿主，都复用同一个 `AIAgent` 构造范式（`01` §3）与 SSE 词汇（`01` §4），
  不各自重新实现事件分发；业务工具层统一走 `02` §7。

---

## 16. 接入检查清单（进程内直跑路线）

- ✅ `AIAgent` **进程内直跑**：你的 Python 进程，或嵌入 Python 运行时的宿主进程；不 spawn Hermes 网关、不调 `127.0.0.1:8642` 的 `/v1`、不调 `hermes` CLI。
- ✅ B 类框架（Electron / React / Vue / Koa）用**本地桥接**（stdio / 命名管道 / Unix socket / 嵌入 webview）
  连 Python 后端；桥端口是你自己的本地端口，**不是** Hermes 网关 8642。
- ✅ C 类框架（.NET/Java/C/C++/Rust）用 pythonnet/JPype/libpython/PyO3 **嵌入** Python 运行时，或独立 Python 进程 + 本地桥接；Library 仍在进程内（嵌入）或受控进程内（桥接）。
- ✅ 渲染层/宿主只消费 `AIAgent` 的 SSE 事件，不反向控制内核执行。
- ✅ 打包时按 `06` §2 补齐 hidden-import；pywebview 额外分发 `webview/lib`；PyQt/PySide 带 Qt 插件；C 类嵌入需随包分发对应 venv 的 libpython。
- （进程内直跑路线）不引 Hermes 网关 / `API_SERVER_KEY` / CORS / `electron-updater` 自更网关 / 远程后端；若选跨进程路线则按需引入（见 references/02-integration-core.md §2 路径 D）。
- （进程内直跑路线）不依赖网关专属能力（消息平台集成、cron 多投递目标、SSH/Docker 远程）——进程内直跑无；需时自建工具层（`02` §7）或选网关路线。

### 何时改选跨进程路线（对照判据）

若选用进程内直跑路线，出现以下任一真实需求时可**改选**跨进程路线（见 references/02-integration-core.md §2 路径 D）：

- **需要外部 OpenAI 兼容调用**：Open WebUI / LobeChat / 其它语言 / curl / CI 要当客户端调 Hermes → 跨进程路线。
- **需要接消息平台**（Telegram/Slack/QQ/Discord…）或 **cron 多投递** → 跨进程路线。
- **需要多客户端 / 远程 / 多用户 profile 隔离** → 跨进程路线。
- **需要 runs/jobs/sessions 等完整管理端点** → 跨进程路线。

> 具体选哪条跨进程路线及其落地，见 references/02-integration-core.md §2 路径 D。

反过来说：**纯桌面单机 GUI、仅进程内自调、无对外被调需求** → 保持进程内直跑路线，不开跨进程服务
（避免常驻服务 + 端口 + 认证 + 跨进程状态同步的不必要复杂度）。
完整落地见 `15-api-server.md`。

