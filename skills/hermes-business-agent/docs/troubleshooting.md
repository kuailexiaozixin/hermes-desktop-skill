# 排障（troubleshooting）

> 问题沉淀首选文件。遇到新坑，修完后在此追加一条。按现象归类。

---

## 1. `ModuleNotFoundError: No module named 'run_agent'`

**原因（按概率）**：
1. 装错了包：装了 `pip install hermes`（Helmholtz 无关包），而不是 `pip install hermes-agent`。
   → 重装：`pip uninstall hermes; pip install hermes-agent`。
2. **Python 解释器不一致**：跑 GUI 的 Python ≠ 装 hermes-agent 的 Python。
   → 用同一个 venv 的 python；跑 `scripts/probe_library.py` 验证（见 `05-install-and-env.md`）。
3. **23 模块名冲突**：项目根有 `tools.py`/`utils.py`，覆盖了 Hermes 的同名模块。
   → 把业务代码移进带包名的目录（如 `src/myapp/`），绝不在根留 `tools.py`/`utils.py`。

**排查**：`python -c "import run_agent; print(run_agent.__file__)"` 看实际导入的是哪份。

---

## 2. 流式完全不输出 / UI 静默

**原因**：
1. `stream_callback` 传错了位置——传成了**构造器**的 `stream_delta_callback`，而方法参数版没传。
   → 正确：`agent.run_conversation(user_message=..., stream_callback=on_delta)`（方法参数）。
2. 模型/路径不走流式，一次性返回全文。
   → 用 `07-quality-gates.md#gates` §2 的断言验证；若确实没触发，检查 callback 接法。

**铁律**：集成后必跑回调触发断言（见 `01` §4 / `07` §2）。

---

## 3. 界面冻结（Tkinter）或请求卡死（FastHTML）

**原因**：在**主线程/事件循环**里直接调了 `run_conversation()`（它同步阻塞）。
→ 必须 worker 线程 + 队列（Tkinter `root.after` / FastHTML SSE 生成器）。见 `02` §2（worker 线程 + 队列桥接）。

---

## 4. 打包后启动崩溃 / `ImportError` 运行时才报

**原因**：Hermes 的 hidden-import 没列全（尤其函数内懒加载的子模块）。
→ 逐个列 hidden-import（见 `06-packaging.md` §2）。**禁止 `--collect-submodules tools`**（OOM）。
迭代式补齐：看 traceback 缺哪个模块就加哪个 `--hidden-import`。

---

## 5. 冻结态 EXE 启动即崩（写配置失败）

**原因**：`HERMES_HOME` 没设，Hermes 写到只读区（如 `Program Files`）。
→ 在 `main.py` 顶部（任何 Hermes 导入前）设 `HERMES_HOME=<exe>/hermes_data` 并确保可写。
见 `05-install-and-env.md` §3 / `06` §4。

---

## 6. `Python requires >=3.11, <3.14`

**原因**：用了 3.10 或 3.14+。
→ 切到 3.11–3.13。见 `05-install-and-env.md` §1。

---

## 7. venv 的 python.exe 报 `did not find executable at '<路径>'`

**原因**：venv 的 `pyvenv.cfg` 里 `home = ` 那一行指向的 base 解释器目录已失效（换机器 / 用户名变了，
`C:\Users\<旧用户名>\...` 指向了不存在的目录）。实测该情形下 `python.exe` 只打印这一行、
退出码仍为 0，所以脚本里要判的是"没有输出"而不是"非零退出"。
→ 重建 venv：`python -m venv .venv`；或用 `scripts/check_api_signature.py --path <run_agent.py>`
（纯 ast 解析，不需要能跑的解释器）。

---

## 8. 回调里碰 GUI 控件导致偶发崩溃

**原因**：回调在 **worker 线程**执行，Tk/WebView 控件非线程安全。
→ 回调只 `queue.put(...)`，渲染全交主线程。见 `03` §3。

---

## 9. 版本漂移：代码忽然跑不通

**原因**：PyPI 升到新版（如 0.18.x→0.19.0），签名/默认变了。
→ 跑 `scripts/track_upstream.py` 与 `scripts/check_api_signature.py`；有 `REMOVED`/`DEFAULT_CHANGED`
则按 `SKILL.md`〔入场检查〕更新技能（先更新 `01-library-api.md` 与 examples，再验证）。

---

## 10. 三系统「融合模式」起来了，却没有 Agent 对话（静默回退假绿）

**症状**：`连接系统/main.py` 正常启动、`/dashboard` 200，但 `/api/chat` 404、`/healthz` 404；
日志里一行 `[连接系统] 融合装配失败，回退业务自建 app：ModuleNotFoundError: No module named 'server'`。

**原因**：Agent 底座代码在三系统根下的 `Agent系统/`（外部 submodule），不在三系统根本身。
装配函数的 `sys.path` 若只加了「根 + 业务系统 + 连接系统」，`from server import app` 就取不到底座模块，
而 `except` 分支回退成**纯业务 app**——它照样 200，于是"看起来起来了"。

→ 修 `ensure_syspath()` 把 `Agent系统/` 入 path（`examples/01-hermes-desktop/连接系统/bridge.py` 已修）；
底座目录整体缺失时直接返回 `None` 让入口报错，不再静默回退。

**防复发（三类判据，缺一即误判）**：
1. 融合成功的唯一硬证据是日志出现 `[连接系统] 融合装配完成`——禁止拿 HTTP 200 当装配证据。
2. `verify_tristructure.py` 是**静态**门禁（扫 import 与文件在位），本例它全绿而运行时是坏的；
   运行时靠 `release_gate.py --verify-launch --launch-root examples/01-hermes-desktop/连接系统 --expect "<页面标志>"`。
3. `sys.path` 组装只留一处（`bridge.ensure_syspath()`），入口 `main.py` 不再重复维护目录清单——
   两份清单各写一遍且都漏了 `Agent系统/`，正是这次故障的土壤。

---

## 11. 文档与源码冲突：`max_iterations` 默认值（官方 500 / 源码 90）

**现象**：官方文档（`hermes-llms-full.txt` 的 Library 参数表）写 `max_iterations` 默认 `500`，
本机 0.19.0 内省是 `90`（`python scripts/probe_library.py` 直接打印该值，`scripts/api-baseline.json` 亦记 `90`）。

**结论（以源码为准）**：**90 是真值**。但两者不一致这件事本身就是风险——按 500 估算最坏成本会低估 5 倍以上，
而按 90 认为"有默认值兜着"又会被文档的 500 误导。所以本技能的处理方式是**不选边、直接取消依赖**：

- 集成侧一律**显式设** `max_iterations`（业务问答 10~30，带多步工具的写面 20~40，见 `21` §3）；
- 默认值的唯一出处是 `01` §3.2 第 11 行，其余文档只引用不重述（`00-index` §5 已登记此归属）；
- 每次版本漂移后以 `probe_library.py` 的打印值为准更新 `01`，禁止用文档值回填。

**泛化规则**：凡"文档 A 源码 B"的冲突，本技能只在 `01`/`03`/`05` 等**归属文档**里记一次实测值，
在本文记一次结论与处置，其余位置一律指针化——三处各写一遍数字是假绿的源头（改了两处、漏一处）。
