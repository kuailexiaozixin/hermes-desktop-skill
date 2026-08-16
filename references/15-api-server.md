# 15 · API Server 路线（把 AIAgent 暴露为 OpenAI 兼容服务）

> 依据：官方文档 `hermes-llms-full.txt`（API Server 专章 / Developer Guide / Open WebUI 集成）+ 源码
> `gateway/platforms/api_server.py`（5566 行，0.19.0 核实）+ 研究报告 `api-server-research/report-api-server.md`。
> **定位**：本文是「API Server / `/v1`」路线的**完整落地手册**（何时选 / 怎么落地 / 与进程内直跑对照自建）。
> 呼应入口：`02` §1 路径 D（何时/怎么/代价）、`04` §16（何时放开判据）、`10` §2.5（模块存在性）。

---

> **路线平等声明**：调用 Python Library 有 5 条**平等可选**技术路线——进程内直跑 / Hermes 网关 / spawn CLI / API Server / `/v1`——**无先后顺序，按需选用其一**。本文是其中「API Server / `/v1`」路线的完整落地手册；其余 4 条路线见 `01-library-api.md`（进程内直跑示例）/ `10-hermes-cli.md`（spawn CLI）/ `16-gateway-package.md`（Hermes 网关）。本文中「进程内直跑」仅作叙述对照，不代表该路线优先或推荐。

## 0. 定位：API Server 是什么

**API Server 是把 Hermes 的 `AIAgent`（带全部工具集）以「OpenAI 兼容 HTTP 服务」暴露出去的一层**。

- **它是 agent runtime，不是纯 LLM 代理**：每个请求在服务端创建一个 `AIAgent` 实例，工具调用（terminal / file / browser / MCP / web search）**在服务端所在主机执行**，返回最终结果。
- 它是 Hermes 三种对外协议之一（对比 ACP = IDE 的 JSON-RPC、TUI gateway = 自定义 host 的 JSON-RPC；API Server = HTTP + SSE 的 OpenAI 兼容，生态兼容性最强），三者驱动同一个 `AIAgent` 核心。
- **在技能中的位置**：5 条平等可选路线之一（与进程内直跑 / spawn CLI / Hermes 网关并列，无先后顺序）；当你需要"被外部 OpenAI 兼容客户端调用"时按本文选用。
- **实现所在**：`/v1` 端点实现在 `gateway/platforms/api_server.py`；`gateway` 包全量模块枚举见 `16-gateway-package.md`。

---

## 1. 何时选 API Server（判据）

出现以下任一**真实需求**才选 API Server；纯桌面单机 GUI 不应开：

| 需求 | 是否选 API Server |
| --- | --- |
| 外部 OpenAI 兼容前端（Open WebUI / LobeChat / LibreChat / ChatBox…）要当客户端调 | ✅ 选 |
| curl / CI / 其它编程语言要调用 Hermes（语言无关 / 非 Python 消费） | ✅ 选 |
| 接消息平台（Telegram/Slack/QQ/Discord…）或 cron 多投递 | ✅（网关形态，非纯 API Server） |
| 多客户端 / 远程 / 多用户 profile 隔离 | ✅ 选 |
| 需要 runs/jobs/sessions 等完整管理端点 | ✅ 选（网关 API Server，最全） |
| **纯桌面单机 GUI、仅进程内自调、无对外被调需求** | ❌ 不选（保持进程内，避免常驻服务/端口/认证/跨进程状态开销） |

呼应：`02` §1 路径 D、`04` §16「何时放开」判据。

---

## 2. 三种实现路径（衔接进程内直跑路线的关键）

| 路径 | 形态 | 说明 | 何时用 |
| --- | --- | --- | --- |
| **方式 A：官方网关** | 常驻服务 | `API_SERVER_ENABLED` + `hermes gateway`，功能最全（runs/jobs/sessions/approval），需常驻进程 + 端口 + Bearer + CORS | 要全功能管理端点、可接受常驻服务 |
| **方式 B：进程内自建薄层** | 单进程 | 自己 `from run_agent import AIAgent` + FastAPI/aiohttp 包一层 `/v1`，**保留单 EXE、无常驻服务** | 只想要"被 OpenAI 客户端调"，且不想丢单进程 |
| **方式 C：仅 dashboard** | 单进程 | 起 `hermes_cli.web_server`（FastAPI）得浏览器管理界面，**不含** `/v1/chat/completions` | 只要 Web 管理 UI |

> **推荐**：能进程内就**方式 B**（保留单 EXE，代价=自写桥接 + 认证）；要 runs/jobs/sessions 全端点才**方式 A**。
> 方式 B 的机制 = `api_server` adapter 本身（每请求建 `AIAgent`），只是把"网关持有运行时配置"换成"你自己持有"。

---

## 3. 官方方式：配置与启动（方式 A）

### 环境变量（0.19.0；`config.yaml` 暂不支持 API Server，用 env）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `API_SERVER_ENABLED` | `false` | 开/关 |
| `API_SERVER_PORT` | `8642` | HTTP 端口 |
| `API_SERVER_HOST` | `127.0.0.1` | 绑定地址（默认仅本机） |
| `API_SERVER_KEY` | 必填 | Bearer 密钥 |
| `API_SERVER_CORS_ORIGINS` | 无 | 允许的浏览器源，逗号分隔 |
| `API_SERVER_MODEL_NAME` | profile 名 | `/v1/models` 的 model id |

### 启动与验证

```bash
hermes config set API_SERVER_ENABLED true
hermes config set API_SERVER_KEY your-secret-key     # 落 $HERMES_HOME/.env
hermes gateway                                        # [API Server] listening on http://127.0.0.1:8642

curl -s http://127.0.0.1:8642/health                  # {"status":"ok",...}
curl -s -H "Authorization: Bearer your-secret-key" http://127.0.0.1:8642/v1/models
```

> ⚠️ **实测依赖（防假绿，0.19.0 隔离 venv 验证）**：
> ① `api_server` adapter 依赖 **aiohttp**——`hermes-agent[web]` **不含** aiohttp，缺它时网关日志报
> `API Server: aiohttp not installed` 且 api_server 不启动。需单独 `pip install aiohttp`。
> ② `API_SERVER_KEY` 必须 **≥16 字符**——源码强校验，短 key 会 `Refusing to start`（防猜测=远程代码执行），
> 用 `openssl rand -hex 32` 生成。
> ③ 上述 `/health` 200 + `/v1/models` 认证探测可用 `scripts/check_api_server.py` 复现。

### 多用户 profile 隔离

```bash
hermes profile create alice ; hermes profile create bob
# 各自 .env 写独立 API_SERVER_PORT / API_SERVER_KEY
cat >> $HERMES_HOME/profiles/alice/.env <<EOF
API_SERVER_ENABLED=true
API_SERVER_PORT=8643
API_SERVER_KEY=alice-secret
EOF
hermes -p alice gateway &  hermes -p bob gateway &
# /v1/models → alice / bob 两个 model id，各自隔离 config/记忆/技能
```

---

## 4. 端点能力全清单（源码核实 `gateway/platforms/api_server.py`）

| 端点 | 能力 |
| --- | --- |
| `POST /v1/chat/completions` | OpenAI Chat Completions；`stream:true` SSE；内联图（text+image_url，含 data: URL）；`hermes.tool.progress` 工具进度事件 |
| `POST /v1/responses` | OpenAI Responses API；`previous_response_id` 服务端状态化；`conversation` 命名会话；流式 `function_call`/`function_call_output` |
| `GET/DELETE /v1/responses/{id}` | 取回/删除已存 response |
| `POST /v1/runs` | 启动长会话 run，返回 `run_id` |
| `GET /v1/runs/{id}` | 轮询 run 状态（dashboard 无需长连接） |
| `GET /v1/runs/{id}/events` | SSE 流（工具进度/token/生命周期）；未消费缓冲 5 分钟过期 |
| `POST /v1/runs/{id}/approval` | 解决待人工审批 |
| `POST /v1/runs/{id}/stop` | 中断运行中回合 |
| `GET /v1/models` | 列 agent 为可用模型（前端发现必需） |
| `GET /v1/capabilities` | 机器可读能力标志（chat/responses/run_*/session_*）供外部 UI 探测 |
| `GET /v1/skills` · `/v1/toolsets` | 确定性枚举技能/工具集（含 tools 列表） |
| `GET /health` · `/v1/health` | 存活探针 `{"status":"ok"}` |
| `GET /health/detailed` | 就绪检查（config/state/model/disk/网关平台/活跃 run，不暴露敏感值） |
| `GET/POST /api/sessions*` | 会话 CRUD、messages、fork、chat、chat/stream（SSE） |
| `GET/POST/PATCH/DELETE /api/jobs*` | 定时任务 CRUD + pause/resume/run |

**状态与记忆作用域**：
- `X-Hermes-Session-Id`：延续会话（按 id 从 state.db 载历史；需认证才允许）。
- `X-Hermes-Session-Key`：跨 transcript 的长期记忆作用域（供 Honcho 等 memory provider 派生稳定 scope，≤256 字符）。

---

## 4bis. `/v1/runs` 异步审批协议（GUI 审批对接范式）

> `/v1/runs` 提供「运行中待人工审批」的原生异步能力：run 可长时间挂起、暂停在 `waiting_for_approval`，由外部（GUI / 用户）解析审批后继续。
> 这是「GUI 业务系统对接审批流程」的原生强项（源码核实 `gateway/platforms/api_server.py`）。

**状态机**：`queued → running → waiting_for_approval → done`

| 阶段 | 端点 | 说明 |
| --- | --- | --- |
| 启动 | `POST /v1/runs` | 立即返回 `run_id`（202），异步执行 |
| 监听 | `GET /v1/runs/{id}/events` | SSE 生命周期事件流（工具进度 / token / lifecycle） |
| 轮询 | `GET /v1/runs/{id}` | 非长连接轮询状态；**遇 `waiting_for_approval` 表示待人工审批** |
| 审批 | `POST /v1/runs/{id}/approval` | 提交审批决策（放行/驳回），run 继续 |
| 中断 | `POST /v1/runs/{id}/stop` | 终止运行中回合 |

**审批机制**：由「危险命令」驱动（`tools/approval.py`：`detect_dangerous_command` + `approval_callback` + plugin 钩子 `pre_approval_request`/`post_approval_response` + smart approval + 永久 allowlist）；外部服务依赖可用 delegation 子任务替代。

**GUI 业务对接范式（推荐）**：
1. 前端 `POST /v1/runs` 启动 → 订阅 `/events` SSE 流
2. 收到 `waiting_for_approval` 状态时，GUI 弹「危险操作审批」对话框（展示命令 + 参数）
3. 用户点「放行 / 驳回」→ `POST /v1/runs/{id}/approval` 提交决策
4. run 继续，事件流恢复，直至 `done`

> 审批决策在进程内亦可走 `tools.terminal_tool.set_approval_callback()`（CLI 交互）或 plugin 钩子（`pre_approval_request` / `post_approval_response`）；三者驱动同一 `AIAgent` 核心。

---

## 5. 认证与安全

- **Bearer 认证**：`Authorization: Bearer <API_SERVER_KEY>`；官方**必配**（含 loopback）——因为 API Server 能调 agent 工具集（含终端命令）。**key 必须 ≥16 字符**（源码强校验，短 key 拒绝启动，防猜测=远程代码执行），建议 `openssl rand -hex 32` 生成。
- **CORS**：默认关闭；浏览器直连需 `API_SERVER_CORS_ORIGINS` 白名单（preflight 缓存 10min，SSE 带 CORS 头）。
- **安全头**：`X-Content-Type-Options: nosniff`、`Referrer-Policy: no-referrer`。
- **沙箱告警（源码级）**：绑非本机地址 + `terminal.backend: local`（未沙箱）时打醒目告警——工具以宿主机身份执行；建议 `terminal.backend: docker` 或防火墙收紧端口。
- **并发上限**：`gateway.api_server.max_concurrent_runs` 防请求洪泛。

---

## 6. 客户端接入示例

```python
# OpenAI Python SDK（语言无关，任何语言发 HTTP 即可）
from openai import OpenAI
client = OpenAI(base_url="http://127.0.0.1:8642/v1", api_key="your-secret-key")
for chunk in client.chat.completions.create(
    model="hermes-agent",
    messages=[{"role":"user","content":"列出当前目录文件"}],
    stream=True,
):
    print(chunk.choices[0].delta.content or "", end="")
```

```bash
curl http://127.0.0.1:8642/v1/chat/completions \
  -H "Authorization: Bearer your-secret-key" -H "Content-Type: application/json" \
  -d '{"model":"hermes-agent","messages":[{"role":"user","content":"Hello!"}]}'
```

**Open WebUI（典型前端）**：`docker run -p 3000:8080 -e OPENAI_API_BASE_URL=http://host.docker.internal:8642/v1 -e OPENAI_API_KEY=your-secret-key ghcr.io/open-webui/open-webui:main`，然后在模型下拉选 agent（server-to-server，无需 CORS）。

---

## 7. 进程内自建薄层（方式 B，含代码骨架）【本技能特色】

在你的桌面进程里包一层 `/v1`，保留单进程、可随 EXE 交付，不引入常驻网关。

```python
# api_surface.py —— 在桌面应用内暴露 OpenAI 兼容端点（FastAPI）
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from run_agent import AIAgent          # 构造范式见 01 §3
import json

app = FastAPI()
# 认证：自行校验 Authorization: Bearer <你的 key>（勿用 Hermes API_SERVER_KEY 之外的裸鉴权）

@app.post("/v1/chat/completions")
async def chat(req: Request):
    body = await req.json()
    messages = body.get("messages", [])
    user_msg = next((m["content"] for m in reversed(messages) if m["role"]=="user"), "")
    stream = body.get("stream", False)

    agent = AIAgent(provider=..., model=...,      # 从你的配置解析（01 §3）
                    disabled_toolsets=["terminal"], quiet_mode=True)
    if not stream:
        out = agent.run_conversation(user_msg)
        return {"id":"chatcmpl-1","object":"chat.completion","model":"hermes-agent",
                "choices":[{"index":0,"message":{"role":"assistant","content":out},"finish_reason":"stop"}]}
    # stream: 用 02 §2 的 worker+queue 把 stream_callback 转 SSE（此处示意，落地见 02 §2）
    return StreamingResponse(_sse(agent, user_msg), media_type="text/event-stream")
```

**要点**：
- 单进程、随 EXE；代价=自写 HTTP 桥接 + 认证，且**无 runs/jobs/sessions 现成端点**（按需自补）。
- 每个请求建 `AIAgent`（stateless，同官方 adapter）；工具在桌面进程内执行。
- 复用 `01` §3 构造 + `02` §2 worker+queue 事件分发；安全护栏走 `02` §7。
- 对比官方方式 A：本方式保留单 EXE、无常驻服务，但不含全功能管理端点。

---

## 8. 与进程内直跑路线的对比与取舍

| 维度 | 进程内 | API Server（方式 B / A） |
| --- | --- | --- |
| 交付 | 单 EXE、双击即用 | B 仍单进程；A 需常驻服务/端口/认证 |
| 状态 | Python 对象直接调用 | 无状态 per-turn；会话需显式 ID（`X-Hermes-Session-Id`/`previous_response_id`） |
| 治理 | 进程内自建护栏，无网络暴露面 | 需 `API_SERVER_KEY` + CORS；工具在服务端执行（key 泄露=命令执行） |
| 部署 | 无需运维 | A 要守护常驻服务 |
| 序列化 | 无 | HTTP 开销 |
| 外部调用 | 仅本进程 | 任意语言/curl/CI/远程/多客户端 |

**本质代价**：放开 API Server 不是"起不起网关"，而是**引入 HTTP 桥接 + 跨进程/跨客户端状态语义**——这是"放开限制"辨析里"跨进程状态同步是真必然代价"的具体落点。

---

## 9. 边界与限制（要知道的坑）

- **response 存储上限 100 条**（SQLite，LRU）——`previous_response_id` 只保最近 100 轮。
- **不支持文件上传**：仅内联图片（text+image_url / data: URL）；`file`/`input_file`/`file_id` 及非图 data: URL 返回 `400 unsupported_content_type`。
- **`model` 字段装饰性**：请求 model 名只作路由/展示，真实模型服务端配置（可用 `model_routes` 做 per-client 路由）。
- **无状态 per-turn**：请求间不保留 transcript（除非显式 Session-Id / Responses）；不支持异步投递（terminal notify_on_complete / delegate background 不推送）。
- 开在公网/非本机 + local terminal 有安全风险，务必沙箱 + 强密钥。

---

## 10. 接入检查清单（API Server 形态）

- ✅ 已选对方式（A 官方网关 / B 进程内自建 / C 仅 dashboard），并在 02 §1 路径 D 明确"为何放开"。
- ✅ `API_SERVER_KEY` 已配且非空（方式 A），或进程内自建已实现等价鉴权（方式 B）。
- ✅ 默认仅绑 `127.0.0.1`；绑非本机时 `terminal.backend` 已沙箱（docker/remote）。
- ✅ `/health` 200（方式 A）。
- ✅ `/v1/models` 带 Bearer 可列出 model（方式 A）。
- ✅ 用 OpenAI SDK / curl 各跑通一次 `/v1/chat/completions`（非流式 + 流式各一）。
- ✅ 若需会话延续，已验证 `X-Hermes-Session-Id` / `previous_response_id` 行为。
- ✅ 与进程内直跑路线对比后确认"此需求确实需要 API Server"（非为开而开）。
