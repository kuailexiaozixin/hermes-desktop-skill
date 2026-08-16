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

## 7. venv 的 python.exe 报「did not find executable」

**原因**：venv 的 `pyvenv.cfg` 记录的 base 解释器路径已失效（如换机器 / 用户名变了，
`C:\Users\<旧用户名>\...` 指向了已不存在的目录）。
→ 重建 venv：`python -m venv .venv`；或用 `scripts/check_api_signature.py --path <run_agent.py>`
（纯 ast 解析，不需要能跑的解释器）。

---

## 8. 回调里碰 GUI 控件导致偶发崩溃

**原因**：回调在 **worker 线程**执行，Tk/WebView 控件非线程安全。
→ 回调只 `queue.put(...)`，渲染全交主线程。见 `03` §3。

---

## 9. 版本漂移：代码忽然跑不通

**原因**：PyPI 升到新版（如 0.19.0→0.19.0），签名/默认变了。
→ 跑 `scripts/track_upstream.py` 与 `scripts/check_api_signature.py`；有 `REMOVED`/`DEFAULT_CHANGED`
则按 `SKILL.md §0` 更新技能（先更新 `01-library-api.md` 与 examples，再验证）。
