# Contributing to Hermes Desktop (Example 01)

首先感谢你愿意为这个项目贡献代码！以下是参与开发的约定，请花一分钟阅读。

## 开发流程

本项目是「Hermes Desktop 通用底座」的完整参考实现，采用**进程内集成 Hermes Python Library** 的范式。欢迎提交：

- **Bug 修复**：任何功能的缺陷或异常
- **新集成示例**：在 `app_tools/` 中新增业务工具接入示例
- **文档改进**：README、docs/、注释、示例笔记
- **渠道连接器**：`channels/` 中新增 IM 平台桥接

## 环境准备

```bash
pip install -r requirements.txt
python main.py          # 纯服务模式，http://127.0.0.1:5001
# 或
python launcher.py      # pywebview 桌面窗口模式
```

需要先配置模型（`HERMES_API_KEY` 或 `HERMES_HOME/config.yaml`），见 `.env.example` 与 README。

## 提交规范

1. **分支**：从 `main` 切出功能分支，命名如 `feat/xxx`、`fix/xxx`。
2. **提交信息**：用简洁的祈使句，如 `fix: 修复多会话切换时上下文丢失`。
3. **测试**：新增/修改功能请尽量补充或更新 `tests/` 下的测试，确保 `python -m pytest tests/` 通过。
4. **语法**：提交前运行 `python -m py_compile *.py` 与 `python -c "import main"` 确认无编译错误。
5. **Pull Request**：描述改动动机、实现方式、验证结果；如涉及行为变化请更新 README。

## 代码风格

- 保持与现有代码一致的风格（`snake_case`、类型注解、docstring）。
- 业务逻辑与 Hermes 内核解耦：新增工具注册到 `app_tools/`，不侵入 `agent_runtime.py` 内核。
- 不把敏感信息（API Key、token）提交到仓库——一律走 `.env` / `HERMES_HOME/config.yaml`（已被 `.gitignore` 忽略）。

## 许可证

本项目以 **MIT 许可证** 发布。贡献即表示你同意你的代码以相同许可证授权。
