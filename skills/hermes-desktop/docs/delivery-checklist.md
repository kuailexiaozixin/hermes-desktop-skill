# 交付验收清单（Delivery Checklist）

> 打包完成后、交付给用户前，逐项确认（对应工作流 ⑦「打包交付」）。
> 机器可验的项由 `scripts/release_gate.py` 覆盖；带 ✍️ 的项为人工确认项。

---

## A. 机器门禁（release_gate 全自动）

- [ ] `python scripts/release_gate.py` 全绿（exit 0）
  - [ ] `quality_check`：py_compile + 结构门禁 + 离线桥接测试 12/12 + 源码签名漂移无破坏性变更
  - [ ] `check_endpoints`：前端→后端路由链路无未覆盖引用（运行时 404 隐患）
  - [ ] `check_js_modules`：前端 ES 模块强制校验（仅「禁用 HTMX/Pico 的原生 ES 模块前端」示例；无 node/无 JS 前端自动 SKIP，不阻塞纯 Python / Tkinter / HTMX·Pico 示例）；有 JS 前端时必须 SYNTAX-OK + ALL IMPORTS RESOLVED OK
  - [ ] `smoke_test_web`：网页无头冒烟，`GET /` 含关键 DOM id + `/healthz` 200（已把 B 档 DOM id 检查自动化）
  - [ ] CI 建议项 `verify_imports` / `check_refs`：仅告警不阻塞（失败也建议修）

## B. 真实运行（✍️ 人工，最不能省）

- [ ] **启动 `启动.bat` 双击启动**，无需终端、无需额外配置
- [ ] 完成**一次真实 LLM 往返**：流式逐字可见 + 至少一次工具/推理事件出现
  - 🔴 只测 HTTP 200 是假绿——Library 导入失败时 Web 框架照样 200
- [ ] 关键 DOM id 渲染正常（已由 `smoke_test_web.py` 自动断言，这里作人工复核）：
  - [ ] `convSearch`（会话搜索框）
  - [ ] `usageChip` / `side-foot` 用量入口
  - [ ] `analyticsBody`（用量分析面板，若启用）
  - [ ] 首页标题含 `Hermes Desktop`
- [ ] 窗口关闭即退出（无残留进程）

## C. 产物与文档

- [ ] `dist/*.exe` 为 `--onefile` 单文件（无 `_internal/` 目录）
- [ ] `.hermes_data` 运行数据写入 `<exe>/hermes_data`，用户目录未被污染
- [ ] `README.md` 双用途（用户说明书 + LLM 克隆说明书）齐全：启动方式、API Key 配置、能力清单、已知限制
- [ ] 若接了自定义工具 / toolset：已在 README 写明白名单与 `disabled_toolsets` 策略

## D. 版本与漂移（若改了技能本体）

- [ ] `scripts/track_upstream.py`：**[② 文档 md5 ✅] 且 [③ 源码签名 ✅]**（硬判据）；[① PyPI 版本] 允许显示 0.19.0 漂移（基线锁 0.19.0，已知非缺陷，见 CHANGELOG）
- [ ] `scripts/check_api_signature.py`：OK:true（无 REMOVED/ADDED/DEFAULT_CHANGED）
- [ ] 基线表 / `scripts/api-baseline.json` / `CHANGELOG.md` 已随版本更新
- [ ] `version` 号已 +0.1.0（见 SKILL.md _frontmatter）

---

## 反复核实（万无一失）循环

技能内容（API 签名 / 版本基线 / 路径引用 / 门禁脚本）**任何改动**后，必须重跑：

```bash
python scripts/track_upstream.py     # 上游漂移
python scripts/check_api_signature.py # 源码签名
python scripts/check_skill_gate.py    # 技能结构
python scripts/quality_check.py       # 全量门禁
python scripts/check_endpoints.py     # 路由链路
python scripts/check_js_modules.py    # 前端 ES 模块强制校验（原生 ES 模块前端示例；否则 SKIP）
python scripts/smoke_test_web.py      # 网页无头冒烟（结构级）
python scripts/release_gate.py        # 统一发布门禁（串联以上 + 2 CI 建议项）
```

**核心断言全绿才算落地**：`track_upstream` 只要 [② 文档 md5]+[③ 源码签名] ✅ 即视为通过（[①] PyPI 0.19.0 漂移为已知非缺陷）；其余脚本必须 exit 0。任一项硬失败即阻断，先修再交付。
