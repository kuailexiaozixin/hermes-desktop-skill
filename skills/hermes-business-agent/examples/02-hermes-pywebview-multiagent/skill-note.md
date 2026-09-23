# 示例 02 · Hermes pywebview 多 Agent 桌面客户端（本技能视角）

> **来源**：开源项目 [`Felix-Forever/hermes-agent-desktop`](https://github.com/Felix-Forever/hermes-agent-desktop)（MIT），完整浅克隆去除 `.git` 后落于此。
> **体积**：源码实际约 0.3MB（`app.py` 15KB + `index.html` 106KB + 4 张截图 + 文档），极轻量。

## 它与 01 旗舰示例的关系

| | 01-hermes-desktop（旗舰底座） | 02-hermes-pywebview-multiagent（本项目） |
| --- | --- | --- |
| GUI 路线 | FastHTML + pywebview | **纯 pywebview**（单文件 `app.py` + `index.html`，aiohttp 内嵌） |
| 内核接入 | 进程内 `AIAgent` | **进程内 `AIAgent`**（`from run_agent import AIAgent`，无 gateway） |
| 侧重 | 通用底座（业务解耦、能力全集） | **多 Agent 协作 + Skill Store**（PM 编排、20 智能体、可视化技能商店） |
| 形态 | 大而全（35 模块） | 小而精（单文件可读） |

**填补的空白**：
1. **pywebview 极简形态**——01 是 FastHTML 路线，02 展示"纯 pywebview + aiohttp 内嵌 API server"的另一种轻量落地，可作为 `references/04-rendering-frameworks.md` 之外的 pywebview 直接范本。
2. **多 Agent / 委派主题**——展示"PM 自动拆解任务、委派给专门智能体、汇总结果"的编排思路，呼应技能「委派中心/循环」能力维度（01 未覆盖）。
3. **Skill Store 可视化**——展示技能商店的 GUI 形态（安装/搜索/过滤/启用），呼应 01 的 `skillhub_client`。

## 与本技能路线的契合点（已核实）

- `from run_agent import AIAgent` —— 进程内 Hermes Python Library，**符合本技能唯一路线**。
- 无 gateway、无端口 8642、无 API_SERVER_KEY —— 单一进程。
- pywebview 桌面窗口 + aiohttp 内嵌 server —— 与本技能「进程内直跑、不起第二个进程」原则一致。
- `hermes_cli.config.load_config` 加载模型/api_key —— 与 `HERMES_HOME` 配置对接。

## 使用与改编建议

- 直接可跑：`pip install pywebview aiohttp hermes-agent` → `python app.py`（pywebview 缺失时回退浏览器打开）。
- 改编为业务应用时，参考其「单文件 API server + 前端 index.html」的极简组织；把编排逻辑换成你自己的业务工具集即可。
- 注意：本项目 README 主打「多 Agent」宣传，实际 `app.py` 是单 `AIAgent` + 编排辅助逻辑；作为范本请以源码为准，勿照搬宣传口径。

## 为何 examples 不收录「走网关路线」的社区桌面项目

Electron / Node / Tauri / Web（如 wesight、hermes-workspace、pan-ui、Hermes-CN-Desktop、HermesOffice 等）若走「Hermes 网关 / 子进程」路线，与 examples/ 当前「进程内 Library 集成、可运行 Python 范本」定位不同；且克隆体积大（48–107MB）、无法作为 Python 代码范本复用。此类项目不落入本目录，避免稀释 examples 的「可运行 Python 范本」定位。

注意：Electron / React·Vue / Koa 等框架**本身**是合法的集成目标——只要以「Python 进程内 `AIAgent` + 本地桥接」方式接入（见 `references/04-rendering-frameworks.md` §7–§9），即属本技能覆盖范围，并非互斥。
