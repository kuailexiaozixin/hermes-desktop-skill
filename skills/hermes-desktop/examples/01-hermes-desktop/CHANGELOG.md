# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 语义化版本规范。

## [Unreleased]

### 上下文文件（Context Files）原生支持对齐
- **修正**：原生上下文文件此前被错误绑在「🔁 循环」目标循环开关上（`skip_context_files=not _goal_on`，默认关），
  普通对话不加载 `.hermes.md`/`AGENTS.md`/`CLAUDE.md`/`.cursorrules`。现已与 goal loop 解耦，
  `agent.context_files` 默认 `True`，普通对话即加载项目上下文。
- **修正**：SOUL 人格此前 `load_soul_identity` 默认 `False`，Soul 面板写入的 `HERMES_HOME/SOUL.md` 不被 agent 读取、
  形同虚设。`agent.soul_enabled` 默认 `True`，面板改动现在真实生效。
- **增强**：agent 工作目录指向会话「绑定文件夹」（原生发现扫用户项目），经 `TERMINAL_CWD` 传递；无绑定时回退启动目录且不残留，
  使 `build_context_files_prompt(cwd=resolve_context_cwd())` 真正作用于用户代码，而非应用启动目录（后者可能落在
  hermes 安装树内被库守卫跳过）。
- **新增**：`GET /api/context-files?dir=<path>` 可见性端点，报告指定/当前工作目录发现的原生上下文文件与 SOUL.md 状态（供调试与 QA）。
- **保留**：自定义「会话固定文件夹上下文」（整目录文本注入）作为互补能力不变；原生上下文文件自带 prompt-injection 安全扫描与截断。
- **测试**：新增 `tests/test_context_files_native.py`（离线，example01 venv 运行），验证默认开启、工作目录命中、无串味。

## [1.0.0] - 2026-08-15

### 首次开源发布

`Hermes Desktop 通用底座`（example 01）的初始开源版本——一个在桌面应用中**进程内集成 Hermes Python Library** 的完整参考实现，对标官方 Hermes Desktop 桌面体验，功能完整迁移、业务彻底解耦。

**核心能力：**

- 多会话 + 流式对话（逐字 SSE）+ 思考折叠区 + 工具时间线卡片
- 模型中心（36 家厂商预设 + 自定义 + 密钥管理）
- 工具/技能/MCP 中心 + 大一统技能市场（聚合 8 源）+ MCP 商店
- LLM Wiki 三层互联知识库 + 13 项补充功能（Goals / 快照 / MOA / 备份 / 项目 / 策展等）
- IM 渠道桥接（微信/企微/钉钉/飞书/QQ/Slack/Discord/Telegram/Webhook）
- 循环中心 / 委派中心 / 定时任务中心 / 审批闭环
- Token 用量追踪 + 用量分析面板
- 上下文管理面板（context.engine 选择 + 压缩状态 + token 跟踪）
- 记忆管理（provider 切换 + 向量检索 + 分层查看）
- pywebview 桌面壳 + PyInstaller 单文件打包
