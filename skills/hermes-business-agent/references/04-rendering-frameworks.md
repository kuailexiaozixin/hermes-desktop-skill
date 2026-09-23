# 04 · 多框架接入与整合（Hermes Python Library 接入）

> 本文件讲解如何把 Hermes Python Library（`from run_agent import AIAgent`）接入到不同应用框架。
> 调用 Python Library 有 5 条**平等可选**技术路线（进程内直跑 / Hermes 网关 / spawn CLI / API Server / `/v1`），**无先后顺序**。本文以**进程内直跑**为叙述示例（仅示例，不代表该路线优先），讲解各框架如何把 `AIAgent` 接进 GUI；跨进程路线的选型与落地见 references/02-integration-core.md §2.1–§2.5（五条路线逐节）。
> 本文其余「不连网关 / 不碰 `8642`」的约束，均为**进程内直跑路线**下的接入约定；若选用跨进程路线，则按对应路线评估（见 references/02-integration-core.md §2.1–§2.5（五条路线逐节））。
> 各框架的本质差异只是「UI 线程 / 宿主进程 与 Python 主线程如何交互」。
> 本文件**只讲接入与整合**，不对标任何外部项目。
>
> 按宿主技术栈分三类：
>
> - **A 类 · Python 原生**：FastHTML / Tkinter / pywebview / textual / PyQt6·PySide6 / wxPython——Library 与 UI 同进程，最直接。
> - **B 类 · Python 后端 + JS/Web 前端桥接**：Electron / React·Vue(+Vite) / Koa BFF——Python 进程内跑 `AIAgent`，JS 前端经**本地桥接**（stdio / 命名管道 / 本地 socket / 嵌入 webview）通信。
> - **C 类 · 其他语言宿主**：.NET(C#) / Java / C / C++ / Rust——嵌入 Python 运行时（pythonnet / JPype / libpython / PyO3）或独立 Python 进程 + 本地桥接；Library 仍在进程内（嵌入）或受控进程内（桥接）。
>
> 红线见 §16。通用桥接范式见 `02` §3（worker + 队列）、SSE 词汇与事件来源见 `01` §4.1。
>
> **篇幅与阅读提示**：A 类（Python 原生框架）是本文重点与最常用路径，应优先掌握；B/C 类为完整性与参考给出。
> C 类嵌入代码为**示意、未经 0.19.0 实测**（见 §10 提示），复制前务必自行验证。
> 本文各框架节末尾重复的「进程内直跑不连 `8642` / 改选其它路线另行评估」均为同一约束的框架化重申，可按需略读。

---

## 1. FastHTML（服务端 SSE 桥接）· A 类

- 形态：Python 服务端用 FastHTML/uvicorn 渲染页面，经 SSE 把内核事件推到浏览器。
- 桥接：后端持有 `AIAgent`（`02` §3 的 worker+queue 模式），把 `stream_callback` 收到的分片按
  `01` §4.1 的映射转成 SSE `type`（`delta`/`reasoning`/`action`/`action_result`/`done`/`error`）。
- 前端范式：工具卡片 + 推理折叠 + 代码复制 + Mermaid 可视化。
- 适用：rich Web UI、流式工具可视化、附件抽屉、Usage Analytics、多会话侧栏。
- 依赖：uvicorn 与 jinja2 已是 `hermes-agent` 核心依赖；FastHTML 不在任何 extra 里，应用须自行声明 `python-fasthtml`。

---

## 2. Tkinter（原生桌面 GUI）· A 类

- 形态：纯 Python 原生窗口，无浏览器、无 Node。
- 桥接：在 Tk 主循环外起 worker 线程跑 `AIAgent`，worker 只往队列塞事件，再用 `root.after()` 把队列里的条目回主线程更新控件。
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
- 桥接：在 textual `App` 里起线程 worker（`self.run_worker(..., thread=True)`）跑 `AIAgent`，
  worker 线程把 `stream_callback` 的分片塞进 `queue.Queue`，再由 UI 侧用 `app.call_from_thread` 之外的
  常规读取路径（`set_interval` 轮询队列，或 worker 结束后一次性取回）更新 Widget：
  正文增量写 Rich 文本区，工具调用与结果用 `DataTable`/`Tree` 近似工具卡，收尾刷新取 `run_conversation` 的返回值。
  禁止用 `event_callback` 当事件源（0.19.0 只发 `session:compress`），事件到界面的映射关系见 `01` §4.1。
- 适用：CLI 工具、SSH 远程运维助手、服务器侧智能体、无图形环境。
- 注意：无图形；图片/图表用链接或终端图形库近似。

---

## 5. PyQt6 / PySide6（Qt 原生桌面）· A 类

- 形态：Python + Qt 原生窗口，表现力介于 Tkinter 与 Web 之间，跨平台（Win/mac/Linux），原生菜单/托盘/系统托盘集成好。
- 桥接：`QThread` worker 跑 `AIAgent`，在 worker 的 `run()` 里把 `stream_callback` 分片经自定义
  `pyqtSignal` / `Signal` 发回主线程更新 `QWidget`（`emit` 跨线程安全，禁止直接碰控件）；
  正文增量 → `QTextEdit` 追加，工具调用与结果 → `QListWidget` 工具卡。
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
- 最小骨架（Python 后端，经 stdio 与 Electron 通信；核心 worker+queue 见 `02` §3，此处为该框架落地形态）：

  ```python
  # backend.py —— 进程内跑 AIAgent，经 stdio 与 Electron 通信（非 Hermes 网关）
  import sys, json, threading
  from queue import Queue
  from run_agent import AIAgent

  agent = AIAgent(...)            # 构造范式见 01 §3
  q: Queue = Queue()

  def pump():                     # 常驻：每取到一个事件就打一行 JSON 到 stdout
      while True:
          print(json.dumps(q.get()), flush=True)

  threading.Thread(target=pump, daemon=True).start()

  for line in sys.stdin:                          # 读 Electron 发来的用户消息
      msg = json.loads(line)
      threading.Thread(                # run_conversation 阻塞，必须在 worker 线程里跑
          target=lambda: agent.run_conversation(
              msg["text"],
              stream_callback=lambda t: q.put({"type": "delta", "text": t}),
          ),
          daemon=True,
      ).start()
  ```

  这里只转发 `delta`；`reasoning`/`action`/`action_result`/`done`/`error` 各来自哪个回调，见 `01` §4.1 的映射表——禁止接 `event_callback` 当 SSE 源，它在 0.19.0 只发 `session:compress`。

  Electron 侧：`child_process.spawn('python', ['backend.py'])`，`stdout.on('data', ...)` 收事件、
  `child.stdin.write(json + '\n')` 发消息。
- 进程内直跑路线**不**装 Hermes 网关、不连 `127.0.0.1:8642`、不用 `electron-updater` 自更网关；若选跨进程路线则另行评估（见 references/02-integration-core.md §2.1–§2.5（五条路线逐节））。
- 适用：需要成熟桌面壳（窗口/托盘/快捷键/自动更新壳）+ Web 技术栈的团队。
- 打包坑：Python 后端需随 Electron 包分发并**显式定位解释器/venv**（`06` §2）；`child_process.spawn` 的 `python` 路径勿依赖系统 PATH（环境差异会导致找不到解释器），应打包自带 venv 或 embeddable 解释器。

---

## 8. React / Vue（+Vite）（Web 前端 + Python 后端）· B 类

- 形态：React/Vue 单页前端（Vite 构建），后端是 Python 进程内 `AIAgent`。
- 桥接：两种本地模式——
  1. **纯本地桥**：Python 后端经 stdio/命名管道与前端 dev-server 插件通信；或前端直接
     `new WebSocket('ws://127.0.0.1:<本地端口>')` 连 Python 后端（该端口是你自己的本地桥，**不是** Hermes 网关 8642）。
  2. **FastHTML 混合**：用 FastHTML 做后端 + SSE（写法见本文 §1 与 `templates/fasthtml_minimal/`），React/Vue 作为前端组件挂载——走 FastHTML 的
     SSE 桥，无需自建 WS。
- 最小骨架（Python 本地 WebSocket 桥，非 Hermes 网关；核心 worker+queue 见 `02` §3，此处为该框架落地形态）：

  ```python
  # ws_bridge.py —— 进程内 AIAgent + 本地 WebSocket 桥（仅本机，非 8642）
  import asyncio, json, threading
  from run_agent import AIAgent

  agent = AIAgent(...)            # 构造范式见 01 §3

  async def handler(ws):
      async for raw in ws:
          payload = json.loads(raw)
          q: asyncio.Queue = asyncio.Queue()
          loop = asyncio.get_running_loop()

          def worker():           # 阻塞的 run_conversation 放线程里跑
              try:
                  result = agent.run_conversation(
                      payload["text"],
                      stream_callback=lambda t: loop.call_soon_threadsafe(
                          q.put_nowait, {"type": "delta", "text": t}),
                  )
              finally:            # 收尾一条 done，前端据此关流
                  loop.call_soon_threadsafe(
                      q.put_nowait, {"type": "done", "final": result})

          threading.Thread(target=worker, daemon=True).start()
          while True:
              ev = await q.get()
              await ws.send_json(ev)
              if ev["type"] == "done":
                  break
  # 监听 127.0.0.1:<本地端口>，仅本机；非 Hermes 网关 8642
  ```

  回调侧只有一个跨线程入口可用：`stream_callback` 收正文分片，`run_conversation` 的返回值即终态。`event_callback` 是构造器/属性上的回调、不是 `run_conversation` 的参数，且 0.19.0 内核只在压缩时发 `session:compress`；`reasoning`/`action`/`action_result` 等 SSE `type` 各自的来源见 `01` §4.1。

- 进程内直跑路线不连 `127.0.0.1:8642` 的 Hermes `/v1`；若选跨进程路线则按需（见 references/02-integration-core.md §2.1–§2.5（五条路线逐节））。
- 适用：已有 React/Vue 技术栈的团队、内部 Web 控制台。

---

## 9. Koa / Node BFF（Node 后端桥接 Python 进程）· B 类

- 形态：Node(Koa) 作 BFF，桥接一个 Python Hermes 进程；前端经 BFF 通信。
- 桥接：Koa 用 `child_process` 拉起 Python 后端，经 **Socket.IO / 命名管道** 桥接
  （例如 `ipc:///tmp/hermes-agent-bridge.sock` 或本地 TCP）；Python 端跑 `AIAgent` 进程内，经桥接回传 SSE 事件。
- 进程内直跑路线**不**托管 Hermes 网关子进程、**不**监听 `127.0.0.1:8642`、**不**用网关的自更新能力——
  那是网关路线的能力；若选跨进程路线则另行评估（见 references/02-integration-core.md §2.1–§2.5（五条路线逐节））。
- 适用：Node 团队、需要 BFF 聚合多服务。

---

> **C 类（§10–13）说明**：以下嵌入路线（pythonnet / JPype / libpython / PyO3）代码为**示意**，
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
      agent.run_conversation("你好");   // 形参名是 user_message；C# 具名实参须与之同名，故这里按位置传
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

## 14. 怎么选宿主：三问定类，类内按四个维度取舍

选宿主是一趟问答，不是一张对照表。按 1→3 问，每问的分支直接指向本文对应节的写法。

**问 1 · Agent 要接进去的那个界面，是用什么语言写的？** 这一问定类，别跳。

- **纯 Python，界面今天从零起 → A 类（§1–§6）**：Library 与 UI 同进程，最直接，也是本文重点。
- **界面已经在前端团队手里（React/Vue/Electron/Koa）→ B 类（§7–§9）**：Python 进程内跑 `AIAgent`，
  JS 前端经**本地桥**（stdio / 命名管道 / 本地 socket / 嵌入 webview）通信。硬套 A 类等于替前端团队重写界面。
- **宿主是 .NET / Java / C / C++ / Rust → C 类（§10–§13）**：优先子进程 + 本地桥；
  嵌入 Python 运行时（pythonnet / JPype / libpython / PyO3）仅当必须，且先验证 `PYTHONHOME` 与 GIL（工程复杂度这一类最高）。

**问 2 · 定类之后，在类内按四个维度取舍**：Web 表达力、打包体积与分发、依赖复杂度、跨平台。
下面每类内部按这四个维度给出的差异选一节照抄：

- **A 类内部**：要富 UI、流式工具卡、多会话侧栏 → FastHTML（§1）；在此基础上要独立窗口/托盘 → 加 pywebview 壳（§3 + §15 第一条）；
  要最低依赖、内网或无头/SSH 环境 → Tkinter（§2）或 textual（§4，终端 TUI）；
  要原生菜单、系统集成、更强的控件表达 → PyQt6/PySide6（§5）或 wxPython（§6）。
- **B 类内部**：已有 React/Vue 工程 → §8（+ Python 后端）；前端团队要一个成熟桌面壳 → §7 Electron；
  Node 团队做 BFF 聚合多个下游 → §9 Koa。三者桥接结构相同（§15 的 B 类通用范式），换的是宿主壳不是协议。
- **C 类内部**：按宿主语言各一节（§10 .NET / §11 Java / §12 C·C++ / §13 Rust），
  每节都是「嵌入」与「子进程桥」二选一（§15 的 C 类通用范式）；两端的 Library 都在某个进程内，默认都**不**走网关 8642。

问 2 那四个维度的取值（照抄上面的类内路由时，用这四行核对取舍方向）：
- **Web 表达力**：FastHTML / pywebview / Electron / React·Vue 最强（富工具卡、推理折叠、Mermaid）；Tkinter/textual 最弱。
- **打包体积与分发**：A 类纯 Python（Tkinter/textual 最小）；pywebview/Qt 需带渲染层/插件；Electron 体积最大。
- **依赖复杂度**：Tkinter → pywebview → Qt → Electron 递增；C 类嵌入（pythonnet/JPype/libpython/PyO3）工程复杂度最高（GIL/PYTHONHOME/venv）。
- **跨平台**：Qt / wxPython / Electron / pywebview 最佳；Tkinter 内建但 UI 弱。

**问 3 · 回到 SKILL.md 第 ② 步核对自洽**：这个宿主 + 调用路线 + 工程形态三件必须彼此不矛盾
（例如进程内直跑却选了 Electron 又要远程访问，就是串路线）。对不上就退回问 1 换类，禁止在桥接层塞网络代码补洞。

## 15. 框架整合与组合

- **Web UI 进原生壳**：FastHTML 后端 + pywebview 壳 = 富 Web 体验 + 独立窗口/托盘。两者共用同一套
  `AIAgent` worker+queue（`02` §3），仅把 HTTP/SSE 端点改为 pywebview 的本地 `webview.create_window` 内部地址。
- **原生 GUI 与系统托盘**：Tkinter / PyQt 适合做系统托盘助手、无头环境的最小控件；若需要 richer 面板，
  可把原生 GUI 作为启动器/托盘层，Web 部分交给 FastHTML + pywebview。
- **多智能体布局**：pywebview 或 Electron 壳内用多个 `AIAgent` 实例（各自 worker+queue），前端用多面板呈现；
  见 `examples/02-hermes-pywebview-multiagent`。
- **B 类通用桥接范式**（进程内形态）：Electron / React / Vue / Koa 都遵循同一结构——**Python 进程内 `AIAgent` + 本地桥
  （stdio/命名管道/Unix socket/嵌入 webview）连 JS 前端**；桥端口是你自己的本地端口，默认不指向 Hermes 网关 8642（若放开为网关形态则按网关方案）。
- **C 类通用范式**：.NET/Java/C/C++/Rust 都遵循「**嵌入 Python 运行时（进程内 Library）** 或 **独立 Python 进程 + 本地桥接**」二选一；前者 Library 在宿主进程内，后者 Library 在受控 Python 进程内，二者默认都**不**走 Hermes 网关（若放开为网关形态则按网关方案）。
- **共享内核约束**：无论哪种渲染层/宿主，都复用同一个 `AIAgent` 构造范式（`01` §3）与 SSE 词汇及事件来源（`01` §4.1），
  不各自重新实现事件分发；业务工具层统一走 `02` §7。

---

## 16. 接入检查清单（进程内直跑路线）

- [ ] `AIAgent` **进程内直跑**：你的 Python 进程，或嵌入 Python 运行时的宿主进程；不 spawn Hermes 网关、不调 `127.0.0.1:8642` 的 `/v1`、不调 `hermes` CLI。
- [ ] B 类框架（Electron / React / Vue / Koa）用**本地桥接**（stdio / 命名管道 / Unix socket / 嵌入 webview）
  连 Python 后端；桥端口是你自己的本地端口，**不是** Hermes 网关 8642。
- [ ] C 类框架（.NET/Java/C/C++/Rust）用 pythonnet/JPype/libpython/PyO3 **嵌入** Python 运行时，或独立 Python 进程 + 本地桥接；Library 仍在进程内（嵌入）或受控进程内（桥接）。
- [ ] 渲染层/宿主只消费由内核回调转出的事件流（映射见 `01` §4.1），不反向控制内核执行。
- [ ] 打包时按 `06` §2 补齐 hidden-import；pywebview 额外分发 `webview/lib`；PyQt/PySide 带 Qt 插件；C 类嵌入需随包分发对应 venv 的 libpython。
- （进程内直跑路线）不引 Hermes 网关 / `API_SERVER_KEY` / CORS / `electron-updater` 自更网关 / 远程后端；若选跨进程路线则按需引入（见 references/02-integration-core.md §2.1–§2.5（五条路线逐节））。
- （进程内直跑路线）不依赖网关专属能力（消息平台集成、cron 多投递目标、SSH/Docker 远程）——这三项由网关进程提供，进程内直跑没有对应实现；需要时自建工具层（`02` §7）或改选网关路线。

### 何时改选跨进程路线（对照判据）

若选用进程内直跑路线，出现以下任一真实需求时可**改选**跨进程路线（见 references/02-integration-core.md §2.1–§2.5（五条路线逐节））：

- **需要外部 OpenAI 兼容调用**：Open WebUI / LobeChat / 其它语言 / curl / CI 要当客户端调 Hermes → 跨进程路线。
- **需要接消息平台**（Telegram/Slack/QQ/Discord…）或 **cron 多投递** → 跨进程路线。
- **需要多客户端 / 远程 / 多用户 profile 隔离** → 跨进程路线。
- **需要 runs/jobs/sessions 等完整管理端点** → 跨进程路线。

> 具体选哪条跨进程路线及其落地，见 references/02-integration-core.md §2.1–§2.5（五条路线逐节）。

反过来说：**纯桌面单机 GUI、仅进程内自调、无对外被调需求** → 保持进程内直跑路线，不开跨进程服务
（避免常驻服务 + 端口 + 认证 + 跨进程状态同步的不必要复杂度）。
完整落地见 `15-api-server.md`。

