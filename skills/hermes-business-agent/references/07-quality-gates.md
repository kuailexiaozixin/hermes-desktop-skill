# 07 · 反模式红线、门禁与工作流

> 本文是 **5 条路线共用**的质量护栏与门禁（进程内直跑 / Hermes 网关 / spawn CLI / API Server / `/v1`，见 `02` §2.1–§2.5）。
> 任何新增能力/改动**先过 §1 红线**，再用 §2 门禁验证。§1 每条红线都标了适用路线；未标即全路线通用。
> 流程主线只有一处：SKILL.md 的工作流（入场检查 + 八步 + 回路）。本文 §4 只做「脚本 ↔ SKILL.md 第 N 步」映射，不另排一遍顺序。

---

## 1. 反模式红线（禁止触线即路线错误）<a id="antipatterns"></a>

> 「适用路线」用 `02` §2.1–§2.5 的编号：① 进程内直跑 / ② Hermes 网关 / ③ spawn CLI / ④ API Server / ⑤ 仅 `/v1`。
> 标「全」的与路线无关；标具体路线的，只在**你选了该路线**时才算违规——选了 ②④ 却去配端口/鉴权是正常做法，不是红线。

| # | 红线 | 适用路线 | 为什么 |
| --- | --- | --- | --- |
| R1 | 起 Hermes **网关** 或 spawn `hermes` **CLI 子进程**（在你选的是进程内形态时） | ① | 路线① 默认不含网关/子进程；选了 ②③④⑤ 则本就如此，不在此列（逐条见 `02` §2.2–§2.5） |
| R2 | 连 `127.0.0.1:8642` / 配 `API_SERVER_KEY` / 配 CORS（在你选的是进程内形态时） | ① | 路线① 默认无网关与公网服务端；放开为 ④/⑤ 时按需启用，且必须启用 |
| R3 | 用 **Node / Electron** 包 Hermes 内核 | ① | 路线① 单文件 Python EXE 不含 Node 运行时（browser 工具的 Node 由 Hermes 托管、非应用层）；Node 只做 UI 壳/桥接（`04` §7–§9） |
| R4 | 硬编码 `enabled_toolsets=["file"]` 之类减法反向写法 | 全（工具面配置所在处） | 会砍掉 browser/记忆/联网等能力，功能退化；坚持 `enabled=None` + `disabled` 减法（见 `01` §3.2）；④/⑤ 由服务端持有时同理，只是配置点换到服务侧 |
| R5 | 启用 `terminal` 工具集却不自建审批（在你选的路线没有网关审批分类器时） | ①③⑤ | 网关的「危险命令审批分类器」无触发源；审批须自建工具层（见 `03` §2、`02` §7.2）；选 ②/④ 时有原生审批（`approvals.mode`、`/v1/runs/{id}/approval`） |
| R6 | 宣称「已支持子代理委派卡片 / delegation 事件」 | 全 | `event_callback` 透传委派**未经实测**；先实测，否则静默不显示（`01` §4.1） |
| R7 | 宣称「真实账单成本」 | ①⑤ | 无网关计费时 `get_credits_*` 为**估算**（见 `01` §5）；②/④ 有网关侧数据可依 |
| R8 | 冻结交付**不显式钉根**，或按 `_MEIPASS`/`__file__` 相对算根 | 冻结交付（①⑤ 打包时） | 库对 `sys.frozen` 零感知（`05` §3 实测 0 命中），不钉就退回平台默认根、数据脱离制品目录；按包内相对算根则退出即删、用户数据丢失。须在导入前 `setdefault` 到 `<exe>/hermes_data` |
| R9 | 用 `--onedir` / `--collect-submodules tools` 打包 | 冻结交付 | 体积爆炸/OOM；必须 `--onefile` + 逐个 hidden-import（`06` §1–2） |
| R10 | 用 `os.execv` 重入解释器 | 冻结交付 | Windows CRT 不加引号，空格路径崩；用 `subprocess.call`+`sys.exit`（`06` §3） |
| R11 | 触碰出厂 `.hermes_data` 不备份 | 全 | 必须 备份→变更→还原→md5 校验；不杀用户运行中的 EXE |
| R12 | 在技能内容文件写机器专属绝对路径 / 兄弟技能名 / 外部业务项目名 | 全 | 自包含铁律：须可单独外发、跨机器复现 |
| R13 | 用 `execute_code`（PTC）把多笔业务写折进一轮，从而**绕掉"每笔写过一次闸门"** | 全（凡开放该工具且有写面者；① 最易犯） | 内核那道护栏是**整段脚本一次批**：`tools.approval.check_execute_code_guard` 自陈 "approval is one-shot for this run"，且其 docstring 记明"纯本地 / 非交互 / 无 TTY / 非 gateway 会话直接返回 approved"——桌面进程内默认正落在这个范围里（实测口径见 `03` §3.4）。它守的是**命令危险性**，不是业务审批：一轮做完 N 件写，人只看到 1 次确认，第 ⑥ 步的逐笔闸门被静默压掉。要折轮次走 `21` §6 的主路子，业务写仍逐笔过闸门 |

---

<a id="gates"></a>
## 2. 门禁脚本（`scripts/`）

> 末列「主线位置」取 SKILL.md 的锚点名：**入场检查**、第 ①–⑧ 步、〔回路〕。流程顺序以 SKILL.md 为唯一主线，本表不另排一遍。

| 脚本 | 作用 | 适用路线 | 主线位置 |
| --- | --- | --- | --- |
| `track_upstream.py` / `probe_library.py` | 上游漂移四线跟踪 / 探测已装 Library（版本、路径、可导入） | 全 | 入场检查；每次升级后 |
| `check_api_signature.py` | 比对 `api-baseline.json`（当前 `baseline_version` 的签名基线）发现 API 漂移 | 全 | 入场检查 |
| `gen_api_reference.py` | 重生成 `references/api-reference/`（升级后） | 全 | 入场检查（升级后） |
| `check_skill_gate.py` | 技能自身结构/引用门禁（关键文件在位 + 文档体积） | 全（改技能时） | ⑧ |
| `quality_check.py` | 6 段一键 Check（py_compile + 技能结构 + 离线桥接 + 签名漂移 + 网页回归 + 文档链接） | 全 | ⑦ |
| `check_golden_coverage.py` | **跑在业务项目上**的对账门：Golden 用例集 ↔ 契约表面表/验收表，12 条硬门禁（回指双向、背书非空、逐工具覆盖、写面回读、弱断言、禁止面未被期望触发、计算题行登记了来源），离线无 Key、不执行用例；用法与它查不到的三件事见脚本首段与 `20` §4.3 | 全（有 Golden 集才跑） | ⑤⑦ |
| `check_doc_links.py` | 文档相对链接完整性（被 quality_check 第 6 段调用） | 全（改文档时） | ⑦ |
| `check_js_modules.py` | 前端 ES 模块完整性 | 有 JS 前端（B 类宿主 / ④⑤ 客户端） | ⑤⑧ |
| `check_endpoints.py` | 前端→后端路由链路校验（捕获运行时 404；递归扫全部 `.py` 含 `routes/` 包） | 有 HTTP 面（路线①⑤ 自建 / ④） | ⑤⑧ |
| `smoke_test_web.py` | 网页无头冒烟（关键 DOM id + `/healthz` 200，无需 Key） | 有 Web UI | ⑦⑧ |
| `ui_window_verify.py` / `ui_automate.py` | 原生窗口视觉质检 / UI 交互自动化（可选） | FastHTML+pywebview | ⑦ |
| `verify_tristructure.py` | 三系统架构验证：6 硬门禁（骨架 / 业务纯净 / 唯一装配点 / 独立入口 / 底座无业务痕迹 / `替换Agent系统.md` 在位）+ 1 软门禁（`agent_zero_diff`，不可判定降级 SKIP；`--strict` 下 SKIP 计失败） | 工程形态（与路线正交） | ⑧ |
| `check_api_server.py` | 路线④/⑤ 条件门禁：`/health` 200 + `/v1/models` Bearer 探测（`15` §3 实测依赖）；服务不可达退出码 2 = 不适用。经 `release_gate.py --api-server` 调用 | ④⑤（选这两条才跑） | ⑧ |
| `release_gate.py` | 发布总闸：6 硬门禁（track_upstream→quality_check→check_endpoints→smoke_test_web→check_js_modules→version 一致性）+ 2 CI 建议项；`--verify-launch` 加跑 `06` §7 四步启动验证（真起进程+探端口+健康端点+首页标志，自动收尾）；`--api-server` 加跑路线④⑤ 探测 | 全 | ⑧ |

<a id="drift"></a>**上游漂移跟踪**：能力/签名漂移由 `check_api_signature.py`（比对 `api-baseline.json`，0.19.0 基线）+ `track_upstream.py`（含第四线：`references/api-reference/` 记录的版本 vs 本地已装，`--regenerate-apiref` 可自动重生成）/ `probe_library.py` 看守；升级 hermes-agent 后先跑 `check_api_signature.py`，有漂移先更新本文档与基线（见 SKILL.md〔入场检查〕）。

**`track_upstream.py` 的退出码语义**（源码 `scripts/track_upstream.py:351-365` 实测）：不带 `--gate` 时四条线任一 DRIFT 即返回 1——包含 ① PyPI 版本线，而基线锁定后上游一发新版它必然报，所以它的 1 只表示「上游发新版了」，不表示本技能失效；带 `--gate`（`release_gate.py` 的 [0] 步用法）时四条线一律只打印提示、恒返回 0。因此「签名漂没漂」的硬阻断点是 `check_api_signature.py`（它同时是 `quality_check.py` 六段之一），不是 `track_upstream --gate`。

**改 .py 门禁**：`py_compile` + 导入测试。**改 .js 门禁**：`node --check`。
**改 .py 后打包门禁**：启动 EXE 验证业务健康端点（`release_gate.py --verify-launch`）。

---

## 3. 运行数据保护与启动自检

- **出厂数据保护**（R11）：`HERMES_HOME` 由启动器钉住（本实现钉在 `<exe>/hermes_data`，`05` §3）；变更前备份，变更后
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
> 反模式 T1–T7）见 `09-integration-e2e.md`。本文只给护栏与门禁，跑通步骤在那篇。

---

## 4. 本文与 SKILL.md 主线的对应（不另排流程）

流程主线只有一处：SKILL.md 工作流主线。本节只回答「护栏在什么时候被触发」，不重排顺序。

| 主线位置 | 触发本护栏的动作 |
| --- | --- |
| 〔入场检查〕 | 漂移四线（§2 前三行脚本）+ `probe_library.py` 与 `HERMES_HOME` 可写核查；有 `REMOVED`/`DEFAULT_CHANGED` 先修技能再开工 |
| 第 ①②⑤⑥ 步 | 每加一个能力/工具开关，先对 §1 红线表（尤其 R4/R5/R6 与各自的「适用路线」列）+ `03` §1–§2 |
| 第 ③④⑦ 步 | Check 段 `quality_check.py`；前端改动加 `node --check` + `check_js_modules.py`；§3 的 `runtime_ready()` 自检 |
| 第 ⑤⑦ 步 | `check_golden_coverage.py` 用例↔契约对账：第 ⑤ 步每加一个工具跑一次（核四件同提交），第 ⑦ 步开跑 Golden 回归前再跑一次（不过就不记通过率） |
| 任一步出口不过 | 进 `17-debug-discipline.md` 闭环（不占步骤），结论落 `docs/troubleshooting.md` |
| 第 ⑧ 步 | `release_gate.py --verify-launch`（`06` §7 四步启动验证）→ 路线④⑤ 再加 `--api-server`（内部调 `check_api_server.py`）→ 三系统形态加 `verify_tristructure.py` → R12 无机器路径复查（`check_skill_gate.py` 已随 `quality_check` 跑过） |

> 改 `hermes-agent` 版本 → 回到〔入场检查〕，本节不另立流程。
