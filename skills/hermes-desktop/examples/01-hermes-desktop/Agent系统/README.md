# Hermes Desktop · AI Agent 桌面助手

> 一个功能完备的 **AI Agent 桌面应用** —— 基于 [Hermes](https://github.com/kuailexiaozixin/hermes-agent) 与 FastHTML 服务端渲染 + pywebview 原生窗口，把桌面 AI 助手的通用能力（多会话流式对话、工具调用、技能市场、MCP、知识库、记忆、定时任务等）整合为开箱即用的桌面程序。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](pyproject.toml)
[![CI](https://github.com/kuailexiaozixin/hermes-desktop/actions/workflows/ci.yml/badge.svg)](https://github.com/kuailexiaozixin/hermes-desktop/actions/workflows/ci.yml)

[English](README.en.md) · [文档](docs/) · [贡献指南](CONTRIBUTING.md) · [安全](SECURITY.md)

---

## 它是什么

**Hermes Desktop** 是一个可直接运行的 AI Agent 桌面助手，提供完整的桌面 AI 体验：

- **多会话 + 流式对话**：逐字 SSE 输出，服务端持久化，支持新建/切换/重命名/置顶/删除
- **模型中心**：36 家厂商预设 + 自定义 + 密钥管理
- **工具 / 技能 / MCP 中心**：内置工具集、技能 CRUD、MCP 增删启停
- **大一统技能市场**：聚合 SkillHub / skills.sh / clawhub / lobehub / browse-sh / 官方 / GitHub / Claude 共 8 个来源
- **LLM Wiki 知识库**：三层互联 + 反向链接 + 自动索引 + 图谱
- **记忆与上下文管理**：provider 切换 + 向量检索 + 分层；`context.engine` 选择 + 压缩 + token 跟踪
- **循环 / 委派 / 定时任务**：8 内置循环 + 目标拆分给子智能体 + cron 自然语言调度
- **IM 渠道桥接**：微信/企微/钉钉/飞书/QQ/Slack/Discord/Telegram/Webhook + 二维码登录
- **审批闭环**：危险命令弹窗确认，纯进程内删除
- 纯本地运行、离线可用，可打包为单文件 Windows EXE，双击即用

> 桌面体验对标官方 Hermes Desktop：思考折叠区、工具时间线、产物抽屉等一应俱全。

## ✨ 功能亮点

| 能力 | 说明 |
| --- | --- |
| 多会话 + 流式对话 | 逐字 SSE 输出，服务端持久化，支持新建/切换/重命名/置顶/删除 |
| 思考折叠区 + 工具时间线 | `<thinking>` 分流 + 工具开始/完成/结果卡片 |
| 模型中心 | 36 家厂商预设 + 自定义 + 密钥管理 |
| 工具 / 技能 / MCP 中心 | 工具集开关、技能 CRUD、MCP 增删启停 |
| **大一统技能市场** | 聚合 8 个来源（SkillHub / skills.sh / clawhub / lobehub / browse-sh / 官方 / GitHub / Claude） |
| **MCP 商店** | LobeHub 生态在线浏览 / 搜索 / 安装 / 卸载 |
| **LLM Wiki 知识库** | 三层互联 + 反向链接 + 自动索引 + 图谱 |
| **补充功能 × 13** | Goals / 快照 / MOA / 备份 / 项目 / 策展 / 批量 / 旅程 / 路由等 |
| **IM 渠道桥接** | 微信/企微/钉钉/飞书/QQ/Slack/Discord/Telegram/Webhook + 二维码登录 |
| 循环 / 委派 / 定时任务 | 8 内置循环 + 目标拆分给子智能体 + cron 自然语言调度 |
| 审批闭环 | 危险命令弹窗确认，纯进程内删除 |
| Token 用量 + 分析面板 | 会话 token 追踪 + 近 30 日趋势 + 按模型分布 |
| **上下文管理** | `context.engine` 选择 + 压缩状态 + token 跟踪 |
| **记忆管理** | provider 切换 + 向量检索 + 分层查看 |
| 主题切换 / 图片附件 | 浅深双主题 / 粘贴上传图片由视觉工具查看 |
| 桌面打包 | pywebview 原生窗口 + PyInstaller 单文件 EXE |

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置模型（二选一）
#    a) 环境变量
set HERMES_API_KEY=sk-...
#    b) 或 HERMES_HOME/config.yaml 中配置 provider（参考 .env.example）

# 3. 启动
python main.py           # 服务模式 → 打开 http://127.0.0.1:5001
# 或
python launcher.py       # 桌面窗口模式（pywebview 原生窗口）
```

发一条消息 → 应看到**逐字流式输出** + **工具时间线卡片** + **思考折叠区**；打开设置可配置模型、工具、技能、MCP 等。

## 📦 打包成桌面 EXE

```bash
python build.py          # PyInstaller 单文件 EXE（外置隔离 venv + 完整 hidden-import + HERMES_HOME 处理）
```

## 🗂 目录结构

```
├── main.py                  # FastHTML 路由层：页面外壳 + /api/* 端点 + SSE 桥接
├── agent_runtime.py         # Agent 运行时：build_agent / stream_agent_chat / 审批
├── hermes_config.py         # 配置面：模型 / 技能 / MCP / 定时任务 / HERMES_HOME 播种
├── hermes_features.py       # 补充功能后端（13 项）
├── unified_skills_client.py # 大一统技能市场（聚合 8 源）
├── wiki_engine.py           # LLM Wiki 三层互联知识库
├── sessions.py              # 服务端多会话持久化
├── memory_providers.py      # 记忆增强（provider 切换 / 向量检索 / 分层）
├── context_provider.py      # 上下文管理（引擎选择 / 压缩状态 / token 跟踪）
├── frameworks/              # 循环 / 委派 / 指令框架
├── routes/                  # FastHTML 路由子包（chat / skills / features / misc / ...）
├── channels/                # IM 渠道桥接（10 个连接器）
├── app_tools/               # 工具扩展点（默认含演示工具）
├── static/                  # 前端 UI（app.css / app.js / 各面板）
├── docs/                    # 文档（mcp-server.md / integration-notes/）
├── tests/                   # 测试套件（离线桥接 / 回归）
├── bundled_skills/          # 出厂演示技能
├── build.py                 # PyInstaller 打包
├── launcher.py              # pywebview 桌面壳
└── 启动.bat                 # Windows 一键启动
```

## ✅ 验证

```bash
python -m py_compile *.py          # 语法编译
python -c "import main"            # 离线可导入
python -m pytest tests/            # 运行测试（含离线桥接）
```

启动后 `curl /healthz`、`/api/conversations`、`/api/models` 均返回 200。

## 🤝 贡献

欢迎提交 Bug 修复、功能改进、文档改进。请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [行为准则](CODE_OF_CONDUCT.md)。发现安全漏洞请按 [SECURITY.md](SECURITY.md) 私密报告。

## 📄 许可证

[MIT](LICENSE) © 2026 kuailexiaozixin
