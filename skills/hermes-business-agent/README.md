# Hermes Business Agent 技能

> 用途：把 Agent 接进真实业务流程，或从零开发 Agent 驱动的业务系统。形态不限——桌面 EXE、本地服务、常驻后端都可以；本技能给出的是一条"定业务 → 定形态 → 跑通内核 → 接界面 → 赋业务 → 立闸门 → 取证 → 交付"的工作流，加一整套经源码核实的参考实现与事实库。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skill: hermes-business-agent](https://img.shields.io/badge/Skill-hermes--business--agent-blue)](#)
[![Python](https://img.shields.io/badge/Python-3.11%20%E2%80%93%203.13-blue)](references/05-install-and-env.md)

这是一份可独立阅读的 Hermes Agent 业务集成技能与技术手册。版本号只记在一处：`SKILL.md` 的 frontmatter 与 `CHANGELOG.md` 顶部，本文不复述。

## 这是什么

- **一条工作流主线**（`SKILL.md`）：〔入场检查〕+ 第 ①–⑧ 步 + 〔回路〕。每步有输入、动作、产出与出口判据，出口不过就进调试闭环。
- **权威事实来源**：内置 Hermes 官方文档全文 `hermes-llms-full.txt`（随官网漂移更新），所有参考文档基于 `hermes-agent` 的锁定基线版本逐条源码内省核实（基线号见 `scripts/api-baseline.json`）。
- **22 篇参考文档**（`references/00`–`21`）：Library API、集成路线、工具与能力层、宿主框架、打包、质量门禁、端到端验证、业务建模与运营降级。逐篇反查索引在 `references/00-index.md` §3。
- **3 个可运行示例**（`examples/`）：三系统底座 / 多智能体桌面客户端 / 官方 WebUI 三路线，见 `examples/README.md`。
- **质量门禁脚本**（`scripts/`）：上游漂移跟踪、API 签名核对、技能结构、文档链接、端到端冒烟、发布总闸。

## 快速开始

装本技能后直接对话触发即可（`SKILL.md` 会从〔入场检查〕开始引导）。要跑参考实现：

```bash
# 示例 01（三系统底座）：Agent系统/ 是 git submodule，先拉底座
git submodule update --init --recursive
cd examples/01-hermes-desktop/连接系统 && python main.py     # 融合模式 → http://127.0.0.1:8800/dashboard
# 或 cd examples/01-hermes-desktop/业务系统 && python app.py  # 纯业务、无 Agent → :8810/dashboard
```

## 目录结构

```
hermes-business-agent-skill/
├── SKILL.md                 # 唯一工作流主线（入场检查 + 八步 + 回路）与 frontmatter 版本号
├── CHANGELOG.md             # 版本历史
├── hermes-llms-full.txt     # Hermes 官方文档全文（语义权威源）
├── references/              # 22 篇参考文档 + api-reference/（自动生成 API 参考）
├── examples/                # 3 个参考实现（01 三系统底座 / 02 多智能体 / 03 官方 WebUI）
├── scripts/                 # 质量门禁与上游跟踪脚本
├── docs/                    # glossary.md 术语表 · troubleshooting.md 排障沉淀 · delivery-checklist.md 交付清单
└── templates/               # 最小骨架模板
```

## 该读哪一篇

主题导航与「第 N 步该读哪几篇」的反查索引只有一处：
[`references/00-index.md`](references/00-index.md) §3（按主线步骤）与 §1（按官方文档检索）。本文不重复列一遍——那份表会随文档增删漂移，这张表就不会。

## 设计理念

Hermes Agent 的根性是解决「AI 失忆症」：内置学习循环从经验沉淀记忆与技能、consent-aware 的写审批、运行越久越强。
机制基线与其对集成的含义见 [`references/00-index.md`](references/00-index.md) §2 与 §4。

## 许可证

[MIT](LICENSE) © 2026 kuailexiaozixin。各示例独立 MIT 授权（见各目录 `LICENSE`）。
