# docs/ 文档目录

> Hermes Desktop 通用底座（`01-hermes-desktop`）的文档组织结构。

## 目录结构

```
docs/
├── README.md                ← 本文档（目录结构说明）
├── mcp-server.md            ← MCP 服务器能力说明（如何让外部程序连接本应用）
└── integration-notes/       ← 集成笔记（安装 / 示例 / 各功能接入的实操笔记）
    ├── 02-route-selection-examples.md
    ├── 08-office-examples.md
    ├── 09-session-examples.md
    ├── 10-install-examples.md
    ├── 11-packaging-examples.md
    ├── 14-antipatterns-examples.md
    ├── 18-goals-examples.md
    ├── 19-snapshot-examples.md
    ├── 20-moa-examples.md
    ├── 21-projects-examples.md
    ├── 22-bundles-examples.md
    ├── 23-security-audit-examples.md
    ├── 24-blueprint-examples.md
    ├── 25-batch-examples.md
    ├── 26-journey-examples.md
    ├── 27-backup-examples.md
    ├── 28-profiles-examples.md
    ├── 29-curator-examples.md
    └── 30-routing-examples.md
```

## 文档定位

| 你想了解什么？ | 看哪里 |
|---------------|--------|
| 如何让外部程序（Claude Code / Cursor 等）连接本应用 | `mcp-server.md` |
| 安装与依赖 | `integration-notes/10-install-examples.md` |
| 打包成桌面 EXE | `integration-notes/11-packaging-examples.md` |
| 各功能（会话 / 快照 / MOA / 项目 / 批量 / 路由…）接入笔记 | `integration-notes/` 对应文件 |

## 分类体系

- **能力说明**（`mcp-server.md`）：正式的功能说明文档
- **集成笔记**（`integration-notes/`）：各功能接入与示例的实操笔记

> 早期内部调研、审计与批判文档（对竞品的对比研究）不属于开源文档体系，已不随本仓库发布。
