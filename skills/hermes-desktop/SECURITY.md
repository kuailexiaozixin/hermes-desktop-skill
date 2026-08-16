# Security Policy

## Supported Versions

本项目为文档/技能仓库，维护最新版本（`main`）与最新 Release。

| Version | Supported |
|---------|-----------|
| main / latest release | ✅ |
| older releases | ❌ |

## Reporting a Vulnerability

请**不要**通过公开 issue 报告安全漏洞。请通过仓库的 **Private vulnerability report** 私密报告。

报告时请包含：漏洞类型 / 影响模块 / 复现步骤 / 影响范围 / 修复建议（可选）。

## 本项目安全注意事项

本仓库是 **Hermes Agent 桌面集成技能与参考实现**。参考实现（`examples/`）是本地单进程运行的桌面示例：

- **API 密钥**：模型密钥存放于 `HERMES_HOME/config.yaml` / `.env`（均被 `.gitignore` 忽略），**不要**提交到仓库。
- **会话密钥**：`.sesskey` 属敏感文件，已被 `.gitignore` 排除，切勿上传。
- **MCP / 审批**：参考实现可将工具暴露给连接的客户端，危险命令经弹窗审批，请在可信环境使用。

我们会在收到报告后尽快响应，并在修复后发布安全更新。
