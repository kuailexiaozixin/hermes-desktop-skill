# 模板 · tkinter_minimal（Tkinter + worker 线程最小空壳）

进程内 Hermes 桌面集成的**最小起点**（无浏览器内核，体积小）。只做「一句话进、一句话出、流式可见」。

## 用法

```bash
cp -r templates/tkinter_minimal my_app
cd my_app
pip install -r requirements.txt
set HERMES_API_KEY=sk-...        # Windows
# macOS / Linux: export HERMES_API_KEY=sk-...
python main.py
```

## 下一步

1. `scripts/probe_library.py` 确认 Library 健康。
2. 升级 `worker` 成 examples 的 `agent_runtime.stream_agent_chat` 完整版
   （工具卡片、思考折叠区、会话历史）。
3. 注册业务工具（`references/02-integration-core.md#tools`）。
4. 打包（`references/06-packaging.md`，Tkinter 是标准库，只需补 Hermes hidden-import）。

> 选型对比见 `references/04-rendering-frameworks.md`。
