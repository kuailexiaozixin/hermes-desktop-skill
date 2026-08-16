# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 语义化版本规范。

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
