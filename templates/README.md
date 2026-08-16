# 模板（templates）

两套可直接实例化的最小骨架。**铁律：先把空壳跑通，再加业务**。

| 目录 | 路线 | 适用 |
| --- | --- | --- |
| `fasthtml_minimal/` | FastHTML + SSE | 富交互、Markdown/表格/卡片、产品级 UI |
| `tkinter_minimal/` | Tkinter + worker 线程 | 纯原生、体积小、内部小工具 |

## 实例化

```bash
cp -r templates/fasthtml_minimal  my_app
# 或
cp -r templates/tkinter_minimal   my_app
```

然后按各自 README 安装依赖、设 `HERMES_API_KEY`、运行。

## 升级路径（按 SKILL.md §5）

空壳跑通后，把 `stream_worker`/`worker` 升级为 `examples/01-hermes-desktop/agent_runtime.py`
的完整版（加工具卡片、思考折叠区、会话历史、审批），再注册业务工具（references/02-integration-core.md#tools）、接表格办公（references/02-integration-core.md#office）、
最后打包（references/06-packaging.md）。

> 两套骨架的 Hermes 集成内核完全一致，差异只在 GUI 壳与渲染（见 `references/04-rendering-frameworks.md`）。
