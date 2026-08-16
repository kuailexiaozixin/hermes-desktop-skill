# 模板 · fasthtml_minimal（FastHTML + SSE 最小空壳）

进程内 Hermes 桌面集成的**最小起点**。只做「一句话进、一句话出、流式可见」。

## 用法

```bash
cp -r templates/fasthtml_minimal my_app
cd my_app
pip install -r requirements.txt
set HERMES_API_KEY=sk-...        # Windows
# macOS / Linux: export HERMES_API_KEY=sk-...
python main.py          # 浏览器模式：http://localhost:5001
python main.py --desktop # pywebview 原生桌面窗口（失败自动回退浏览器）
```

## 下一步（按 SKILL.md §5 顺序）

1. `scripts/probe_library.py` 确认 Library 健康。
2. 把 `stream_worker` 升级成 `examples/01-hermes-desktop/agent_runtime.py` 的完整版
   （加 `tool_start/complete`、`reasoning` 回调 + `_ThinkingSplitter`）。
3. 注册业务工具（`references/02-integration-core.md#tools`）。
4. 表格/办公需求走 `references/02-integration-core.md#office` 治理模型。
5. 打包（`references/06-packaging.md`）。

> 本模板内置 pywebview 桌面模式（`python main.py --desktop`）：后台 uvicorn 拉起服务 + 原生窗口加载，
> 与 `examples/01-hermes-desktop/launcher.py` 同模式；pywebview/WebView2 缺失时自动回退默认浏览器。
