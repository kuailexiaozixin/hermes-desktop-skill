# 打包 — 示例落地细节（from examples/01-hermes-desktop，已实测）

> 本文件从 `references/06-packaging.md` 抽出：该旗舰示例对打包铁律的具体落地（build 三件套、冻结 onefile 专属坑的「示例已做」文件/行号、版本互斥的示例约束）。
> 属示例耦合内容，不进入技能核心骨干（通用打包铁律/坑/体积/venv 隔离见 `references/06-packaging.md` §1/§3/§4/§5/§6 现象-后果-规避原理/§7 原则）。

---

## §2 示例打包三件套（build.py / launcher.py / 启动.bat）

旗舰示例已落地完整、可复用的打包三件套（`examples/01-hermes-desktop/`）：

| 文件 | 作用 |
| --- | --- |
| `build.py` | PyInstaller 单文件配方。**自动建外置隔离 venv + 装依赖 + 重入打包**；`--windowed` 出发布版。 |
| `launcher.py` | 自包含桌面壳（pywebview），拉起 FastHTML 服务 + 打开窗口；是打包入口（`ENTRY="launcher.py"`）。**不依赖任何其它技能**。 |
| `启动.bat` | GBK+CRLF 派发脚本，`python launcher.py`；双击即用。 |

直接复用：复制 `examples/01-hermes-desktop/` 到你的工程后，`python build.py` 即可产出 `dist/HermesDesktop.exe`。
若你已有自己的最小 venv，可 `python build.py --skip-venv` 直接打包。

## §6 冻结 onefile 专属坑的「示例已做」落地

> 进程内路线（`from run_agent import AIAgent`，不走 gateway、不走 `/v1`）冻结成 onefile EXE 时，有三条**官方文档完全没有、本技能旗舰示例已实测并规避**的坑。照搬「普通 Python 包 + PyInstaller」的思路必踩。
> 旗舰示例 `examples/01-hermes-desktop` 已逐条落地规避（见下方各条「示例已做」）。若你**从零自建**进程内应用，须显式复刻这些兜底——否则静默降级、不报任何错。

### 6.1 内置 toolset 枚举 `glob("*.py")` 在冻结后落空 → 绝大多数工具集不注册
- **规避（示例已做）**：调用 `discover_builtin_tools()` 之后，用 `pkgutil.iter_modules(tools.__path__)` 枚举已冻结、可 import 的 `tools.*` 子模块并逐一 `import_module`（导入即 self-register），**不要依赖文件系统 glob**。见 `examples/01-hermes-desktop/agent_runtime.py:162` 的 `if getattr(sys, "frozen", False):` 冻结兜底分支。

### 6.2 pip entry-point 插件元数据丢失 → 「插件」面板显示 0
- **规避（示例已做）**：冻结态把出厂内置插件目录拷进 `<exe>/plugins`（或设 `HERMES_PLUGINS_DIR` 指向 `_MEIPASS/plugins`），走**目录扫描**而非 entry points。见 `examples/01-hermes-desktop/hermes_config.py:1027`（`接通原生 bundled 插件目录（冻结态 _MEIPASS/plugins）`）与 `main.py:1835`（`/api/plugins` 用 `pkgutil.walk_packages` 枚举，对冻结态同样有效）。

### 6.3 网关原生审批在进程内不生效 → 需自建审批闭环
- **规避（示例已做）**：自建标记 + 前端闭环——命令类工具输出带 `[APPROVAL_REQUIRED: cmd]` 标记，前端拦截该标记、弹确认、用户同意后回灌执行。见 `examples/01-hermes-desktop/agent_runtime.py:1579`（`审批闭环：Agent 在回答里写 [...] 即触发前端弹窗`）。

## §7 版本互斥的示例约束

- 示例**禁止**在目录内建 `.venv`、禁止把 `C:\Users\xxx\...` 绝对路径写进启动脚本
  （跨机器无法复现）。启动器一律用 `venv_name` 去 `FD_VENV_HOME` 下解析，跨机器可迁移。
- 未实测不得宣称「双击即运行」——必须在目标干净机器上真跑一次 `build.py` + 启动 EXE 验证。
