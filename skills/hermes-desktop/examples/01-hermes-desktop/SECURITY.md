# Security Policy

## Supported Versions

本项目当前处于早期开发阶段，仅维护最新版本（`main` 分支）。建议始终使用最新提交或最新 Release。

| Version | Supported |
|---------|-----------|
| main / latest release | ✅ |
| older releases | ❌ |

## Reporting a Vulnerability

请**不要**通过公开 issue 报告安全漏洞。请通过以下任一渠道私密报告：

- 在仓库创建 **Private vulnerability report**（GitHub 支持，推荐）
- 通过仓库 issues 页面选择「Report a vulnerability」入口

报告时请包含：

- 漏洞类型与影响的模块
- 复现步骤与最小示例
- 影响范围与潜在危害
- 修复建议（可选）

## Security Notes for This Project

本项目是**本地单进程运行的桌面示例**，不含网络鉴权边界，请只在你信任的环境中使用：

- **API 密钥**：模型密钥存放在 `HERMES_HOME/config.yaml` / `.env`（已被 `.gitignore` 忽略），**不要**提交到仓库。
- **MCP 服务器**：应用可将工具暴露给连接的客户端，请在可信环境中使用。
- **审批机制**：危险命令通过 `/api/approve` 弹窗确认，纯进程内删除，无外部边界。

我们会在收到报告后尽快响应，并在修复后发布安全更新。
