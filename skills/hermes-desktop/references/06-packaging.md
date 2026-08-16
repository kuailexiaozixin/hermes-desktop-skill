# 06 · 打包与一键启动（PyInstaller 单文件 EXE + 启动.bat）

> 本文针对 **进程内 Library 路线**的打包与一键启动交付。所有 hidden-import 与陷阱均经 0.19.0
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

> ⛔ **禁止** `--collect-submodules tools` / `--collect-submodules agent`：会把全部子模块（含重型
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
- ⛔ **禁止 UTF-8（无 BOM）**：cmd 按 GBK 逐字节解析 .bat，UTF-8 中文在 `if ( ... )` 括号块内会乱码、
  破坏命令解析 → **双击闪退 / 无法启动**（高频坑，务必先查编码）。
- ⛔ **禁止 `chcp 65001`**：它把输出切到 UTF-8，与 GBK 编码的 bat 冲突，反致乱码；仅 UTF-8 bat 才需要它，而 UTF-8 bat 本身就不该用。
- 尽量精简（目标 ≤10 行核心），只定位 + 派发。
- 路径一律带引号：`cd /d "%~dp0"`、`"%PYEXE%" app.py`（防空格/中文路径）。
- 关键命令后 `if errorlevel 1 pause`，报错不闪退、可读错误。

### 3.3 venv 位置规范

- ⛔ **禁止在 examples / 项目目录内建 `.venv` 或 `venv`**（污染示例、体积大、易被误提交）。
- **全局 venv**：`%LOCALAPPDATA%\hermes-desktop\venvs\<name>\`，每个示例一个命名 venv（如
  `hermes-desktop-01`、`hermes-desktop-02`），互不干扰（版本互斥场景见 §5）。

### 3.4 创建模板

**源码直跑形态（如 examples/02）**：

```bat
@echo off
cd /d "%~dp0"
set PYTHONHOME=
title <应用名>
set VENV=%LOCALAPPDATA%\hermes-desktop\venvs\<name>
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

**打包 EXE 形态（如 examples/01）**：

```bat
@echo off
cd /d "%~dp0"
set PYTHONHOME=
set HERMES_DESKTOP_REEXEC=1
"%LOCALAPPDATA%\hermes-desktop\venvs\<name>\Scripts\python.exe" launcher.py
if errorlevel 1 pause
```

决策（依赖预检、选 EXE/解释器）全部在 `launcher.py`，bat 仅派发。

### 3.5 launcher.py 决策

- **`launcher.py`**：做决策（解析 `requirements.txt` 做预检，不写死模块名；选解释器/EXE）。
- examples 禁止写死解释器路径、禁止在目录内建 `.venv`、禁止降级全局包。
- ⛔ **禁止 `os.execv` 重入**：Windows CRT 不加引号，空格路径会崩。用
  `subprocess.call([...])` + `sys.exit(...)` 代替。

---

## 4. 冻结三坑（必读）

1. **`HERMES_HOME` 不可重定向**：冻结态恒为 `<exe>/hermes_data`（见 `05` §3）。启动器不得设
   自定义 HOME 覆盖它。
2. **Node/browser**：browser 工具需 Node；冻结环境要把托管 Node 一并分发，或启动自检提示缺失。
3. **动态导入/插件**：任何 `importlib.import_module` 动态加载的技能/MCP 模块，必须在 hidden-import
   或 `datas` 中显式包含，否则运行时 `ModuleNotFoundError`。

---

## 5. 版本互斥 venv（isolated_venv）

当应用依赖与 `hermes-agent` 对某包版本冲突时，**不要降级全局包**，也不要在本应用目录内建 venv：
用目录外隔离 venv：

```
%LOCALAPPDATA%/hermes-desktop/venvs/<name>/     # --system-site-packages + 重入
```

这样冲突包各居其位，互不污染；重入逻辑在 `launcher.py` 中处理。

---

## 6. 发版门禁

打包后**必须**启动 EXE 并验证业务健康端点（`scripts/check_endpoints.py` / `smoke_test_web.py`），
**防止 HTTP 200 假绿**（服务起了但业务路由挂了）。完整门禁见 `07` §2。一键启动脚本的完整
可启动验证见 §7。

---

## 7. 确保启动的验证流程（核心）

> 写好的 bat **必须逐项验证**，不能只看"能运行"。因受环境限制无法直接运行 `.cmd/.bat` 时，
> 用手动等价步骤逐步验证；有终端权限时直接双击验证。通过判据如下：

### 步骤 1 · venv 与依赖
```bash
python -m venv "%LOCALAPPDATA%\hermes-desktop\venvs\<name>"      # 模拟首次创建
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

---

## 8. 常见失败与诊断表

| 现象 | 根因 | 修复 |
| --- | --- | --- |
| 双击闪退 / 中文乱码 / 命令不执行 | bat 编码非 GBK（UTF-8）或含 `chcp 65001` | 用 **GBK + CRLF** 重写，去掉 `chcp 65001` |
| 黑窗一闪即关 | `python` 不在 PATH / venv 未建 / 依赖未装 | 先 `where python`；补 `pause` 看报错 |
| `ModuleNotFoundError` | 依赖未装或 requirements 不完整 | 重跑安装；核对应用实际 import |
| 端口占用 | `<port>` 被其他进程占用 | `netstat -ano | grep <port>` 定位并释放 |
| 打开浏览器而非窗口 | pywebview 未装 / 后端缺失 | 确认 venv 内 `pywebview` 已装 |
