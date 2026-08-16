# Hermes Desktop 技能

> 面向「桌面应用中集成 Hermes Agent」的完整技能 —— 进程内 Library 集成 + FastHTML/pywebview 完整参考实现，附官方文档权威事实来源与自进化理念主题。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skill: hermes-desktop](https://img.shields.io/badge/Skill-hermes--desktop-blue)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](examples/01-hermes-desktop/pyproject.toml)

这是一个**灵犀（WPS AI 助手）技能**，也是一份可独立阅读的 **Hermes Agent 桌面集成技术手册**。它把「在桌面应用里集成 Hermes Agent」这件事做成了一整套可复用的参考实现与权威知识库。

## 这是什么

- **权威事实来源**：内置 Hermes 官方文档全文 `hermes-llms-full.txt`（随官网漂移更新），所有参考文档基于 `hermes-agent==0.19.0` 源码逐条内省核实。
- **18 篇参考文档**（`references/`）：从 Library API、集成内核、工具/能力层，到打包、质量门禁、端到端验证、自进化理念，覆盖集成全生命周期。
- **3 个可运行示例**（`examples/`）：通用桌面底座 / 多智能体桌面客户端 / 官方 WebUI 三路线，均自包含、可复制、可二次开发。
- **质量门禁脚本**（`scripts/`）：上游漂移跟踪、API 签名核对、文档链接、技能门禁、端到端冒烟。

## 快速开始

把本技能安装为灵犀技能后，直接对话触发即可；或按示例独立运行：

```bash
# 参考实现 01 —— 通用桌面底座（功能最全）
cd examples/01-hermes-desktop
pip install -r requirements.txt
python main.py            # 服务模式 → http://127.0.0.1:5001
# 或 python launcher.py  # pywebview 桌面窗口
```

三个示例的完整介绍见 [examples/README.md](examples/README.md)。

## 目录结构

```
hermes-desktop-skill/
├── SKILL.md                 # 技能主入口（MOC / 能力地图 / 权威事实来源 / 门禁）
├── CHANGELOG.md             # 技能版本历史（当前 1.7.25）
├── hermes-llms-full.txt     # Hermes 官方文档全文（HARD-GATE，随上游漂移更新）
├── references/              # 18 篇参考文档 + api-reference 自动生成 API 参考
├── examples/                # 3 个可运行参考实现（01 通用底座 / 02 多智能体 / 03 官方WebUI）
├── scripts/                 # 质量门禁与上游跟踪脚本
├── docs/                    # 词汇表 / 排障 / 交付清单
└── templates/               # 模板
```

## 主题导航（references/）

| 主题 | 文档 |
|---|---|
| 核心 API 与库结构 | `01-library-api` / `10-hermes-cli` / `12-tools-modules` / `13-agent-modules` / `16-gateway-package` |
| 业务整合与路线选型 | `02-integration-core` / `15-api-server` |
| GUI 集成与能力 | `03/04/08/11/14` |
| 环境、打包与质量 | `05-install-and-env` / `06-packaging` / `07-quality-gates` / `09-integration-e2e` |
| **自进化 / 学习循环理念** | `18-self-improvement` |

## 设计理念

Hermes Agent 的根性是**解决「AI 失忆症」**——通过内置学习循环从经验沉淀记忆与技能、consent-aware 写审批、运行越久越强。详见 [references/18-self-improvement.md](references/18-self-improvement.md) 与 [设计理念分析](docs/)。

## 许可证

[MIT](LICENSE) © 2026 kuailexiaozixin。各示例独立 MIT 授权（见各目录 `LICENSE`）。
