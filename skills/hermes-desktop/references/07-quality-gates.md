# 07 · 反模式红线、门禁与工作流

> 进程内 Library 路线的质量护栏。任何新增能力/改动**先过 §1 红线**，再用 §2 门禁验证。

---

## 1. 反模式红线（⛔ 触线即路线错误）<a id="antipatterns"></a>

| # | 红线 | 为什么 |
| --- | --- | --- |
| R1 | **进程内直跑路线下**起 Hermes **网关** 或 spawn `hermes` **CLI 子进程** | 进程内直跑路线默认不含网关/子进程；若选用跨进程路线则按对应路线评估，不在此列（选型与落地见 references/02-integration-core.md §2 路径 D） |
| R2 | **进程内形态下**连 `127.0.0.1:8642` / 配 `API_SERVER_KEY` / 配 CORS | 进程内形态默认无网关/公网服务端；若放开为 API Server /`/v1` 形态则按需启用 |
| R3 | **进程内形态下**用 **Node / Electron** 包 Hermes | 进程内单文件 Python EXE 默认无 Node 运行时（browser 工具的 Node 是 Hermes 托管、非应用层）；放开为网关/Electron 形态则另行评估 |
| R4 | 硬编码 `enabled_toolsets=["file"]` 之类减法反向写法 | 会砍掉 browser/记忆/联网等能力，功能退化；坚持 `enabled=None` + `disabled` 减法（见 `01` §3.2） |
| R5 | 进程内形态启用 `terminal` 工具集却不自建审批 | 网关的「危险命令审批分类器」无触发源；审批须自建工具层（见 `03` §2） |
| R6 | 宣称「已支持子代理委派卡片 / delegation 事件」 | `event_callback` 透传委派**未经实测**；先实测，否则静默不显示（`01` §4.1） |
| R7 | 宣称「真实账单成本」 | 进程内无网关计费，`get_credits_*` 为**估算**（见 `01` §5） |
| R8 | 冻结态重定向 `HERMES_HOME` | 恒为 `<exe>/hermes_data`，不可改（`05` §3） |
| R9 | 用 `--onedir` / `--collect-submodules tools` 打包 | 体积爆炸/OOM；必须 `--onefile` + 逐个 hidden-import（`06` §1–2） |
| R10 | 用 `os.execv` 重入解释器 | Windows CRT 不加引号，空格路径崩；用 `subprocess.call`+`sys.exit`（`06` §3） |
| R11 | 触碰出厂 `.hermes_data` 不备份 | 必须 备份→变更→还原→md5 校验；不杀用户运行中的 EXE |
| R12 | 在技能内容文件写机器专属绝对路径 / 兄弟技能名 / 外部业务项目名 | 自包含铁律：须可单独外发、跨机器复现 |

---

<a id="gates"></a>
## 2. 门禁脚本（`scripts/`）

| 脚本 | 作用 | 何时跑 |
| --- | --- | --- |
| `check_skill_gate.py` | 技能结构/引用门禁（质量总闸） | 每次改动后 |
| `check_api_signature.py` | 比对 `api-baseline.json`（0.19.0 签名基线），发现 Library API 漂移 | 升级 hermes-agent 后 |
| `check_js_modules.py` | 前端 30 模块完整性 | 改前端后 |
| `quality_check.py` | 代码质量（py_compile + 导入测试） | 改 `.py` 后（门禁：改 .py → py_compile + 导入测试） |
| `check_endpoints.py` | 前端→后端路由链路校验（捕获运行时 404；递归扫描示例目录全部 `.py`，含 `routes/` 包） | 改前端/打包后 |
| `smoke_test_web.py` | Web UI 冒烟 | 打包后 |
| `release_gate.py` | 发布总闸：6 硬门禁（track_upstream→quality_check→check_endpoints→smoke_test_web→check_js_modules→version 一致性）+ 2 CI 建议项 | 发版前 |
| `track_upstream.py` / `probe_library.py` | 上游变化跟踪（doc/src 签名漂移看守） | 定期/升级前 |

<a id="drift"></a>**上游漂移跟踪**：能力/签名漂移由 `check_api_signature.py`（比对 `api-baseline.json`，0.19.0 基线）+ `track_upstream.py`（含第四线：`references/api-reference/` 记录的版本 vs 本地已装，`--regenerate-apiref` 可自动重生成）/ `probe_library.py` 看守；升级 hermes-agent 后先跑 `check_api_signature.py`，有漂移先更新本文档与基线（见 §4 步骤 4）。

**改 .py 门禁**：`py_compile` + 导入测试。**改 .js 门禁**：`node --check`。
**改 .py 后打包门禁**：启动 EXE 验证业务健康端点。

---

## 3. 运行数据保护与启动自检

- **出厂数据保护**（R11）：`HERMES_HOME` 冻结态为 `<exe>/hermes_data`；变更前备份，变更后
  md5 校验还原；绝不 `rmtree(release/)`；不杀用户运行中的 EXE。
- **启动自检**（进程内形态下替代网关 `/health`）：进程内形态不起 HTTP 服务也能自检。旗舰示例
  `runtime_ready()` 模式：

```python
def runtime_ready() -> dict:
    import importlib.metadata as md
    info = {"importable": False, "version": None, "callbacks_ok": False, "tools_registered": False}
    info["version"] = md.version("hermes-agent")          # 应为 0.19.0
    from run_agent import AIAgent
    info["importable"] = True
    params = inspect.signature(AIAgent.__init__).parameters
    info["callbacks_ok"] = all(k in params for k in
        ("tool_start_callback","tool_complete_callback","reasoning_callback",
         "event_callback")) and "stream_callback" in inspect.signature(AIAgent.run_conversation).parameters
    info["tools_registered"] = bool(register_pure_python_tools().get("ok"))
    return info
```

---

> 完整的「跑通一个集成」端到端 walkthrough（含 Hermes 作为 Agent 的测试特殊性、专项断言清单 A1–A9、
> 反模式 T1–T7）见 `09-integration-e2e.md`。本文 §2/§4 是护栏与门禁，该章是具体的跑通步骤。

---

## 4. 推荐工作流

1. 写/改代码 → 跑 `quality_check.py`（py_compile+导入）。
2. 前端改动 → `node --check` 各 `.js` + `check_js_modules.py`。
3. 涉及能力开关 → 先对照 `03-capabilities-and-toolsets.md`，确认不违 §1 红线（尤其 R4/R5/R6）。
4. 升级 hermes-agent → `check_api_signature.py` 比对基线，有漂移先更新本文档与基线。
5. 打包 → `release_gate.py`（quality→endpoints→smoke）；启动 EXE 验证业务端点。
6. 提交前 → `check_skill_gate.py` 总闸 + 确认无机器路径/兄弟技能名/外部项目名残留（R12）。
