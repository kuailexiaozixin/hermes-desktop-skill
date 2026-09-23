# 05 · 安装与环境（HERMES_HOME 唯一真相）

> 环境根目录的**唯一真相源是 `hermes_constants`**。本文所有路径 API 均经 0.19.0 内省核实。

---

## 1. 安装

**Python 版本是硬约束，不是建议**：wheel 元数据 `Requires-Python: <3.14,>=3.11`（`hermes_agent-0.19.0.dist-info/METADATA:7` 实测）。
3.10 与 3.14 都会被 pip 直接拒装、不会退化成警告，报错原文含 `requires a different Python`
（pip 源码两条消息：`pip/_internal/resolution/legacy/resolver.py:106` 的
`Package '<name>' requires a different Python: <版本> not in '<3.14,>=3.11>'`，与
`pip/_internal/index/package_finder.py:91` 的 `Link requires a different Python (...)`）。

```bash
python -m venv venv
venv\Scripts\python -m pip install -U pip
venv\Scripts\python -m pip install "hermes-agent[web]==0.19.0"
```

- 包名是连字符 `hermes-agent`，导入符号是 `run_agent.AIAgent`。PyPI 上另有一个无关的 `hermes` 包（科研元数据工具），装错会命令冲突。
- **extras 共 42 个**（同一 METADATA 的 `Provides-Extra` 计数），绝大多数是供应商或平台专用
  （`anthropic` `mcp` `slack` `feishu` `voice` `computer-use` `bedrock` …），按实际用到的加。
  `[all]` 不要一并带上：它是 10 个自引用子 extra 的并集（`hermes-agent[cron]`/`[cli]`/`[pty]`/`[mcp]`/`[homeassistant]`/`[sms]`/`[acp]`/`[google]` 等），极重。
- **`[web]` 里到底有什么**：只有 `fastapi==0.133.1`、`uvicorn[standard]==0.41.0`、`starlette==1.0.1`、
  `python-multipart==0.0.27` 四项，而这四项本就在核心依赖里（核心给的是范围，如 `fastapi<1,>=0.104.0`），
  `[web]` 只是把它们钉成精确版本。**FastHTML 不在任何 extra 里**，走 FastHTML 路线要自己声明 `python-fasthtml`；
  `jinja2` 同理是核心依赖，与 `[web]` 无关。
- **extras 按路线选，不要顺手 `[all]`**：上两条已说清 `[web]` 的真实作用是钉版不是增能、FastHTML 要自己声明
  `python-fasthtml`；Tkinter / PyQt / textual / Electron 等原生或本地桥接路线用基础包即可。
  **最小依赖是打包能瘦身的前提**：多装一件就在 `--onefile` 制品里多占一份体积，打包侧对应的规矩见 `06` §1。
- 装完是 23 个顶层模块平铺进 site-packages（`run_agent`、`agent`、`tools`、`toolsets`、`gateway`、`hermes_cli` …），
  没有统一命名空间包，因此导入写 `from run_agent import AIAgent` 而不是 `from hermes_agent import ...`；模块全清单见 `14`。
- 校验：`venv/Scripts/python -c "import importlib.metadata as m; print(m.version('hermes-agent'))"`
  应输出 `0.19.0`。

---

## 2. 环境根目录：`HERMES_HOME`

`HERMES_HOME` 是 Hermes 所有运行时数据（会话、记忆、技能、配置、缓存）的根。**不要手写路径常量**——
一律走 `hermes_constants`：

| 函数 | 返回 | 用途 |
| --- | --- | --- |
| `get_hermes_home()` | `Path` | 数据根。解析顺序：上下文覆盖 → `HERMES_HOME` → 平台默认；平台默认在 Windows 是 `%LOCALAPPDATA%\hermes`，在 POSIX 才是 `~/.hermes`（源码 `_get_platform_default_hermes_home` 实测） |
| `get_hermes_home_override()` | `str \| None` | 当前上下文覆盖值 |
| `set_hermes_home_override(path)` | `Token` | **运行时覆盖**（返回 contextvars token，可还原） |
| `reset_hermes_home_override(token)` | `None` | 还原覆盖 |
| `display_hermes_home()` | `str` | 给人看的根目录串 |
| `get_default_hermes_root()` | `Path` | 默认根（未覆盖时） |
| `get_config_path()` | `Path` | `config.yaml` 路径 |
| `get_hermes_dir(new_subpath, old_name)` | `Path` | 子目录解析（兼容旧名） |
| `get_real_home(env=None)` | `str` | 真实用户主目录（考虑子进程环境） |
| `get_subprocess_home(env=None)` / `apply_subprocess_home_env(env)` | `str` / `None` | 子进程继承的 HOME |
| `get_env_path()` | `Path` | env 文件位置 |
| `get_skills_dir()` | `Path` | 用户技能目录 |
| `get_optional_skills_dir(default=None)` | `Path` | 可选技能目录 |
| `get_optional_mcps_dir(default=None)` | `Path` | 可选 MCP 目录 |
| `get_bundled_skills_dir(default=None)` | `Path` | 内置技能目录 |
| `find_node_executable(command)` | `str \| None` | 找 Node（browser 工具需要） |
| `heal_hermes_managed_node()` | `bool` | 修复 Hermes 托管 Node |

> 读取/设置数据位置**只许用上述 API**。直接拼 `~/.hermes` 字符串会在非默认配置下出错。

---

## 3. 冻结（打包 EXE）后的数据根：谁钉的、能不能改

**先破一句误传**：`hermes-agent` 对"冻结"毫不知情。实测 `hermes_constants.py`、`run_agent.py`、`agent/`、
`hermes_cli/` 四处共 364 个 `.py`，`sys.frozen`、`_MEIPASS`、`hermes_data` 三个词命中 **0 次**。
所以库既不会把数据根挪到 EXE 同目录，也谈不上"不可重定向"——§2 那行的解析顺序
（上下文覆盖 → `HERMES_HOME` → 平台默认）在冻结态一字不变地生效。两条真实约束由此推出：

1. **没人钉根，数据就不在制品目录**：EXE 启动器什么都不设时，根取平台默认
   （Windows `%LOCALAPPDATA%\hermes`、POSIX `~/.hermes`）。"删了 EXE 数据还在""同机两个应用共用一棵根"
   都是这个默认造成的。根**必须由启动器显式钉住**，库不会替你钉。
2. **按 `_MEIPASS` 或 `__file__` 相对算根会丢数据**：onefile 解包的临时目录退出即删。
   正确算法是 `Path(sys.executable).parent`（EXE 摆放处）——它在包外、可写、持久。

- 出厂数据（`.hermes_data` 内的默认配置/技能）**冻结态只读**；运行时变更写入同一目录。
- 触碰出厂数据前必须**备份 → 变更 → 还原 → md5 校验**（见 `07` §3 运行数据保护）。
- 不杀用户正在运行的 EXE。

参考实现的钉根写法（`examples/01-hermes-desktop/Agent系统` 的 `main.py:6-10`、`server.py:23-28`、
`launcher.py:168-173`、`routes/__init__.py:53-58` 四处，全部在任何 hermes 导入之前）：

```python
if getattr(sys, "frozen", False):
    os.environ.setdefault(                    # setdefault 而非赋值：外层先设则让位
        "HERMES_HOME",
        os.path.join(os.path.dirname(sys.executable), "hermes_data"),
    )
```

`setdefault` 的含义是"约定但可让位"：外层（`启动.bat`、服务包装器、多租户脚本）先设了 `HERMES_HOME`，
就以外部为准。因此「桌面单目录交付把根钉在 `<exe>/hermes_data`」是**产品决策**（随制品一起卸载、
不污染用户配置目录），不是库的限制。要把根指到数据盘，先设环境变量或走 §2 的覆盖 API 都有效
（服务端取舍见 `06` §9.1）。核对实际生效的根只用 API，别自己拼路径：
`python -c "import hermes_constants as hc; print(hc.get_hermes_home())"`。

---

## 4. Node 与浏览器工具

`browser` 工具集（13 个工具）依赖一个 Node 运行时。`hermes_constants.find_node_executable()`
会自动探测 Hermes 托管 Node；缺失时 browser 工具不可用但**不应崩溃**——用 `heal_hermes_managed_node()`
尝试修复。桌面应用若启用浏览器能力，启动自检应确认 Node 可用（见 `01` §7、`07` §3 自检）。

---

## 5. 凭证

- `api_key` / `base_url` 可构造时传入，也可走默认凭证源（环境变量 `HERMES_API_KEY`、`OPENAI_API_KEY` 等）。
- 多供应商/多 Profile 切换：`AIAgent.switch_model(...)` 运行时换；持久 Profile 由 `hermes_cli.profiles` 管理
  （进程内路线一般只用 `switch_model`，不依赖 CLI）。
- 不要在技能文件里硬编码密钥；密钥来自用户配置或环境变量。

---

## 6. 典型布局（进程内桌面应用）

```
<app>/
├── app.exe                # 打包产物（冻结态）
├── hermes_data/           # HERMES_HOME（启动器钉住的数据根，见 §3）
│   ├── config.yaml
│   ├── skills/
│   ├── memory/
│   └── sessions/
├── venv/                  # 开发期虚拟环境（仅开发用）
└── requirements.txt       # 实际依赖清单（解析用，不固定版本号）
```
