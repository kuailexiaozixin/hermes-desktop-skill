# Contributing to hermes-desktop 技能

感谢你愿意为这个技能贡献内容！本仓库既是灵犀技能，也是 Hermes Agent 桌面集成的技术手册。

## 可以贡献什么

- **新增/修正参考文档**（`references/`）：基于 Hermes 官方文档或源码的集成要点、API 用法
- **新增/改进示例**（`examples/`）：新的 Hermes 集成路线、业务工具接入范式
- **质量门禁脚本**（`scripts/`）：上游跟踪、API 签名核对、文档链接、冒烟测试
- **文档纠错**：术语、事实基线、链接、示例代码修正

## 铁律

1. **事实必须核实**：任何对 Hermes API / 行为的断言，需经官方文档 `hermes-llms-full.txt` 或 `hermes-agent==0.19.0` 源码核实，并在 `references/00-index.md` 登记事实基线。
2. **修改前备份**：改动 `SKILL.md` / `references/` 前先备份原文件。
3. **版本联动**：改动技能后 bump `SKILL.md` 的 `version`，并在 `CHANGELOG.md` 追加对应条目（`version` 必须与 CHANGELOG 最新一致）。
4. **过门禁**：提交前跑 `scripts/quality_check.py`（6 步）与 `scripts/check_skill_gate.py`，全绿再提交。
5. **上游漂移**：官方文档更新时运行 `scripts/track_upstream.py`，用 `--update-docs` 同步 `hermes-llms-full.txt` 并更新 `references/docs-baseline.json`。
6. **不提交敏感信息**：`.sesskey`、`.env`、`HERMES_HOME` 等一律被 `.gitignore` 排除，勿误提交。

## 提交规范

- 分支从 `main` 切出（`docs/xxx`、`feat/xxx`、`fix/xxx`）。
- 提交信息用简洁祈使句，如 `docs: 补充 18-self-improvement 学习循环 GUI 落地要点`。
- PR 描述改动动机、实现方式、验证结果（门禁日志）。

## 许可证

本仓库以 **MIT** 发布；贡献即表示同意你的内容以相同许可证授权。
