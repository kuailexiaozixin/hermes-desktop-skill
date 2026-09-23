# 06 · 交付：单文件 EXE 的打包与一键启动，或常驻服务的部署与回滚

> 本文覆盖两种交付形态的**产出、启动与验证**：**冻结单文件**（路线①，以及自建薄层的路线⑤ → §1–§8）与
> **常驻服务 / sidecar**（路线②③，与选方式 A 的路线④ → §9）。所有 hidden-import 与陷阱均经 0.19.0
> 实测/技能门禁脚本约束。一键启动脚本的创建与确保启动流程见 §3、§7、§8。

---

## 1. 总体策略（最小 venv → 单文件）

1. **最小 venv**：仅装 `hermes-agent[web]` + 应用真实依赖；不要混入无关大型包。
2. 在该 venv 内跑 PyInstaller（避免全局包被一起打进 EXE）。
3. 用 `--onefile`（**禁用 `--onedir`**）、`console=True`、`--noupx`。
4. 构建超时设 ≥ 600s（或后台运行）；Library 较大，冷构建慢。

```bash
venv\Scripts\pyinstaller hermes_desktop_launcher.spec
# 或命令行等价：
venv\Scripts\python -m PyInstaller ^
  --onefile --console --noupx ^
  --name hermes-desktop ^
  --hidden-import run_agent ^
  --hidden-import hermes_constants ^
  --hidden-import gateway ^
  launcher.py
```

---

## 2. Hidden-import 清单（逐个显式，禁 --collect-submodules tools）

`run_agent` 在运行时**懒加载** `tools/*` 与 `agent/*` 子模块，PyInstaller 的静态分析抓不到，
必须**逐个 `--hidden-import`**。扫一遍 `site-packages/tools/` 与 `site-packages/agent/` 的 `.py`
模块名，逐条列出：

- 核心：`run_agent`、`hermes_constants`、`hermes_state`、`hermes_logging`、`hermes_time`、
  `hermes_bootstrap`、`toolsets`、`gateway`
- `tools.*`：把 `site-packages/tools/` 下每个模块都加（如 `tools.file_tools`、`tools.browser_tool`、
  `tools.terminal_tool`、`tools.kanban_tools`、`tools.memory_tool`、`tools.skills_tool`、
  `tools.mcp_tool`、`tools.vision_tools`、`tools.image_generation_tool`、`tools.tts_tool`、
  `tools.code_execution_tool`、`tools.computer_use_tool`、`tools.cronjob_tools` …）。
- `agent.*`：同理加 `agent.agent_init`、`agent.tool_executor`、`agent.context_engine`、
  `agent.moa_loop`、`agent.memory_manager`、`agent.memory_provider`、`agent.tool_guardrails`、
  `agent.credential_pool` … 等运行时会用到的。

> **禁止** `--collect-submodules tools` / `--collect-submodules agent`：会把全部子模块（含重型
> 可选依赖）全打进 EXE，极易 OOM 或体积爆炸。函数内懒加载的模块也须显式 `--hidden-import`。

`pywebview` 额外：加 `clr` + `webview.platforms.winforms` + `webview.platforms.edgechromium`，
并把 `webview/lib` 目录随包分发（用 `datas` 或 `binaries`）。

---

## 3. 一键启动脚本（bat 只派发 + launcher.py 决策）

### 3.1 定位与两种形态

**一键启动脚本** = 用户双击即可运行应用，无需打开终端、无需手动配置环境。常见两种形态：

| 形态 | 脚本职责 | 示例 |
| --- | --- | --- |
| A. 源码直跑 | 定位 venv 的 python → 运行 `app.py` | `examples/02-hermes-pywebview-multiagent` |
| B. 打包 EXE | 定位并派发 EXE / venv → 决策交给 `launcher.py` | `examples/01-hermes-desktop` 产线 |

> 铁律：**bat 只做「定位 + 派发」，不写业务逻辑**。复杂决策（预检依赖、选解释器、首次安装）放
> `launcher.py`。

### 3.2 bat 文件铁律（Windows）

- **编码 = GBK**（中文 Windows cmd 默认 ANSI 代码页即为 GBK）；**行尾 = CRLF**。
- **禁止** UTF-8（无 BOM）：cmd 按 GBK 逐字节解析 .bat，UTF-8 中文在 `if ( ... )` 括号块内会乱码、
  破坏命令解析 → **双击闪退 / 无法启动**（高频坑，务必先查编码）。
- **禁止** `chcp 65001`：它把输出切到 UTF-8，与 GBK 编码的 bat 冲突，反致乱码；仅 UTF-8 bat 才需要它，而 UTF-8 bat 本身就不该用。
- 尽量精简（目标 ≤10 行核心），只定位 + 派发。
- 路径一律带引号：`cd /d "%~dp0"`、`"%PYEXE%" app.py`（防空格/中文路径）。
- 关键命令后 `if errorlevel 1 pause`，报错不闪退、可读错误。

### 3.3 venv 位置规范

- **禁止在 examples / 项目目录内建 `.venv` 或 `venv`**（污染示例、体积大、易被误提交）。
- **全局 venv**：`%LOCALAPPDATA%\hermes-business-agent\venvs\<name>\`，一个应用一个叶子目录，互不干扰
  （叶子名由应用自己取，如 `hermes-desktop-01`；它与本技能的上级目录名无关。版本互斥场景见 §5）。

### 3.4 创建模板

**源码直跑形态（如 examples/02-hermes-pywebview-multiagent）**：

```bat
@echo off
cd /d "%~dp0"
set PYTHONHOME=
title <应用名>
set VENV=%LOCALAPPDATA%\hermes-business-agent\venvs\<name>
set PYEXE=%VENV%\Scripts\python.exe

if not exist "%PYEXE%" (
    echo [首次运行] 创建全局虚拟环境 <name> ...
    python -m venv "%VENV%"
    "%PYEXE%" -m pip install --upgrade pip -q
    "%PYEXE%" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 ( echo [错误] 依赖安装失败，请检查网络。 & pause & exit /b 1 )
)

echo [启动] python app.py ...
"%PYEXE%" app.py
if errorlevel 1 pause
```

配套：目录下提供 `requirements.txt`（固定运行依赖），供首次安装与 launcher 预检。

**打包 EXE 形态（如 examples/01-hermes-desktop）**：

```bat
@echo off
cd /d "%~dp0"
set PYTHONHOME=
set HERMES_DESKTOP_REEXEC=1
"%LOCALAPPDATA%\hermes-business-agent\venvs\<name>\Scripts\python.exe" launcher.py
if errorlevel 1 pause
```

决策（依赖预检、选 EXE/解释器）全部在 `launcher.py`，bat 仅派发。

### 3.5 launcher.py 决策

- **`launcher.py`**：做决策（解析 `requirements.txt` 做预检，不写死模块名；选解释器/EXE）。
- examples 禁止写死解释器路径、禁止在目录内建 `.venv`、禁止降级全局包。
- **禁止** `os.execv` 重入：Windows CRT 不加引号，空格路径会崩。用
  `subprocess.call([...])` + `sys.exit(...)` 代替。

---

## 4. 冻结三坑（必读）

1. **数据根没人替你钉**：库不感知 `sys.frozen`，启动器不设 `HERMES_HOME` 就退回平台默认根
   （Windows `%LOCALAPPDATA%\hermes`），数据脱离制品目录。必须在任何 hermes 导入之前把根钉到
   `Path(sys.executable).parent / "hermes_data"`，且用 `setdefault` 以便外层包装器覆盖（写法见 `05` §3）。
   **禁止**按 `_MEIPASS` / `__file__` 相对算根——onefile 解包目录退出即删，用户数据随之丢失。
2. **Node/browser**：browser 工具需 Node；冻结环境要把托管 Node 一并分发，或启动自检提示缺失。
3. **动态导入/插件**：任何 `importlib.import_module` 动态加载的技能/MCP 模块，必须在 hidden-import
   或 `datas` 中显式包含，否则运行时 `ModuleNotFoundError`。

---

## 5. 版本互斥 venv（isolated_venv）

当应用依赖与 `hermes-agent` 对某包版本冲突时，**不要降级全局包**，也不要在本应用目录内建 venv：
用目录外隔离 venv：

```
%LOCALAPPDATA%/hermes-business-agent/venvs/<name>/     # --system-site-packages + 重入
```

这样冲突包各居其位，互不污染；重入逻辑在 `launcher.py` 中处理。

---

## 6. 发版门禁

打包后**必须**启动 EXE 并验证业务健康端点（`scripts/check_endpoints.py` / `smoke_test_web.py`），
**防止 HTTP 200 假绿**（服务起了但业务路由挂了）。完整门禁见 `07` §2。一键启动脚本的完整
可启动验证见 §7，其**步骤 1–3 已可执行化**：

```bash
python scripts/release_gate.py --verify-launch \
  --launch-root <交付目录> --launch-python <该目录用的 python> \
  --launch-port <端口> --health-path /healthz --expect "<页面标志文本>"
```

它按 §7 的判据真起进程、等端口、探健康端点与首页，跑完自动终止进程树并确认端口释放；
`--expect` 是防假绿的关键一档（只验 200 会把"起错了服务"也判过）。步骤 4 的"窗口真打开"不在此列，
仍需人工或 `scripts/ui_window_verify.py` 确认。

---

## 7. 确保启动的验证流程（核心）

> 写好的 bat **必须逐项验证**，不能只看"能运行"。因受环境限制无法直接运行 `.cmd/.bat` 时，
> 用手动等价步骤逐步验证；有终端权限时直接双击验证。通过判据如下
> （步骤 1–3 可用 `release_gate.py --verify-launch` 代跑，见 §6；下面是判据本身，人工核对时同样照单走）：

### 步骤 1 · venv 与依赖
```bash
python -m venv "%LOCALAPPDATA%\hermes-business-agent\venvs\<name>"      # 模拟首次创建
"%PYEXE%" -m pip install -r "%~dp0requirements.txt"              # 安装依赖，退出码 0
"%PYEXE%" -c "import <app依赖模块>"                               # 关键导入可解析
```
判据：安装退出码 0；应用所有顶层 `import` 均能解析（无 ModuleNotFoundError）。

### 步骤 2 · 启动应用（后台）
```bash
cd "<项目目录>" && "%PYEXE%" app.py &                            # 后台运行，重定向日志
```
判据：无 traceback；日志出现 "listening on http://127.0.0.1:<port>" 或等价的启动完成行。

### 步骤 3 · 端口与健康端点
```bash
netstat -ano | grep <port> | grep LISTENING                      # 端口在监听
curl -s http://127.0.0.1:<port>/health                          # 健康端点 200
```
判据：端口 LISTENING；`/health`（或等价端点）返回 200。

### 步骤 4 · 前端 / 窗口
```bash
curl -s http://127.0.0.1:<port>/ | grep <页面标志文本>           # 首页 200 且加载
```
判据：首页 200、含关键内容；桌面窗口打开（或按设计回退浏览器）。

### 收尾
- 验证后必须终止测试进程、释放端口（`netstat` 定位 PID → `taskkill //F //PID <pid> //T`）。
- 记录验证结果；若因环境无法跑 .bat 本体，明确说明"已用等价步骤验证，请用户双击最终确认"。
- **四步全绿只到"起得来"这一格**：它们不含任何业务动作，看不见 hidden-import 之外的功能缺失、范围错乱与写面没回读。
  "在制品上把本期验收表覆盖到的用例重跑一遍、且在隔离环境里跑"归 SKILL.md 第 ⑧ 步的验收前置事项，本节不重复一遍。

---

## 8. 常见失败与诊断表

| 现象 | 根因 | 修复 |
| --- | --- | --- |
| 双击闪退 / 中文乱码 / 命令不执行 | bat 编码非 GBK（UTF-8）或含 `chcp 65001` | 用 **GBK + CRLF** 重写，去掉 `chcp 65001` |
| 黑窗一闪即关 | `python` 不在 PATH / venv 未建 / 依赖未装 | 先 `where python`；补 `pause` 看报错 |
| `ModuleNotFoundError` | 依赖未装或 requirements 不完整 | 重跑安装；核对应用实际 import |
| 端口占用 | `<port>` 被其他进程占用 | `netstat -ano | grep <port>` 定位并释放 |
| 打开浏览器而非窗口 | pywebview 未装 / 后端缺失 | 确认 venv 内 `pywebview` 已装 |

---

## 9. 常驻服务 / sidecar 交付（路线②③④）

> 何时读本节：第 ② 步选了网关 / spawn CLI / API Server 方式 A，或交付物是「主程序 + 服务依赖」而非单个 EXE。
> 走路线① 与⑤（单进程随 EXE）的，§1–§8 就是全部，本节可跳过。
> 机制与端点事实归 `15`（API Server）与 `16`（网关包）；本节只管**部署之后**的四件事：起得来、看得见、升得上、退得回。

### 9.1 服务端不要走冻结产物

桌面交付那套「根钉在制品目录」的约定（成因见 `05` §3）搬到服务器上是反效果：多 profile / 多租户
各自一棵数据子树做不了（`00-index` §4：并发约束是「勿让两进程指向同一数据目录」），
日志与备份也全部落在制品目录里。服务端因此按**源码 + 专用 venv**常驻运行，
`HERMES_HOME` 用 `hermes_constants` 的覆盖 API 指到数据盘上的独立目录（禁止手拼 `~/.hermes` 字符串）。
只有「办公室机器上双击装一个本地服务」这种形态才值得打包成 EXE 当 sidecar。

### 9.2 部署形态三选

| 形态 | 进程 | 适用 | 守护责任 |
| --- | --- | --- | --- |
| 本机 sidecar | 随主程序起，绑 `127.0.0.1` | 单用户、不愿装服务，路线③ 或④ 方式 B | 主程序负责起停与崩溃重启（与 GUI 同生共死） |
| 内网常驻服务 | 独立进程，多客户端连 | 小团队共享一个业务 Agent | 部署层（下节） |
| 容器 / Managed Mode | 镜像内不可变核心 + 外挂数据卷 | 需编排、需扩缩、terminal 必须沙箱 | 编排器；`hermes-llms-full.txt` 的 `Managed Mode` / `Docker` 章节为权威（检索地图 `00-index` §1.1） |

三者的**不变项**：`HERMES_HOME` 落在可备份的位置；凭证只走环境变量或 `$HERMES_HOME/.env`；健康端点可探；
数据目录与制品目录分离（升级换制品、数据不动）。

### 9.3 进程守护：`hermes gateway` 是前台进程，守护层必须外置

`15` §3 的启动方式（`hermes gateway`）以前台进程运行，缺失依赖时往日志里报（例如 `API Server: aiohttp not installed`
并**不启动该 adapter**）——这决定了交付时必须补三件：

1. **守护**：Windows 用服务包装器（WinSW / NSSM）或任务计划程序「开机启动 + 失败重启」；Linux 用 systemd unit
   （`Restart=always`、`EnvironmentFile` 指向该 profile 的 `.env`）。禁止把「双击 bat」当服务部署形态——用户注销即进程消失。
2. **首启预检**：守护拉起前先跑 `runtime_ready()` 型自检（`07` §3）+ `python scripts/probe_library.py`，
   并断言本路线的真实依赖（方式 A 必查 aiohttp 已装、key 长度 ≥16；`15` §3 的三条实测依赖）。预检失败**不要静默重试**，
   让它带着原因退出，日志首行可读。
3. **就绪探针**：`/health`（存活）与 `/health/detailed`（就绪：config/state/model/disk/网关平台/活跃 run，`15` §4）
   分开设——前者只证明端口在，后者才证明业务可用。守护层用后者决定「重启还是继续等」。

### 9.4 日志与观测落点

- Hermes 侧日志（网关 / adapter 启动与错误）与 `hermes_logging` 输出 → 重定向到**文件**，禁止只留在控制台；
  按天或按大小轮转，保留期与业务审计要求对齐。
- 业务侧指标（每次会话一行 + 工具调用子表）另存一张表，字段清单见 `21` §2.1，禁止把 Hermes 会话库当业务数仓查（`21` §2.2）。
- 一条硬要求：**服务重启后，日志里能拼出「哪个会话在何时中断」**——常驻服务的用户不记得你重启过，
  只有日志记得。做不到这一点，`21` §7 的线上归因回路在服务端形态下是断的。
- 禁止日志里出现明文 key、provider 凭据、未脱敏业务快照（`21` §2.3）。

### 9.5 配置与密钥

`15` §3 的方式：`hermes config set API_SERVER_KEY …` 落 `$HERMES_HOME/.env`。服务端额外两条：

- 每个 profile 一份 `.env`（`hermes -p <name> gateway` 各自独立端口与 key，`15` §3 多用户隔离），禁止多 profile 共用一个 key。
- `.env` **不进制品、不进仓库**：升级会整目录换，配置与密钥必须在制品之外；权限收紧到服务账号可读。

### 9.6 滚动升级与回滚（顺序不可换）

Hermes 发版频繁，服务端形态下「升级」是常规动作而不是例外，所以必须一开始就设计成可回退：

1. 先跑漂移核查（SKILL.md〔入场检查〕：`check_api_signature.py` 是硬条件，`track_upstream.py` **不带 `--gate`** 才有判定力——带 `--gate` 时它对四条漂移线恒返回 0，退出码语义见 `07` §2），确认新版本没把回调签名改掉；
2. **备份数据**：`HERMES_HOME` 整树备份，按 `07` §3 的「备份 → 变更 → 还原 → md5 校验」走完，禁止跳过（R11：那是用户的业务资产与记忆/技能沉淀）；
3. 制品双版本并存（`releases/<ver>/` + 一个当前指向），依赖装在**版本互斥的独立 venv**（§5 的 `isolated_venv`），
   这样回滚只是把指向切回去，不必重装依赖；
4. 起新版实例到**备用端口**，跑 `python scripts/release_gate.py --verify-launch --api-server --api-key <key>`
   （服务没起时该步退出码 2 记 SKIP，起着但断言不过 = 硬失败；`15` §3），再对本路线端点做一轮真实客户端往返；
5. 切流量/改守护配置指向新实例，观察 §9.4 的失败分类日志与 `21` §6 的基线——**观察多久、看哪几条、出现什么信号就回切**，
   判据在 SKILL.md 第 ⑧ 步的观察窗四格（本节只管切法，不重复写阈值）；
6. 回滚 = 切回旧指向 + 必要时还原 §2 的数据备份。**数据回滚与制品回滚要分别能单独执行**——
   多数线上问题出在数据形状，不在代码。

> 禁止原地 `pip install -U hermes-agent` 然后重启生产服务：既没有可回退的制品，也可能踩到未核查的签名漂移
> （漂移的回调会让流式静默不触发，`07` §2 的教训），还极可能把版本互斥依赖装脏。

### 9.7 多客户端与并发（路线②④ 的真实增量工作量）

- **实例不共享**：`AIAgent` 非线程安全、每次对话新建（`15` §0 说明官方 adapter 即「每请求建一个 `AIAgent`」）；
  自建薄层同样按请求新建，禁止复用全局实例省启动开销——那是会话串台 + 计数器错乱（SKILL.md 第 ③ 步铁律在服务端更贵）。
- **并发上限**：`gateway.api_server.max_concurrent_runs` 防请求洪泛（`15` §5）；自建层要自己实现等价限制并返回**确定**的拒绝响应
  （配合 `21` §5 的降级契约，禁止排队到用户以为程序无响应）。
- **会话语义靠头不靠记忆**：延续会话用 `X-Hermes-Session-Id`，跨会话记忆作用域用 `X-Hermes-Session-Key`（`15` §4）；
  客户端传"我是谁、看哪个账套"，**服务端校验后**才生成业务上下文快照（`19` §4 注入位置的强制要求）。
- **数据目录隔离**：多租户 / 多 profile 各自一棵 `HERMES_HOME` 子树，禁止两进程指向同一数据目录（`00-index` §4 并发写约束）。
- **绑定地址与沙箱**：判据、告警来源与收紧手段唯一归 `15` §5（源码级告警 + `terminal.backend`），部署时照它执行，
  本节不重复阈值。

### 9.8 服务端交付的验收（补 §7 四步在服务形态下的缺项）

§7 的四步（依赖 → 启动 → 端口+健康 → 界面）在服务形态下同样走，另外加三条：

1. **重启自恢复**：手动 kill 服务进程，确认守护层拉起且 `/health/detailed` 回到就绪——这条是 `21` §6 列的验收用例，
   也是「常驻」唯一的定义。
2. **升级演练**：在预发环境走完 §9.6 六步一次，并**执行一次回滚**。没演练过回滚的服务端交付不算交付。
3. **多客户端不串**：两个客户端各自带自己的 `X-Hermes-Session-Id` 并发对话，断言历史与范围互不渗入。

### 9.9 反模式（禁止）

- 禁止把桌面交付的「双击 bat + 全局 venv」照搬成服务端部署方式（§9.1、§9.3）。
- 禁止冻结 EXE 上服务器跑：根钉在制品目录，备份、隔离、日志全被制品目录绑死。
- 禁止只探 `/health` 就算"服务正常"（`/health/detailed` 才证明业务就绪）。
- 禁止共享一个 `AIAgent` 实例服务多客户端。
- 禁止绑 `0.0.0.0` 而 `terminal.backend` 仍是 local。
- 禁止升级不备份 `HERMES_HOME`，或制品回滚与数据回滚混成一步做不了。
